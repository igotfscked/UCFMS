"""Fixed-width layout of the Texas UCF data file (see LAYOUT.md).

Jake's revised map of 2026-10-14, confirmed against 104 real records.
"""

FIELDS = [
    ("OwnerLastName", 40),
    ("OwnerFirstName", 30),
    ("OwnerAddressLine1", 30),
    ("OwnerAddressLine2", 30),
    ("OwnerAddressLine3", 30),
    ("OwnerCity", 30),
    ("OwnerState", 2),
    ("OwnerZipCode", 9),
    ("HolderIDNumber", 12),
    ("HolderReportYear", 4),
    ("PropertyTypeCode", 4),
    ("SequenceNumber", 6),
    ("NRFlag", 1),
    ("BeginningTransactionDate", 10),
    ("EndingTransactionDate", 10),
    ("DollarAmount", 10),       # zero-filled, implied cents: 0000006270 = $62.70
    ("NumberOfShares", 10),
    ("ReportDate", 10),
    ("HolderName", 40),
    ("HolderAddressLine1", 30),
    ("HolderAddressLine2", 30),
    ("HolderAddressLine3", 30),
    ("HolderCity", 30),
    ("HolderState", 2),
    ("HolderZipCode", 9),
    ("UpdatedDate", 10),        # Jake's map called this RECENTCLAIMDATE
    ("LastUpdatedDate", 10),    # Jake's map called this UPDATEDDATE
]

RECORD_LENGTH = sum(n for _, n in FIELDS)  # 469

# (name, start, end) as 0-based slice bounds
SLICES = []
_pos = 0
for _name, _len in FIELDS:
    SLICES.append((_name, _pos, _pos + _len))
    _pos += _len

NAMES = [n for n, _ in FIELDS]
DATE_FIELDS = {
    "BeginningTransactionDate", "EndingTransactionDate", "ReportDate",
    "UpdatedDate", "LastUpdatedDate",
}

# NRFlag is a claim-status flag (Jake, 2026-10-14):
# Y = a claim was filed at some point, N = none.
NR_FLAGS = {"Y": "Claim filed", "N": "No claim filed"}

# Property ID = holder ID + report year + type + sequence (bytes 202-227).
PROPERTY_ID_FIELDS = ("HolderIDNumber", "HolderReportYear", "PropertyTypeCode", "SequenceNumber")
