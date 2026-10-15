"""Tiny stdlib web UI + JSON API over the UCF SQLite database."""

import csv
import io
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import db

PAGE = (Path(__file__).parent / "index.html").read_text(encoding="utf-8")


def make_handler(db_path):
    class Handler(BaseHTTPRequestHandler):
        def _con(self):
            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            return con

        def _send(self, code, body, ctype="application/json", extra=None):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", f"{ctype}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            try:
                if url.path == "/":
                    return self._send(200, PAGE, "text/html")
                con = self._con()
                if url.path == "/api/search":
                    filters = {k: q.get(k) for k in db.SEARCH_FIELDS}
                    total, rows = db.search(
                        con, filters,
                        limit=min(int(q.get("limit", 50)), 500),
                        offset=int(q.get("offset", 0)),
                        sort=q.get("sort", "name"))
                    return self._send(200, json.dumps({"total": total, "rows": rows}))
                if url.path == "/api/export.csv":
                    filters = {k: q.get(k) for k in db.SEARCH_FIELDS}
                    _, rows = db.search(con, filters, limit=50000, sort=q.get("sort", "name"))
                    buf = io.StringIO()
                    w = csv.DictWriter(buf, fieldnames=db.RESULT_COLS + ["NRFlagDescription"])
                    w.writeheader()
                    w.writerows(rows)
                    return self._send(200, buf.getvalue(), "text/csv",
                                      {"Content-Disposition": "attachment; filename=ucf_results.csv"})
                if url.path == "/api/record":
                    rec = db.get_record(con, int(q["id"]))
                    return self._send(200 if rec else 404, json.dumps(rec))
                if url.path == "/api/meta":
                    n = con.execute("SELECT COUNT(*) FROM records").fetchone()[0]
                    return self._send(200, json.dumps(
                        {"records": n, "property_types": db.property_types(con)}))
                return self._send(404, json.dumps({"error": "not found"}))
            except ValueError as e:
                return self._send(400, json.dumps({"error": str(e)}))

        def log_message(self, fmt, *args):
            pass

    return Handler


def serve(db_path, host="127.0.0.1", port=8000):
    httpd = ThreadingHTTPServer((host, port), make_handler(db_path))
    print(f"UCF search running at http://{host}:{port}/  (Ctrl+C to stop)")
    httpd.serve_forever()
