# Comptroller forms 53-120, 53-125, 53-126 and 53-111-A filled from UCFMS claims

Status: **draft for Jake's review**, 2026-10-15. Part of [../APP_DESIGN.md](../APP_DESIGN.md) section 5.

| Form | What it is | Fillable as supplied? |
|---|---|---|
| **53-120** (Rev. 7-15/8) | Heir Claim Form: page 1 instructions and document checklist, page 2 claimant information and affidavit. The base of every claim package | No. [make_fillable_53120.py](make_fillable_53120.py) makes [53-120.pdf](53-120.pdf): page 1's checklist and property IDs removed, 31 named fields added (19 claimant, 12 reserved checklist rows) |
| **53-126** (8-05) | Limited Authorization, individual claim | Yes, 21 fields |
| **53-125** (8-05) | Limited Authorization, business claim | Yes, 22 fields |
| **53-111-A** (Rev. 9-21/5) | Affidavit of Heirship: page 1 instructions, pages 2-3 the affidavit (page 2 is a scan) | No. [make_fillable_affidavit.py](make_fillable_affidavit.py) adds 6 fields to a copy, [53-111-A.pdf](53-111-A.pdf) |

The mainframe never draws a form. It only supplies field values, and Adobe
puts them on the page.

## Claim package

One package per claim, in the order the Comptroller asks for ("attach all
supporting documentation BEHIND the claim form"):

1. **53-120 page 1**: instructions and the document checklist for this claim.
2. **53-120 page 2**: claimant information, filled; affidavit signed by hand.
3. **53-126** (individual) or **53-125** (business): authorization, filled; signed by hand.
4. **53-111-A pages 2-3**, heir claims only (`CLMT-RELATION` = `H`): reported
   owner, claim number and decedent filled; the witness, family history,
   attestation and notary sections are completed by hand. Its own instruction
   page is left out. Skipped with a warning when the claim total is over
   $10,000.00, since the form is for claims under $10,000.01.
5. Supporting documents the checklist asks for, gathered by the claimant.

## 53-120 page 1: checklist by property type

Jake's copy of page 1 was issued for one claim, so its checklist named that
claim's documents and property IDs. Per Jake, [53-120.pdf](53-120.pdf) now has
all of that removed (the header, Claim ID box, mail-to and the two instruction
sentences stay) and the checklist area is an empty bordered box holding twelve
reserved multiline fields, `F120_DocReq01` to `F120_DocReq12`.

When a package is built, UCFFORM will fill those rows: one per required
document, with its description and the property IDs it applies to, chosen from
the property type codes of the claim's active items (plus the claimant's
relationship). **That logic is not written yet**; until it is, the rows are
blank and page 1 prints as the general instructions. The planned shape is a
table, not code: a `DOCREQ` member of `HLQ.UCF.PARMLIB` mapping property type
code (and relationship) to document codes, and document code to the text that
the original checklist used (Proof of SSN, Proof of ID, Death Certificate, Last
Will, Affidavit of Heirship, Insurance Policy, Original Check MS16, Order
Admitting Will to Probate).

## Route (no Infoprint Server)

```
CLAIM.HDR + PARMLIB(DESIGNEE)
        |  batch step UCFFORM (COBOL), one claim or a selection
        v
HLQ.UCF.FORMS (PDSE)   two FDF members per claim, plain text, field name = value:
                       F0000001 -> 53-120     A0000001 -> 53-126 or 53-125
                       H0000001 -> 53-111-A (heir claims only)
        |  download as text (FTP ASCII, or Zowe CLI: zowe files download all-members
        |  "HLQ.UCF.FORMS" -e .fdf) into a PC folder that also holds the three blank forms
        v
F/A/H0000001.fdf -- double-click --> Adobe opens that form already filled
or:  python fill_forms.py FOLDER --> filled/F, A, H0000001.pdf and the package P0000001.pdf
        v
print, sign and date by hand, add the supporting documents, mail to the Comptroller
```

**FDF** (Forms Data Format) is Adobe's own text format for form data. Each file
names its form (`/F (53-120.pdf)`) and lists `/T (field) /V (value)` pairs, so
COBOL writes it with ordinary `STRING` statements. Rules for UCFFORM: escape
`\`, `(` and `)` in values with a backslash; download as text so EBCDIC becomes
ASCII; member names are `F`, `A` or `H` + the last 7 digits of the claim ID.
`HLQ.UCF.FORMS` is a PDSE (RECFM=VB, LRECL=255) so one-member-per-form never
fills a directory; the JCL thread's one-time job `jcl/UCFFMDEF.jcl` creates it
and `PARMLIB(DESIGNEE)`.

**Tested here** with three sample claims: the walkthrough's ABBOTT claim
(individual), an invented business, A & T CATTLE CO, and an heir claim by an
invented heir, LINDA M ABBIT, for the real record of ABBIT GEORGE A ($0.50).

| Claim | FDF members | Filled |
|---|---|---|
| 0000001 ABBOTT ALBERT L, individual | [F0000001.fdf](F0000001.fdf), [A0000001.fdf](A0000001.fdf) | [package P0000001.pdf](filled/P0000001.pdf) (53-120 + 53-126) |
| 0000002 A & T CATTLE CO, business | [F0000002.fdf](F0000002.fdf), [A0000002.fdf](A0000002.fdf) | [package P0000002.pdf](filled/P0000002.pdf) (53-120 + 53-125) |
| 0000003 ABBIT LINDA M, heir of ABBIT GEORGE A | [F0000003.fdf](F0000003.fdf), [A0000003.fdf](A0000003.fdf), [H0000003.fdf](H0000003.fdf) | [package P0000003.pdf](filled/P0000003.pdf) (53-120 + 53-126 + 53-111-A) |

[make_sample_fdf.py](make_sample_fdf.py) models UCFFORM's output;
[fill_forms.py](fill_forms.py) is the PC bulk filler and package builder.

## 53-120 field map (names added by make_fillable_53120.py)

| Field | On the form | UCFMS source |
|---|---|---|
| F120_ClaimID1, F120_ClaimID2 | Claim ID box, pages 1 and 2 | `CH-COMPTROLLER-REF`; blank until the Comptroller issues one |
| F120_LastName | Name (Last) | `CLMT-LAST-NAME` (business name for a business claim) |
| F120_FirstName, F120_MiddleName | (First), (Middle) | `CLMT-FIRST-NAME`, `CLMT-MIDDLE-INIT` |
| F120_MaidenName | (Maiden) | blank; not stored |
| F120_SSN | Social Security Number | **never filled**: UCFMS doesn't store SSNs. Typed in Adobe or written by hand |
| F120_AddlLast ... F120_AddlSSN | Additional Owner row | blank; UCFMS has one claimant per claim |
| F120_MailAddr | Current mailing address | `CLMT-ADDR-1` + `CLMT-ADDR-2` |
| F120_DayPhone | Daytime phone | `CLMT-PHONE` |
| F120_City, F120_State, F120_ZIP | City, State, ZIP code | `CLMT-CITY`, `CLMT-STATE`, `CLMT-ZIP` (ZIP+4 as 79029-0118) |
| F120_Email, F120_FAX | Email address, FAX | `CLMT-EMAIL`, `CLMT-FAX` |
| F120_DocReq01 ... F120_DocReq12 | page 1 checklist rows (reserved) | blank until the property-type logic is written |
| (none) | signatures, dates, Match the Promise Yes/No/% | by hand |

Field names start `F120_` because 53-125/53-126 also have `FAX` and `Phone`;
merged into one package PDF, same-named fields would share one value.

## 53-125 / 53-126 field map

`CH-CLMT-TYPE` picks the form: `I` = individual = 53-126, `B` = business = 53-125.

| Form field | On the form | 53-126 | 53-125 | UCFMS source |
|---|---|:-:|:-:|---|
| Claim1, Claim2 | CLAIM NUMBER(S) box | ✓ | ✓ | `CH-COMPTROLLER-REF`; blank until issued |
| Designee, Designe2 | "hereby designate ___ and/or ___" | ✓ | ✓ | designee person, designee entity (PARMLIB) |
| Person, Entity | Name of person / entity | ✓ | ✓ | PARMLIB |
| Add1, Add2 | designee address, 2 lines | ✓ | ✓ | PARMLIB |
| Phone, FAX | designee telephone / facsimile | ✓ | ✓ | PARMLIB |
| PIlicNO | Private Investigator's License Number | ✓ | ✓ | PARMLIB |
| TxprNo | Sales Taxpayer's Number | ✓ | ✓ | PARMLIB |
| Day, Month, Year | "Signed this __ day of __, __" | ✓ | ✓ | blank: dated by hand when signed |
| Claimant | Printed Name of Claimant | ✓ | | `CLMT-FIRST-NAME` + `CLMT-MIDDLE-INIT` + `CLMT-LAST-NAME` |
| ClmntTtl | Title of Claimant | ✓ | | blank (individuals) |
| ClPrint | Printed Name of Claimant | | ✓ | `CLMT-LAST-NAME` (business name) |
| ClRep | Printed Name of Claimant's representative | | ✓ | `CLMT-REP-NAME` |
| ClRepT | Title of Claimant's representative | | ✓ | `CLMT-REP-TITLE` |
| ClAdd1 | claimant address line 1 | ✓ | ✓ | `CLMT-ADDR-1` + `CLMT-ADDR-2` |
| ClAdd2 | claimant address line 2 | ✓ | ✓ | `CLMT-CITY` `CLMT-STATE` `CLMT-ZIP` |
| ClPhon, ClFAX | claimant telephone / facsimile | ✓ | ✓ | `CLMT-PHONE`, `CLMT-FAX` |
| (signature) | Signature line | | | never filled |

The **designee** is whoever the claimant authorizes to deal with the
Comptroller, which on these forms is your firm. It is the same on every claim,
so it lives in `HLQ.UCF.PARMLIB(DESIGNEE)` as `KEYWORD=value` lines (`PERSON=`,
`ENTITY=`, `ADDR1=`, `ADDR2=`, `PHONE=`, `FAX=`, `PILIC=`, `TXPRNO=`) that an
admin edits in ISPF. All its values are site placeholders.

## 53-111-A field map (names added by make_fillable_affidavit.py)

| Field | On the form | UCFMS source |
|---|---|---|
| AOH_OwnerName1, AOH_OwnerName2 | Name of reported owner, pages 2 and 3 | owner name from the claim items' owner snapshot, as on the tape (ABBIT GEORGE A) |
| AOH_ClaimNo1, AOH_ClaimNo2 | Claim number, pages 2 and 3 | `CH-COMPTROLLER-REF`; blank until issued |
| AOH_Decedent1, AOH_Decedent2 | "Estate of" and "facts of heirship of" | the same owner name in first-middle-last order (GEORGE A ABBIT) |
| (none) | witness, decedent, marital and family history, attestation, notary | by hand |

## Changes this caused elsewhere

- Claim header gains `CLMT-TYPE`, `CLMT-FAX`, `CLMT-REP-NAME`, `CLMT-REP-TITLE`
  and is now **700 bytes** ([../CLAIMS_LAYOUT.md](../CLAIMS_LAYOUT.md)). Index offsets don't move.
- New datasets `HLQ.UCF.FORMS` (PDSE) and `HLQ.UCF.PARMLIB(DESIGNEE)`.
- Claimant screen asks for claimant type, fax and, for businesses, the representative's name and title.
- Print pop-up (F11 on Claim Detail) option **4 Claim forms (53-120 + authorization)**;
  report catalog `CLM011` writes forms for a selection of claims.

## Open points

1. **53-120 page 1 checklist logic** (decided: built by UCFMS from property type
   codes, to be written). See "53-120 page 1" above.
2. **Property IDs on the form are the Comptroller's short IDs** (1254118,
   36533119). The tape carries a 26-byte holder/year/type/sequence ID instead, so
   UCFMS can't print the Comptroller's IDs unless they are entered on the claim.
3. **Claim2 / second claim number:** UCFMS stores one Comptroller claim number per claim.
