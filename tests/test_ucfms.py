import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ucfms import db  # noqa: E402
from ucfms.layout import FIELDS, RECORD_LENGTH  # noqa: E402
from ucfms.sample import write_sample  # noqa: E402


def rec(**kw):
    return "".join(kw.get(n, "").ljust(w)[:w] for n, w in FIELDS)


class LayoutTests(unittest.TestCase):
    def test_record_length(self):
        self.assertEqual(RECORD_LENGTH, 469)
        self.assertEqual(len(FIELDS), 27)

    def test_parse_positions(self):
        line = rec(OwnerLastName="DOE", OwnerZipCode="787011234", HolderIDNumber="740550600002",
                   PropertyTypeCode="AC01", HolderName="FIRST BANK", LastUpdatedDate="03/16/1992")
        r = db.parse_record(line)
        self.assertEqual(r["OwnerLastName"], "DOE")
        self.assertEqual(r["OwnerZipCode"], "787011234")
        self.assertEqual(r["PropertyTypeCode"], "AC01")
        self.assertEqual(r["HolderName"], "FIRST BANK")
        self.assertEqual(r["LastUpdatedDate"], "03/16/1992")
        self.assertEqual(line[201:213], "740550600002")  # columns 202-213
        self.assertEqual(line[278:282], "FIRS")          # HolderName starts at 279
        self.assertEqual(line[192:201], "787011234")  # columns 193-201

    def test_short_line_padded(self):
        self.assertEqual(db.parse_record("SMITH")["OwnerLastName"], "SMITH")

    def test_numbers_and_dates(self):
        self.assertEqual(db.parse_number("  1,234.50"), 1234.5)
        self.assertEqual(db.parse_number("0000012345", 2), 123.45)
        self.assertIsNone(db.parse_number(""))
        self.assertEqual(db.parse_date("03/07/2021"), "2021-03-07")
        self.assertEqual(db.parse_date("20210307"), "2021-03-07")
        self.assertIsNone(db.parse_date("99/99/9999"))


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        src = os.path.join(cls.tmp.name, "sample.txt")
        write_sample(src, 2000)
        extra = os.path.join(cls.tmp.name, "extra.txt")
        with open(extra, "w") as f:  # continuous stream, no newlines
            f.write(rec(OwnerLastName="ZYLSTRA", OwnerFirstName="ANN", OwnerZipCode="78701",
                        PropertyTypeCode="CK01", DollarAmount="0000002500", HolderName="TEXAS FIRST BANK"))
            f.write(rec(OwnerLastName="ZYLSTRA HOLDINGS LLC", OwnerZipCode="787019999",
                        PropertyTypeCode="AC01", DollarAmount="0000010000", HolderName="FIRST BANK OF TEXAS"))
        cls.con = db.connect(os.path.join(cls.tmp.name, "t.db"))
        cls.n, cls.bad = db.load_file(cls.con, src)
        db.load_file(cls.con, extra)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def brute(self, pred):
        return sum(1 for r in self.con.execute("SELECT * FROM records") if pred(dict(r)))

    def test_loaded(self):
        self.assertEqual((self.n, self.bad), (2000, 0))

    def test_owner_last_prefix_case_insensitive(self):
        total, rows = db.search(self.con, {"owner_last": "smith"}, limit=5000)
        self.assertEqual(total, self.brute(lambda r: r["OwnerLastName"].startswith("SMITH")))
        self.assertTrue(any(r["OwnerLastName"] == "SMITHSON" for r in rows))

    def test_business_name(self):
        total, _ = db.search(self.con, {"owner_last": "Acme Oil"})
        self.assertEqual(total, self.brute(lambda r: r["OwnerLastName"].startswith("ACME OIL")))
        self.assertGreater(total, 0)

    def test_holder(self):
        total, _ = db.search(self.con, {"holder": "wells fargo"})
        self.assertEqual(total, self.brute(lambda r: r["HolderName"].startswith("WELLS FARGO")))

    def test_holder_words_any_order(self):
        total, rows = db.search(self.con, {"holder_words": "bank texas first"})
        self.assertEqual(total, 2)

    def test_owner_words(self):
        total, rows = db.search(self.con, {"owner_name_words": "ann zylstra"})
        self.assertEqual([r["OwnerFirstName"] for r in rows], ["ANN"])

    def test_zip_5_and_9(self):
        self.assertEqual(db.search(self.con, {"zip": "78701"})[0],
                         self.brute(lambda r: r["OwnerZipCode"][:5] == "78701"))
        self.assertEqual(db.search(self.con, {"zip": "78701-9999"})[0], 1)
        self.assertEqual(db.search(self.con, {"zip": "770"})[0],
                         self.brute(lambda r: r["OwnerZipCode"].startswith("770")))

    def test_type_plus_zip(self):
        z = self.con.execute("SELECT owner_zip5 FROM records WHERE PropertyTypeCode='AC01' LIMIT 1").fetchone()[0]
        total, rows = db.search(self.con, {"property_type": "ac01", "zip": z})
        self.assertEqual(total, self.brute(
            lambda r: r["PropertyTypeCode"] == "AC01" and r["OwnerZipCode"][:5] == z))
        self.assertTrue(all(r["PropertyTypeCode"] == "AC01" for r in rows))

    def test_amount_and_sort(self):
        total, rows = db.search(self.con, {"min_amount": "4000"}, sort="amount", limit=1000)
        self.assertTrue(rows and all(r["amount"] >= 4000 for r in rows))
        _, z = db.search(self.con, {"owner_last": "zylstra holdings"})
        self.assertEqual(z[0]["amount"], 100.0)
        self.assertEqual([r["amount"] for r in rows], sorted((r["amount"] for r in rows), reverse=True))

    def test_property_type_descriptions(self):
        _, rows = db.search(self.con, {"property_type": "CK01"}, limit=5)
        self.assertTrue(rows)
        self.assertTrue(all(r["PropertyTypeDescription"] == "Cashier's Check" for r in rows))
        rec = db.get_record(self.con, rows[0]["id"])
        self.assertEqual(rec["PropertyTypeDescription"], "Cashier's Check")
        types = {t["code"]: t for t in db.property_types(self.con)}
        self.assertEqual(types["IR99"]["description"], "Aggregate Ira Bal < $50")
        self.assertTrue(types["CK01"]["in_data"])
        self.assertFalse(types["ZZZZ"]["in_data"])
        self.assertEqual(db.describe_type("QQ99"), "(code not in list)")

    def test_requires_criterion(self):
        with self.assertRaises(ValueError):
            db.search(self.con, {})


REAL = os.path.join(os.path.dirname(__file__), "..", "sample", "ucf_real_sample_104.txt")


@unittest.skipUnless(os.path.exists(REAL), "real sample records not present (not distributed publicly)")
class RealSampleTests(unittest.TestCase):
    """Jake's 104 real records (pasted 2026-10-14, trailing blanks lost)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.con = db.connect(os.path.join(cls.tmp.name, "r.db"))
        cls.n, cls.bad = db.load_file(cls.con, REAL)
        cls.rows = [dict(r) for r in cls.con.execute("SELECT * FROM records")]

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def test_every_line_is_one_record(self):
        self.assertEqual((self.n, self.bad), (104, 0))

    def test_fields_well_formed(self):
        import re
        for r in self.rows:
            self.assertRegex(r["HolderIDNumber"], r"^\d{12}$")
            self.assertRegex(r["HolderReportYear"], r"^(19|20)\d\d$")
            self.assertRegex(r["SequenceNumber"], r"^\d{6}$")
            self.assertIn(r["NRFlag"], ("Y", "N"))
            self.assertRegex(r["HolderState"], r"^[A-Z]{2}$")
            self.assertTrue(r["HolderName"] and r["HolderName"][0] != " ")
            self.assertIsNotNone(r["report_date_iso"])
            for f in ("UpdatedDate", "LastUpdatedDate"):
                self.assertTrue(re.fullmatch(r"\d\d/\d\d/\d{4}", r[f]), (f, r[f]))

    def test_nr_flag_descriptions(self):
        _, rows = db.search(self.con, {"owner_last": "A D J AUDIO"})
        self.assertEqual((rows[0]["NRFlag"], rows[0]["NRFlagDescription"]), ("Y", "Claim filed"))
        _, rows = db.search(self.con, {"owner_last": "A & D OIL"})
        self.assertEqual(rows[0]["NRFlagDescription"], "No claim filed")
        self.assertEqual(db.describe_nr_flag("R"), "Unknown (R)")

    def test_implied_cents(self):
        oil = [r for r in self.rows if r["OwnerLastName"] == "A & D OIL CO"][0]
        self.assertEqual(oil["DollarAmount"], "0000006270")
        self.assertEqual(oil["amount"], 62.70)

    def test_known_record(self):
        r = [r for r in self.rows if r["OwnerLastName"] == "A & A AUTO SERV"][0]
        self.assertEqual(r["OwnerCity"], "CORPUS CHRISTI")
        self.assertEqual(r["property_id"], "7405506000021989UT01000098")
        self.assertEqual(r["HolderName"], "AEP TX CENTRAL")
        self.assertEqual(r["HolderCity"], "CANTON")
        self.assertEqual((r["UpdatedDate"], r["LastUpdatedDate"]), ("06/07/1989", "03/16/1992"))

    def test_search_by_property_id_and_holder(self):
        _, rows = db.search(self.con, {"property_id": "7405506000021989UT01000098"})
        self.assertEqual([r["OwnerLastName"] for r in rows], ["A & A AUTO SERV"])
        self.assertEqual(db.search(self.con, {"property_id": "7405506000021989UT01"})[0], 2)
        self.assertGreater(db.search(self.con, {"holder_words": "first city bank"})[0], 1)


@unittest.skipUnless(os.path.exists(os.path.join(os.path.dirname(REAL), "ucf_real_sample_2009_6.txt")),
                     "real sample records not present (not distributed publicly)")
class Real2009SampleTests(unittest.TestCase):
    """Jake's 6 later records (report year 2009), pasted 2026-10-14."""

    def test_loads_and_keys_are_unique(self):
        path = os.path.join(os.path.dirname(REAL), "ucf_real_sample_2009_6.txt")
        with tempfile.TemporaryDirectory() as tmp:
            con = db.connect(os.path.join(tmp, "r.db"))
            self.assertEqual(db.load_file(con, path), (6, 0))
            rows = [dict(r) for r in con.execute("SELECT * FROM records")]
            con.close()
        self.assertTrue(all(r["HolderReportYear"] == "2009" for r in rows))
        abbot = sorted(r["property_id"] for r in rows if r["OwnerLastName"] == "ABBOT")
        self.assertEqual(abbot, ["2331026550012009MI02000018", "2331026550012009MI02000019"])
        keys = {r["OwnerLastName"].ljust(40) + r["property_id"] for r in rows}
        self.assertEqual(len(keys), 6)
        self.assertEqual([r["amount"] for r in rows if r["OwnerFirstName"] == "KELLY M"], [0.01])


if __name__ == "__main__":
    unittest.main()
