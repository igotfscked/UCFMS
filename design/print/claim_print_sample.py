"""Sample output of the UCFMS claim print program (UCFCLPRT).

Writes, next to this script:
  CLAIM_PRINT_SAMPLE.txt  133-byte FBA lines (ASA carriage control in column 1),
                          exactly what the batch step writes to SYSOUT
  CLAIM_PRINT_SAMPLE.pdf  how that line data looks once a page printer or an
                          Infoprint PDF transform lays it out (landscape, 132
                          columns, Courier)

Data is the walkthrough claim: real 2009 owner records (ABBOT ALBERT L),
invented claimant contact details.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
W = 132

CLAIM = dict(
    id="0000000001", status="CLOSED", opened=("10/14/2026", "JSMITH"),
    submitted=("10/14/2026", "JSMITH"), closed=("11/02/2026", "JSMITH"),
    ref="", note="COMPTROLLER PAID IN FULL",
    name="ABBOTT, ALBERT L", rel="OWNER", addr=["4417 WOODLAWN AVE", "TEXARKANA TX 75503"],
    phone="903-555-0187", email="",
)
ITEMS = [
    ("0001", "ABBOT ALBERT L", "2331026550012009MI02000018", "MI02", "MINERAL ROYALTY",
     "SUNOCO PARTNERS MKTG & TERMINAL LP", "12/01/2009", 3),
    ("0002", "ABBOT ALBERT L", "2331026550012009MI02000019", "MI02", "MINERAL ROYALTY",
     "SUNOCO PARTNERS MKTG & TERMINAL LP", "12/01/2009", 4),
]
RUN = ("11/02/2026", "14:05", "JSMITH")


def money(cents):
    return f"{cents // 100:,}.{cents % 100:02d}"


def line(cc, text=""):
    assert len(text) <= W, (len(text), text)
    return cc + text.ljust(W)


def build():
    c, out, page = CLAIM, [], 1
    left = "UCFMS  CLAIM PACKAGE"
    mid = "TEXAS UNCLAIMED PROPERTY"
    right = f"RUN {RUN[0]} {RUN[1]}   PAGE {page:>4}"
    hdr = left + mid.center(W - len(left) - len(right)) + right
    out.append(line("1", hdr))
    out.append(line(" ", "UCFCLPRT".ljust(W - 12) + f"USER {RUN[2]:<7}"))
    out.append(line("0", f"CLAIM ID   {c['id']}      STATUS  {c['status']:<10}"
                         f"OPENED {c['opened'][0]} {c['opened'][1]:<8}  "
                         f"SUBMITTED {c['submitted'][0]} {c['submitted'][1]:<8}  "
                         f"CLOSED {c['closed'][0]} {c['closed'][1]}"))
    out.append(line(" ", f"COMPTROLLER REF  {c['ref'] or '(none)':<22}CLOSING NOTE  {c['note']}"))
    out.append(line("0", f"CLAIMANT   {c['name']:<40}RELATIONSHIP  {c['rel']}"))
    out.append(line(" ", f"           {c['addr'][0]}"))
    out.append(line(" ", f"           {c['addr'][1]:<40}PHONE  {c['phone']:<16}EMAIL  {c['email'] or '(none)'}"))
    cols = (f"{'SEQ':<4} {'OWNER NAME':<22} {'PROPERTY ID':<26} {'TYPE':<4} {'DESCRIPTION':<18} "
            f"{'HOLDER':<30} {'REPORT DT':<10} {'AMOUNT':>8}")
    out.append(line("0", cols))
    out.append(line(" ", " ".join("-" * len(p) for p in
                                  ["SEQ ", "-" * 22, "-" * 26, "TYPE", "-" * 18, "-" * 30, "-" * 10, "-" * 8])))
    total = 0
    for seq, owner, pid, typ, desc, holder, rdate, cents in ITEMS:
        total += cents
        out.append(line(" ", f"{seq:<4} {owner:<22} {pid} {typ} {desc:<18} {holder[:30]:<30} "
                             f"{rdate} {money(cents):>8}"))
    pad = len(cols) - 8
    out.append(line(" ", " " * pad + "-" * 8))
    out.append(line(" ", f"{'ACTIVE ITEMS':>{pad - 22}} {len(ITEMS):>4}      CLAIM TOTAL {money(total):>8}"))
    out.append(line("0", "AMOUNTS ARE THE COMPTROLLER'S DOLLARAMOUNT FOR EACH ACTIVE ITEM. REMOVED ITEMS ARE NOT PRINTED"
                         " (PARM ITEMS=ALL PRINTS THEM)."))
    out.append(line("-", f"*** END OF CLAIM {c['id']} ***"))
    return out


def write_pdf(lines, path):
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.pdfgen import canvas
    pw, ph = landscape(letter)
    size = 8.2
    lead = size * 1.45
    cv = canvas.Canvas(path, pagesize=(pw, ph))
    cv.setTitle("UCFMS claim package sample")
    x0, y = 0.45 * 72, ph - 0.55 * 72
    cv.setFont("Courier", size)
    for ln in lines:
        cc, text = ln[0], ln[1:].rstrip()
        if cc == "1" and y < ph - 0.6 * 72:
            cv.showPage(); cv.setFont("Courier", size); y = ph - 0.55 * 72
        y -= {"0": 2, "-": 3}.get(cc, 1) * lead if cc != "1" else lead
        cv.drawString(x0, y, text)
    cv.save()


if __name__ == "__main__":
    lines = build()
    with open(os.path.join(HERE, "CLAIM_PRINT_SAMPLE.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    write_pdf(lines, os.path.join(HERE, "CLAIM_PRINT_SAMPLE.pdf"))
    print(len(lines), "lines")
