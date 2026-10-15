"""Command line: python -m ucfms {load,search,serve,sample} ..."""

import argparse
import sys
import time

from . import db


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
    elif a.cmd == "serve":
        from .web import serve
        serve(a.db, a.host, a.port)


if __name__ == "__main__":
    main()
