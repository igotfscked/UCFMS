"""Make a fillable copy of Comptroller form 53-120 (Heir Claim Form).

The 53-120 PDF Jake supplied has no form fields (unlike 53-125/53-126), so this
adds named text fields at the boxes on the form. The printed form itself is not
changed except page 1: its document checklist (Proof of SSN, Proof of ID, Death
Certificate, ... with that claim's Property IDs) is removed, leaving the header,
mail-to and instructions intro and an empty bordered area. Twelve reserved fields,
F120_DocReq01..F120_DocReq12, sit in that area for the checklist UCFMS will build
per claim from property type codes (logic to be written). Run once on a PC; the
result, 53-120.pdf, is the blank that the FDF files point at.

    python3 make_fillable_53120.py ORIGINAL_53-120.pdf 53-120.pdf

Field positions are in PDF points from the bottom-left of a US-letter page,
measured from the form's own label positions.
"""
import sys

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (ArrayObject, ContentStream, BooleanObject, DictionaryObject, FloatObject,
                           NameObject, NumberObject, TextStringObject)

# (page, name, x0, y0, x1, y1). Names start F120_ so they never collide with
# 53-125/53-126 fields (both have FAX, Phone) when forms are merged into one package.
ROW = lambda k: (681 - 25 * k, 695 - 25 * k)     # B. CLAIMANT INFORMATION rows
FIELDS = [
    (0, "F120_ClaimID1", 456, 698, 590, 718),
    (1, "F120_ClaimID2", 456, 728, 590, 748),
    (1, "F120_LastName", 23, *ROW(0)[:1], 170, ROW(0)[1]),
    (1, "F120_FirstName", 173, ROW(0)[0], 250, ROW(0)[1]),
    (1, "F120_MiddleName", 253, ROW(0)[0], 330, ROW(0)[1]),
    (1, "F120_MaidenName", 333, ROW(0)[0], 400, ROW(0)[1]),
    (1, "F120_SSN", 403, ROW(0)[0], 570, ROW(0)[1]),
    (1, "F120_AddlLast", 23, ROW(1)[0], 170, ROW(1)[1]),
    (1, "F120_AddlFirst", 173, ROW(1)[0], 250, ROW(1)[1]),
    (1, "F120_AddlMiddle", 253, ROW(1)[0], 330, ROW(1)[1]),
    (1, "F120_AddlMaiden", 333, ROW(1)[0], 400, ROW(1)[1]),
    (1, "F120_AddlSSN", 403, ROW(1)[0], 570, ROW(1)[1]),
    (1, "F120_MailAddr", 23, ROW(2)[0], 400, ROW(2)[1]),
    (1, "F120_DayPhone", 403, ROW(2)[0], 570, ROW(2)[1]),
    (1, "F120_City", 23, ROW(3)[0], 270, ROW(3)[1]),
    (1, "F120_State", 273, ROW(3)[0], 400, ROW(3)[1]),
    (1, "F120_ZIP", 403, ROW(3)[0], 570, ROW(3)[1]),
    (1, "F120_Email", 23, ROW(4)[0], 400, ROW(4)[1]),
    (1, "F120_FAX", 403, ROW(4)[0], 570, ROW(4)[1]),
]
# Page 1 checklist area (PDF y 527 down to 150): 12 reserved multiline rows.
DOCREQ_ROWS = 12
FIELDS += [(0, f"F120_DocReq{k + 1:02d}", 25, 524 - 31 * (k + 1), 587, 524 - 31 * k)
           for k in range(DOCREQ_ROWS)]
MULTILINE = {name for _, name, *_ in FIELDS if name.startswith("F120_DocReq")}

# Content-stream operations 243..1048 of page 1 in Rev. 7-15/8 draw the checklist
# rows (text, checkboxes, Property ID lines and the box sides). Checked by marker text.
CHECKLIST_OPS = (243, 1049)


def clean_page1(writer):
    page = writer.pages[0]
    cs = ContentStream(page.get_contents(), writer)
    ops = cs.operations
    a, b = CHECKLIST_OPS
    assert ops[a + 6][1] == b"Tj" and ops[b][1] == b"m", "53-120 revision differs; re-measure CHECKLIST_OPS"
    sides = ContentStream(None, writer)
    sides.set_data(b"q 0.5 w 0 J 0 G 20 527 m 20 150 l S 592 527 m 592 150 l S Q")
    cs.operations = ops[:a] + sides.operations + ops[b:]
    page.replace_contents(cs)


def main(src, dst, field_list=None, prep=None):
    field_list = FIELDS if field_list is None else field_list
    writer = PdfWriter(clone_from=PdfReader(src))
    if prep:
        prep(writer)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"), NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
    })
    font_ref = writer._add_object(font)
    fields = ArrayObject()
    for page_no, name, x0, y0, x1, y1 in field_list:
        page = writer.pages[page_no]
        w = DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"), NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/FT"): NameObject("/Tx"), NameObject("/T"): TextStringObject(name),
            NameObject("/Rect"): ArrayObject([FloatObject(v) for v in (x0, y0, x1, y1)]),
            NameObject("/F"): NumberObject(4), NameObject("/DA"): TextStringObject("/Helv 9 Tf 0 g"),
            NameObject("/MK"): DictionaryObject(), NameObject("/P"): page.indirect_reference,
        })
        if name in MULTILINE:
            w[NameObject("/Ff")] = NumberObject(4096)
            w[NameObject("/DA")] = TextStringObject("/Helv 8 Tf 0 g")
        ref = writer._add_object(w)
        if "/Annots" not in page:
            page[NameObject("/Annots")] = ArrayObject()
        page["/Annots"].append(ref)
        fields.append(ref)
    writer._root_object[NameObject("/AcroForm")] = DictionaryObject({
        NameObject("/Fields"): fields,
        NameObject("/DA"): TextStringObject("/Helv 9 Tf 0 g"),
        NameObject("/DR"): DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/Helv"): font_ref})}),
        NameObject("/NeedAppearances"): BooleanObject(True),
    })
    with open(dst, "wb") as f:
        writer.write(f)
    print(dst, len(field_list), "fields")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], prep=clean_page1)
