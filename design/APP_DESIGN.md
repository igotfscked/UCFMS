# UCFMS interactive application: high-level business logic

Status: **draft for Jake's review**, 2026-10-14. Nothing here is coded yet.
Screen mockups for every ISPF panel and CICS map: [SCREENS.md](SCREENS.md).
Claim rules are Jake's answers of 2026-10-14 (section 10).

> **Updated 2026-10-14 17:05** for the 469-byte layout and 66-byte key settled
> in the JCL thread. Stored records stay 535 bytes: Jake dropped the added
> claim flag (17:15), so a record's claim status is worked out from the claims
> files (section 4).

Builds on the VSAM design in [../jcl/README.md](../jcl/README.md): base KSDS
`HLQ.OWNER.KSDS` (66-byte key = OwnerLastName 40 + Property ID 26, then the
469-byte tape record; see [../LAYOUT.md](../LAYOUT.md)) and the PropertyID alternate index path
`HLQ.OWNER.PROPID.PATH`.

---

## 1. Shape of the application

```
                 +---------------------------------------------+
  ISPF panels -->|  UCFMAIN  shell: sign-on, menu, dispatch,    |<-- CICS BMS maps
  (TSO)          |           navigation, selection basket       |    (tran UCF0)
                 +----+-----------+-----------+-----------+-----+
                      |           |           |           |
                  UCFQRY0     UCFCLM0     UCFRPT0     UCFADM0      <- module controllers
                  1 Query     2 Claims    3 Reports   4 Admin         (screens + flow)
                      |           |           |           |
                  UCFQSRV     UCFCSRV     UCFRSRV     (JCL skeletons,  <- business logic
                      |           |           |        checks)            (no screen, no I/O verbs)
                      +-----+-----+-----+-----+
                            |           |
                        UCFDOWN     UCFDCLM                          <- data access
                       owner file  claims files                        (two builds each:
                                                                        native VSAM / EXEC CICS)
```

Three layers, so one set of business rules serves both front ends:

| Layer | What it owns | ISPF build | CICS build |
|---|---|---|---|
| Presentation (controller) | screens, PF keys, line commands, field edits | COBOL + `ISPLINK` (DISPLAY, TBDISPLAY) | COBOL + BMS `SEND/RECEIVE MAP`, pseudo-conversational |
| Business logic (service) | validation, claim state rules, totals, which records qualify | **same COBOL source** | **same COBOL source** |
| Data access | every VSAM read/write | native COBOL `READ/START/WRITE` on VSAM | `EXEC CICS READ/STARTBR/WRITE`, recoverable files |

A COBOL program can't contain both native file I/O and `EXEC CICS` file
commands, which is why data access is split out: the service routines call
`UCFDOWN`/`UCFDCLM` with a request block and never know which build they got.

## 2. Shell (UCFMAIN)

Responsibilities:

1. **Start-up:** get user ID (TSO `SYSUID` / CICS `ASSIGN USERID`), check the
   user's authority level (query / claims / reports / admin, via RACF resource
   profiles), build the common area, start an empty selection basket.
2. **Main menu:** options 1–4 plus X (exit). Options the user isn't authorised
   for are shown greyed or rejected.
3. **Dispatch:** set `COMM-MODULE` and `COMM-ACTION`, call the module, read
   back `COMM-NEXT`.
4. **Navigation:** module returns one of
   `MENU` (back to menu), `GOTO n` (jump straight to module n, e.g. Query to
   Claims carrying the basket), `EXIT`. PF3 = back one level, PF12 = cancel
   to menu, `=n` fast path like ISPF.
5. **Messages:** module puts a return code + message ID; shell shows it on the
   next screen.
6. **Clean-up on exit:** free the basket, close files (ISPF build).

The shell holds no business rules.

### Common area (copybook UCFCOMM, ~4 KB)

Passed `CALL ... USING UCFCOMM` in ISPF, and as the COMMAREA in CICS (kept
well under the 32 KB COMMAREA limit; bulk data goes in the basket).

| Group | Fields |
|---|---|
| Header | version, user ID, authority flags, terminal/session ID, current module, action, next-step, PF key |
| Result | return code (00 ok, 04 warning/end of list, 08 not found, 12 validation error, 16 record locked or changed by another user, 20 I/O error), reason code, message ID + text |
| Basket | basket name, item count, total dollars |
| Context | current claim ID, current owner key (66 bytes), last search criteria |
| Module area | 3 KB `REDEFINES` per module: query paging keys, claim edit fields, report selection, admin options |

### Selection basket

The hand-off between Query and Claims: a list of owner keys the user picked.

| ISPF | CICS |
|---|---|
| temporary ISPF table `UCFBASK` (`TBCREATE ... NOWRITE`), one row per owner key + amount + type | TS queue `UCFB` + termid (or a container on a channel), one item per owner key |

## 3. Module 1: Query (UCFQRY0 / UCFQSRV)

Read-only against the owner file. Functions:

| Function | Access path |
|---|---|
| Owner last name / business name (prefix) | base KSDS, generic key `START KEY >= 'SMITH'`, read while key starts with SMITH |
| Last name + first name | as above, filter first name |
| Property ID (26) | `PROPID.PATH` (alternate index, offset 267). Not unique: one ID can list several owners |
| Holder ID (12) | same path, generic key on the first 12 bytes of the property ID |
| Holder name | holder lookup KSDS (key HolderName + base key), generic browse, then read the base record by key |
| Owner ZIP (5 or 9) | ZIP lookup KSDS (key OwnerZip + property type + base key), generic browse on 5 digits, then read the base record. ZIP `00000` (unknown) isn't in the lookup, so a search for it is refused |
| Property type + ZIP | ZIP lookup KSDS alone: the type is in its key, so ZIP + type is a generic browse with no base reads for non-matching types |
| Any other filter (city, state, report year, minimum amount) | applied to rows read through one of the paths above; a search with no indexed field is refused online and offered as a batch report |

The holder-name and ZIP lookup files belong to the JCL thread (see
[../VALIDATION.md](../VALIDATION.md)): alternate indexes won't work because
ZIP `00000` and large holders have too many records for one AIX entry.

"Owner key" below always means the full 66-byte base key, the only value that
identifies one record.

Screens: criteria entry, result list (scrollable, line commands
`S` select into basket, `D` detail, `C` show claims on this property),
record detail (all 27 fields + claim status), basket view.

Business rules in UCFQSRV:
- Validate criteria (at least one indexed field; ZIP numeric; type code in the
  116-code table).
- Paging: store first/last key of the page in the common area; next page
  restarts the browse from the saved key (needed for pseudo-conversational CICS,
  harmless in ISPF).
- Each result row shows the record's UCFMS claim status, worked out from the
  claims files (section 4): on an open or submitted claim, on a closed claim,
  or never claimed. The tape's NRFlag is shown beside it as reported.
- A record already on an OPEN or SUBMITTED claim can't be selected.
- **Sounds like (optional, Soundex):** see "Sounds-like search" below.
- PF key "Claim": `GOTO 2` with the basket, action "new claim" or "add to
  claim nnnn".

### Sounds-like search (optional)

Jake approved this only if it is optional and breaks nothing, so it is an
extra path that the rest of Query never depends on.

- **Codes:** standard American Soundex (first letter + 3 digits). JOHN, JON
  and JHON all give J500; MUHAMMAD, MOHAMMED and MOHAMED all give M530; SMITH
  and SMYTH give S530. One COBOL routine, `UCFSNDX`, computes it, and both the
  load job and Query call the same routine so the codes always match.
- **File:** a Soundex lookup KSDS keyed on Soundex(OwnerLastName) (4) + the
  66-byte base key, built after the base file at load time. The JCL thread
  defines and loads it.
- **Search:** with match type 3, Query computes the Soundex of the entered last
  name, browses the lookup file on that 4-byte code, and reads each base
  record by key. If a first name was entered, Query compares its Soundex with
  each candidate's first name (no index needed). Other filters (ZIP, type,
  amount) apply as usual. Results are shown for the user to pick from; nothing
  is merged.
- **Limits:** a code like S530 matches many names, so a sounds-like search
  without a first name or another filter is capped (e.g. first 500 matches)
  with a message to narrow it. For business names Soundex mostly reflects
  the first word.
- **If the file isn't there:** Query checks for it on first use (CICS: file
  not defined or not open; ISPF: DD not allocated, or OPEN status 35) and
  also treats it as missing if `UCF.CTL` shows it was built before the last
  owner-file load. In that case option 3 is refused with "Sounds-like search
  isn't available; use Starts with", and every other search works unchanged.

### NUMIDENT lookup (optional)

A second optional extra, built the same way as sounds-like: nothing else in
Query depends on it. Full design in [../NUMIDENT.md](../NUMIDENT.md).

- **File:** `HLQ.NUMI.KSDS` (SSA death, claim and SS-5 records from NARA's
  public use files), keyed last name 20 + first name 15 + SSN + kind +
  reference number, with an SSN alternate index. Loaded by UCFNDEF/UCFNLOAD,
  stamped `NUMISTAT` in UCF.CTL. It is reference data and never updated online.
- **From a record:** on Record Detail, `F9=NUMIDENT` browses the file on the
  owner's last name (first 20 bytes) + first initial and lists candidates,
  one per SSN, best first, with the reasons (name, middle initial, residence
  ZIP at death matches the owner ZIP, born in Texas, death on file). These
  are leads for the user to check, never an identification, and nothing is
  written anywhere. Business names and owners with no first name are not matched.
- **On its own:** criteria entry gets a NUMIDENT option (last name, first
  name, SSN, birth or death year, ZIP at death) and a person view that lists
  every record for one SSN through the SSN path.
- **Claims:** for heir claims the candidate's date of death, parents and
  place of birth help the Affidavit of Heirship and the death-certificate
  step. The claim keeps no SSN, as before (section 4); a user who wants to
  note a NUMIDENT match types it into the claim notes.
- **If the file isn't there:** CICS file not defined/open, or ISPF DD not
  allocated: `F9` and the NUMIDENT option say "NUMIDENT isn't loaded" and
  everything else works unchanged. An owner reload doesn't make it stale.

## 4. Module 2: Claims (UCFCLM0 / UCFCSRV)

The only module that changes data. Functions Jake named, plus the minimum
needed around them:

| Function | What it does |
|---|---|
| Create | new claim ID, claimant details, items from the basket |
| Add to | add basket records to an existing claim |
| Remove from | take an item off a claim (kept in history, marked removed) |
| Process | submit, close or cancel the claim (see below) |
| List / view | find claims by ID, claimant name, status, or property |
| Cancel | withdraw a claim |

### Claims datasets (new)

Field-level layouts, indexes and copybooks: [CLAIMS_LAYOUT.md](CLAIMS_LAYOUT.md).

Each claims file is defined with one blank seed record (claim ID 0) so the
empty KSDS can be opened (JCL thread, UCFCLDEF). Every claims program and
browse skips claim ID 0, and claim IDs from the counter start at 1.

| Dataset | Org | Key | Content |
|---|---|---|---|
| `HLQ.CLAIM.HDR` | KSDS, 648 bytes | ClaimID (10) | tracking (status, opened/submitted/closed/canceled dates and users), claimant info, item count, total dollars, **version counter**, notes |
| `HLQ.CLAIM.HDR.BYUSER` | AIX, unique | user + status + ClaimID (19) | each user's claims by status |
| `HLQ.CLAIM.HDR.BYSTAT` | AIX, unique | status + ClaimID (11) | all claims in a status |
| `HLQ.CLAIM.ITEM` | KSDS, 246 bytes | ClaimID (10) + item sequence (4) | one per property on the claim, in the order added: 66-byte owner key, active/removed, snapshot of the tape fields |
| `HLQ.CLAIM.ITEM.BYPROP` | AIX, non-unique | owner key (66) | which claims include this property |
| `HLQ.CLAIM.AUDIT` | ESDS, 210 bytes | none | one record per change: who, when, claim, item, action, before/after status, amount |
| `HLQ.UCF.CTL` | KSDS, 100 bytes | record ID (8) | next ClaimID counter, load statistics, last consistency-check date |

Items carry the full 66-byte owner key, not just the property ID, because the
property ID is not unique.

### Claim lifecycle

```
 OPEN ──submit──> SUBMITTED ──close──> CLOSED
   │                  │
   └──cancel──────────┴──cancel──> CANCELED
```

Approval, denial and payment are the Comptroller's decisions, not UCFMS logic.
UCFMS records that a claim was submitted and later closed; the outcome goes in
the closing note.

Rules:
- Items can be added or removed only while OPEN.
- A property can be on only one active (OPEN or SUBMITTED) claim.
- One claim may hold records under different owner names or spellings.
- The claim amount is the sum of DollarAmount (implied cents: `0000006270` = $62.70) over the active items; there is
  no separate paid amount, and shares aren't totalled.
- Every status change and item change writes an audit record.
- Claimed records stay in the owner file; Claims never deletes them, and never
  touches the Comptroller's `UpdatedDate` (the old RecentClaimDate).

### A record's claim status (worked out, not stored)

Nothing is added to the owner record; it stays the 535-byte key + tape record.
Query works out each row's status from the claims files:

1. Read `CLAIM.ITEM.BYPROP` with the row's 66-byte owner key. Not found (the
   usual case) means never on a UCFMS claim; that's one keyed read per row.
2. For each item found with item status `A` (removed items are skipped), read
   its claim header for the status and dates.
3. Show the strongest result: `OPN` (OPEN) or `SUB` (SUBMITTED) if any, else
   `CLS` (CLOSED), else blank. CANCELED claims count as never claimed.
4. Record detail also shows the claim ID with its opened, submitted and closed
   dates from the header.

Because the claims files are the only place this lives, a tape reload can't
lose it and needs no extra step.

**What the tape says about Comptroller claims, and its limit.** The tape's
NRFlag (column 228) is `Y` when a claim was filed with the Comptroller at some
point and `N` when not (Jake). UCFMS shows it as reported and never changes it.
The tape's dates can't confirm or replace it: in the 110 sample records two of
the three `Y` records were never updated after they arrived, and 42% of the `N`
records were updated (see [../VALIDATION.md](../VALIDATION.md)). So UCFMS
doesn't infer Comptroller claim status from `UpdatedDate` or `LastUpdatedDate`;
the NRFlag is the only tape signal, and UCFMS's own claims are the only status
it can vouch for.

### What one claims update does (one unit of work)

Example, "add basket to claim 1234":
1. Read claim header for update; reject if status isn't OPEN or the version
   counter changed since the user's screen was built (someone else updated it).
2. For each basket item: `ENQ` on its owner key, so two users can't add the
   same property at the same moment; check `BYPROP` as above and reject it if
   it's active on an OPEN or SUBMITTED claim; write the claim item.
3. Rewrite the header with new totals and version + 1.
4. Write audit records.
5. Commit (which also releases the ENQs). Any failure in 1–4 undoes all of them.

Submit, close and cancel only change the header (status, date, user, version)
and write audit records; the items and the owner file are untouched.

## 5. Module 3: Reports (UCFRPT0 / UCFRSRV), open-ended

Built as a **report catalog** so new reports are entries, not shell changes.
Each catalog entry: report ID, title, parameters, and whether it runs online
(small counts, immediate) or batch (JCL skeleton submitted, output to a
dataset or SYSOUT).

First entries:
- Open claims: count and dollars by status, by age band.
- Closed and canceled claims: count and dollars for a date range.
- Claims by property type code.
- Owner file profile: record count, dollars by type, by holder report year.

ISPF submits batch reports with file tailoring (`FTOPEN/FTINCL/FTCLOSE` + `SUBMIT`).
CICS writes the job to the internal reader through `SPOOLOPEN/SPOOLWRITE`.

### Printing claims: page printer and PDF

A claim prints as a **claim package**: page header, claim tracking block,
claimant block, one line per active item (seq, owner, property ID, type and
description, holder, report date, DollarAmount), active-item count and claim
total, then a skip to a new page for the next claim. Sample:
[print/CLAIM_PRINT_SAMPLE.txt](print/CLAIM_PRINT_SAMPLE.txt) (the raw line data)
and [print/CLAIM_PRINT_SAMPLE.pdf](print/CLAIM_PRINT_SAMPLE.pdf) (how it lays out
on a page), from `print/claim_print_sample.py`.

**Programs.** One formatting routine, `UCFCLFMT`, turns a claim header plus its
items into 133-byte print lines (ASA carriage control in column 1, 132 print
columns, landscape). Two callers share it, like the business-logic layer:

| Caller | Runs | Selects claims by | Writes to |
|---|---|---|---|
| `UCFCLPRT` | batch | `PARM='CLAIM=nnnnnnnnnn'`, or `STATUS=`, `USER=`, `FROM=`/`TO=` dates through the BYSTAT / BYUSER indexes; `ITEMS=ALL` also prints removed items | `//REPORT DD SYSOUT=...` (FBA, LRECL 133) or a dataset |
| `UCFCLPR1` | CICS, one claim | the claim on screen | JES SYSOUT directly with `EXEC CICS SPOOLOPEN OUTPUT` / `SPOOLWRITE`, no batch job |

Batch reads the claims files with `DISP=SHR` while CICS has them open
(SHAREOPTIONS 2), so a claim being changed at that moment may print as it was
just before the change.

**Page printer.** The SYSOUT class and destination (`OUTPUT` statement with
`CLASS`, `DEST`, `FORMS`, and for an AFP printer `PAGEDEF`/`FORMDEF`) route the
line data to the site's page printer. Those names are placeholders.

**PDF.** Jake's site has no Infoprint Server (2026-10-15), so route 3 is the
one UCFMS uses; 1 and 2 stay listed in case that changes.
1. **Infoprint Server with its transforms (preferred if licensed):** point the
   `OUTPUT` statement's `DEST` at an Infoprint printer definition that converts
   line data to PDF and writes it to a z/OS UNIX file or emails it. Same job,
   different destination.
2. **An output archive product** (Content Manager OnDemand, CA View and
   similar) that already serves SYSOUT as PDF.
3. **No print software:** write the report to a dataset (`RECFM=FBA,LRECL=133`),
   download it as text (FTP or Zowe CLI) and convert it on a workstation. The
   sample generator above does exactly that conversion.

**Comptroller forms.** The claim form 53-120, the authorization forms
53-125 (business) and 53-126 (individual) and, for heir claims, the Affidavit of
Heirship 53-111-A are filled from claim data: batch step `UCFFORM` writes FDF
members per claim to the PDSE `HLQ.UCF.FORMS`, the user downloads them next to
the blank forms, and Adobe opens each form already filled; a PC script also
assembles the claim package (53-120 both pages, the authorization, then the
affidavit). 53-120 page 1 is a blank template: its document checklist and
property IDs were removed, and reserved fields `F120_DocReq01`..`12` will carry
a checklist UCFMS builds from the claim's property type codes (logic to be
written). Field map, route and tested samples:
[forms/FORMS.md](forms/FORMS.md).

For a merge into letters (Word mail merge and similar), `UCFCLPRT` also takes
`FORMAT=CSV`: one row per active item with the claim and claimant fields
repeated, written to a dataset for download.

**How users start it.**
- **ISPF:** F11=Print on Claim Detail opens a small pop-up (1 printer, 2 PDF,
  3 dataset or CSV, 4 claim forms: 53-120 + authorization) and submits `UCFCLPRT` for that claim with
  file tailoring. Reports catalog entry `CLM010 Claim packages` prints a batch
  of claims by status, user and date range.
- **CICS:** F11=Print on Claim Detail runs `UCFCLPR1` and the output is on the
  spool at once; the PDF route then follows the destination. `CLM010` from
  CICS submits the batch job through the internal reader like other batch
  reports. `CLM011` writes claim forms for a selection of claims.

## 6. Module 4: Data file administration (UCFADM0), open-ended

Restricted to admin authority. Mostly builds and submits batch JCL; online it
only shows status.

First functions:
- Define files (UCFDEF), load from tape (UCFLOAD), build/rebuild AIXs.
- Define the claims files (new job, not written yet).
- Consistency checks (batch): claim items whose owner key is no longer in the
  owner file, items with no header, header totals ≠ sum of active items, a
  property active on more than one OPEN/SUBMITTED claim, AIX and lookup-file counts vs base, DUPKEYS count from the last load.
- Backup (`REPRO` / DFSMSdss) and restore.
- CICS file control: close the owner and claims files before batch jobs touch
  them, open them after (`SET FILE CLOSED/OPEN`, or CEMT).
- Show the last load date, record counts and last check result from `UCF.CTL`.

A reload replaces the owner file and leaves the claims files alone. The
consistency check afterwards lists claim items whose record isn't on the new
tape; the claim keeps its item snapshot, so nothing is lost.

## 7. ISPF front end

- Started by `ISPSTART PGM(UCFMAIN) NEWAPPL(UCF)` from a TSO CLIST/REXX that
  allocates the VSAM files and the panel/skeleton/table libraries.
- UCFMAIN `CALL`s module controllers dynamically, `USING UCFCOMM`.
- Panels: `UCFP000` menu, `UCFPQ01` criteria, `UCFPQ02` result list
  (TBDISPLAY), `UCFPQ03` detail, `UCFPQ04` basket, `UCFPC01` claim list,
  `UCFPC02` claim detail/items, `UCFPC03` claimant entry, `UCFPC04` status
  change, `UCFPR01` report catalog, `UCFPA01` admin menu.
- Owner file opened input only. Claims updates go through CICS (section 8).

## 8. CICS front end

- One transaction per module (`UCF0` shell, `UCFQ`, `UCFC`, `UCFR`, `UCFA`) so
  RACF can restrict claims and admin by transaction ID.
- Pseudo-conversational: each program ends with
  `RETURN TRANSID(next) COMMAREA(UCFCOMM)`; the shell `XCTL`s to modules.
- Mapsets `UCFM000`, `UCFMQ01`... mirroring the ISPF panels.
- Claims files and `UCF.CTL` defined recoverable (`RECOVERY(BACKOUTONLY)` or
  RLS with `LOG(UNDO)`), so step 5 above is `EXEC CICS SYNCPOINT` and any
  error is `SYNCPOINT ROLLBACK`. Locks are held only inside one task, never
  across a screen; the version counter covers the gap between screens.
- ClaimID counter read for update inside the same unit of work.
- The owner file is read-only everywhere.

### CICS is the main front end; ISPF stays

Jake expects CICS to be the main way in but wants ISPF kept. So CICS owns every
claims update. The ISPF claims module
calls the same claim service in CICS through EXCI, so both front ends get the
same ACID behaviour on one live dataset. ISPF reads the owner and claims files
directly; a claim changed in CICS a moment ago may show stale in ISPF until the
next read (SHAREOPTIONS 2 allows one updater plus readers).

If CICS is down, ISPF can still query but not change claims. VSAM RLS +
DFSMStvs would let ISPF update natively and transactionally, but needs a
Parallel Sysplex and a DFSMStvs licence.

## 9. Program and copybook names

| Name | Kind |
|---|---|
| UCFMAIN | shell |
| UCFQRY0, UCFCLM0, UCFRPT0, UCFADM0 | module controllers |
| UCFQSRV, UCFCSRV, UCFRSRV | business logic |
| UCFDOWN, UCFDCLM | data access (built twice: `...B` native, `...C` CICS) |
| UCFCOMM | common area |
| UCFREC | 535-byte owner record (66-byte key, 27 tape fields at +66) |
| UCFCLMH, UCFCLMI, UCFAUD, UCFCTL | claims header, item, audit, control records |

## 10. Claim rule decisions (Jake, 2026-10-14)

1. Statuses are OPEN, SUBMITTED, CLOSED and CANCELED. Approve, deny and pay are the Comptroller's.
2. A property can be on only one active claim.
3. One claim can hold records under different owner names; spellings vary (John, Jhon, Jon).
4. Claims don't update the Comptroller's claim date (now `UpdatedDate`).
5. Claim amount is the total of DollarAmount; no separate paid amount.
6. CICS is the main front end; ISPF is kept and updates claims through CICS.
7. No flag is added to the owner record (Jake, 17:15). A record's UCFMS claim status is worked out from the claims files; the tape's NRFlag is shown as the Comptroller's signal.
