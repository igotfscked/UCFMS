# NUMIDENT: SSA death, claim and SS-5 records

NUMIDENT is the Social Security Administration's master file of Social Security numbers. NARA (the National Archives) released public use copies of three parts of it for people who are dead, or would be over 110 by the end of 2007. SortedByName.com bought the full set from NARA in July 2025 and shares it for download, unchanged, at <https://sortedbyname.com/sources/numident.html>. Their webmaster asks for a backlink to SortedByName.com in return.

In UCFMS it is a **separate reference dataset**. It is never merged into the owner file or the claims files. Owners are matched to NUMIDENT people by name, with ZIP, place of birth and dates as supporting evidence, and the candidates are shown for a person to judge. This matters most for heir claims: a candidate's date of death, parents and birthplace help with the Affidavit of Heirship (53-111-A) and the death-certificate step.

## What's in it

| Kind | Records | People (SSNs) | Coverage | Key extra fields |
|---|---|---|---|---|
| `D` Death | 49,459,293 | 49,459,293 (one record each) | deaths reported to SSA 1936-2007, minus state-reported deaths, which NARA can't release (an estimated 10-30% of deaths) | date of death, **residence ZIP at death**, ZIP of the lump-sum death payment |
| `C` Claim | 25,230,486 | 25,140,847 | life and death benefit claims (entry code `L` or `D`) | **father's and mother's names**, place of birth, claim date, date of death from the claim |
| `S` SS-5 | 72,182,729 | 40,873,455 (several versions each: name changes, corrections) | applications for a number | **parents' names**, place of birth, other names used, sex, race |

About 147 million records in all. A person can be in one, two or all three kinds. Data before 1962 (deaths) and 1973 (applications) is patchy.

Sources: NARA's record layouts and Supplemental User Notes 1-7 (Jake's copies, kept with the project files, not in this repo), and NARA's [NUMIDENT FAQ](https://aad.archives.gov/aad/content/aad_docs/rg047_num_faq_2018Dec.pdf).

## Record format

Each kind is a fixed 500-column record in NARA's "pre-CSV" layout. The fields this project uses are in `ucfms/numident.py` (`LAYOUTS`), and copybook [design/copybooks/UCFNUMI.cpy](design/copybooks/UCFNUMI.cpy) maps all of them. These columns are the same in all three kinds:

| Columns | Field |
|---|---|
| 1-11 | NUMI-REFERENCE-NUM |
| 13-21 | NUMI-SSN |
| 27 | NUMI-ENTRY-CODE: `T` death data, `D` death claim, `L` life claim |
| 29-36 | NUMI-CYCLE-DATE, CCYYMMDD |
| 37-51, 52 | first name, overflow flag |
| 53-67, 68 | middle name, overflow flag |
| 69-88, 89 | last name, overflow flag |
| 90-93 | suffix |
| 97-104 | date of birth, MMDDCCYY |
| 105 | sex: `0` unknown, `1` male, `2` female |

Death: residence ZIP 119-127, lump-sum ZIP 128-136, date of death 145-152 (MMDDCCYY), source of death 142-143. The agency layout repeats columns 37-186 three times (187-336, 337-486), with the number of postings in 487; NARA's copies hold one posting per record. Claim and SS-5: mother 107-163, father 164-220, birth city 221-232, birth state or country 234-235, foreign indicator 236. Claim only: claim date 282-289, date of death 298-305.

Things NARA changed in the public use copies (User Notes 2-6):

- **Masked records.** Records of people who might be alive are all `Z`s (2,229 claim records, 60,213 SS-5 records). The loader skips any record whose SSN is `ZZZZZZZZZ`.
- **`*` became letters.** An overflow flag is `O` (name or city cut off at the field size), the foreign-born flag is a lower-case `f`, and a corrected DOB is `C`.
- **Birthplace codes overlap.** `CA` with a blank foreign flag is California; with `f` it is Canada. `ucfms/numident_codes.py` holds NARA's two code lists (56 state and territory codes, 310 country codes).
- **Unknown date parts** are `00` or `XX`. The loader keeps what it can: `1995-02` or just `1920`.
- **Record length.** Claims are 499 characters plus a line feed, SS-5 records 500 or fewer, death records 487. Short lines are padded. The death certificate number is `X`ed out where it had anything, and so is "other number" when it wasn't the person's own SSN.

SortedByName says their files "may be different with the .csv layout, but the column header explanations remain the same". The loader reads both: NARA fixed-width files, and CSV files whose header row uses the layout's field names (`NUMI_SSN`, `NUMI-NH-NAME-LAST`, `NUMI_DOD_DTH_1` and so on). It names any CSV columns it couldn't place, so a header it doesn't know shows up straight away.

## Using it on the PC (SQLite and the web page)

NUMIDENT goes into its own table in the same database as the owner records.

```sh
# Load the owners first, then NUMIDENT. --only-ucf-names keeps only people
# whose last name is an owner last name, which drops most of the 147 million.
python3 -m ucfms --db ucf.db load ucf_tape.txt
python3 -m ucfms --db ucf.db numi load --only-ucf-names NARA.D*.DTH NARA.C*.CLM NARA.S*.SS5

python3 -m ucfms --db ucf.db numi search --last ABBIT --first GEO
python3 -m ucfms --db ucf.db numi search --last MUHAMMAD --sounds-like --dod-year 1988
python3 -m ucfms --db ucf.db numi person 123456789     # every record for one SSN
python3 -m ucfms --db ucf.db numi match 42             # candidates for UCF record 42
python3 -m ucfms --db ucf.db serve
```

The kind comes from `--kind`, then from the file name (`SS5`, `DTH`/`DEATH`, `CLM`/`CLAIM`), then from each record's entry code. On the web page, a record's detail has **Find in NUMIDENT**, and a NUMIDENT section below the results searches by name, Soundex, SSN, birth or death year, ZIP at death, birthplace or kind.

### How a match is scored

Matching runs on an owner with a first name (business names are skipped). Candidates must have the same last name, the first 20 characters, since NUMIDENT's field is 20 long. With sounds-like, the Soundex code has to match instead. The first initial must also match. Then all of a person's records (one SSN) are combined:

| Evidence | Points |
|---|---|
| Last name the same / only sounds alike | 40 / 20 |
| First name the same / one is a shortened form of the other / only an initial to compare | 30 / 20 / 10. A different first name with the same initial is dropped |
| Middle initial the same / different | +10 / -10 |
| Residence ZIP at death = owner ZIP / death payment ZIP = owner ZIP / same 3-digit ZIP area / died in Texas | +25 / +15 / +10 / +5 |
| Born in Texas | +5 |

Each candidate lists its reasons, for example "last name, first name, middle initial, residence ZIP at death, born in Texas, death on file". A high score is a lead to check, not an identification. The weights are a starting point, and Jake may want to change them.

## On the mainframe

Two optional jobs, in the same style as the Soundex lookup. Nothing else depends on them.

| Job | What it does |
|---|---|
| [jcl/UCFNDEF.jcl](jcl/UCFNDEF.jcl) | Defines `HLQ.NUMI.KSDS` (556 bytes, `KEYS(56 0)`), the alternate index `HLQ.NUMI.SSN.AIX` (`KEYS(9 68)`, nonunique) and `HLQ.NUMI.SSN.PATH` |
| [jcl/UCFNLOAD.jcl](jcl/UCFNLOAD.jcl) | ICETOOL builds the key in front of each record, sorts and loads, skipping masked records and setting duplicate keys aside in `HLQ.NUMI.DUPKEYS`. Then it builds the SSN index and stamps `NUMISTAT` in UCF.CTL |

Stored record: last name 20 + first name 15 + SSN 9 + kind 1 + reference number 11 = a 56-byte key, followed by the unchanged NARA record. Every NARA field is at its column + 56. A last name, or last name + first name, is a generic key. The SSN path lists one person's records.

**Getting the data there.** The downloads land on a PC, so the PC trims them and writes NARA's fixed layout. That works whether they came as fixed-width or CSV:

```sh
python3 -m ucfms --db ucf.db numi extract --only-ucf-names NARA.D01.DTH death01.txt
```

Upload each file in ASCII mode with `quote site recfm=fb lrecl=500`, as `UCF.NUMI.UPLOAD.DEATH`, `.CLAIM` and `.SS5` (placeholders), or concatenate several in UCFNLOAD. The whole of NUMIDENT stored this way is about 82 GB, far more than a 3390-27, so trimming to owner last names isn't optional on Jake's Hercules system. The defines are sized for about 20 million records, roughly 14,000 cylinders.

**In Query** ([design/APP_DESIGN.md](design/APP_DESIGN.md) section 3), `F9=NUMIDENT` on Record Detail opens a candidates screen (UCFPQ05 / CICS map UCFMQ05). It browses the KSDS on the owner's last name + first initial and scores the candidates with the rules above:

```
+--------------------------------------------------------------------------------+
|UCFPQ05                UCFMS - Query - NUMIDENT Candidates           Row 1 of 2 |
|Command ===> ________________________________________________ Scroll ===> CSR   |
|  Owner ABBIT GEORGE A                AUSTIN TX 787010000                       |
|  Leads to check, not identifications. S=Person  (all records for the SSN)      |
|                                                                                |
|  S Score SSN       Name                      Born       Died       Kinds       |
|  _   110 900000001 GEORGE ALLEN ABBIT        04/12/1911 02/--/1995 Death Claim |
|          last name, first name, middle initial, ZIP at death, born TX          |
|  _    60 900000002 GEORGE B ABBIT            --/--/1920 07/04/1980 Death       |
|          last name, first name, middle initial differs                         |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
| F1=Help  F3=Exit  F5=Sounds like  F7=Up  F8=Down  F12=Cancel                   |
+--------------------------------------------------------------------------------+
```

(Invented people and SSNs. SSNs starting with 9 are never issued.) The CICS map has the same body with the usual header and PF line. `UCFNUMI` is the placeholder CICS FILE name. If the file isn't loaded, F9 says so and nothing else changes.

## Privacy and the public repo

NUMIDENT is public record about dead people, but it still carries SSNs and parents' names. As with the Comptroller data, **none of it goes into the public repo**: the tests use invented people only. Claims still store no SSN. The two NARA code lists in `ucfms/numident_codes.py` are only code tables.

## Open questions for Jake

1. Did the downloads come as NARA fixed-width files or as CSV? If CSV, send the header line and one row of each kind (any row works, it never leaves the project), and I'll check the column mapping.
2. Do you want all three kinds, or just Death + Claim? SS-5 is the biggest, and its main extra is parents' names, which Claim records also have.
3. Should a heir claim record the NUMIDENT match it relied on, for example the decedent's date of death and SSN in the claim header? Today nothing is stored.
