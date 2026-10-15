"""Generate CLAIMS_LAYOUT.md and COBOL copybooks for the UCFMS claims files.

Edit the field lists below and rerun:  python3 claims_layout.py
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))


def plen(pic):
    """Byte length of a DISPLAY picture such as X(10), 9(8), 9(11)V99."""
    n = 0
    for ch, rep in re.findall(r"([X9])(?:\((\d+)\))?", pic.replace("V", "")):
        n += int(rep) if rep else 1
    return n


# (cobol name, picture, description)   picture None = group header
RECORDS = [
    dict(
        name="Claim header", cpy="UCFCLMH", prefix="CH", dsn="HLQ.CLAIM.HDR",
        org="KSDS, one record per claim", key="CH-CLAIM-ID (bytes 1-10)",
        fields=[
            ("TRACKING", None, "Claim tracking data"),
            ("CLAIM-ID", "9(10)", "Claim ID number, from the UCF.CTL counter. Primary key"),
            ("CREATED-BY", "X(8)", "User ID that opened the claim. Start of the BYUSER key"),
            ("STATUS", "X(1)", "O=OPEN S=SUBMITTED C=CLOSED X=CANCELED. Start of the BYSTAT key"),
            ("CLAIM-ID-2", "9(10)", "Copy of CLAIM-ID, so the BYUSER and BYSTAT keys are unique"),
            ("DATE-OPENED", "9(8)", "YYYYMMDD"),
            ("TIME-OPENED", "9(6)", "HHMMSS"),
            ("DATE-SUBMITTED", "9(8)", "YYYYMMDD, zeros until submitted"),
            ("SUBMITTED-BY", "X(8)", "User ID"),
            ("DATE-CLOSED", "9(8)", "YYYYMMDD, zeros until closed"),
            ("CLOSED-BY", "X(8)", "User ID"),
            ("DATE-CANCELED", "9(8)", "YYYYMMDD, zeros unless canceled"),
            ("CANCELED-BY", "X(8)", "User ID"),
            ("STATUS-DATE", "9(8)", "Date the current status began; used for aging"),
            ("COMPTROLLER-REF", "X(20)", "Comptroller's own claim number once submitted (proposed)"),
            ("CLOSE-NOTE", "X(60)", "Outcome as reported by the Comptroller, or cancel reason"),
            ("CLAIMANT", None, "Claimant info"),
            ("CLMT-TYPE", "X(1)", "I=Individual (form 53-126) B=Business (form 53-125)"),
            ("CLMT-LAST-NAME", "X(40)", "Last name, or business name when CLMT-TYPE=B"),
            ("CLMT-FIRST-NAME", "X(30)", ""),
            ("CLMT-MIDDLE-INIT", "X(1)", ""),
            ("CLMT-RELATION", "X(1)", "O=Owner H=Heir A=Agent B=Business officer (starting list)"),
            ("CLMT-ADDR-1", "X(30)", ""),
            ("CLMT-ADDR-2", "X(30)", ""),
            ("CLMT-CITY", "X(30)", ""),
            ("CLMT-STATE", "X(2)", ""),
            ("CLMT-ZIP", "X(9)", "ZIP+4, no hyphen"),
            ("CLMT-PHONE", "X(15)", ""),
            ("CLMT-FAX", "X(15)", "Forms 53-125/53-126 ask for it"),
            ("CLMT-EMAIL", "X(60)", ""),
            ("CLMT-REP-NAME", "X(40)", "Business claims: printed name of the claimant's representative"),
            ("CLMT-REP-TITLE", "X(30)", "Business claims: representative's title"),
            ("ITEMS", None, "Property item chain and totals"),
            ("NEXT-ITEM-SEQ", "9(4)", "Next item sequence number to assign (starts 0001)"),
            ("ACTIVE-ITEMS", "9(4)", "Count of items with status A"),
            ("TOTAL-AMOUNT", "9(11)V99", "Sum of active items' DollarAmount"),
            ("CONTROL", None, "Update control"),
            ("LAST-UPD-DATE", "9(8)", "YYYYMMDD"),
            ("LAST-UPD-TIME", "9(6)", "HHMMSS"),
            ("LAST-UPD-USER", "X(8)", ""),
            ("VERSION", "9(8)", "Adds 1 on every rewrite; screens compare it before updating"),
            ("NOTES", "X(120)", "Free text"),
            ("FILLER", "X(16)", "Room to grow"),
        ]),
    dict(
        name="Claim item", cpy="UCFCLMI", prefix="CI", dsn="HLQ.CLAIM.ITEM",
        org="KSDS, one record per property on a claim", key="CI-CLAIM-ID + CI-ITEM-SEQ (bytes 1-14)",
        fields=[
            ("KEY", None, "Key: claim ID + sequence = the chain"),
            ("CLAIM-ID", "9(10)", "Claim this item belongs to"),
            ("ITEM-SEQ", "9(4)", "0001, 0002, ... in the order added; never reused"),
            ("PROPERTY", None, "Link to the owner record"),
            ("OWNER-KEY", "X(66)", "Full owner KSDS key: OwnerLastName 40 + Property ID 26. BYPROP key"),
            ("ITEM-STATUS", "X(1)", "A=Active R=Removed"),
            ("ADDED-DATE", "9(8)", "YYYYMMDD"),
            ("ADDED-USER", "X(8)", ""),
            ("REMOVED-DATE", "9(8)", "zeros while active"),
            ("REMOVED-USER", "X(8)", ""),
            ("SNAPSHOT", None, "Copy of tape fields when added (kept if the record leaves the tape)"),
            ("OWNER-FIRST-NAME", "X(30)", ""),
            ("OWNER-ZIP", "X(9)", ""),
            ("HOLDER-NAME", "X(40)", ""),
            ("PROPERTY-TYPE", "X(4)", ""),
            ("DOLLAR-AMOUNT", "9(8)V99", "Same format as the tape: implied cents"),
            ("NUMBER-OF-SHARES", "9(10)", ""),
            ("REPORT-DATE", "X(10)", "MM/DD/YYYY as on tape"),
            ("FILLER", "X(20)", "Room to grow"),
        ]),
    dict(
        name="Claim audit", cpy="UCFAUD", prefix="AU", dsn="HLQ.CLAIM.AUDIT",
        org="ESDS, append only, one record per change", key="none (read in time order; batch sorts by claim)",
        fields=[
            ("WHEN", None, ""),
            ("DATE", "9(8)", "YYYYMMDD"),
            ("TIME", "9(8)", "HHMMSSth"),
            ("USER", "X(8)", ""),
            ("TRAN", "X(4)", "CICS transaction, or ISPF"),
            ("TERM", "X(8)", "Terminal or TSO session"),
            ("WHAT", None, ""),
            ("CLAIM-ID", "9(10)", ""),
            ("ITEM-SEQ", "9(4)", "0000 for header changes"),
            ("ACTION", "X(2)", "CR create, AI add item, RI remove item, EC edit claimant, SU submit, CL close, CX cancel"),
            ("STATUS-BEFORE", "X(1)", ""),
            ("STATUS-AFTER", "X(1)", ""),
            ("AMOUNT", "9(11)V99", "Item amount, or claim total for header actions"),
            ("OWNER-KEY", "X(66)", "For item actions"),
            ("NOTE", "X(60)", ""),
            ("FILLER", "X(17)", ""),
        ]),
    dict(
        name="Control record", cpy="UCFCTL", prefix="CT", dsn="HLQ.UCF.CTL",
        org="KSDS, a few named records", key="CT-REC-ID (bytes 1-8)",
        fields=[
            ("REC-ID", "X(8)", "CLAIMNO = claim counter; LOADSTAT = last load; CHKSTAT = last check"),
            ("LAST-CLAIM-ID", "9(10)", "CLAIMNO: last ID issued; read for update, add 1, rewrite"),
            ("LAST-UPD-DATE", "9(8)", ""),
            ("LAST-UPD-USER", "X(8)", ""),
            ("DATA", "X(66)", "LOADSTAT / CHKSTAT detail (record counts, dates, error counts)"),
        ]),
]

AIXES = [
    ("HLQ.CLAIM.HDR.BYUSER", "HLQ.CLAIM.HDR", "CREATED-BY + STATUS + CLAIM-ID-2", 10, 19, "UNIQUEKEY",
     "My claims, by status: generic key user (8) or user + status (9)"),
    ("HLQ.CLAIM.HDR.BYSTAT", "HLQ.CLAIM.HDR", "STATUS + CLAIM-ID-2", 18, 11, "UNIQUEKEY",
     "All claims in one status, oldest ID first (reports, work queues)"),
    ("HLQ.CLAIM.ITEM.BYPROP", "HLQ.CLAIM.ITEM", "OWNER-KEY", 14, 66, "NONUNIQUEKEY",
     "Which claims include this property"),
]


def layout(rec):
    rows, off = [], 0
    for name, pic, desc in rec["fields"]:
        if pic is None:
            rows.append((name, None, None, None, desc))
            continue
        n = plen(pic)
        rows.append((name, pic, off + 1, n, desc))
        off += n
    return rows, off


def copybook(rec, rows, total):
    p = rec["prefix"]
    out = [f"      *----------------------------------------------------------*",
           f"      * {rec['cpy']:8} {rec['name'].upper():<20} {rec['dsn']:<25}*",
           f"      * RECORD LENGTH {total:<4}  GENERATED BY CLAIMS_LAYOUT.PY      *",
           f"      *----------------------------------------------------------*",
           f"       01  {p}-RECORD."]
    for name, pic, start, n, desc in rows:
        if pic is None:
            out.append(f"           05  {p}-{name}.")
            continue
        lvl = "10" if any(r[1] is None for r in rows) else "05"
        nm = "FILLER" if name == "FILLER" else f"{p}-{name}"
        out.append(f"               {lvl}  {nm:<28} PIC {pic}." if lvl == "10" else f"           {lvl}  {nm:<32} PIC {pic}.")
    return "\n".join(out) + "\n"


md = ["# UCFMS claims files: field layouts", "",
      "Status: **draft for Jake's review**, 2026-10-14. Companion to "
      "[APP_DESIGN.md](APP_DESIGN.md) section 4. Generated by `claims_layout.py` "
      "in this folder, which also writes the COBOL copybooks in "
      "[copybooks/](copybooks/); edit the field lists there and rerun it.", "",
      "All fields are DISPLAY (no packed or binary), so records read cleanly with "
      "IDCAMS `PRINT CHARACTER`. Dates are `YYYYMMDD`, zeros when not set. "
      "Amounts are implied cents, like the tape's DollarAmount.", "",
      "## How the files fit together", "",
      "```",
      "CLAIM.HDR  0000001234  JSMITH   O 0000001234  opened 20261014 ...  claimant ...",
      "   |  CLAIM.ITEM keys, read in order with one generic browse on the claim ID:",
      "   +-- 0000001234 0001  -> owner key SMITH...1740123456712019CK13000014",
      "   +-- 0000001234 0002  -> owner key SMITH...1750987654302018AC01000203",
      "   +-- 0000001234 0003  -> owner key SMITH...1750987654302018AC02000077 (removed)",
      "CLAIM.AUDIT  every create / add / remove / submit / close / cancel, in time order",
      "UCF.CTL      CLAIMNO record hands out the next claim ID",
      "```", "",
      "**The \"linked list\" of properties.** Jake described each claim's properties "
      "as a linked list. In a KSDS that chain is the key itself: claim ID + a 4-digit "
      "sequence number. A browse that starts at `0000001234 0000` and reads forward "
      "until the claim ID changes returns the claim's properties in the order they "
      "were added. No next/previous pointers are stored, so nothing can break when an "
      "item is removed: a removed item keeps its place with status `R`, and "
      "`CH-NEXT-ITEM-SEQ` in the header gives the next number. Up to 9,999 items per claim.", "",
      "**Claims by user, by status.** An alternate index on the header, not a separate "
      "lookup file. Its key is user ID + status + claim ID, three fields placed next to "
      "each other at the front of the header for this purpose. Because the AIX is in "
      "the header's upgrade set, VSAM keeps it right automatically whenever a claim "
      "changes status, inside the same CICS unit of work; a lookup KSDS would need the "
      "program to delete and re-add its record on every status change. Each key is "
      "unique, so no AIX record grows large. A browse on the user ID alone lists that "
      "user's claims grouped O, S, C, X; on user + `O` it lists only their open claims. "
      "A second index on status + claim ID gives the same view across all users.", "",
      "\"User\" here is the user who opened the claim. If claims get handed between "
      "staff, an `ASSIGNED-TO` field with its own index can be added later.", "",
      "**Not stored on purpose:** SSN, TIN, date of birth or bank details for the "
      "claimant. Identity proof goes to the Comptroller with the claim; keeping it here "
      "would make these files sensitive.", "",
      "**Seed record.** Each claims file is created with one blank record whose claim "
      "ID is 0, so the empty KSDS can be opened (JCL job UCFCLDEF). Programs and browses "
      "skip claim ID 0; real IDs start at 1.", "",
      "## Datasets and indexes", "",
      "| Dataset | Organisation | Key | Record length |", "|---|---|---|---|"]
built = []
for rec in RECORDS:
    rows, total = layout(rec)
    built.append((rec, rows, total))
    md.append(f"| `{rec['dsn']}` | {rec['org']} | {rec['key']} | {total} |")
md += ["", "| Alternate index | Over | Key fields | Offset | Length | Type | Answers |",
       "|---|---|---|---:|---:|---|---|"]
for a in AIXES:
    md.append(f"| `{a[0]}` | `{a[1]}` | {a[2]} | {a[3]} | {a[4]} | {a[5]} | {a[6]} |")
md += ["", "Offsets are 0-based as IDCAMS `KEYS(length offset)` wants them; the tables "
       "below use 1-based columns.", ""]
for rec, rows, total in built:
    md += [f"## {rec['name']}: `{rec['dsn']}` (copybook {rec['cpy']}, {total} bytes)", "",
           "| Field | PIC | Start | Len | Notes |", "|---|---|---:|---:|---|"]
    for name, pic, start, n, desc in rows:
        if pic is None:
            md.append(f"| **{desc or name}** | | | | |")
        else:
            nm = "FILLER" if name == "FILLER" else f"{rec['prefix']}-{name}"
            md.append(f"| {nm} | `{pic}` | {start} | {n} | {desc} |")
    md.append("")
    os.makedirs(os.path.join(HERE, "copybooks"), exist_ok=True)
    with open(os.path.join(HERE, "copybooks", rec["cpy"] + ".cpy"), "w") as f:
        f.write(copybook(rec, rows, total))

# sanity: AIX offsets match the header/item layouts
hdr = {r[0]: r for r in built[0][1] if r[1]}
assert hdr["CREATED-BY"][2] - 1 == 10 and hdr["STATUS"][2] - 1 == 18
assert hdr["CLAIM-ID-2"][2] - 1 + 10 == 10 + 19
itm = {r[0]: r for r in built[1][1] if r[1]}
assert itm["OWNER-KEY"][2] - 1 == 14

md += ["## Status codes and dates", "",
       "| STATUS | Meaning | Date field set | Items editable |", "|---|---|---|---|",
       "| `O` | OPEN | DATE-OPENED | yes |",
       "| `S` | SUBMITTED | DATE-SUBMITTED | no |",
       "| `C` | CLOSED | DATE-CLOSED | no |",
       "| `X` | CANCELED | DATE-CANCELED | no |", "",
       "Every status change also sets STATUS-DATE, LAST-UPD-*, adds 1 to VERSION, and "
       "writes an audit record, all in one unit of work. The BYUSER and BYSTAT indexes "
       "follow the change automatically.", ""]
with open(os.path.join(HERE, "CLAIMS_LAYOUT.md"), "w") as f:
    f.write("\n".join(md))
for rec, rows, total in built:
    print(rec["cpy"], total)
