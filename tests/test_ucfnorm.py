"""Tests for awk/ucfnorm.awk, checked against the Python parser."""
import csv
import io
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ucfms import db  # noqa: E402
from ucfms.layout import FIELDS, NAMES  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPT = os.path.join(ROOT, "awk", "ucfnorm.awk")
SAMPLE = os.path.join(ROOT, "sample", "ucf_sample.txt")
AWK = shutil.which("awk")


def rec(**kw):
    return "".join(kw.get(n, "").ljust(w)[:w] for n, w in FIELDS)


def run(data, *args):
    p = subprocess.run([AWK, "-f", SCRIPT, *args], input=data.encode("latin-1"),
                       capture_output=True, env={**os.environ, "LC_ALL": "C"})
    return p.returncode, p.stdout.decode("latin-1"), p.stderr.decode("latin-1")


@unittest.skipUnless(AWK, "no awk on PATH")
class UcfNormTests(unittest.TestCase):
    def test_csv_matches_python_parser(self):
        with open(SAMPLE, encoding="latin-1") as f:
            data = f.read()
        rc, out, err = run(data)
        self.assertEqual(rc, 0)
        self.assertIn("1000 read, 1000 written, 0 dropped, 0 warnings", err)
        rows = list(csv.reader(io.StringIO(out)))
        self.assertEqual(rows[0], NAMES)
        for line, row in zip(data.splitlines(), rows[1:]):
            r = db.parse_record(line)
            self.assertEqual(row[0], " ".join(r["OwnerLastName"].split()))
            self.assertEqual(row[10], r["PropertyTypeCode"])
            self.assertAlmostEqual(float(row[15]), int(r["DollarAmount"]) / 100)

    def test_fields(self):
        line = rec(OwnerLastName="  DOE,  JOHN", OwnerZipCode="787011234", HolderZipCode="737010000",
                   NRFlag="Y", DollarAmount="0000006270", NumberOfShares="0000000012",
                   ReportDate="03/16/1992", HolderName='THE "BIG" BANK')
        rc, out, err = run(line + "\r\n", "-v", "header=0")
        row = next(csv.reader(io.StringIO(out)))
        self.assertEqual(row[0], "DOE, JOHN")
        self.assertEqual(row[7], "78701-1234")
        self.assertEqual(row[24], "73701")
        self.assertEqual(row[15], "62.70")
        self.assertEqual(row[16], "12")
        self.assertEqual(row[17], "1992-03-16")
        self.assertEqual(row[18], 'THE "BIG" BANK')

    def test_fixed_round_trip(self):
        line = rec(OwnerLastName="DOE", NRFlag="N", DollarAmount="0000000100",
                   NumberOfShares="0000000000", ReportDate="01/02/2003")
        rc, out, err = run(line.rstrip() + "\r\n", "-v", "fmt=fixed")
        self.assertEqual(out, line + "\n")

    def test_stream_and_pipe(self):
        line = rec(OwnerLastName="DOE", NRFlag="N", DollarAmount="0000000005")
        rc, out, err = run(line * 3, "-v", "stream=1", "-v", "fmt=pipe", "-v", "propid=1")
        rows = out.splitlines()
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[1].split("|")[15], "0.05")
        self.assertEqual(len(rows[0].split("|")), 28)

    def test_strict_drops_bad_records(self):
        good = rec(OwnerLastName="DOE", NRFlag="N", DollarAmount="0000000005")
        bad = rec(OwnerLastName="BAD", NRFlag="N", DollarAmount="12.50", ReportDate="1992-03-16")
        rc, out, err = run(good + "\n" + bad + "\n", "-v", "strict=1", "-v", "header=0")
        self.assertEqual(out.count("\n"), 1)
        self.assertIn("DollarAmount is not all digits", err)
        self.assertIn("ReportDate is not MM/DD/YYYY", err)
        self.assertIn("1 dropped", err)

    def test_bad_option(self):
        rc, out, err = run("", "-v", "fmt=xml")
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
