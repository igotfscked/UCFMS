"""Build the UCFMS animated walkthrough page.

Usage: python3 build_walkthrough.py OUT.html

Screens use the same 24x80 builder as ../mockups.py, so ISPF and CICS chrome
match SCREENS.md. In a body, [[text]] marks characters the user types during
the step and {{text}} marks a highlighted area. Scenario records come from
../../sample/ucf_real_sample_2009_6.txt (real 2009 records); claimant contact
details and claim notes are invented examples.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "..", "mockups.py")).read()
ns = {}
exec(src[: src.index("\nmd = [")], ns)          # S (screens) and build()
SCREENS = {s["key"]: s for s in ns["S"]}
build = ns["build"]

MARK = re.compile(r"\[\[(.*?)\]\]|\{\{(.*?)\}\}")


def parse_body(body):
    """Strip markers; return clean body and (row, col, len, kind, text) marks."""
    lines = body.strip("\n").split("\n")
    clean, marks = [], []
    for r, line in enumerate(lines):
        out, col, pos = "", 0, 0
        for m in MARK.finditer(line):
            out += line[pos:m.start()]
            text = m.group(1) if m.group(1) is not None else m.group(2)
            kind = "type" if m.group(1) is not None else "hl"
            marks.append((r, len(out), len(text), kind, text))
            out += text
            pos = m.end()
        out += line[pos:]
        clean.append(out)
    return "\n".join(clean), marks


def screen(step, kind):
    base = dict(SCREENS[step["screen"]])
    body, marks = parse_body(step["body"])
    base.update(body=body, msg=step.get("msg", ""))
    if "title" in step:
        base["title"] = step["title"]
    framed = build(base, kind).split("\n")
    grid = [l[1:-1] for l in framed[1:-1]]
    assert len(grid) == 24 and all(len(g) == 80 for g in grid)
    out_marks = [dict(r=r + 2, c=c, n=n, k=k) for r, c, n, k, _ in marks]
    cmd = step.get("cmd")
    if cmd:
        row = grid[1]
        c = row.index("===> ") + 5
        grid[1] = row[:c] + cmd + row[c + len(cmd):]
        out_marks.insert(0, dict(r=1, c=c, n=len(cmd), k="type"))
    return grid, out_marks


def cics_key(k):
    return re.sub(r"^F(\d+)$", r"PF\1", k)


STEPS = []


def step(chapter, screen_key, caption, body, key="Enter", msg="", cmd=None,
         ispf=None, cics=None, title=None):
    st = dict(chapter=chapter, screen=screen_key, caption=caption, body=body,
              key=key, msg=msg)
    if cmd:
        st["cmd"] = cmd
    if title:
        st["title"] = title
    st["note_ispf"], st["note_cics"] = ispf, cics
    STEPS.append(st)


# ---------------------------------------------------------------- scenario
PID18 = "2331026550012009MI02000018"
PID19 = "2331026550012009MI02000019"
PIDGA = "8409096800022009MS01000042"

step("Sign on", "menu",
     "A claims clerk signs on. The shell checks the user's authority and offers the four modules. "
     "Choosing 1 opens Query.",
     """
  Unclaimed Funds Management System                  User . . : JSMITH
  Texas Comptroller UCF data                         Access . : ALL

  Select an option:

     {{1  Query      Search owner records, select records for a claim}}
     2  Claims     Create, add to, remove from and process claims
     3  Reports    Claim and owner-file reports
     4  Admin      Data file administration

     X  Exit

  Owner file loaded . : 10/01/2026   Records . : 8,412,077
  Basket  . . . . . . : 0 records
""", cmd="1",
     ispf="Started from TSO with ISPSTART PGM(UCFMAIN) NEWAPPL(UCF).",
     cics="Started by typing transaction UCF0 on a clear screen.")

step("Query", "q1",
     "A caller says he is Albert Abbott. The clerk types the last name as he spells it and keeps "
     "the default match, Starts with, which reads the owner KSDS by generic key.",
     """
  Indexed fields (fill at least one):
    Owner last name / business  . . [[ABBOTT]]__________________________________
    Property ID or holder ID  . . . __________________________
    Holder name . . . . . . . . . . ________________________________________
    Owner ZIP (5 or 9)  . . . . . . _________

  Filters:
    Owner first name  . . . . . . . ______________________________
    Property type code  . . . . . . ____   (blank = all, ? = list)
    Owner city  . . . . . . . . . . ______________________________
    Owner state . . . . . . . . . . __
    Holder report year  . . . . . . ____
    Minimum dollar amount . . . . . __________

  Name match  . . . . . . . . . . 1  1=Starts with  2=Exact  3=Sounds like
  Exclude records already claimed N  (Y/N)
""")

step("Query", "q1",
     "Nothing starts with ABBOTT: the Comptroller spelled him ABBOT. The clerk switches the match "
     "to 3, Sounds like, which uses the optional Soundex lookup file (ABBOTT = A130).",
     """
  Indexed fields (fill at least one):
    Owner last name / business  . . ABBOTT__________________________________
    Property ID or holder ID  . . . __________________________
    Holder name . . . . . . . . . . ________________________________________
    Owner ZIP (5 or 9)  . . . . . . _________

  Filters:
    Owner first name  . . . . . . . ______________________________
    Property type code  . . . . . . ____   (blank = all, ? = list)
    Owner city  . . . . . . . . . . ______________________________
    Owner state . . . . . . . . . . __
    Holder report year  . . . . . . ____
    Minimum dollar amount . . . . . __________

  {{Name match  . . . . . . . . . . [[3]]  1=Starts with  2=Exact  3=Sounds like}}
  Exclude records already claimed N  (Y/N)
""", msg="No owner records start with ABBOTT")

RES_HDR = """
  Search: last name sounds like ABBOTT (Soundex A130)       Rows 1-5 of 5
  Line cmds: S=Select to basket  D=Detail  C=Claims on property  U=Unselect

  Cmd Owner name               ZIP   Type      Amount Holder             Clm
  --- ------------------------ ----- ---- ----------- ------------------ ---
"""


def res(rows, basket):
    return RES_HDR.rstrip("\n") + "\n" + "\n".join(rows) + "\n\n" + basket + "\n"


R = dict(
    ga="  {c} ABBIT GEORGE A           75501 MS01        0.50 EXPRESS SVCS INC   {f}",
    rl="  {c} ABBITT ROBERT L          75505 MS09        0.00 SALLIE MAE INC     {f}",
    km="  {c} ABBITT KELLY M           77539 IN05        0.01 US AUTO INS SVCS I {f}",
    a18="  {c} ABBOT ALBERT L           00000 MI02        0.03 SUNOCO PARTNERS MK {f}",
    a19="  {c} ABBOT ALBERT L           00000 MI02        0.04 SUNOCO PARTNERS MK {f}",
)


def row(k, c=" _ ", f="   "):
    return R[k].format(c=c, f=f)


step("Query", "q2",
     "Five real records sound like ABBOTT: ABBIT, ABBITT and ABBOT. The two ABBOT ALBERT L "
     "rows are both Sunoco mineral royalties. The clerk types S on each to put them in the basket.",
     res([row("ga"), row("rl"), row("km"),
          "   [[S]]  ABBOT ALBERT L           00000 MI02        0.03 SUNOCO PARTNERS MK    ",
          "   [[S]]  ABBOT ALBERT L           00000 MI02        0.04 SUNOCO PARTNERS MK    "],
         "  Basket: 0 records"),
     ispf="The list is an ISPF table shown with TBDISPLAY; S is a line command.",
     cics="The map holds one page; paging keys are saved in the COMMAREA between screens.")

step("Query", "q2",
     "Both records are in the basket ($0.07; amounts are stored in implied cents). Before claiming, "
     "the clerk opens one with D to check the details.",
     res([row("ga"), row("rl"), row("km"),
          "   [[D]]  ABBOT ALBERT L           00000 MI02        0.03 SUNOCO PARTNERS MK    ",
          "   S  ABBOT ALBERT L           00000 MI02        0.04 SUNOCO PARTNERS MK    "],
         "  {{Basket: 2 records  $0.07}}"),
     msg="2 records added to basket")

step("Query", "q3",
     "Every tape field is shown. NR flag N means no claim was ever filed with the Comptroller, "
     "and UCFMS finds no claim of its own on this property. F5 opens the basket.",
     f"""
  Owner . . . ABBOT                                    ALBERT L
  Address . . (no address on file)

  City/St/ZIP                                   00000 (unknown)
  Holder  . . SUNOCO PARTNERS MKTG & TERMINAL LP       ID 233102655001
              1818 MARKET ST STE LL
  City/St/ZIP PHILADELPHIA                   PA 19103
  Property ID {PID18}    Type MI02 Mineral Royalty
  Amount  . .         0.03   Shares  . .            0    Report year 2009
  Trans dates 05/01/2004 to                   Report date 12/01/2009
  Claim date  04/29/2011   Last updated 04/29/2011  (Comptroller fields)
  {{NR flag . . N  No claim filed with the Comptroller}}
  {{UCFMS . . . not on any UCFMS claim}}

  Claims on this property:
    (none)
""", key="F5")

step("Claims", "q4",
     "The basket holds the two owner keys. Choice 1 starts a new claim with them.",
     f"""
  Line cmds: R=Remove from basket  D=Detail              Rows 1-2 of 2

  Cmd Owner name               Property ID                Type      Amount
  --- ------------------------ -------------------------- ---- -----------
   _  ABBOT ALBERT L           {PID18} MI02        0.03
   _  ABBOT ALBERT L           {PID19} MI02        0.04

                                           Total  2 records        0.07

  Send basket to:
    1  New claim
    2  Existing claim . . ID __________
  Choice  . . [[1]]
""",
     ispf="The basket is a temporary ISPF table, UCFBASK.",
     cics="The basket is a CICS TS queue named UCFB + terminal ID.")

step("Claims", "c3",
     "The claimant spells his name ABBOTT. That's fine: one claim can cover records under other "
     "spellings. Type I means his authorization prints on Comptroller form 53-126. "
     "(Contact details here are invented examples.)",
     """
  New claim from basket: 2 records  $0.07

  Claimant type . . . . [[I]]  I=Individual (form 53-126)  B=Business (53-125)
  Claimant name . . . . [[ABBOTT]]______________________ [[ALBERT]]________ [[L]]
  Relationship  . . . . [[1]]  1=Owner  2=Heir  3=Agent  4=Business officer
  Address line 1  . . . [[4417 WOODLAWN AVE]]_____________
  Address line 2  . . . ______________________________
  City  . . . . . . . . [[TEXARKANA]]_____________________
  State / ZIP . . . . . [[TX]]  [[75503]]____
  Phone . . . . . . . . [[903-555-0187]]     Fax . . _______________
  Email . . . . . . . . ______________________________________________
  Business only:
    Representative  . . ________________________________________
    Title . . . . . . . ______________________________

  Notes . . . . . . . . ____________________________________________________

  Press Enter to create the claim, F12 to cancel.
""")

CLM_HDR = """
  Claim 0000000001   Status {st:<10} since {since}   Version {v}
  Claimant  ABBOTT ALBERT L                Relationship OWNER
            4417 WOODLAWN AVE, TEXARKANA TX 75503       Phone 903-555-0187
  Created   10/14/2026 JSMITH      Updated {upd} JSMITH

  Line cmds: R=Remove item  D=Owner record detail
  Cmd Seq  Owner name       Property ID                Type      Amount Status
  --- ---- ---------------- -------------------------- ---- ----------- -------
"""


def item(seq, name, pid, typ, amt, status, c=" _ "):
    return f"  {c} {seq} {name:<16} {pid} {typ} {amt:>11} {status}"


def claim(st, since, v, upd, items, total_line):
    return (CLM_HDR.format(st=st, since=since, v=v, upd=upd).rstrip("\n") + "\n"
            + "\n".join(items) + "\n\n" + total_line + "\n")


I1 = item("0001", "ABBOT ALBERT L", PID18, "MI02", "0.03", "ACTIVE")
I2 = item("0002", "ABBOT ALBERT L", PID19, "MI02", "0.04", "ACTIVE")

step("Claims", "c2",
     "Claim 0000000001 is created in one unit of work: the next ID from the control file, the "
     "header, items 0001 and 0002 (the claim's chain), and audit records. F3 goes back to the results.",
     claim("OPEN", "10/14/2026", 1, "10/14/2026", [I1, I2],
           "                                {{Active  2 items  Total        0.07}}"),
     msg="Claim 0000000001 created", key="F3",
     ispf="ISPF sends the update to the CICS claim service through EXCI, so both front ends share one ACID path.",
     cics="EXEC CICS SYNCPOINT commits the header, items, counter and audit together.")

step("Claims", "q2",
     "The ABBOT rows now show OPN and can't be selected again. The clerk wonders whether ABBIT "
     "GEORGE A is the same family, selects it, and presses F6 to send it to a claim.",
     res(["   [[S]]  ABBIT GEORGE A           75501 MS01        0.50 EXPRESS SVCS INC      ",
          row("rl"), row("km"),
          "   _  ABBOT ALBERT L           00000 MI02        0.03 SUNOCO PARTNERS MK {{OPN}}",
          "   _  ABBOT ALBERT L           00000 MI02        0.04 SUNOCO PARTNERS MK {{OPN}}"],
         "  Basket: 0 records"), key="F6")

step("Claims", "q4",
     "This time the basket goes to the existing claim: choice 2 with claim ID 0000000001.",
     f"""
  Line cmds: R=Remove from basket  D=Detail              Rows 1-1 of 1

  Cmd Owner name               Property ID                Type      Amount
  --- ------------------------ -------------------------- ---- -----------
   _  ABBIT GEORGE A           {PIDGA} MS01        0.50

                                           Total  1 record         0.50

  Send basket to:
    1  New claim
    2  Existing claim . . ID [[0000000001]]
  Choice  . . [[2]]
""")

I3 = item("0003", "ABBIT GEORGE A", PIDGA, "MS01", "0.50", "ACTIVE", c=" [[R]] ")
step("Claims", "c2",
     "Item 0003 is added to the end of the chain. On a closer look the first name is GEORGE, not "
     "ALBERT, so the clerk removes it with R.",
     claim("OPEN", "10/14/2026", 2, "10/14/2026", [I1, I2, I3],
           "                                Active  3 items  Total        0.57"),
     msg="1 record added to claim 0000000001")

I3R = item("0003", "ABBIT GEORGE A", PIDGA, "MS01", "0.50", "{{REMOVED}}")
step("Claims", "c2",
     "The removed item keeps its place in the chain with status R, and the audit file records who "
     "removed it. The total is back to $0.07. F6 processes the claim.",
     claim("OPEN", "10/14/2026", 3, "10/14/2026", [I1, I2, I3R],
           "                                Active  2 items  Total        0.07"),
     msg="Item 0003 removed", key="F6")

step("Claims", "c4",
     "From OPEN the only moves are SUBMITTED or CANCELED. The clerk submits it.",
     """
  Claim 0000000001   Claimant ABBOTT ALBERT L
  Current status  OPEN       since 10/14/2026      Items 2   Amount 0.07

  New status:
     2  SUBMITTED  Sent to the Comptroller
     4  CANCELED   Withdrawn; records become claimable again
  Choice  . . [[2]]

  Closing note  . . [[Mailed to Comptroller with ID proof]]___________________
                    ______________________________________________________
  Effective date  . 10/14/2026

  Press Enter to apply. The change is logged with your user ID.
""")

step("Claims", "c2",
     "SUBMITTED: items can no longer change. The by-user and by-status indexes follow the new "
     "status automatically because they are in the header's upgrade set.",
     claim("SUBMITTED", "10/14/2026", 4, "10/14/2026",
           [I1, I2, item("0003", "ABBIT GEORGE A", PIDGA, "MS01", "0.50", "REMOVED")],
           "                                Active  2 items  Total        0.07"),
     msg="Claim 0000000001 submitted", key="F6")

step("Claims", "c4",
     "Weeks later the Comptroller pays. Approval and payment are the Comptroller's decisions, so "
     "UCFMS just closes the claim with a note.",
     """
  Claim 0000000001   Claimant ABBOTT ALBERT L
  Current status  SUBMITTED  since 10/14/2026      Items 2   Amount 0.07

  New status:
     3  CLOSED     Comptroller has finished with the claim
     4  CANCELED   Withdrawn; records become claimable again
  Choice  . . [[3]]

  Closing note  . . [[Comptroller paid in full]]______________________________
                    ______________________________________________________
  Effective date  . 11/02/2026

  Press Enter to apply. The change is logged with your user ID.
""")

step("Claims", "c1",
     "Find Claims with Opened by * lists the clerk's own claims through the BYUSER index "
     "(user + status + claim ID). Typing =3 jumps straight to Reports.",
     """
  Claim ID __________  Claimant ________________  Status _  Opened by [[*]]_______

  Line cmds: S=Open  P=Process (change status)  X=Cancel claim

  Cmd Claim ID   Claimant              Status    Items      Amount Updated
  --- ---------- --------------------- --------- ----- ----------- ----------
   _  {{0000000001 ABBOTT ALBERT L       CLOSED        2        0.07 11/02/2026}}






                                                         Rows 1-1 of 1
""", msg="Claim 0000000001 closed", cmd="=3")

step("Reports", "r1",
     "Reports is a catalog, so new reports are new rows. The clerk runs CLM002 online.",
     """
  Line cmds: S=Run  B=Run in batch (online reports too)

  Cmd ID     Report                                   Mode    Last run
  --- ------ ---------------------------------------- ------- ----------
   _  CLM001 Open claims by status and age            Online  11/01/2026
   [[S]]  CLM002 Closed and canceled claims, date range   Online  10/31/2026
   _  CLM003 Claims by property type code             Batch   10/01/2026
   _  OWN001 Owner file profile (counts, dollars)     Batch   10/01/2026
   _  OWN002 Owner records by holder report year      Batch   ----------




                                                         Rows 1-5 of 5
""")

step("Reports", "r2",
     "The result reads the BYSTAT index (status + claim ID) for C and X claims in the date range. "
     "Typing =4 jumps to Admin.",
     """
  Closed and canceled claims, 10/01/2026 to 11/02/2026

  Status         Claims        Amount
  ------------- -------  ------------
  {{CLOSED              1          0.07}}
  CANCELED            0          0.00
  ------------- -------  ------------
  Total               1          0.07





""", title="UCFMS - Report CLM002 - Closed Claims", cmd="=4")

step("Admin", "a1",
     "Admin builds JCL from skeletons and submits it. Option 3 reloads the owner file from a new tape.",
     """
  Owner file . . UCF.PROD.OWNER.KSDS        Loaded 10/01/2026  8,412,077 recs
  Claims files . UCF.PROD.CLAIM.*           Last check 11/01/2026  0 errors

   1  File status        Record counts, last load, CICS open/closed state
   2  Define files       Owner KSDS/AIX (UCFDEF), claims files
   {{3  Load from tape     UCFLOAD: tape to owner KSDS, rebuild indexes}}
   4  Rebuild indexes    BLDINDEX for one or all alternate indexes
   5  Consistency check  Claims vs owner file, totals, AIX counts
   6  Backup / restore   REPRO or DFSMSdss of owner and claims files
   7  CICS files         Close or open files around batch jobs

  Tape DSN  . . UCF.TAPE.INPUT_______________   Volser . . UCF001
  Job card  . . //JSMITHA  JOB (ACCT),'UCF ADMIN',CLASS=A,MSGCLASS=X____
""", cmd="3")

step("Admin", "a2",
     "A reload replaces every owner record, so the clerk must type LOAD to confirm. Claims are "
     "untouched; option 5 afterwards lists claim items whose record left the tape.",
     """
  You are about to submit:  3  Load from tape

    UCFDEF   delete and redefine UCF.PROD.OWNER.KSDS and its AIXs
    UCFLOAD  load tape UCF.TAPE.INPUT volser UCF001, rebuild AIXs

  This REPLACES all 8,412,077 owner records.
  Claims are not changed. Run option 5 afterwards to list claim items
  whose record is not on the new tape.

  CICS file UCFOWNR is OPEN. It will be closed before the job and
  opened after it ends.

  Type LOAD to confirm . . [[LOAD]]    then press Enter.
""",
     ispf="ISPF tailors the JCL with FTOPEN/FTINCL/FTCLOSE and SUBMITs it.",
     cics="CICS writes the JCL to the internal reader with SPOOLOPEN/SPOOLWRITE.")

step("Admin", "a1",
     "The jobs are on their way. That's the whole loop: find, claim, track, report, and maintain "
     "the data, with the same screens in ISPF and CICS.",
     """
  Owner file . . UCF.PROD.OWNER.KSDS        Loaded 10/01/2026  8,412,077 recs
  Claims files . UCF.PROD.CLAIM.*           Last check 11/01/2026  0 errors

   1  File status        Record counts, last load, CICS open/closed state
   2  Define files       Owner KSDS/AIX (UCFDEF), claims files
   3  Load from tape     UCFLOAD: tape to owner KSDS, rebuild indexes
   4  Rebuild indexes    BLDINDEX for one or all alternate indexes
   5  Consistency check  Claims vs owner file, totals, AIX counts
   6  Backup / restore   REPRO or DFSMSdss of owner and claims files
   7  CICS files         Close or open files around batch jobs

  Tape DSN  . . UCF.TAPE.INPUT_______________   Volser . . UCF001
  Job card  . . //JSMITHA  JOB (ACCT),'UCF ADMIN',CLASS=A,MSGCLASS=X____
""", msg="{{Jobs UCFDEF and UCFLOAD submitted (JOB04711, JOB04712)}}", key="")

# ---------------------------------------------------------------- output
out = []
for st in STEPS:
    s = dict(chapter=st["chapter"], caption=st["caption"],
             note_ispf=st["note_ispf"], note_cics=st["note_cics"])
    for kind in ("ispf", "cics"):
        stc = dict(st)
        msg = st["msg"]
        hl_msg = msg.startswith("{{")
        stc["msg"] = msg.strip("{}")
        grid, marks = screen(stc, kind)
        if hl_msg:
            mr = 22
            c = grid[mr].index(stc["msg"])
            marks.append(dict(r=mr, c=c, n=len(stc["msg"]), k="hl"))
        s[kind] = dict(grid=grid, marks=marks,
                       key=(cics_key(st["key"]) if kind == "cics" else st["key"]),
                       panel=SCREENS[st["screen"]]["panel" if kind == "ispf" else "map"])
    out.append(s)

tpl = open(os.path.join(HERE, "walkthrough_template.html")).read()
html = tpl.replace("/*__STEPS__*/[]", json.dumps(out, separators=(",", ":")))
open(sys.argv[1], "w").write(html)
print(len(out), "steps,", len(html), "bytes")
