"""List every dummy site value in the JCL and COBOL, with file:line.

    python3 placeholders.py            # print the table
    python3 placeholders.py --update   # rewrite the JCL table in PLACEHOLDERS.md
    python3 placeholders.py --check    # exit 1 if any dummy value is left

After Jake's real values are swapped in, --check should report nothing.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = sorted(
    [os.path.join(HERE, f) for f in os.listdir(HERE) if f.endswith(".jcl")]
    + [os.path.join(HERE, "..", "cobol", f) for f in os.listdir(os.path.join(HERE, "..", "cobol"))
       if f.endswith(".cbl")])

# (placeholder, regex, what it stands for)
TOKENS = [
    ("(ACCT)", r"\(ACCT\)", "Job card accounting information"),
    ("'UCF ...' programmer name", r"JOB \(ACCT\),'[^']*'", "Job card programmer-name field"),
    ("CLASS=A", r"CLASS=A\b", "Job class"),
    ("MSGCLASS=X", r"MSGCLASS=X\b", "Output class for job logs"),
    ("UCF.PROD (HLQ)", r"SET HLQ=UCF\.PROD\b", "High-level qualifier for every UCFMS dataset"),
    ("UCF.TAPE.INPUT", r"UCF\.TAPE\.INPUT", "Dataset name on the Comptroller tape"),
    ("UCF001", r"VOLSER=UCF001", "Tape volume serial"),
    ("UCF.NUMI.UPLOAD.*", r"UCF\.NUMI\.UPLOAD\.", "NUMIDENT files uploaded from the PC (death, claim, SS-5)"),
    ("UNIT=TAPE", r"UNIT=TAPE\b", "Tape unit name"),
    ("LABEL=(1,SL)", r"LABEL=\(1,SL\)", "Tape label type and file sequence"),
    ("UNIT=SYSDA", r"UNIT=SYSDA\b", "Disk unit name for work and new datasets"),
    ("UCF.PROD.LOADLIB", r"UCF\.PROD\.LOADLIB", "Load library for UCFSNDX, UCFSDXB, UCFCTLU"),
    ("UCF.PROD.SOURCE", r"UCF\.PROD\.SOURCE", "COBOL source library"),
    ("UCF.PROD.COPYLIB", r"UCF\.PROD\.COPYLIB", "COBOL copybook library"),
    ("CEE.SCEELKED", r"CEE\.SCEELKED", "Language Environment link library"),
    ("IGYWCL", r"\bIGYWCL\b", "COBOL compile-and-link procedure"),
    ("DATACLAS(XXXXXXXX)", r"DATACLAS\(XXXXXXXX\)", "SMS data class (commented out; needed over 4 GB)"),
    ("STORCLAS(XXXXXXXX)", r"STORCLAS\(XXXXXXXX\)", "SMS storage class (commented out)"),
    ("LOG(UNDO)", r"LOG\(UNDO\)", "CICS recovery attribute (commented out; or RECOVERY on the CICS FILE)"),
    ("CYLINDERS / TRACKS", r"(CYLINDERS|TRACKS)\(\d+ \d+\)", "VSAM primary/secondary space, sized for about 10 million owner records (NUMIDENT: about 20 million)"),
    ("SPACE=(CYL,...)", r"SPACE=\((CYL|TRK),", "Work and sequential dataset space"),
    ("*** DESIGNEE ... ***", r"\*\*\* [^*]+ \*\*\*", "PARMLIB(DESIGNEE) values: your firm as printed on forms 53-125/53-126"),
]

BEGIN, END = "<!-- jcl-table:begin -->", "<!-- jcl-table:end -->"


def scan():
    hits = {t[0]: [] for t in TOKENS}
    for path in FILES:
        name = os.path.relpath(path, HERE)
        for i, line in enumerate(open(path, encoding="utf-8"), 1):
            for label, rx, _ in TOKENS:
                if re.search(rx, line):
                    hits[label].append(f"{name}:{i}")
    return hits


def table(hits):
    rows = ["| Placeholder | Stands for | Where (file:line) |", "|---|---|---|"]
    for label, _, what in TOKENS:
        where = ", ".join(hits[label]) or "(none left)"
        rows.append(f"| `{label}` | {what} | {where} |")
    return "\n".join(rows)


def main():
    hits = scan()
    if "--check" in sys.argv:
        left = {k: v for k, v in hits.items() if v}
        for k, v in left.items():
            print(f"{k}: {', '.join(v)}")
        sys.exit(1 if left else 0)
    if "--update" in sys.argv:
        p = os.path.join(HERE, "PLACEHOLDERS.md")
        s = open(p, encoding="utf-8").read()
        a, b = s.index(BEGIN) + len(BEGIN), s.index(END)
        open(p, "w", encoding="utf-8").write(s[:a] + "\n" + table(hits) + "\n" + s[b:])
        print("updated", p)
    else:
        print(table(hits))


if __name__ == "__main__":
    main()
