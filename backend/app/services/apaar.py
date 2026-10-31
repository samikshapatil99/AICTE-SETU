import re
from sqlalchemy.orm import Session
from app.models import ApaarRegistry

def check_format(apaar_id):
    if not apaar_id:
        return False, "MISSING_APAAR"
    if not re.fullmatch(r"\d{12}", str(apaar_id).strip()):
        return False, "INVALID_FORMAT"
    return True, None

def validate_apaar(db: Session, apaar_id, record):
    ok, reason = check_format(apaar_id)
    if not ok:
        return {"valid": False, "reason": reason}
    reg = db.get(ApaarRegistry, str(apaar_id).strip())
    if not reg:
        return {"valid": False, "reason": "APAAR_NOT_FOUND"}
    # soft cross-check name/DOB
    name_match = (reg.name or "").strip().lower() == (record.get("name") or "").strip().lower()
    dob_match = reg.dob == record.get("dob")
    if not (name_match and dob_match):
        return {"valid": True, "reason": "MISMATCH_NAME_DOB", "soft": True, "registry": {"name": reg.name, "dob": reg.dob}}
    return {"valid": True, "reason": None, "registry": {"name": reg.name, "dob": reg.dob}}