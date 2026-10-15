"""Load Texas UCF fixed-width files into SQLite and search them."""

import re
import sqlite3
from datetime import date

from .layout import NAMES, NR_FLAGS, PROPERTY_ID_FIELDS, RECORD_LENGTH, SLICES
from .property_types import PROPERTY_TYPES

DERIVED = [
    ("owner_last_u", "TEXT"),   # upper-cased, single-spaced, for prefix search
    ("owner_first_u", "TEXT"),
    ("owner_city_u", "TEXT"),
    ("holder_u", "TEXT"),
    ("owner_zip5", "TEXT"),
    ("property_id", "TEXT"),  # HolderIDNumber+year+type+sequence
    ("amount", "REAL"),
    ("shares", "REAL"),
    ("report_date_iso", "TEXT"),
    ("source_file", "TEXT"),
    ("source_line", "INTEGER"),
]

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY,
    {", ".join(f'{n} TEXT' for n in NAMES)},
    {", ".join(f'{n} {t}' for n, t in DERIVED)}
);
CREATE VIRTUAL TABLE IF NOT EXISTS names_fts USING fts5(
    owner, holder, content='', tokenize='unicode61'
);
CREATE TABLE IF NOT EXISTS property_types (
    code TEXT PRIMARY KEY, description TEXT
);
CREATE TABLE IF NOT EXISTS load_log (
    source_file TEXT, loaded_at TEXT, records INTEGER, bad_length INTEGER
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS ix_owner_last ON records(owner_last_u, owner_first_u);
CREATE INDEX IF NOT EXISTS ix_holder ON records(holder_u);
CREATE INDEX IF NOT EXISTS ix_zip ON records(owner_zip5);
CREATE INDEX IF NOT EXISTS ix_type_zip ON records(PropertyTypeCode, owner_zip5);
CREATE INDEX IF NOT EXISTS ix_city ON records(owner_city_u);
CREATE INDEX IF NOT EXISTS ix_property_id ON records(property_id);
"""

_ws = re.compile(r"\s+")


def norm(s):
    return _ws.sub(" ", s).strip().upper()


def with_squashed(s):
    """'H-E-B GROCERY' -> 'H-E-B GROCERY HEB' so HEB and O'BRIEN/OBRIEN both match."""
    extra = [w for w in (re.sub(r"[^\w]", "", t) for t in s.split() if re.search(r"[^\w]", t)) if w]
    return " ".join([s] + extra)


def parse_date(s):
    """Return ISO date for common 10-char formats, else None."""
    s = s.strip()
    if not s:
        return None
    for pat, order in (
        (r"(\d{1,2})/(\d{1,2})/(\d{4})$", "mdy"),
        (r"(\d{4})-(\d{1,2})-(\d{1,2})$", "ymd"),
        (r"(\d{4})(\d{2})(\d{2})$", "ymd"),
        (r"(\d{1,2})-(\d{1,2})-(\d{4})$", "mdy"),
    ):
        m = re.match(pat, s)
        if m:
            a, b, c = (int(x) for x in m.groups())
            y, mo, d = (c, a, b) if order == "mdy" else (a, b, c)
            try:
                return date(y, mo, d).isoformat()
            except ValueError:
                return None
    return None


def parse_number(s, implied_decimals=0):
    """'1,234.56' -> 1234.56; '0000012345' with implied_decimals=2 -> 123.45."""
    s = s.strip().replace(",", "").replace("$", "")
    if not s:
        return None
    neg = s.endswith("-") or s.startswith("-")
    s = s.strip("-+ ")
    try:
        v = float(s) if "." in s else int(s) / (10 ** implied_decimals)
    except ValueError:
        return None
    return -v if neg else v


def parse_record(line):
    """Split one fixed-width record into a dict of stripped raw values."""
    line = line.rstrip("\r\n")
    if len(line) < RECORD_LENGTH:
        line = line.ljust(RECORD_LENGTH)
    return {name: line[a:b].strip() for name, a, b in SLICES}


def iter_records(path, encoding="latin-1"):
    """Yield (line_no, raw_line). Handles newline-delimited files and
    files that are one continuous stream of 500-char records."""
    with open(path, "r", encoding=encoding, newline="") as f:
        head = f.read(RECORD_LENGTH * 4)
        f.seek(0)
        if "\n" in head or "\r" in head:
            for i, line in enumerate(f, 1):
                line = line.rstrip("\r\n")
                if line.strip():
                    yield i, line
        else:
            i = 0
            while True:
                chunk = f.read(RECORD_LENGTH)
                if not chunk:
                    break
                i += 1
                if chunk.strip():
                    yield i, chunk


def connect(db_path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    con.executemany("INSERT OR REPLACE INTO property_types VALUES (?, ?)", PROPERTY_TYPES.items())
    con.commit()
    return con


def load_file(con, path, implied_decimals=2, encoding="latin-1", batch=20000):
    cols = NAMES + [n for n, _ in DERIVED]
    insert = f"INSERT INTO records ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
    count = bad = 0
    rows, fts = [], []
    start_id = con.execute("SELECT COALESCE(MAX(id), 0) FROM records").fetchone()[0]

    def flush():
        con.executemany(insert, rows)
        con.executemany("INSERT INTO names_fts(rowid, owner, holder) VALUES (?, ?, ?)", fts)
        rows.clear()
        fts.clear()

    for line_no, line in iter_records(path, encoding):
        if len(line) != RECORD_LENGTH:
            bad += 1
        r = parse_record(line)
        count += 1
        zip9 = re.sub(r"\D", "", r["OwnerZipCode"])
        rows.append([r[n] for n in NAMES] + [
            norm(r["OwnerLastName"]),
            norm(r["OwnerFirstName"]),
            norm(r["OwnerCity"]),
            norm(r["HolderName"]),
            zip9[:5] or None,
            "".join(r[n] for n in PROPERTY_ID_FIELDS),
            parse_number(r["DollarAmount"], implied_decimals),
            parse_number(r["NumberOfShares"]),
            parse_date(r["ReportDate"]),
            str(path),
            line_no,
        ])
        owner = f'{r["OwnerFirstName"]} {r["OwnerLastName"]}'
        fts.append((start_id + count, with_squashed(owner), with_squashed(r["HolderName"])))
        if len(rows) >= batch:
            flush()
    flush()
    con.executescript(INDEXES)
    con.execute("INSERT INTO load_log VALUES (?, datetime('now'), ?, ?)", (str(path), count, bad))
    con.commit()
    return count, bad


# ---------------------------------------------------------------- search

SEARCH_FIELDS = (
    "owner_last", "owner_first", "owner_name_words", "holder", "holder_words",
    "zip", "city", "state", "property_type", "report_year", "min_amount", "property_id",
)

RESULT_COLS = [
    "id", "OwnerLastName", "OwnerFirstName", "OwnerAddressLine1", "OwnerCity",
    "OwnerState", "OwnerZipCode", "PropertyTypeCode", "PropertyTypeDescription",
    "property_id", "NRFlag", "amount",
    "DollarAmount", "NumberOfShares", "HolderName", "HolderCity", "HolderState",
    "HolderReportYear", "ReportDate",
]

SORTS = {
    "name": "owner_last_u, owner_first_u",
    "amount": "amount DESC",
    "holder": "holder_u",
    "zip": "owner_zip5",
}


def _fts_terms(text):
    words = re.findall(r"\w+", text)
    return " AND ".join(f'"{w}"*' for w in words) if words else None


def _prefix(where, args, col, value):
    """Index-friendly prefix match: col >= 'ABC' AND col < 'ABD'."""
    v = norm(value)
    if not v:
        return
    where.append(f"({col} >= ? AND {col} < ?)")
    args += [v, v[:-1] + chr(ord(v[-1]) + 1)]


def build_query(f):
    where, args = [], []
    _prefix(where, args, "owner_last_u", f.get("owner_last") or "")
    _prefix(where, args, "owner_first_u", f.get("owner_first") or "")
    _prefix(where, args, "holder_u", f.get("holder") or "")
    _prefix(where, args, "owner_city_u", f.get("city") or "")
    _prefix(where, args, "property_id", re.sub(r"\s", "", f.get("property_id") or ""))

    fts = []
    if f.get("owner_name_words"):
        t = _fts_terms(f["owner_name_words"])
        if t:
            fts.append(f"owner : ({t})")
    if f.get("holder_words"):
        t = _fts_terms(f["holder_words"])
        if t:
            fts.append(f"holder : ({t})")
    if fts:
        where.append("id IN (SELECT rowid FROM names_fts WHERE names_fts MATCH ?)")
        args.append(" AND ".join(fts))

    z = re.sub(r"\D", "", f.get("zip") or "")
    if len(z) >= 5:
        where.append("owner_zip5 = ?")
        args.append(z[:5])
        if len(z) == 9:
            where.append("OwnerZipCode LIKE ?")
            args.append(z + "%")
    elif z:
        _prefix(where, args, "owner_zip5", z)
    if f.get("state"):
        where.append("OwnerState = ?")
        args.append(f["state"].strip().upper())
    if f.get("property_type"):
        where.append("PropertyTypeCode = ?")
        args.append(f["property_type"].strip().upper())
    if f.get("report_year"):
        where.append("HolderReportYear = ?")
        args.append(str(f["report_year"]).strip())
    if f.get("min_amount") not in (None, ""):
        where.append("amount >= ?")
        args.append(float(f["min_amount"]))
    return where, args


def search(con, filters, limit=100, offset=0, sort="name"):
    where, args = build_query(filters)
    if not where:
        raise ValueError("Give at least one search criterion.")
    clause = " AND ".join(where)
    total = con.execute(f"SELECT COUNT(*) FROM records WHERE {clause}", args).fetchone()[0]
    rows = con.execute(
        f"SELECT {', '.join(RESULT_COLS)} FROM records "
        "LEFT JOIN (SELECT code, description AS PropertyTypeDescription FROM property_types) "
        f"ON code = PropertyTypeCode WHERE {clause} "
        f"ORDER BY {SORTS.get(sort, SORTS['name'])} LIMIT ? OFFSET ?",
        args + [int(limit), int(offset)],
    ).fetchall()
    out = []
    for r in rows:
        r = dict(r)
        r["NRFlagDescription"] = describe_nr_flag(r["NRFlag"])
        out.append(r)
    return total, out


def describe_nr_flag(flag):
    return NR_FLAGS.get(flag, f"Unknown ({flag})" if flag else "")


def describe_type(code):
    return PROPERTY_TYPES.get(code, "(code not in list)" if code else "")


def get_record(con, rec_id):
    r = con.execute("SELECT * FROM records WHERE id = ?", (rec_id,)).fetchone()
    if not r:
        return None
    r = dict(r)
    out = {}
    for k, v in r.items():
        out[k] = v
        if k == "PropertyTypeCode":
            out["PropertyTypeDescription"] = describe_type(v)
        if k == "NRFlag":
            out["NRFlagDescription"] = describe_nr_flag(v)
    return out


def property_types(con):
    """Every listed code plus any extra codes present in the data, with
    a flag for whether the loaded data contains it."""
    present = {r[0] for r in con.execute(
        "SELECT DISTINCT PropertyTypeCode FROM records WHERE PropertyTypeCode != ''")}
    codes = sorted(set(PROPERTY_TYPES) | present)
    return [{"code": c, "description": describe_type(c), "in_data": c in present} for c in codes]
