"""Make a fillable copy of the Texas Affidavit of Heirship (Comptroller form 53-111-A).

The PDF Jake supplied has no form fields, and its first form page is a scan.
This adds only the fields UCFMS can fill (reported owner, claim number, name of
the deceased person); everything else is completed by hand by the witness in
front of a notary. Field names start AOH_ so they don't collide with the other
forms when merged into one package.

    python3 make_fillable_affidavit.py ORIGINAL.pdf 53-111-A.pdf
"""
import sys

from make_fillable_53120 import main

# (page, name, x0, y0, x1, y1) in PDF points; page 0 is the instruction sheet
FIELDS = [
    (1, "AOH_OwnerName1", 92, 664, 302, 685),
    (1, "AOH_ClaimNo1", 350, 664, 588, 685),
    (1, "AOH_Decedent1", 342, 646, 588, 659),
    (1, "AOH_Decedent2", 354, 500, 588, 512),
    (2, "AOH_OwnerName2", 92, 745, 302, 768),
    (2, "AOH_ClaimNo2", 350, 745, 588, 768),
]

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], FIELDS)
