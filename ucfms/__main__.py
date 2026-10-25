"""Command line: python -m ucfms {load,search,serve,sample,types,numi} ..."""

import argparse
import sys
import time

from . import db, numident


def main(argv=None):
    p = argparse.ArgumentParser(prog="ucfms", description="Texas unclaimed property search")
    p.add_argument("--db", default="ucf.db", help="SQLite database path (default ucf.db)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("load", help="load one or more fixed-width UCF files")
    s.add_argument("files", nargs="+")
    s.add_argument("--implied-decimals", type=int, default=2,
                   help="digits of DollarAmount after the implied decimal point (default 2: cents)")
    s.add_argument("--encoding", default="latin-1")
    s.add_argument("--replace", action="store_true", help="empty the database first")

    s = sub.add_parser("search", help="search from the command line")
    for k in db.SEARCH_FIELDS:
        s.add_argument("--" + k.replace("_", "-"), dest=k)
    s.add_argument("--limit", type=int, default=25)
    s.add_argument("--sort", default="name", choices=list(db.SORTS))

    s = sub.add_parser("serve", help="run the web search page")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)

    sub.add_parser("types", help="list property type codes")

    s = sub.add_parser("sample", help="write a synthetic file in the UCF layout")
    s.add_argument("out")
    s.add_argument("-n", type=int, default=1000)

    s = sub.add_parser("numi", help="SSA NUMIDENT death, claim and SS-5 records (see NUMIDENT.md)")
    nsub = s.add_subparsers(dest="numi_cmd", required=True)
    n = nsub.add_parser("load", help="load NARA NUMIDENT files (fixed-width or CSV)")
    n.add_argument("files", nargs="+")
    n.add_argument("--kind", choices=["D", "C", "S"],
                   help="D death, C claim, S SS-5 (default: from the file name, else each record's entry code)")
    n.add_argument("--only-ucf-names", action="store_true",
                   help="keep only people whose last name is an owner last name already loaded")
    n.add_argument("--encoding", default="latin-1")
    n.add_argument("--replace", action="store_true", help="empty the NUMIDENT table first")
    n = nsub.add_parser("search", help="search NUMIDENT")
    for k in numident.SEARCH_FIELDS:
        if k != "sounds_like":
            n.add_argument("--" + k.replace("_", "-"), dest=k)
    n.add_argument("--sounds-like", action="store_true", help="match the last name by Soundex")
    n.add_argument("--limit", type=int, default=25)
    n = nsub.add_parser("match", help="rank NUMIDENT people who could be a UCF owner record")
    n.add_argument("id", type=int, help="UCF record id (as shown by the web page or search --ids)")
    n.add_argument("--sounds-like", action="store_true")
    n = nsub.add_parser("person", help="every NUMIDENT record for one SSN")
    n.add_argument("ssn")
    n = nsub.add_parser("extract", help="write NARA 500-column records (from fixed or CSV) for upload to the mainframe")
    n.add_argument("src")
    n.add_argument("dst")
    n.add_argument("--kind", choices=["D", "C", "S"])
    n.add_argument("--only-ucf-names", action="store_true",
                   help="keep only people whose last name is an owner last name loaded in --db")

    a = p.parse_args(argv)

    if a.cmd == "sample":
        from .sample import write_sample
        write_sample(a.out, a.n)
        print(f"wrote {a.n} records to {a.out}")
    elif a.cmd == "load":
        con = db.connect(a.db)
        if a.replace:
            con.executescript("DELETE FROM records; DELETE FROM names_fts; DELETE FROM load_log;")
        for path in a.files:
            t = time.time()
            n, bad = db.load_file(con, path, a.implied_decimals, a.encoding)
            print(f"{path}: {n:,} records in {time.time() - t:.1f}s"
                  + (f" ({bad:,} lines not exactly 500 chars)" if bad else ""))
    elif a.cmd == "search":
        con = db.connect(a.db)
        filters = {k: getattr(a, k) for k in db.SEARCH_FIELDS}
        try:
            total, rows = db.search(con, filters, a.limit, sort=a.sort)
        except ValueError as e:
            sys.exit(str(e))
        print(f"{total:,} matching records")
        for r in rows:
            name = r["OwnerLastName"] + (", " + r["OwnerFirstName"] if r["OwnerFirstName"] else "")
            amt = f'{r["amount"]:>12,.2f}' if r["amount"] is not None else " " * 12
            ptype = f'{r["PropertyTypeCode"]} {r["PropertyTypeDescription"] or ""}'
            print(f'{name[:30]:30} {r["OwnerCity"][:12]:12} {r["OwnerZipCode"]:9} '
                  f'{ptype[:25]:25} {amt}  {r["HolderName"][:28]}')
    elif a.cmd == "types":
        con = db.connect(a.db)
        for t in db.property_types(con):
            print(f'{t["code"]}  {t["description"]}' + ("" if t["in_data"] else "  (none loaded)"))
    elif a.cmd == "numi":
        numi(a)
    elif a.cmd == "serve":
        from .web import serve
        serve(a.db, a.host, a.port)


def numi(a):
    con = db.connect(a.db)
    numident.ensure_schema(con)
    if a.numi_cmd == "extract":
        names = numident.ucf_last_names(con) if a.only_ucf_names else None
        if names is not None and not names:
            sys.exit("--only-ucf-names: load the UCF owner file first")
        n, dropped = numident.extract(a.src, a.dst, a.kind, names)
        print(f"wrote {n:,} records to {a.dst}" + (f" ({dropped:,} left out)" if dropped else ""))
        return
    if a.numi_cmd == "load":
        if a.replace:
            con.executescript("DELETE FROM numident; DELETE FROM numident_load_log;")
        names = numident.ucf_last_names(con) if a.only_ucf_names else None
        if names is not None and not names:
            sys.exit("--only-ucf-names: load the UCF owner file first")
        for path in a.files:
            t = time.time()
            n, masked, skipped = numident.load_file(con, path, a.kind, names, a.encoding)
            print(f"{path}: {n:,} records in {time.time() - t:.1f}s"
                  + (f", {masked:,} masked by NARA" if masked else "")
                  + (f", {skipped:,} with no matching owner last name" if skipped else ""))
            if numident.iter_file.unmapped:
                print("  CSV columns not used: " + ", ".join(numident.iter_file.unmapped))
    elif a.numi_cmd == "search":
        f = {k: getattr(a, k, None) for k in numident.SEARCH_FIELDS}
        f["sounds_like"] = "1" if a.sounds_like else ""
        try:
            total, rows = numident.search(con, f, a.limit)
        except ValueError as e:
            sys.exit(str(e))
        print(f"{total:,} matching NUMIDENT records")
        for r in rows:
            _numi_line(r)
    elif a.numi_cmd == "person":
        for r in numident.person(con, a.ssn):
            _numi_line(r)
    elif a.numi_cmd == "match":
        rec = db.get_record(con, a.id)
        if not rec:
            sys.exit(f"no UCF record {a.id}")
        print(f'{rec["OwnerLastName"]}, {rec["OwnerFirstName"]}  {rec["OwnerCity"]} {rec["OwnerZipCode"]}')
        cands = numident.match_owner(con, rec, sounds_like=a.sounds_like)
        if not cands:
            print("no NUMIDENT candidates")
        for c in cands:
            print(f'{c["score"]:4} {c["ssn"]} {c["name"][:30]:30} born {c["dob"] or "?":10} '
                  f'died {c["dod"] or "?":10} [{c["kinds"]}] {", ".join(c["why"])}')


def _numi_line(r):
    name = " ".join(x for x in (r["first_name"], r["middle_name"], r["last_name"], r["suffix"]) if x)
    print(f'{r["kind"]} {r["ssn"]} {name[:32]:32} born {r["dob"] or "?":10} died {r["dod"] or "?":10} '
          f'{(r["pob"] or "")[:16]:16} ZIP {r["zip_residence"] or "":9}')


if __name__ == "__main__":
    main()
