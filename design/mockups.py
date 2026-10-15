"""Generate 24x80 3270 mockups (ISPF + CICS) for UCFMS into SCREENS.md."""
import re
import sys

W, H = 80, 24

# Each screen: id, title, ispf panel, cics map, tranid, what it does,
# cmd label, body (rows 3-21, max 19 lines), pf keys, sample message, notes
S = []

def scr(**k):
    S.append(k)

scr(key="menu", title="UCFMS - Main Menu", panel="UCFP000", map="UCFM000", tran="UCF0",
    purpose="Shell entry point. Shows the four modules; options the user is not authorised for are shown as `(no access)` and rejected.",
    cmd="Option", body="""
  Unclaimed Funds Management System                  User . . : JSMITH
  Texas Comptroller UCF data                         Access . : CLAIMS

  Select an option:

     1  Query      Search owner records, select records for a claim
     2  Claims     Create, add to, remove from and process claims
     3  Reports    Claim and owner-file reports
     4  Admin      Data file administration          (no access)

     X  Exit

  Owner file loaded . : 2026-10-01   Records . : 8,412,077
  Basket  . . . . . . : 0 records
""", pf="F1=Help  F3=Exit", msg="",
    notes="`=n` from any panel jumps straight to module n (ISPF fast path). In CICS the same is typed in the Selection field on any screen.")

scr(key="q1", title="UCFMS - Query - Search Criteria", panel="UCFPQ01", map="UCFMQ01", tran="UCFQ",
    purpose="Enter search criteria. At least one indexed field (last name, property ID or holder ID, holder name, owner ZIP) is required; the rest narrow the result.",
    cmd="Command", body="""
  Indexed fields (fill at least one):
    Owner last name / business  . . SMITH___________________________________
    Property ID or holder ID  . . . __________________________
    Holder name . . . . . . . . . . ________________________________________
    Owner ZIP (5 or 9)  . . . . . . 78701____

  Filters:
    Owner first name  . . . . . . . JOHN__________________________
    Property type code  . . . . . . ____   (blank = all, ? = list)
    Owner city  . . . . . . . . . . ______________________________
    Owner state . . . . . . . . . . __
    Holder report year  . . . . . . ____
    Minimum dollar amount . . . . . __________

  Name match  . . . . . . . . . . 1  1=Starts with  2=Exact  3=Sounds like
  Exclude records already claimed N  (Y/N)
""", pf="F1=Help  F3=Exit  F4=Type list  F5=Basket  F12=Cancel", msg="Enter criteria and press Enter",
    notes="Sounds like (3) uses Soundex, so JON, JOHN and JHON (J500) or MUHAMMAD and MOHAMMED (M530) match, on last name and, if entered, first name. It is optional: if the Soundex lookup file isn't built, option 3 is refused with a message and every other search works unchanged. The property ID field takes the full 26-byte ID or just the 12-digit holder ID, which lists all of that holder's properties. F4 or `?` in the type field pops up the 116 property type codes. Validation errors (non-numeric ZIP, unknown type, nothing indexed) put the cursor on the field.")

scr(key="q2", title="UCFMS - Query - Results", panel="UCFPQ02", map="UCFMQ02", tran="UCFQ",
    purpose="Scrollable result list. Line commands act on one row; the claim column shows whether the property is already on a claim.",
    cmd="Command", scroll=True, body="""
  Search: last name SMITH, first JOHN, ZIP 78701           Rows 1-12 of 37
  Line cmds: S=Select to basket  D=Detail  C=Claims on property  U=Unselect

  Cmd Owner name               ZIP   Type      Amount Holder             Clm
  --- ------------------------ ----- ---- ----------- ------------------ ---
   _  SMITH JOHN A             78701 AC01      125.40 FIRST NATL BANK
   S  SMITH JOHN A             78701 CK13    1,204.00 ACME SUPPLY CO
   _  SMITH JOHN B             78701 MI02       88.12 PERMIAN ROYALTY LP OPN
   _  SMITH JOHN C             78701 IN03   15,000.00 LONE STAR LIFE INS
   _  SMITH JOHN D             78701 AC02        5.00 CAPITAL CU         CLS
   _  SMITH JOHN E             78701 SC01      310.77 TX TRANSFER AGENT
   _  SMITH JOHN F             78701 CK01       42.00 FROST BANK         SUB
   _  SMITH JOHN G             78701 UT01       19.95 AUSTIN ENERGY
   _  SMITH JOHNNY             78701 AC01      640.00 BANK OF AMERICA
   _  SMITH JOHNNY R           78701 CK15       77.10 WELLS FARGO
   _  SMITH JOHNSON INC        78701 MS16    2,500.00 HEB GROCERY
   _  SMITH JOHNSTON MARY      78701 AC03    9,812.33 CHASE BANK

  Basket: 1 record  $1,204.00
""", pf="F1=Help  F3=Exit  F5=Basket  F6=Claim  F7=Up  F8=Down  F12=Cancel",
    msg="1 record added to basket",
    notes="Clm is worked out from the claims files (claim-item index on the owner key, then the claim header): `OPN` = on an OPEN claim, `SUB` = on a SUBMITTED claim, `CLS` = was on a CLOSED claim, blank = never claimed. Selecting an `OPN` or `SUB` row is refused. F6 goes to Claims with the basket. CICS pages by saving the first/last key of the page in the COMMAREA.")

scr(key="q3", title="UCFMS - Query - Record Detail", panel="UCFPQ03", map="UCFMQ03", tran="UCFQ",
    purpose="All 27 fields of one owner record, plus its claim history.",
    cmd="Command", body="""
  Owner . . . SMITH                                    JOHN A
  Address . . 1200 CONGRESS AVE                  APT 4B

  City/St/ZIP AUSTIN                         TX 787010000
  Holder  . . ACME SUPPLY CO                           ID 174012345671
              PO BOX 2210
  City/St/ZIP HOUSTON                        TX 770010000
  Property ID 1740123456712019CK13000014    Type CK13 Vendor Check
  Amount  . .     1,204.00   Shares  . .            0    Report year 2019
  NR flag . . Y  Claim filed with the Comptroller at some point
  Trans dates 03/01/2017 to 03/01/2017        Report date 11/01/2019
  Claim date  ----------   Last updated 02/01/2024  (Comptroller fields)
  UCFMS . . . not on any UCFMS claim

  Claims on this property:
    (none)
""", pf="F1=Help  F3=Exit  F6=Select to basket  F12=Cancel", msg="",
    notes="Claim date is the tape's UpdatedDate (formerly RecentClaimDate); UCFMS never changes it. NR flag is the tape's NRFlag: Y = a claim was filed with the Comptroller at some point, N = none (Jake; being checked against the dates). The UCFMS line is worked out from the claims files; the tape's dates are not used to infer claim status because they don't track NRFlag (VALIDATION.md). Address line 3 and holder address lines 2-3 show when present. When the property is on claims, each claim ID, status and date is listed and the cursor-select on a claim ID opens Claim Detail.")

scr(key="q4", title="UCFMS - Selection Basket", panel="UCFPQ04", map="UCFMQ04", tran="UCFQ",
    purpose="Records picked in Query, waiting to go onto a claim.",
    cmd="Command", scroll=True, body="""
  Line cmds: R=Remove from basket  D=Detail              Rows 1-3 of 3

  Cmd Owner name               Property ID                Type      Amount
  --- ------------------------ -------------------------- ---- -----------
   _  SMITH JOHN A             1740123456712019CK13000014 CK13    1,204.00
   _  SMITH JOHN A             1750987654302018AC01000203 AC01      125.40
   _  SMITH JOHNNY             1941234567802020AC01001150 AC01      640.00

                                           Total  3 records  1,969.40

  Send basket to:
    1  New claim
    2  Existing claim . . ID __________
  Choice  . . _
""", pf="F1=Help  F3=Exit  F7=Up  F8=Down  F12=Cancel", msg="",
    notes="Choice 1 opens Claimant Entry; choice 2 adds the basket to the given claim (must be OPEN). The basket empties after a successful hand-off.")

scr(key="c1", title="UCFMS - Claims - Find Claims", panel="UCFPC01", map="UCFMC01", tran="UCFC",
    purpose="Find claims by ID, claimant, status or property, then open one.",
    cmd="Command", scroll=True, body="""
  Claim ID __________  Claimant ________________  Status _  Opened by ________
  Property ID __________________________  Created ________ to ________

  Line cmds: S=Open  P=Process (change status)  X=Cancel claim

  Cmd Claim ID   Claimant              Status    Items      Amount Updated
  --- ---------- --------------------- --------- ----- ----------- ----------
   _  0000001234 SMITH JOHN A          OPEN          2    1,329.40 2026-10-14
   _  0000001229 SMITH MARY L          SUBMITTED     1      640.00 2026-10-12
   _  0000001201 SMITH ESTATE OF R     SUBMITTED     6   25,301.88 2026-10-02
   _  0000001188 SMITHSON HOLDINGS     CANCELED      1    2,500.00 2026-09-20
   _  0000001150 SMITH JOHN D          CLOSED        1        5.00 2026-08-30



                                                         Rows 1-5 of 5
""", pf="F1=Help  F3=Exit  F5=New claim  F7=Up  F8=Down  F12=Cancel", msg="",
    notes="Status codes O, S, C, X (OPEN, SUBMITTED, CLOSED, CANCELED). Opened by: a user ID, `*` for your own claims, blank for everyone; with a status it reads the BYUSER index, with only a status the BYSTAT index. P and X are refused on CLOSED or CANCELED claims.")

scr(key="c2", title="UCFMS - Claims - Claim Detail", panel="UCFPC02", map="UCFMC02", tran="UCFC",
    purpose="One claim: header, claimant and items. Items can be added or removed only while the claim is OPEN.",
    cmd="Command", scroll=True, body="""
  Claim 0000001234   Status OPEN       since 2026-10-14   Version 3
  Claimant  SMITH JOHN A                   Relationship OWNER
            1200 CONGRESS AVE APT 4B, AUSTIN TX 78701   Phone 512-555-0142
  Created   2026-10-14 JSMITH        Updated 2026-10-14 JSMITH

  Line cmds: R=Remove item  D=Owner record detail
  Cmd Owner name           Property ID                Type      Amount Status
  --- -------------------- -------------------------- ---- ----------- -------
   _  SMITH JOHN A         1740123456712019CK13000014 CK13    1,204.00 ACTIVE
   _  SMITH JOHN A         1750987654302018AC01000203 AC01      125.40 ACTIVE
   _  SMITH JOHN A         1750987654302018AC02000077 AC02        9.00 REMOVED


                                     Active  2 items  Total  1,329.40

""", pf="F1=Help F3=Exit F4=Claimant F5=Add basket F6=Process F10=History F12=Cancel",
    msg="Item removed",
    notes="Every change is one unit of work. If someone else changed the claim since this screen was shown (version number moved on), the update is refused with `Claim changed by another user - redisplayed` and the screen is refreshed. F10 shows the audit trail.")

scr(key="c3", title="UCFMS - Claims - Claimant", panel="UCFPC03", map="UCFMC03", tran="UCFC",
    purpose="Claimant details for a new claim (from the basket) or for editing an existing one.",
    cmd="Command", body="""
  New claim from basket: 3 records  $1,969.40

  Claimant type . . . . I  I=Individual (form 53-126)  B=Business (53-125)
  Claimant name . . . . SMITH_______________________ JOHN__________ A
  Relationship  . . . . 1  1=Owner  2=Heir  3=Agent  4=Business officer
  Address line 1  . . . 1200 CONGRESS AVE_____________
  Address line 2  . . . APT 4B________________________
  City  . . . . . . . . AUSTIN________________________
  State / ZIP . . . . . TX  78701____
  Phone . . . . . . . . 512-555-0142     Fax . . _______________
  Email . . . . . . . . ______________________________________________
  Business only:
    Representative  . . ________________________________________
    Title . . . . . . . ______________________________

  Notes . . . . . . . . ____________________________________________________

  Press Enter to create the claim, F12 to cancel.
""", pf="F1=Help  F3=Exit  F12=Cancel", msg="",
    notes="Claimant type picks the Comptroller authorization form: I fills 53-126, B fills 53-125 (business name goes in the name field; representative and title are printed on the form). Relationship codes are a starting list. One claim may hold records under several owner names or spellings, so the claimant name does not have to match the owner records. On Enter the claim ID is assigned and Claim Detail opens.")

scr(key="c4", title="UCFMS - Claims - Process Claim", panel="UCFPC04", map="UCFMC04", tran="UCFC",
    purpose="Move a claim to its next status. Only the transitions allowed from the current status are offered.",
    cmd="Command", body="""
  Claim 0000001229   Claimant SMITH MARY L
  Current status  SUBMITTED  since 2026-10-12      Items 1   Amount 640.00

  New status:
     3  CLOSED     Comptroller has finished with the claim
     4  CANCELED   Withdrawn; records become claimable again
  Choice  . . _

  Closing note  . . ______________________________________________________
                    ______________________________________________________
  Effective date  . 2026-10-14

  Press Enter to apply. The change is logged with your user ID.
""", pf="F1=Help  F3=Exit  F12=Cancel", msg="",
    notes="Only the moves allowed from the current status are listed: an OPEN claim offers 2 SUBMITTED and 4 CANCELED, a SUBMITTED claim offers 3 CLOSED and 4 CANCELED. The Comptroller's outcome (paid, denied) goes in the note. The choices come from the lifecycle table, so a rule change does not change this screen.")

scr(key="r1", title="UCFMS - Reports", panel="UCFPR01", map="UCFMR01", tran="UCFR",
    purpose="Report catalog. Online reports show on screen at once; batch reports are submitted as jobs.",
    cmd="Command", scroll=True, body="""
  Line cmds: S=Run  B=Run in batch (online reports too)

  Cmd ID     Report                                   Mode    Last run
  --- ------ ---------------------------------------- ------- ----------
   _  CLM001 Open claims by status and age            Online  2026-10-14
   _  CLM002 Closed and canceled claims, date range   Online  2026-10-13
   _  CLM003 Claims by property type code             Batch   2026-10-01
   _  CLM010 Claim packages (printer, PDF or CSV)     Batch   ----------
   _  CLM011 Claim forms 53-120 + 53-125/53-126     Batch   ----------
   _  OWN001 Owner file profile (counts, dollars)     Batch   2026-10-01
   _  OWN002 Owner records by holder report year      Batch   ----------




                                                         Rows 1-7 of 7
""", pf="F1=Help  F3=Exit  F7=Up  F8=Down  F12=Cancel", msg="",
    notes="New reports are new catalog rows; the screen does not change.")

scr(key="r2", title="UCFMS - Report CLM001 - Open Claims", panel="UCFPR02", map="UCFMR02", tran="UCFR",
    purpose="Example online report result. Every online report uses this same list layout with its own columns.",
    cmd="Command", scroll=True, body="""
  As of 2026-10-14 11:20

  Status         Claims        Amount   0-30 days  31-90 days  Over 90
  ------------- -------  ------------  ----------  ----------  -------
  OPEN               42     58,201.17          30          10        2
  SUBMITTED          26    133,937.50          15          11        0
  ------------- -------  ------------  ----------  ----------  -------
  Total              68    192,138.67          45          21        2

  Age is days since the claim entered its current status.



""", pf="F1=Help  F3=Exit  F7=Up  F8=Down  F11=Print  F12=Cancel", msg="",
    notes="F11 sends the same report to the batch print route.")

scr(key="a1", title="UCFMS - Data File Administration", panel="UCFPA01", map="UCFMA01", tran="UCFA",
    purpose="Admin menu. Each option builds JCL from a skeleton and submits it, except file status which is online.",
    cmd="Option", body="""
  Owner file . . UCF.PROD.OWNER.KSDS        Loaded 2026-10-01  8,412,077 recs
  Claims files . UCF.PROD.CLAIM.*           Last check 2026-10-13  0 errors

   1  File status        Record counts, last load, CICS open/closed state
   2  Define files       Owner KSDS/AIX (UCFDEF), claims files
   3  Load from tape     UCFLOAD: tape to owner KSDS, rebuild indexes
   4  Rebuild indexes    BLDINDEX for one or all alternate indexes
   5  Consistency check  Claims vs owner file, totals, AIX counts
   6  Backup / restore   REPRO or DFSMSdss of owner and claims files
   7  CICS files         Close or open files around batch jobs

  Tape DSN  . . UCF.TAPE.INPUT_______________   Volser . . UCF001
  Job card  . . //JSMITHA  JOB (ACCT),'UCF ADMIN',CLASS=A,MSGCLASS=X____
""", pf="F1=Help  F3=Exit  F12=Cancel", msg="",
    notes="Admin authority only. Options 2, 3 and 6 ask for confirmation (next screen) because they replace data. The option list is a catalog, like Reports.")

scr(key="a2", title="UCFMS - Admin - Confirm Job", panel="UCFPA02", map="UCFMA02", tran="UCFA",
    purpose="Confirmation before submitting a job that replaces or deletes data.",
    cmd="Command", body="""
  You are about to submit:  3  Load from tape

    UCFDEF   delete and redefine UCF.PROD.OWNER.KSDS and its AIXs
    UCFLOAD  load tape UCF.TAPE.INPUT volser UCF001, rebuild AIXs

  This REPLACES all 8,412,077 owner records.
  Claims are not changed. Run option 5 afterwards to list claim items
  whose record is not on the new tape.

  CICS file UCFOWNR is OPEN. It will be closed before the job and
  opened after it ends.

  Type LOAD to confirm . . ____    then press Enter.
""", pf="F1=Help  F3=Exit  F7=Browse JCL  F12=Cancel", msg="",
    notes="F7 shows the tailored JCL before it is submitted (ISPF: BROWSE of the file-tailoring output).")


def frame(lines):
    top = "+" + "-" * W + "+"
    return "\n".join([top] + ["|" + l + "|" for l in lines] + [top])


def build(s, kind):
    body = s["body"].strip("\n").split("\n")
    assert len(body) <= 19, (s["key"], len(body))
    rows = []
    if kind == "ispf":
        left = s["panel"]
        msg = s["msg"]
        r1 = left.ljust(10) + s["title"].center(W - 20)
        r1 = r1.ljust(W)
        rows.append(r1[:W])
        cmd = f"{s['cmd']} ===> " + "_" * (40 if s.get("scroll") else 56)
        if s.get("scroll"):
            cmd = cmd.ljust(W - 18) + "Scroll ===> PAGE"
        rows.append(cmd)
    else:
        r1 = f"{s['tran']} {s['map']}".ljust(14) + s["title"].center(W - 28) + "2026-10-14".rjust(14)
        rows.append(r1)
        sel = "Selection ===> " + "_" * 30
        rows.append(sel.ljust(W - 16) + "JSMITH  11:20:05")
    rows += body
    while len(rows) < 21:
        rows.append("")
    if kind == "ispf":
        rows.append("")
        rows.append((s["msg"] and ("  " + s["msg"])) or "")
        rows.append(" " + s["pf"])
    else:
        rows.append("")
        rows.append(s["msg"] or "")
        pf = re.sub(r"\bF(\d+)=", r"PF\1=", s["pf"]).replace("Exit", "Back")
        pf = pf.replace("Cancel", "Menu")
        rows.append(pf + "  CLEAR=Exit" if len(pf) < W - 12 else pf)
    out = []
    for r in rows:
        assert len(r) <= W, (s["key"], kind, len(r), r)
        out.append(r.ljust(W))
    assert len(out) == H, (s["key"], kind, len(out))
    return frame(out)


md = ["# UCFMS screen mockups",
      "",
      "Status: **draft for Jake's review**, 2026-10-14. Companion to "
      "[APP_DESIGN.md](APP_DESIGN.md). Generated by `mockups.py` in this folder; "
      "edit the screen bodies there and rerun it rather than editing this file.",
      "",
      "Every screen is drawn at 3270 model 2 size (24 rows x 80 columns; the `+--+` "
      "border is outside the screen). Each screen has an ISPF panel and a CICS BMS map "
      "with the **same body**, so users see the same layout in both. Only the top two "
      "and bottom two rows differ:",
      "",
      "| | ISPF panel | CICS map |",
      "|---|---|---|",
      "| Row 1 | panel ID, title, short message | transaction + map name, title, date |",
      "| Row 2 | `Command ===>` / `Option ===>`, scroll amount on lists | `Selection ===>` (fast path, e.g. `=2`), user ID, time |",
      "| Row 23 | long message | message line |",
      "| Row 24 | F keys | PF keys; F3 is Back, F12 returns to the menu, CLEAR exits |",
      "",
      "Conventions: `____` input field; `_` in the Cmd column is a line-command field. "
      "Data shown is invented.",
      "",
      "## Screen flow",
      "",
      "```",
      "Main Menu (1)",
      " |-1-> Search Criteria (2) --Enter--> Results (3)",
      " |                                     |-D--> Record Detail (4)",
      " |                                     |-F5-> Basket (5)",
      " |                                     '-F6-> Basket (5)",
      " |                                     Basket choice 1 -> Claimant (8) -> Claim Detail (7)",
      " |                                     Basket choice 2 -> Claim Detail (7), basket added",
      " |-2-> Find Claims (6) --S--> Claim Detail (7)",
      " |                     --P--> Process Claim (9)",
      " |                     --F5-> New claim: go to Query (2) to fill a basket",
      " |                           Claim Detail: F4 -> Claimant (8), F6 -> Process Claim (9)",
      " |-3-> Reports (10) --S--> online result (11), or job submitted",
      " '-4-> Admin (12) --options 2, 3, 6--> Confirm Job (13)",
      "F3 goes back one screen, F12 returns to the menu, =n jumps to module n.",
      "```",
      "",
      "## Screen index",
      "",
      "| # | Screen | ISPF panel | CICS map | Tran |",
      "|---|---|---|---|---|"]
for i, s in enumerate(S, 1):
    md.append(f"| {i} | [{s['title'].replace('UCFMS - ', '')}](#{i}-{s['panel'].lower()}--{s['map'].lower()}) | {s['panel']} | {s['map']} | {s['tran']} |")
md.append("")
for i, s in enumerate(S, 1):
    md += [f"## {i}. {s['panel']} / {s['map']}", "",
           f"**{s['title']}.** {s['purpose']}", "",
           "ISPF panel:", "", "```", build(s, "ispf"), "```", "",
           "CICS map:", "", "```", build(s, "cics"), "```", ""]
    if s.get("notes"):
        md += [s["notes"], ""]

open(sys.argv[1], "w").write("\n".join(md))
print(len(S), "screens")
