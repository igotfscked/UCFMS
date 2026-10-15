# App design placeholders (for merging into ../jcl/PLACEHOLDERS.md)

Dummy values used in APP_DESIGN.md, CLAIMS_LAYOUT.md and SCREENS.md that Jake
will replace with site values. Values the JCL already uses (HLQ `UCF.PROD`,
tape DSN `UCF.TAPE.INPUT`, volser `UCF001`, job card) are not repeated.

| Placeholder | Where | What it stands for |
|---|---|---|
| `HLQ.CLAIM.HDR`, `.HDR.BYUSER`, `.HDR.BYSTAT`, `.ITEM`, `.ITEM.BYPROP`, `.AUDIT`; `HLQ.UCF.CTL` | CLAIMS_LAYOUT.md | Claims dataset names under the site HLQ |
| Soundex lookup file name (JCL thread to choose) | APP_DESIGN.md section 3 | Optional sounds-like lookup KSDS |
| `UCF0`, `UCFQ`, `UCFC`, `UCFR`, `UCFA` | APP_DESIGN.md section 8, SCREENS.md | CICS transaction IDs |
| `UCFOWNR` (and claims file names, not yet chosen) | SCREENS.md admin screens | CICS FILE resource names (8 chars) |
| `UCFB` + termid | APP_DESIGN.md section 2 | CICS TS queue prefix for the selection basket |
| CICS region APPLID / EXCI connection (none named yet) | APP_DESIGN.md section 8 | Region the ISPF claims module calls through EXCI |
| RACF resource profiles for query / claims / reports / admin authority, and their class | APP_DESIGN.md section 2 | Who may use each module |
| `UCF` (NEWAPPL) and the ISPF panel, skeleton, table and message libraries, plus the load library | APP_DESIGN.md section 7 | TSO/ISPF start-up allocations |
| `JSMITH` | SCREENS.md | Sample user ID shown on mockups only |
| 500 | APP_DESIGN.md section 3 | Cap on sounds-like matches without a narrowing filter |
| SYSOUT class, `DEST`, `FORMS`, `PAGEDEF`/`FORMDEF` for the page printer; Infoprint printer definition for PDF | APP_DESIGN.md section 5 (printing) | Where claim packages print and how PDFs are made |
| `HLQ.UCF.PARMLIB(DESIGNEE)` values: designee person, firm, address, phone, fax, PI license no., sales taxpayer no. | forms/FORMS.md | Your firm as printed on forms 53-125/53-126 |
| `HLQ.UCF.FORMS` (PDSE, VB 255) | forms/FORMS.md | Where UCFFORM writes the FDF members (F = 53-120, A = authorization) |
