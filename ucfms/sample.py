"""Generate a synthetic UCF file in the exact fixed-width layout (fake data)."""

import random

from .layout import FIELDS, RECORD_LENGTH

LAST = ["SMITH", "JOHNSON", "GARCIA", "MARTINEZ", "NGUYEN", "BROWN", "LOPEZ",
        "HERNANDEZ", "WILLIAMS", "DAVIS", "SMITHSON", "O'BRIEN"]
FIRST = ["JAMES", "MARIA", "JOSE", "LINDA", "DAVID", "PATRICIA", "MICHAEL", "ANH"]
BUSINESSES = ["ACME OIL & GAS LLC", "LONE STAR PLUMBING INC", "BLUEBONNET CAFE",
              "GULF COAST FREIGHT CO", "ALAMO DENTAL GROUP PA"]
CITIES = [("HOUSTON", "770"), ("AUSTIN", "787"), ("DALLAS", "752"),
          ("SAN ANTONIO", "782"), ("EL PASO", "799"), ("LUBBOCK", "794")]
HOLDERS = [("BANK OF AMERICA NA", "CHARLOTTE", "NC", "28255"),
           ("WELLS FARGO BANK NA", "SIOUX FALLS", "SD", "57104"),
           ("STATE FARM MUTUAL AUTO INS CO", "BLOOMINGTON", "IL", "61710"),
           ("ONCOR ELECTRIC DELIVERY", "DALLAS", "TX", "75202"),
           ("H-E-B GROCERY COMPANY LP", "SAN ANTONIO", "TX", "78204")]
PROP_TYPES = ["AC01", "AC02", "CK01", "CK13", "MS01", "MS05", "SC01", "IN03", "MI02", "UT01"]


def _date(rng, y0, y1):
    return f"{rng.randint(1, 12):02d}/{rng.randint(1, 28):02d}/{rng.randint(y0, y1)}"


def make_record(rng):
    biz = rng.random() < 0.2
    city, zip3 = rng.choice(CITIES)
    holder, hcity, hst, hzip = rng.choice(HOLDERS)
    ptype = rng.choice(PROP_TYPES)
    year = rng.randint(2015, 2025)
    v = {
        "OwnerLastName": rng.choice(BUSINESSES) if biz else rng.choice(LAST),
        "OwnerFirstName": "" if biz else rng.choice(FIRST),
        "OwnerAddressLine1": f"{rng.randint(100, 9999)} {rng.choice(['MAIN', 'OAK', 'ELM', 'CONGRESS'])} ST",
        "OwnerAddressLine2": rng.choice(["", "", "APT 4B", "STE 200"]),
        "OwnerAddressLine3": "",
        "OwnerCity": city,
        "OwnerState": "TX",
        "OwnerZipCode": f"{zip3}{rng.randint(1, 99):02d}" + (f"{rng.randint(0, 9999):04d}" if rng.random() < 0.5 else ""),
        "HolderIDNumber": f"{17400000000 + HOLDERS.index((holder, hcity, hst, hzip)) * 1111111}1",
        "HolderReportYear": str(year),
        "PropertyTypeCode": ptype,
        "SequenceNumber": f"{rng.randint(1, 999999):06d}",
        "NRFlag": "Y" if rng.random() < 0.03 else "N",
        "BeginningTransactionDate": _date(rng, year - 5, year - 3),
        "EndingTransactionDate": _date(rng, year - 2, year - 1),
        "DollarAmount": f"{rng.randint(1, 500000):010d}",  # implied cents
        "NumberOfShares": f"{rng.randint(1, 5000) if ptype == 'SC01' else 0:010d}",
        "ReportDate": _date(rng, year, year),
        "HolderName": holder,
        "HolderAddressLine1": "PO BOX 1000",
        "HolderAddressLine2": "", "HolderAddressLine3": "",
        "HolderCity": hcity, "HolderState": hst, "HolderZipCode": hzip,
        "UpdatedDate": _date(rng, year, year),
        "LastUpdatedDate": _date(rng, year, 2026),
    }
    out = "".join(v[n].ljust(w)[:w] for n, w in FIELDS)
    assert len(out) == RECORD_LENGTH
    return out


def write_sample(path, n=1000, seed=42):
    rng = random.Random(seed)
    with open(path, "w", encoding="latin-1", newline="") as f:
        for _ in range(n):
            f.write(make_record(rng) + "\r\n")
