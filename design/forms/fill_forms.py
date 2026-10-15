"""PC-side bulk filler: turn downloaded UCFMS .fdf files into filled PDFs and claim packages.

For one form, just double-click its .fdf: Adobe Acrobat or Reader opens the form
already filled. Use this script for many claims at once.

    pip install pypdf
    python fill_forms.py FOLDER

FOLDER holds the downloaded .fdf members and the blank forms 53-120.pdf,
53-125.pdf and 53-126.pdf. For each claim it writes:

    FOLDER/filled/Fnnnnnnn.pdf   53-120 claim form, filled
    FOLDER/filled/Annnnnnn.pdf   53-125 or 53-126 authorization, filled
    FOLDER/filled/Hnnnnnnn.pdf   53-111-A Affidavit of Heirship (heir claims only)
    FOLDER/filled/Pnnnnnnn.pdf   the claim package: 53-120 (page 1 instructions and
                                 checklist, page 2 claimant), the authorization, then
                                 the affidavit's form pages (supporting documents go behind)

The affidavit's page 1 is the Comptroller's instruction sheet for it and is left
out of the package. Fields stay editable so a user can still type the SSN or
correct a value in Adobe before printing.
"""
import os
import re
import sys
from collections import defaultdict

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

FIELD = re.compile(r"/T \(((?:\\.|[^\\)])*)\) /V \(((?:\\.|[^\\)])*)\)")
FORM = re.compile(r"/F \(([^)]*)\)")


def unesc(s):
    return re.sub(r"\\(.)", r"\1", s)


def fill(fdf_path):
    text = open(fdf_path, encoding="latin-1").read()
    form = os.path.join(os.path.dirname(fdf_path), FORM.search(text).group(1))
    values = {unesc(t): unesc(v) for t, v in FIELD.findall(text)}
    writer = PdfWriter(clone_from=PdfReader(form))
    for page in (p for p in writer.pages if "/Annots" in p):
        writer.update_page_form_field_values(page, values, auto_regenerate=False)
    writer.set_need_appearances_writer(True)
    return writer


def save(writer, path):
    with open(path, "wb") as f:
        writer.write(f)
    print("wrote", path)


def merge_form_fonts(package, sources):
    """PdfWriter.append keeps only the first form's AcroForm font resources (/DR);
    53-125/53-126 fields use /HeBo, so copy every source's fonts into the package."""
    fonts = package._root_object["/AcroForm"]["/DR"]["/Font"]
    for src in sources:
        for name, ref in PdfReader(src).trailer["/Root"]["/AcroForm"]["/DR"]["/Font"].items():
            if name not in fonts:
                fonts[NameObject(name)] = ref.get_object().clone(package)


def main(folder):
    out_dir = os.path.join(folder, "filled")
    os.makedirs(out_dir, exist_ok=True)
    claims = defaultdict(dict)                    # claim number -> {"F"|"A"|"H": path}
    for name in sorted(os.listdir(folder)):
        m = re.fullmatch(r"([FAH])(\d{7})\.fdf", name, re.I)
        if m:
            claims[m.group(2)][m.group(1).upper()] = os.path.join(folder, name)
    for num, parts in sorted(claims.items()):
        filled = {}
        for kind, path in parts.items():
            w = fill(path)
            out = os.path.join(out_dir, f"{kind}{num}.pdf")
            save(w, out)
            filled[kind] = out
        package = PdfWriter()
        if "F" in filled:
            package.append(filled["F"])
        if "A" in filled:
            package.append(filled["A"])
        if "H" in filled:
            package.append(filled["H"], pages=[1, 2])
        merge_form_fonts(package, [filled[k] for k in "FAH" if k in filled])
        package.set_need_appearances_writer(True)
        save(package, os.path.join(out_dir, f"P{num}.pdf"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
