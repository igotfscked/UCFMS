"""Model of the mainframe step UCFFORM: claim header + designee profile -> one FDF.

UCFFORM (COBOL, batch) does exactly this for each selected claim and writes the
FDF text as a PDSE member HLQ.UCF.FORMS(Fnnnnnnn) for 53-120, (Annnnnnn) for
53-125/53-126 and, for heir claims only, (Hnnnnnnn) for the Affidavit of Heirship 53-111-A. This script produces the same
text for the walkthrough claim so the route can be tested end to end on a PC:

    python3 make_sample_fdf.py   -> F/A members for claims 1-3, H member for claim 3 (heir)

Claim data: ABBOT/ABBIT owner records are real; claimant contact details, the business
example and the designee profile are invented placeholders.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# HLQ.UCF.PARMLIB(DESIGNEE): the firm that the claimant authorizes. Site values.
DESIGNEE = dict(
    PERSON="DESIGNEE PERSON (SITE VALUE)",
    ENTITY="DESIGNEE FIRM NAME (SITE VALUE)",
    ADDR1="123 SITE ADDRESS ST",
    ADDR2="AUSTIN TX 78701",
    PHONE="512-555-0100",
    FAX="512-555-0101",
    PILIC="A00000",
    TXPRNO="00000000000",
)


def esc(v):
    """FDF string escaping: backslash, parentheses."""
    return v.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def city_line(c):
    zip_ = c["zip"][:5] + ("-" + c["zip"][5:] if len(c["zip"].strip()) == 9 else "")
    return f"{c['city']} {c['state']} {zip_}".strip()


def fields_for(c, d):
    """Form field name -> value. Same map for both forms except the claimant block."""
    f = {
        "Claim1": c["ref1"], "Claim2": c["ref2"],
        "Designee": d["PERSON"], "Designe2": d["ENTITY"],
        "Person": d["PERSON"], "Entity": d["ENTITY"],
        "Add1": d["ADDR1"], "Add2": d["ADDR2"],
        "Phone": d["PHONE"], "FAX": d["FAX"],
        "PIlicNO": d["PILIC"], "TxprNo": d["TXPRNO"],
        "Day": "", "Month": "", "Year": "",           # dated by hand at signing
        "ClAdd1": " ".join(x for x in (c["addr1"], c["addr2"]) if x),
        "ClAdd2": city_line(c),
        "ClPhon": c["phone"], "ClFAX": c["fax"],
    }
    if c["type"] == "B":                              # 53-125 Business claim
        f.update(ClPrint=c["last"], ClRep=c["rep_name"], ClRepT=c["rep_title"])
    else:                                             # 53-126 Individual claim
        name = " ".join(x for x in (c["first"], c["mi"], c["last"]) if x)
        f.update(Claimant=name, ClmntTtl="")
    return f


def fields_53120(c):
    """53-120 claim form. SSN and the additional-owner row are never filled:
    UCFMS doesn't store SSNs, so the claimant writes them in by hand."""
    zip_ = c["zip"][:5] + ("-" + c["zip"][5:] if len(c["zip"].strip()) == 9 else "")
    return {
        "F120_ClaimID1": c["ref1"], "F120_ClaimID2": c["ref1"],
        "F120_LastName": c["last"], "F120_FirstName": c["first"], "F120_MiddleName": c["mi"],
        "F120_MaidenName": "",
        "F120_MailAddr": " ".join(x for x in (c["addr1"], c["addr2"]) if x),
        "F120_DayPhone": c["phone"], "F120_City": c["city"], "F120_State": c["state"], "F120_ZIP": zip_,
        "F120_Email": c["email"], "F120_FAX": c["fax"],
    }


AFFIDAVIT_LIMIT_CENTS = 1000000          # 53-111-A is for claims under $10,000.01


def first_middle_last(owner):
    """Tape owner name 'ABBIT GEORGE A' (last first middle) -> 'GEORGE A ABBIT'."""
    last, *rest = owner.split()
    return " ".join(rest + [last])


def fields_affidavit(c):
    """53-111-A Affidavit of Heirship. Only the names and claim number are filled;
    the affiant, witness, family history and notary sections are completed by hand."""
    dec = first_middle_last(c["owner_name"])
    return {"AOH_OwnerName1": c["owner_name"], "AOH_OwnerName2": c["owner_name"],
            "AOH_ClaimNo1": c["ref1"], "AOH_ClaimNo2": c["ref1"],
            "AOH_Decedent1": dec, "AOH_Decedent2": dec}


def members(c):
    """(member prefix, form, fields) for every FDF member UCFFORM writes for a claim."""
    auth = "53-125.pdf" if c["type"] == "B" else "53-126.pdf"
    out = [("F", "53-120.pdf", fields_53120(c)), ("A", auth, fields_for(c, DESIGNEE))]
    if c["relation"] == "H":
        if c["total_cents"] > AFFIDAVIT_LIMIT_CENTS:
            print(f"warning: claim {c['id']} is over $10,000.00; 53-111-A does not apply, no H member")
        else:
            out.append(("H", "53-111-A.pdf", fields_affidavit(c)))
    return out


def fdf_text(form, fields):
    body = "\n".join(f"<< /T ({k}) /V ({esc(v)}) >>" for k, v in fields.items())
    return (f"%FDF-1.2\n1 0 obj\n<< /FDF << /F ({form})\n/Fields [\n{body}\n] >> >>\nendobj\n"
            f"trailer\n<< /Root 1 0 R >>\n%%EOF\n")


CLAIMS = [
    dict(id="0000000001", type="I", last="ABBOTT", first="ALBERT", mi="L",
         addr1="4417 WOODLAWN AVE", addr2="", city="TEXARKANA", state="TX", zip="75503",
         phone="903-555-0187", fax="", email="", rep_name="", rep_title="", ref1="", ref2="",
         relation="O", owner_name="ABBOT ALBERT L", total_cents=0),
    dict(id="0000000002", type="B", last="A & T CATTLE CO", first="", mi="",
         addr1="PO BOX 118", addr2="", city="DUMAS", state="TX", zip="790290118",
         phone="806-555-0144", fax="806-555-0145", email="", rep_name="MARIA T GARZA",
         rep_title="PRESIDENT", ref1="", ref2="", relation="O", owner_name="A & T CATTLE CO",
         total_cents=0),
    # Heir claim: the owner record ABBIT GEORGE A (8409096800022009MS01000042, $0.50)
    # is real; the heir claimant is invented.
    dict(id="0000000003", type="I", last="ABBIT", first="LINDA", mi="M",
         addr1="210 PECAN ST", addr2="", city="NACOGDOCHES", state="TX", zip="75961",
         phone="936-555-0122", fax="", email="", rep_name="", rep_title="", ref1="", ref2="",
         relation="H", owner_name="ABBIT GEORGE A", total_cents=50),
]

if __name__ == "__main__":
    for c in CLAIMS:
        for prefix, form, fields in members(c):
            name = prefix + c["id"][-7:] + ".fdf"
            with open(os.path.join(HERE, name), "w", newline="\n") as f:
                f.write(fdf_text(form, fields))
            print("wrote", name)
