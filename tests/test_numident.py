"""NUMIDENT loader, search and owner matching. All people and SSNs here are
invented (SSNs starting 9 are never issued); no NARA data is used."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ucfms import db, numident  # noqa: E402
from ucfms.layout import FIELDS  # noqa: E402
from ucfms.numident import LAYOUTS, fixed_record  # noqa: E402


def ucf(**kw):
    return "".join(kw.get(n, "").ljust(w)[:w] for n, w in FIELDS)


DEATH = [
    fixed_record(kind="D", REFERENCE_NUM="00000000001", SSN="900000001", ENTRY_CODE="T",
                 CYCLE_DATE="19950301", FIRST="GEORGE", MIDDLE="ALLEN", LAST="ABBIT",
                 DOB="04121911", SEX="1", ZIP_RESIDENCE="787010000", DOD_DTH="02001995"),
    fixed_record(kind="D", SSN="900000002", ENTRY_CODE="T", FIRST="GEORGE", MIDDLE="B",
                 LAST="ABBIT", DOB="00001920", ZIP_RESIDENCE="10001", DOD_DTH="07041980"),
    fixed_record(kind="D", SSN="900000003", ENTRY_CODE="T", FIRST="GERALD", LAST="ABBIT",
                 DOB="01011915", ZIP_RESIDENCE="787050000", DOD_DTH="01011990"),
    fixed_record(kind="D", SSN="900000004", ENTRY_CODE="T", FIRST="GEO", LAST="ABBOTT",
                 DOB="01011915", ZIP_RESIDENCE="787010000", DOD_DTH="01011990"),
    "Z" * 499,  # a record NARA masked
]
CLAIM = [
    fixed_record(kind="C", SSN="900000001", ENTRY_CODE="D", FIRST="GEORGE", MIDDLE="A",
                 LAST="ABBIT", DOB="04121911", MTH_NAME_FIRST="MARY", MTH_NAME_LAST="JONES",
                 FTH_NAME_FIRST="HENRY", FTH_NAME_LAST="ABBIT", POB_CITY="AUSTIN",
                 POB_STATE_COUNTRY="TX", CLAIM_DATE="03011995", DOD_CLAIM="02101995"),
]
SS5 = [
    fixed_record(kind="S", SSN="900000002", ENTRY_CODE="A", FIRST="GEORGE", LAST="ABBIT",
                 DOB="01011920", POB_STATE_COUNTRY="CA", POB_FOREIGN_IND="f"),
]


class LayoutTests(unittest.TestCase):
    def test_fields_fit_and_do_not_overlap(self):
        for kind, fields in LAYOUTS.items():
            used = set()
            for name, start, n in fields:
                cols = set(range(start, start + n))
                self.assertTrue(cols <= set(range(1, 501)), name)
                self.assertFalse(cols & used, f"{kind} {name} overlaps")
                used |= cols

    def test_names_at_same_columns_in_all_kinds(self):
        pos = {k: {n: s for n, s, _ in f} for k, f in LAYOUTS.items()}
        for name in ("NUMI-SSN", "NUMI-NH-NAME-LAST", "NUMI-NH-NAME-FIRST", "NUMI-DOB"):
            self.assertEqual(len({pos[k][name] for k in "DCS"}), 1, name)

    def test_record_positions(self):
        line = DEATH[0]
        self.assertEqual(len(line), 500)
        self.assertEqual(line[12:21], "900000001")       # 13-21
        self.assertEqual(line[68:73], "ABBIT")           # 69-88
        self.assertEqual(line[144:152], "02001995")      # 145-152 DOD
        self.assertEqual(line[486], "1")                 # 487 number of postings

    def test_dates(self):
        self.assertEqual(numident.parse_mdy("04121911"), ("1911-04-12", 1911))
        self.assertEqual(numident.parse_mdy("02001995"), ("1995-02", 1995))
        self.assertEqual(numident.parse_mdy("XX001920"), ("1920", 1920))
        self.assertEqual(numident.parse_mdy("0000XXXX"), (None, None))
        self.assertEqual(numident.parse_ymd("19950301"), "1995-03-01")

    def test_place_of_birth(self):
        self.assertEqual(numident.pob_description("CA", ""), "California")
        self.assertEqual(numident.pob_description("CA", "f"), "Canada")
        self.assertEqual(numident.pob_description("GMf", ""), "Germany")
        self.assertEqual(numident.pob_description("TX", " "), "Texas")

    def test_soundex(self):
        for name, code in (("ROBERT", "R163"), ("RUPERT", "R163"), ("ASHCRAFT", "A261"),
                           ("TYMCZAK", "T522"), ("MUHAMMAD", "M530"), ("MOHAMED", "M530"),
                           ("O'BRIEN", "O165"), ("123", "")):
            self.assertEqual(numident.soundex(name), code, name)

    def test_soundex_matches_cobol(self):
        from test_soundex import soundex as cobol_mirror, table
        codes = table()
        for name in ("SMITH", "SMYTH", "LEE", "PFISTER", "JACKSON", "WASHINGTON", "HONEYMAN", "VAN DYKE"):
            self.assertEqual(numident.soundex(name), cobol_mirror(name, codes).strip(), name)

    def test_second_death_posting(self):
        line = list(DEATH[2])
        second = fixed_record(kind="D", FIRST="GERRY", LAST="ABBIT", DOD_DTH="01021990")
        line[36 + 150:186 + 150] = second[36:186]
        line[486] = "2"
        occ = list(numident.death_occurrences("".join(line)))
        self.assertEqual([o for o, _ in occ], [1, 2])
        self.assertEqual(occ[1][1]["NUMI-NH-NAME-FIRST"].strip(), "GERRY")
        self.assertEqual(occ[1][1]["NUMI-SSN"], "900000003")


class LoadSearchMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.tmp.name
        with open(os.path.join(t, "owners.txt"), "w") as f:
            f.write(ucf(OwnerLastName="ABBIT", OwnerFirstName="GEORGE A", OwnerCity="AUSTIN",
                        OwnerZipCode="787010000", HolderName="FIRST BANK") + "\n")
            f.write(ucf(OwnerLastName="A & T CATTLE CO", OwnerZipCode="78701") + "\n")
        for name, recs in (("NARA.D01.DTH", DEATH), ("NARA.C01.CLM", CLAIM), ("NARA.S01.R130915.SS5", SS5)):
            with open(os.path.join(t, name), "w") as f:
                f.write("\n".join(recs) + "\n")
        cls.con = db.connect(os.path.join(t, "t.db"))
        db.load_file(cls.con, os.path.join(t, "owners.txt"))
        cls.results = {name: numident.load_file(cls.con, os.path.join(t, name))
                       for name in ("NARA.D01.DTH", "NARA.C01.CLM", "NARA.S01.R130915.SS5")}

    def test_load_counts(self):
        self.assertEqual(self.results["NARA.D01.DTH"], (4, 1, 0))
        self.assertEqual(numident.describe_counts(self.con), {"Death": 4, "Claim": 1, "SS-5": 1})

    def test_kind_from_file_name(self):
        kinds = dict(self.con.execute("SELECT source_file, kind FROM numident_load_log"))
        self.assertEqual(sorted(k for k in kinds.values()), ["C", "D", "S"])

    def test_search_by_name_and_ssn(self):
        total, rows = numident.search(self.con, {"last": "abbit", "first": "geo"})
        self.assertEqual(total, 4)   # 2 death + 1 claim + 1 SS-5
        total, rows = numident.search(self.con, {"ssn": "900-00-0001"})
        self.assertEqual({r["kind"] for r in rows}, {"D", "C"})
        claim = [r for r in rows if r["kind"] == "C"][0]
        self.assertEqual(claim["father"], "HENRY ABBIT")
        self.assertEqual(claim["pob"], "Texas")

    def test_search_sounds_like_and_zip(self):
        total, _ = numident.search(self.con, {"last": "ABBOT", "sounds_like": "1"})
        self.assertEqual(total, 6)
        total, _ = numident.search(self.con, {"zip": "78701"})
        self.assertEqual(total, 2)
        with self.assertRaises(ValueError):
            numident.search(self.con, {"first": "GEORGE"})

    def test_match_owner(self):
        owner = db.search(self.con, {"owner_last": "ABBIT"})[1][0]
        rec = db.get_record(self.con, owner["id"])
        cands = numident.match_owner(self.con, rec)
        self.assertEqual([c["ssn"] for c in cands], ["900000001", "900000002"])  # GERALD dropped
        best = cands[0]
        self.assertIn("residence ZIP at death", best["why"])
        self.assertIn("middle initial", best["why"])
        self.assertIn("born in Texas", best["why"])
        self.assertEqual(best["kinds"], "DC")
        self.assertEqual(best["father"], "HENRY ABBIT")
        self.assertIn("middle initial differs", cands[1]["why"])
        sounds = numident.match_owner(self.con, rec, sounds_like=True)
        self.assertIn("900000004", [c["ssn"] for c in sounds])

    def test_business_not_matched(self):
        owner = db.search(self.con, {"owner_last": "A & T"})[1][0]
        self.assertEqual(numident.match_owner(self.con, db.get_record(self.con, owner["id"])), [])

    def test_only_ucf_names(self):
        path = os.path.join(self.tmp.name, "NARA.D02.DTH")
        with open(path, "w") as f:
            f.write(fixed_record(kind="D", SSN="900000009", LAST="ZZYZX", FIRST="ANN") + "\n")
            f.write(fixed_record(kind="D", SSN="900000010", LAST="ABBIT", FIRST="ANN") + "\n")
        con = db.connect(os.path.join(self.tmp.name, "only.db"))
        db.load_file(con, os.path.join(self.tmp.name, "owners.txt"))
        self.assertEqual(numident.load_file(con, path, only_names=numident.ucf_last_names(con)), (1, 0, 1))

    def test_csv_and_fixed_conversion(self):
        path = os.path.join(self.tmp.name, "death.csv")
        with open(path, "w") as f:
            f.write("NUMI_SSN,NUMI_NH_NAME_FIRST_DTH_1,NUMI_NH_NAME_LAST_DTH_1,NUMI_DOB_DTH_1,"
                    "NUMI_DOD_DTH_1,NUMI_ZIP_RESIDENCE_1,EXTRA\n")
            f.write("900000020,ANN,ZYLSTRA,03151901,12251977,78701,x\n")
        con = db.connect(os.path.join(self.tmp.name, "csv.db"))
        self.assertEqual(numident.load_file(con, path)[0], 1)
        self.assertEqual(numident.iter_file.unmapped, ["EXTRA"])
        r = numident.search(con, {"last": "ZYLSTRA"})[1][0]
        self.assertEqual((r["kind"], r["dob"], r["dod"], r["zip_residence"]), ("D", "1901-03-15", "1977-12-25", "78701"))
        out = os.path.join(self.tmp.name, "death.fixed")
        self.assertEqual(numident.extract(path, out), (1, 0))
        line = open(out).read().rstrip("\n")
        self.assertEqual(len(line), 500)
        self.assertEqual(line[68:75], "ZYLSTRA")
        self.assertEqual(line[144:152], "12251977")
        self.assertEqual(numident.extract(path, out, only_names={"ABBIT"}), (0, 1))


if __name__ == "__main__":
    unittest.main()
