"""SSA NUMIDENT (NARA public use files) as a reference dataset beside the UCF owners.

NUMIDENT has three record types, each a 500-column fixed-width record in NARA's
"pre-CSV" layouts (see NUMIDENT.md):

  D  Death records    49,459,293 records, one per SSN
  C  Claim records    25,230,486 records (life or death benefit claims)
  S  SS-5 records     72,182,729 records (applications; several per SSN)

They are never merged into the owner file. Owners are matched to NUMIDENT
people by name (plus ZIP, place of birth and dates as supporting evidence) and
the matches are shown for a person to judge, the same way sounds-like results are.

The loader takes NARA's fixed-width files and also CSV files with a header row
whose column names are the layout's field names (NUMI_SSN or NUMI-SSN both work).
"""

import csv
import os
import re
from datetime import date

from .numident_codes import COUNTRIES, STATES

KINDS = {"D": "Death", "C": "Claim", "S": "SS-5"}

# (field, 1-based start, length), straight from NARA's record layouts.
_NAMES = [  # identical positions in all three record types
    ("NUMI-REFERENCE-NUM", 1, 11),
    ("NUMI-SSN", 13, 9),
    ("NUMI-ENTRY-CODE", 27, 1),
    ("NUMI-CYCLE-DATE", 29, 8),          # CCYYMMDD
    ("NUMI-NH-NAME-FIRST", 37, 15),
    ("NUMI-NH-NAME-FIRST-OFLO", 52, 1),
    ("NUMI-NH-NAME-MIDDLE", 53, 15),
    ("NUMI-NH-NAME-MIDDLE-OFLO", 68, 1),
    ("NUMI-NH-NAME-LAST", 69, 20),
    ("NUMI-NH-NAME-LAST-OFLO", 89, 1),
    ("NUMI-NH-NAME-SUFFIX", 90, 4),
    ("NUMI-DOB", 97, 8),                 # MMDDCCYY
    ("NUMI-SEX", 105, 1),
]

_PARENTS_POB = [  # claim and SS-5 records
    ("NUMI-MTH-NAME-FIRST", 107, 15),
    ("NUMI-MTH-NAME-MIDDLE", 123, 15),
    ("NUMI-MTH-NAME-LAST", 139, 20),
    ("NUMI-MTH-NAME-SUFFIX", 160, 4),
    ("NUMI-FTH-NAME-FIRST", 164, 15),
    ("NUMI-FTH-NAME-MIDDLE", 180, 15),
    ("NUMI-FTH-NAME-LAST", 196, 20),
    ("NUMI-FTH-NAME-SUFFIX", 217, 4),
    ("NUMI-POB-CITY", 221, 12),
    ("NUMI-POB-CITY-OFLO", 233, 1),
    ("NUMI-POB-STATE-COUNTRY", 234, 2),
    ("NUMI-POB-FOREIGN-IND", 236, 1),
]

LAYOUTS = {
    "C": _NAMES + [("NUMI-DO-CODE", 23, 3), ("NUMI-FORM-CODE", 26, 1)] + _PARENTS_POB + [
        ("NUMI-DO-ADDRESS", 237, 45),
        ("NUMI-CLAIM-DATE", 282, 8),     # MMDDCCYY
        ("NUMI-DOO", 290, 8),            # date of onset, MMDDCCYY
        ("NUMI-DOD-CLAIM", 298, 8),      # MMDDCCYY
        ("NUMI-CONVERSION-RECORD-IND", 498, 1),
        ("NUMI-FLAG-DELETE-IND", 500, 1),   # not in the public use files
    ],
    "S": _NAMES + [
        ("NUMI-INTERVIEW-CODE", 12, 1),
        ("NUMI-CITIZENSHIP-CODE", 22, 1),
        ("NUMI-DO-CODE", 23, 3),
        ("NUMI-FORM-CODE", 26, 1),
        ("NUMI-RACE", 106, 1),
    ] + _PARENTS_POB + [
        ("NUMI-OTH-NAME-FIRST", 237, 15),
        ("NUMI-OTH-NAME-MIDDLE", 253, 15),
        ("NUMI-OTH-NAME-LAST", 269, 20),
        ("NUMI-OTH-NAME-SUFFIX", 290, 4),
        ("NUMI-SIG-NAME-FIRST", 297, 15),
        ("NUMI-SIG-NAME-MIDDLE", 313, 15),
        ("NUMI-SIG-NAME-LAST", 329, 20),
        ("NUMI-SIG-NAME-SUFFIX", 350, 4),
        ("NUMI-SIG-NAME-CODE", 354, 1),
        ("NUMI-NOTIFY", 358, 2),
        ("NUMI-CARD-CODE", 360, 1),
        ("NUMI-DIB-FREEZE-IND", 361, 1),
        ("NUMI-DOB-CHANGE-IND", 362, 1),
        ("NUMI-PRIOR-DOB", 363, 8),
        ("NUMI-CORR-IND", 371, 2),
        ("NUMI-BIRTH-CERTIFICATE-NUMBER", 373, 11),
        ("NUMI-ALIEN-REGISTRATION-NUMBER", 386, 15),
        ("NUMI-CONTROL-NUMBER", 413, 9),
        ("NUMI-DIFFERENT-NUMBER-REASON", 497, 1),
        ("NUMI-CONVERSION-RECORD-IND", 498, 1),
        ("NUMI-ENTRY-SUBCODE", 499, 1),
        ("NUMI-FLAG-DELETE-IND", 500, 1),   # not in the public use files
    ],
    # Death: the name/DOB/sex fields above are occurrence 1 (the -DTH (1) fields,
    # 16/16/21 bytes with the overflow flag last, so the same columns).
    "D": _NAMES + [
        ("NUMI-INDIVIDUALS-OTHER-NUM", 107, 9),
        ("NUMI-RECORD-ID-CODE", 116, 1),
        ("NUMI-PROOF-OF-DEATH", 117, 1),
        ("NUMI-PGM-INVOLVEMENT-IND", 118, 1),
        ("NUMI-ZIP-RESIDENCE", 119, 9),
        ("NUMI-ZIP-LUMP-SUM", 128, 9),
        ("NUMI-PLUS-5-DOB-EX-IND", 137, 1),
        ("NUMI-PLUS-5-EXCEPT-CHANGE-IND", 138, 1),
        ("NUMI-PLUS-5-MBR-DOB-EX-IND", 139, 1),
        ("NUMI-SOURCE-OF-DEATH", 142, 2),
        ("NUMI-VERIFIED-EDR-IND", 144, 1),
        ("NUMI-DOD-DTH", 145, 8),        # MMDDCCYY
        ("NUMI-DTH-CERTIFICATE-NUM", 153, 26),  # masked with X by NARA where filled
        ("NUMI-DTH-POSTING-DATE", 179, 8),  # CCYYMMDD
        ("NUMI-DTH-NOE", 487, 1),        # number of death postings (1-3)
    ],
}
RECORD_LENGTH = 500
DEATH_OCCURS = 150   # occurrence n of the death group starts 150*(n-1) bytes later
DEATH_GROUP = (37, 186)  # columns of occurrence 1

# Death record fields that repeat per occurrence (columns 37-186).
_DEATH_REPEATING = {f for f, s, _ in LAYOUTS["D"] if DEATH_GROUP[0] <= s <= DEATH_GROUP[1]}

COLUMNS = [
    ("kind", "TEXT"), ("ssn", "TEXT"), ("reference_num", "TEXT"), ("entry_code", "TEXT"),
    ("cycle_date", "TEXT"), ("occurrence", "INTEGER"),
    ("last_name", "TEXT"), ("first_name", "TEXT"), ("middle_name", "TEXT"), ("suffix", "TEXT"),
    ("name_overflow", "TEXT"),
    ("dob", "TEXT"), ("dob_year", "INTEGER"), ("dod", "TEXT"), ("dod_year", "INTEGER"),
    ("sex", "TEXT"),
    ("pob_city", "TEXT"), ("pob_code", "TEXT"), ("pob_foreign", "TEXT"), ("pob", "TEXT"),
    ("father", "TEXT"), ("mother", "TEXT"), ("other_name", "TEXT"),
    ("zip_residence", "TEXT"), ("zip_lump_sum", "TEXT"), ("claim_date", "TEXT"),
    ("last_u", "TEXT"), ("first_u", "TEXT"), ("last_sdx", "TEXT"), ("zip5", "TEXT"),
    ("source_file", "TEXT"), ("source_line", "INTEGER"),
]
COLS = [c for c, _ in COLUMNS]

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS numident (
    id INTEGER PRIMARY KEY,
    {", ".join(f"{c} {t}" for c, t in COLUMNS)}
);
CREATE TABLE IF NOT EXISTS numident_load_log (
    source_file TEXT, kind TEXT, loaded_at TEXT, records INTEGER, masked INTEGER, skipped INTEGER
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS ix_numi_name ON numident(last_u, first_u);
CREATE INDEX IF NOT EXISTS ix_numi_sdx ON numident(last_sdx, first_u);
CREATE INDEX IF NOT EXISTS ix_numi_ssn ON numident(ssn);
CREATE INDEX IF NOT EXISTS ix_numi_zip ON numident(zip5);
"""

SEX = {"0": "Unknown", "1": "Male", "2": "Female"}
ENTRY_CODES = {"T": "Death data", "D": "Death claim", "L": "Life claim"}
TX_ZIP3 = tuple(str(n) for n in range(750, 800)) + ("885",)

_ws = re.compile(r"\s+")


def norm(s):
    return _ws.sub(" ", s or "").strip().upper()


# ------------------------------------------------------------- Soundex

_SDX = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "0123012*02245501262301*202"))


def soundex(name):
    """American Soundex, the same rules as cobol/UCFSNDX.cbl (letters only;
    H and W don't separate equal codes, vowels do). '' if no letters."""
    out, prev = "", None
    for ch in (name or "").upper():
        if len(out) == 4:
            break
        c = _SDX.get(ch)
        if c is None:
            continue
        if not out:
            out, prev = ch, c
        elif c == "*":
            pass
        elif c == "0":
            prev = "0"
        elif c != prev:
            out, prev = out + c, c
    return (out + "000")[:4] if out else ""


# ------------------------------------------------------------- parsing

def parse_mdy(s):
    """MMDDCCYY -> (ISO date or partial 'CCYY' / 'CCYY-MM', year or None).
    NUMIDENT fills unknown parts with 00 or XX."""
    s = (s or "").strip()
    if len(s) != 8:
        return None, None
    mm, dd, yyyy = s[0:2], s[2:4], s[4:8]
    year = int(yyyy) if yyyy.isdigit() and yyyy != "0000" else None
    if year is None:
        return None, None
    if mm.isdigit() and 1 <= int(mm) <= 12:
        if dd.isdigit() and int(dd) >= 1:
            try:
                return date(year, int(mm), int(dd)).isoformat(), year
            except ValueError:
                pass
        return f"{year:04d}-{int(mm):02d}", year
    return f"{year:04d}", year


def parse_ymd(s):
    s = (s or "").strip()
    if len(s) == 8 and s.isdigit():
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:])).isoformat()
        except ValueError:
            return None
    return None


def pob_description(code, foreign_ind):
    code = (code or "").strip()
    if not code:
        return ""
    if (foreign_ind or "").strip() in ("f", "*") or code.endswith("f"):
        c = code.rstrip("f")
        return COUNTRIES.get(c, f"{c} (foreign code not in list)") if c else "Foreign"
    return STATES.get(code, f"{code} (code not in list)")


def kind_from_name(path):
    n = os.path.basename(str(path)).upper()
    if "SS5" in n or "SS-5" in n or "APPL" in n:
        return "S"
    if "DTH" in n or "DEATH" in n:
        return "D"
    if "CLM" in n or "CLAIM" in n:
        return "C"
    return None


def kind_from_record(line):
    e = line[26:27]
    return "D" if e == "T" else "C" if e in ("D", "L") else "S"


def slice_fields(line, kind):
    line = line.rstrip("\r\n").ljust(RECORD_LENGTH)
    return {f: line[s - 1:s - 1 + n] for f, s, n in LAYOUTS[kind]}


def death_occurrences(line):
    """Yield the field dict for each death posting on a death record.
    NARA's own reference copies keep one posting per record (and may move
    NUMI-DTH-NOE to column 187); the agency layout allows three."""
    line = line.rstrip("\r\n")
    base = slice_fields(line, "D")
    yield 1, base
    noe = base["NUMI-DTH-NOE"].strip()
    count = int(noe) if noe.isdigit() else 1
    for occ in range(2, min(count, 3) + 1):
        shift = DEATH_OCCURS * (occ - 1)
        seg = line[DEATH_GROUP[0] - 1 + shift:DEATH_GROUP[1] + shift]
        if not seg.strip():
            continue
        f = dict(base)
        padded = line.ljust(RECORD_LENGTH)
        for name, s, n in LAYOUTS["D"]:
            if name in _DEATH_REPEATING:
                f[name] = padded[s - 1 + shift:s - 1 + shift + n]
        yield occ, f


def _person_name(f, prefix):
    parts = [f.get(f"NUMI-{prefix}-NAME-{p}", "").strip() for p in ("FIRST", "MIDDLE", "LAST", "SUFFIX")]
    return " ".join(p for p in parts if p)


def to_row(f, kind, occurrence=1, source=None, line_no=None):
    """Field dict (raw strings) -> row for the numident table, or None if masked."""
    g = {k: (v or "").strip() for k, v in f.items()}
    ssn = g.get("NUMI-SSN", "")
    if not ssn or set(ssn) == {"Z"}:
        return None
    dob, dob_year = parse_mdy(g.get("NUMI-DOB"))
    dod_raw = g.get("NUMI-DOD-DTH") if kind == "D" else g.get("NUMI-DOD-CLAIM")
    dod, dod_year = parse_mdy(dod_raw)
    claim_date, _ = parse_mdy(g.get("NUMI-CLAIM-DATE"))
    last = g.get("NUMI-NH-NAME-LAST", "")
    first = g.get("NUMI-NH-NAME-FIRST", "")
    oflo = "".join(p for p, k in (("F", "FIRST"), ("M", "MIDDLE"), ("L", "LAST"))
                   if g.get(f"NUMI-NH-NAME-{k}-OFLO") in ("O", "*"))
    zip_res = re.sub(r"\D", "", g.get("NUMI-ZIP-RESIDENCE", ""))
    return [
        kind, ssn, g.get("NUMI-REFERENCE-NUM", ""), g.get("NUMI-ENTRY-CODE", ""),
        parse_ymd(g.get("NUMI-CYCLE-DATE")), occurrence,
        last, first, g.get("NUMI-NH-NAME-MIDDLE", ""), g.get("NUMI-NH-NAME-SUFFIX", ""), oflo,
        dob, dob_year, dod, dod_year,
        SEX.get(g.get("NUMI-SEX", ""), g.get("NUMI-SEX", "")),
        g.get("NUMI-POB-CITY", ""), g.get("NUMI-POB-STATE-COUNTRY", ""), g.get("NUMI-POB-FOREIGN-IND", ""),
        pob_description(g.get("NUMI-POB-STATE-COUNTRY"), g.get("NUMI-POB-FOREIGN-IND")),
        _person_name(g, "FTH"), _person_name(g, "MTH"), _person_name(g, "OTH"),
        g.get("NUMI-ZIP-RESIDENCE", ""), g.get("NUMI-ZIP-LUMP-SUM", ""), claim_date,
        norm(last), norm(first), soundex(last), zip_res[:5] if len(zip_res) >= 5 else None,
        source, line_no,
    ]


def _hkey(s):
    """'NUMI_NH_NAME_LAST_DTH (1)' -> 'NHNAMELASTDTH'."""
    k = re.sub(r"[^A-Z0-9]", "", re.sub(r"\(\d\)", "", s.upper()))
    k = k[4:] if k.startswith("NUMI") else k
    return re.sub(r"\d$", "", k)   # occurrence suffix: _DTH_1, _RESIDENCE_1


def csv_field_map(header, kind):
    """CSV column index -> layout field name, matched on the name with
    punctuation dropped (NUMI_NH_NAME_LAST = NUMI-NH-NAME-LAST). Returns
    (mapping, unmapped column names)."""
    want = {_hkey(f): f for f, _, _ in LAYOUTS[kind]}
    want.update({_hkey(f + "-DTH"): f for f, _, _ in LAYOUTS[kind] if kind == "D"})
    mapping, unmapped = {}, []
    for i, h in enumerate(header):
        k = _hkey(h)
        if k in want:
            mapping[i] = want[k]
        else:
            unmapped.append(h)
    return mapping, unmapped


def iter_file(path, kind=None, encoding="latin-1"):
    """Yield (line_no, occurrence, kind, field dict) from a fixed-width or CSV
    NUMIDENT file. The kind comes from the argument, then the file name, then
    the record's entry code (T = death, D/L = claim, anything else = SS-5)."""
    with open(path, "r", encoding=encoding, newline="") as fh:
        first = fh.readline()
        fh.seek(0)
        is_csv = "," in first and "SSN" in first.upper()
        k = kind or kind_from_name(path)
        if is_csv:
            rdr = csv.reader(fh)
            header = next(rdr)
            k = k or ("D" if any("DOD" in h.upper() and "CLAIM" not in h.upper() for h in header)
                      else "C" if any("CLAIM" in h.upper() for h in header) else "S")
            mapping, unmapped = csv_field_map(header, k)
            iter_file.unmapped = unmapped
            for n, row in enumerate(rdr, 2):
                if not any(c.strip() for c in row):
                    continue
                f = {name: row[i] for i, name in mapping.items() if i < len(row)}
                yield n, 1, k, f
            return
        iter_file.unmapped = []
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            kk = k or kind_from_record(line)
            if kk == "D":
                for occ, f in death_occurrences(line):
                    yield n, occ, kk, f
            else:
                yield n, 1, kk, slice_fields(line, kk)


iter_file.unmapped = []


# ------------------------------------------------------------- load

def ensure_schema(con):
    con.executescript(SCHEMA)


def ucf_last_names(con):
    """Owner last names in the UCF table, cut to NUMIDENT's 20 characters."""
    try:
        return {r[0][:20] for r in con.execute("SELECT DISTINCT owner_last_u FROM records") if r[0]}
    except Exception:
        return set()


def load_file(con, path, kind=None, only_names=None, encoding="latin-1", batch=20000):
    """Load one NUMIDENT file. only_names: a set of upper-cased last names to
    keep (e.g. ucf_last_names(con)), which cuts 147 million records down to
    the people who could match a Texas owner. Returns (loaded, masked, skipped)."""
    ensure_schema(con)
    insert = f"INSERT INTO numident ({', '.join(COLS)}) VALUES ({', '.join('?' * len(COLS))})"
    rows, loaded, masked, skipped, kinds = [], 0, 0, 0, set()
    for line_no, occ, k, f in iter_file(path, kind, encoding):
        kinds.add(k)
        r = to_row(f, k, occ, str(path), line_no)
        if r is None:
            masked += 1
            continue
        if only_names is not None and r[COLS.index("last_u")] not in only_names:
            skipped += 1
            continue
        rows.append(r)
        loaded += 1
        if len(rows) >= batch:
            con.executemany(insert, rows)
            rows.clear()
    con.executemany(insert, rows)
    con.executescript(INDEXES)
    con.execute("INSERT INTO numident_load_log VALUES (?, ?, datetime('now'), ?, ?, ?)",
                (str(path), "".join(sorted(kinds)), loaded, masked, skipped))
    con.commit()
    return loaded, masked, skipped


def _require(con):
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name = 'numident'").fetchone():
        raise ValueError("NUMIDENT isn't loaded (python -m ucfms numi load ...).")


def count(con):
    try:
        return con.execute("SELECT COUNT(*) FROM numident").fetchone()[0]
    except Exception:
        return 0


# ------------------------------------------------------------- search

SEARCH_FIELDS = ("last", "first", "sounds_like", "ssn", "dob_year", "dod_year", "zip", "pob", "kind")

RESULT_COLS = [
    "id", "kind", "ssn", "last_name", "first_name", "middle_name", "suffix", "dob", "dod", "sex",
    "pob_city", "pob", "father", "mother", "zip_residence", "zip_lump_sum", "entry_code", "claim_date",
]


def _prefix(where, args, col, v):
    v = norm(v)
    if v:
        where.append(f"({col} >= ? AND {col} < ?)")
        args += [v, v[:-1] + chr(ord(v[-1]) + 1)]


def search(con, f, limit=100, offset=0):
    _require(con)
    where, args = [], []
    last = norm(f.get("last"))
    if last and str(f.get("sounds_like") or "").lower() in ("1", "true", "yes", "on"):
        where.append("last_sdx = ?")
        args.append(soundex(last))
    else:
        _prefix(where, args, "last_u", last[:20])
    _prefix(where, args, "first_u", f.get("first") or "")
    ssn = re.sub(r"\D", "", f.get("ssn") or "")
    if ssn:
        where.append("ssn = ?" if len(ssn) == 9 else "ssn LIKE ?")
        args.append(ssn if len(ssn) == 9 else ssn + "%")
    for k in ("dob_year", "dod_year"):
        if str(f.get(k) or "").strip():
            where.append(f"{k} = ?")
            args.append(int(f[k]))
    z = re.sub(r"\D", "", f.get("zip") or "")
    if len(z) >= 5:
        where.append("zip5 = ?")
        args.append(z[:5])
    elif z:
        _prefix(where, args, "zip5", z)
    if f.get("pob"):
        where.append("pob_code = ?")
        args.append(f["pob"].strip().upper())
    if f.get("kind"):
        where.append("kind = ?")
        args.append(f["kind"].strip().upper()[:1])
    if not any(f.get(k) for k in ("last", "ssn", "zip")):
        raise ValueError("Give a last name, an SSN or a ZIP.")
    clause = " AND ".join(where)
    total = con.execute(f"SELECT COUNT(*) FROM numident WHERE {clause}", args).fetchone()[0]
    rows = con.execute(
        f"SELECT {', '.join(RESULT_COLS)} FROM numident WHERE {clause} "
        "ORDER BY last_u, first_u, ssn, kind LIMIT ? OFFSET ?",
        args + [int(limit), int(offset)]).fetchall()
    return total, [dict(r) for r in rows]


def person(con, ssn):
    """Every NUMIDENT record for one SSN (death, claims, SS-5 versions)."""
    _require(con)
    return [dict(r) for r in con.execute(
        f"SELECT {', '.join(RESULT_COLS)}, cycle_date, other_name FROM numident "
        "WHERE ssn = ? ORDER BY kind, cycle_date", (re.sub(r"\D", "", ssn),))]


# ------------------------------------------------------------- matching

def _owner_name(owner):
    """UCF keeps 'GEORGE A' in OwnerFirstName: first word = first name,
    second word's initial = middle initial."""
    words = norm(owner.get("OwnerFirstName")).split()
    return (norm(owner.get("OwnerLastName")), words[0] if words else "",
            words[1][:1] if len(words) > 1 else "")


def match_owner(con, owner, limit=20, sounds_like=False):
    """Rank NUMIDENT people who could be this UCF owner. owner is a dict
    with the UCF field names. Returns a list of candidates, one per SSN,
    best first, each with a score and the reasons for it. These are leads
    for a person to check, not identifications."""
    _require(con)
    last, first, mid = _owner_name(owner)
    if not last or not first:
        return []   # business names or no first name: nothing to match on
    zip9 = re.sub(r"\D", "", owner.get("OwnerZipCode") or "")
    zip5 = zip9[:5] if len(zip9) >= 5 and zip9[:5] != "00000" else ""
    if sounds_like:
        sql, args = "last_sdx = ?", [soundex(last)]
    else:
        sql, args = "last_u = ?", [last[:20]]
    sql += " AND (first_u >= ? AND first_u < ?)"
    args += [first[0], chr(ord(first[0]) + 1)]
    rows = con.execute(f"SELECT * FROM numident WHERE {sql} LIMIT 5000", args).fetchall()

    # Score each record, then combine a person's records (same SSN): the
    # name evidence comes from the best record, ZIP from the death record,
    # birthplace and parents from claim or SS-5 records.
    people = {}
    for r in rows:
        r = dict(r)
        ev = {}
        if r["last_u"] == last[:20]:
            ev["name"] = (40, "last name")
        else:
            ev["name"] = (20, "last name sounds alike")
        nf = r["first_u"] or ""
        if nf == first:
            ev["first"] = (30, "first name")
        elif len(nf) > 1 and len(first) > 1 and (nf.startswith(first) or first.startswith(nf)):
            ev["first"] = (20, "first name (shortened)")
        elif len(nf) == 1 or len(first) == 1:
            ev["first"] = (10, "first initial")
        else:
            continue    # same first letter, different name
        nm = norm(r["middle_name"])[:1]
        if mid and nm:
            ev["middle"] = (10, "middle initial") if nm == mid else (-10, "middle initial differs")
        z = re.sub(r"\D", "", r["zip_residence"] or "")
        zl = re.sub(r"\D", "", r["zip_lump_sum"] or "")
        if zip5 and z[:5] == zip5:
            ev["zip"] = (25, "residence ZIP at death")
        elif zip5 and zl[:5] == zip5:
            ev["zip"] = (15, "death payment ZIP")
        elif zip5 and len(z) >= 3 and z[:3] == zip5[:3] or zip5 and len(zl) >= 3 and zl[:3] == zip5[:3]:
            ev["zip"] = (10, "same ZIP area")
        elif z[:3] in TX_ZIP3 or zl[:3] in TX_ZIP3:
            ev["zip"] = (5, "died in Texas")
        if r["pob_code"] == "TX" and not r["pob_foreign"]:
            ev["pob"] = (5, "born in Texas")
        p = people.setdefault(r["ssn"], {"ssn": r["ssn"], "ev": {}, "kinds": set(), "name": "",
                                         "name_score": -1, "dob": None, "dod": None, "pob": "",
                                         "father": "", "mother": "", "zip_residence": ""})
        ns = ev["name"][0] + ev["first"][0] + ev.get("middle", (0,))[0]
        if ns > p["name_score"]:
            p["name_score"] = ns
            p["name"] = " ".join(x for x in (r["first_name"], r["middle_name"], r["last_name"], r["suffix"]) if x)
            p["ev"]["name"], p["ev"]["first"] = ev["name"], ev["first"]
        for k in ("middle", "zip", "pob"):   # best of the records that have it
            if k in ev and ev[k][0] > p["ev"].get(k, (-99,))[0]:
                p["ev"][k] = ev[k]
        p["kinds"].add(r["kind"])
        for k in ("dob", "dod", "pob", "father", "mother", "zip_residence"):
            if r[k] and not p[k]:
                p[k] = r[k]
    out = []
    for p in people.values():
        order = [p["ev"][k] for k in ("name", "first", "middle", "zip", "pob") if k in p["ev"]]
        p["score"] = sum(v for v, _ in order)
        p["why"] = [w for _, w in order] + (["death on file"] if p["dod"] else [])
        p["kinds"] = "".join(k for k in "DCS" if k in p["kinds"])
        del p["ev"], p["name_score"]
        out.append(p)
    return sorted(out, key=lambda p: (-p["score"], p["name"]))[:limit]


# ------------------------------------------------------------- fixed-width writer

def to_fixed(f, kind):
    """Field dict -> one 500-column record in NARA's layout (for upload to
    the mainframe when the files arrived as CSV)."""
    buf = [" "] * RECORD_LENGTH
    for name, s, n in LAYOUTS[kind]:
        v = (f.get(name) or "")[:n].ljust(n)
        buf[s - 1:s - 1 + n] = v
    if kind == "D" and not (f.get("NUMI-DTH-NOE") or "").strip():
        buf[486] = "1"
    return "".join(buf)


def extract(src, dst, kind=None, only_names=None, encoding="latin-1"):
    """Write NARA's 500-column records from a fixed-width or CSV NUMIDENT file,
    optionally keeping only people whose last name is in only_names, ready
    to upload to the mainframe (see NUMIDENT.md). Returns (written, dropped)."""
    n = dropped = 0
    with open(dst, "w", encoding=encoding, newline="\n") as out:
        for _, occ, k, f in iter_file(src, kind, encoding):
            if occ != 1:
                continue
            ssn = (f.get("NUMI-SSN") or "").strip()
            if not ssn or set(ssn) == {"Z"} or (
                    only_names is not None and norm(f.get("NUMI-NH-NAME-LAST")) not in only_names):
                dropped += 1
                continue
            out.write(to_fixed(f, k) + "\n")
            n += 1
    return n, dropped


def fixed_record(**fields):
    """Test/sample helper: build a fixed record from short names, e.g.
    fixed_record(kind='D', SSN='900000001', LAST='DOE', FIRST='JOHN')."""
    kind = fields.pop("kind")
    f = {}
    for k, v in fields.items():
        name = k if k.startswith("NUMI-") else "NUMI-" + k.replace("_", "-")
        if name in ("NUMI-LAST", "NUMI-FIRST", "NUMI-MIDDLE", "NUMI-SUFFIX"):
            name = "NUMI-NH-NAME-" + name[5:]
        f[name] = v
    return to_fixed(f, kind)


def describe_counts(con):
    try:
        return {KINDS[k]: n for k, n in con.execute("SELECT kind, COUNT(*) FROM numident GROUP BY kind")}
    except Exception:
        return {}

