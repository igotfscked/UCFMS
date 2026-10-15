"""Checks the Soundex table and logic in cobol/UCFSNDX.cbl.

The COBOL can't be compiled here, so this test reads the routine's 26-letter
code table straight from the source and runs a line-for-line Python mirror of
its PROCEDURE DIVISION against standard American Soundex examples.
"""
import os
import re
import unittest

SRC = os.path.join(os.path.dirname(__file__), "..", "cobol", "UCFSNDX.cbl")
ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def table():
    digits = re.search(r"VALUE '([0-9*]{26})'", open(SRC).read()).group(1)
    return dict(zip(ALPHA, digits))


def soundex(name, codes):
    out, prev = "", None
    for ch in name.upper()[:40]:
        if len(out) == 4:
            break
        if ch not in ALPHA:
            continue
        c = codes[ch]
        if not out:
            out, prev = ch, c
        elif c == "*":        # H, W: skipped, don't separate
            pass
        elif c == "0":        # vowel: separates equal codes
            prev = "0"
        elif c != prev:
            out, prev = out + c, c
    return (out + "000")[:4] if out else "    "


class SoundexTests(unittest.TestCase):
    def test_table(self):
        groups = {"0": "AEIOUY", "*": "HW", "1": "BFPV", "2": "CGJKQSXZ",
                  "3": "DT", "4": "L", "5": "MN", "6": "R"}
        self.assertEqual(table(), {ch: d for d, chs in groups.items() for ch in chs})

    def test_codes(self):
        codes = table()
        for name, want in {
            "ROBERT": "R163", "RUPERT": "R163", "RUBIN": "R150",
            "ASHCRAFT": "A261", "ASHCROFT": "A261", "TYMCZAK": "T522",
            "PFISTER": "P236", "HONEYMAN": "H555",
            "JOHN": "J500", "JON": "J500", "JHON": "J500",
            "MUHAMMAD": "M530", "MOHAMMED": "M530", "MOHAMED": "M530",
            "SMITH": "S530", "SMYTH": "S530", "O'BRIEN": "O165", "LEE": "L000",
            "12345": "    ", "": "    ",
        }.items():
            self.assertEqual(soundex(name, codes), want, name)


if __name__ == "__main__":
    unittest.main()
