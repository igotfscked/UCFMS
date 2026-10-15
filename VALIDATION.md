# Real-sample validation (104 records from Jake, 2026-10-14)

Fixture: `sample/ucf_real_sample_104.txt`. Every pasted line is exactly 469 characters.
Trailing blanks were lost in the paste, so the true record length can't be seen.

## Where the data matches LAYOUT.md

Bytes 1–201 (owner name, address, city, state, ZIP) and the begin and end transaction dates at 229–248 line up exactly.

## Where it differs

### Bytes 202–228 (27 bytes): same span, different contents

The layout puts HolderReportYear at 202, PropertyTypeCode at 206 and PropertyID at 210–228.
The data actually holds:

| Bytes | Len | Content | Evidence |
|---|---|---|---|
| 202–212 | 11 | Holder Texas taxpayer number | Digits in all 104 records. CENTRAL POWER & LIGHT CO and AEP TX CENTRAL (the same company) share 74055060000 |
| 213 | 1 | Unknown: `1` in 99 records, `2` in 4, `3` in 1 | Possibly a report sequence |
| 214–217 | 4 | HolderReportYear | `1989` in all 104 records |
| 218–221 | 4 | PropertyTypeCode | Valid codes; IN01 and INZZ are not in the code list |
| 222–227 | 6 | Item sequence | Digits in all records |
| 228 | 1 | Unknown flag: `N` in 101 records, `Y` in 3 | |

The 27-byte string from 202 to 228 is not unique by itself: two owners under FIRST CITY BANK share
`7405044850011989AC01000001N`. Owner name plus those 27 bytes is unique in all 104 records.

### NumberOfShares is 10 bytes, not 12

All 104 records hold `0000000000` at 259–268, and ReportDate starts at 269. Every field after that sits 2 bytes earlier than the layout says:

| Field | Layout | Data |
|---|---|---|
| NumberOfShares | 259–270 (12) | 259–268 (10) |
| ReportDate | 271–280 | 269–278 |
| HolderName | 281–320 | 279–318 |
| HolderAddressLine1–3 | 321–410 | 319–408 |
| HolderCity | 411–440 | 409–438 |
| HolderState | 441–442 | 439–440 |
| HolderZipCode | 443–451 | 441–449 |
| AddedDate | 452–461 | 450–459 |
| UpdatedDate | 462–471 | 460–469 |
| MostRecentClaimDate | 472–481 | 470–479 (blank in all 104) |
| FillerData | 482–500 | 480–? |

With these positions the fields add up to 498 bytes, not 500. The filler may really be 21 bytes; the tape's LRECL settles it.

## Formats

- **Dates:** MM/DD/YYYY, or blank. The parser already handles both.
- **DollarAmount:** 10 digits, zero-filled, with no decimal point. The highest value is 0000006270, so it's either $62.70 (implied cents) or $6,270.
- **Owner ZIP:** `00000` in 53 of 104 records, and OwnerState is blank in 35. These look like "unknown" placeholders.
- **Data quirk:** one record has city `MISSOURI` and state `CI`. "MISSOURI CITY" appears to have been split across the city and state fields.
- **First name:** blank in 103 of 104 records. Personal names may also sit entirely in OwnerLastName.

## Effect on the HolderName and OwnerZipCode alternate indexes (requested by the design thread)

A non-unique VSAM alternate index stores every base key for one alternate key in a single record. That record must fit in one control interval: at most 32 KB, which is about 550 pointers of 59 bytes each.

- **ZIP:** `00000` alone covers half the records, and many busy ZIPs would exceed 550.
- **HolderName:** large banks and utilities hold far more than 550 items each.

BLDINDEX would fail for both. The proposed replacement is two small index KSDSs built by the same DFSORT load:

- one keyed on HolderName + base key
- one keyed on OwnerZip + base key

Each record carries only its keys. A program does a generic browse on the holder name or ZIP, then reads the base record by key. The PropertyID alternate index is fine as it is, because IDs are nearly unique.

## Jake's revised field map (16:57): fits

Jake's 27-field map adds up to 469 bytes, exactly the length of every sample line. Every field passes a format check in all 104 records:

- digits in the ZIP, holder ID, sequence and amount fields
- Y or N in NRFLAG
- MM/DD/YYYY or blank in the date fields
- two letters in HolderState
- HolderName starts at byte 279 in every record

AddedDate and FillerData are not in the data.

Observation: RECENTCLAIMDATE is filled in every record and falls 1–149 days after REPORTDATE. It is never later than UPDATEDDATE and equals it in 58 records. That pattern looks more like a received or added date than a claim date.

Key: OWNERLASTNAME + HOLDERIDNUMBER + HOLDERREPORTYEAR + PROPERTYTYPE + SEQUENCENUMBER (bytes 1–40 + 202–227, 66 bytes) is unique in all 104 records without NRFLAG. The 26-byte property part alone repeats once.

## NRFlag as claim status (Jake, 17:14): dates don't confirm it

Jake: Y = a claim was filed at some point, N = none. If a claim moved the record, Y records should show UpdatedDate ≠ LastUpdatedDate. Across all 110 samples:

| Flag | Records | UpdatedDate ≠ LastUpdatedDate |
|---|---:|---:|
| Y | 3 | 1 (A J MCKEAN JR OIL TRUST: 07/28/1989 → 10/07/1998) |
| N | 107 | 45 (3 days to about 19 years later) |

Two of the three Y records were never updated after they arrived, and 42% of the N records were updated. So the update date does not track the flag. That doesn't disprove the meaning: a filed claim may not touch LastUpdatedDate. But the dates can't be used to check or infer it.
