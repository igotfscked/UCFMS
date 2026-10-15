# Texas UCF data file: field layout

Jake's revised map, 2026-10-14. It replaces the original 500-byte, 27-field layout.
It was checked against 104 real records (`sample/ucf_real_sample_104.txt`), and every field fits; see VALIDATION.md.
Fixed width, **469 bytes per record**, 1-based columns.

| # | Len | Start | End | Field | Notes |
|---|---:|---:|---:|---|---|
| 1 | 40 | 1 | 40 | OwnerLastName |  |
| 2 | 30 | 41 | 70 | OwnerFirstName |  |
| 3 | 30 | 71 | 100 | OwnerAddressLine1 |  |
| 4 | 30 | 101 | 130 | OwnerAddressLine2 |  |
| 5 | 30 | 131 | 160 | OwnerAddressLine3 |  |
| 6 | 30 | 161 | 190 | OwnerCity |  |
| 7 | 2 | 191 | 192 | OwnerState |  |
| 8 | 9 | 193 | 201 | OwnerZipCode |  |
| 9 | 12 | 202 | 213 | HolderIDNumber | Holder's 11-digit TX taxpayer no. + 1 digit |
| 10 | 4 | 214 | 217 | HolderReportYear |  |
| 11 | 4 | 218 | 221 | PropertyTypeCode |  |
| 12 | 6 | 222 | 227 | SequenceNumber |  |
| 13 | 1 | 228 | 228 | NRFlag | Claim status (Jake, 17:14): Y = a claim was filed at some point, N = none. Sample: N 107, Y 3. The dates do not confirm it; see VALIDATION.md |
| 14 | 10 | 229 | 238 | BeginningTransactionDate |  |
| 15 | 10 | 239 | 248 | EndingTransactionDate |  |
| 16 | 10 | 249 | 258 | DollarAmount | Zero-filled, implied cents: 0000006270 = $62.70 |
| 17 | 10 | 259 | 268 | NumberOfShares | Zero-filled |
| 18 | 10 | 269 | 278 | ReportDate |  |
| 19 | 40 | 279 | 318 | HolderName |  |
| 20 | 30 | 319 | 348 | HolderAddressLine1 |  |
| 21 | 30 | 349 | 378 | HolderAddressLine2 |  |
| 22 | 30 | 379 | 408 | HolderAddressLine3 |  |
| 23 | 30 | 409 | 438 | HolderCity |  |
| 24 | 2 | 439 | 440 | HolderState |  |
| 25 | 9 | 441 | 449 | HolderZipCode |  |
| 26 | 10 | 450 | 459 | UpdatedDate | RECENTCLAIMDATE (renamed per Jake) |
| 27 | 10 | 460 | 469 | LastUpdatedDate | UPDATEDDATE |

- OwnerLastName also holds business names. OwnerFirstName is usually blank.
- Dates are MM/DD/YYYY or blank.
- Property ID = HolderIDNumber + HolderReportYear + PropertyTypeCode + SequenceNumber (bytes 202–227, 26 bytes). It is **not** unique on its own; see VALIDATION.md.
- Owner ZIP `00000` and a blank OwnerState mean unknown.
