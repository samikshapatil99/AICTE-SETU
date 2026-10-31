import uuid, json, hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Student, VerifiableCredential, VerificationRequest, ConsentLedger, AuditLog
from app.auth import current_user

router = APIRouter()

@router.post("/request")
def request_verification(payload: dict = Body(...), user=Depends(current_user), db: Session = Depends(get_db)):
    apaar_id = payload.get("apaar_id")
    requester = payload.get("requester") or user.email
    if not apaar_id:
        raise HTTPException(400, "apaar_id required")
    vid = str(uuid.uuid4())
    expires = datetime.utcnow() + timedelta(days=7)
    vr = VerificationRequest(id=vid, apaar_id=apaar_id, requester=requester, purpose=payload.get("purpose"), fields=payload.get("fields") or [], expires_at=expires)
    db.add(vr)
    db.commit()
    return {"requestId": vid, "status": "pending", "expires_at": expires.isoformat()}

@router.post("/consent/{rid}")
def grant_consent(rid: str, payload: dict = Body(...), user=Depends(current_user), db: Session = Depends(get_db)):
    vr = db.get(VerificationRequest, rid)
    if not vr:
        raise HTTPException(404, "not found")
    granted = bool(payload.get("granted", True))
    fields = payload.get("fields") or vr.fields
    vr.consent_granted = granted
    vr.fields = fields
    vr.status = "consented" if granted else "denied"
    # consent ledger
    cl = ConsentLedger(student_apaar=vr.apaar_id, requester=vr.requester, purpose=vr.purpose, fields=fields, granted=granted, granted_at=datetime.utcnow() if granted else None, expires_at=vr.expires_at)
    db.add(cl)
    db.commit()
    return {"ok": True, "status": vr.status}

@router.get("/result/{rid}")
def verification_result(rid: str, user=Depends(current_user), db: Session = Depends(get_db)):
    vr = db.get(VerificationRequest, rid)
    if not vr:
        raise HTTPException(404, "not found")
    if not vr.consent_granted:
        raise HTTPException(403, "consent not granted")
    student = db.query(Student).filter(Student.apaar_id == vr.apaar_id).first()
    if not student:
        raise HTTPException(404, "student not found")
    all_fields = {"name": student.name, "dob": student.dob, "gender": student.gender, "institution_id": student.institution_id, "programme": student.programme, "branch": student.branch, "year": student.year, "status": student.status, "admission_date": student.admission_date, "social_category": student.social_category}
    allowed = vr.fields or []
    result = {}
    if not allowed:
        for k in ("name", "institution_id", "programme", "status"):
            result[k] = all_fields[k]
    else:
        for f in allowed:
            if f in all_fields:
                result[f] = all_fields[f]
    db.add(AuditLog(actor=vr.requester, role=user.role, action="VERIFICATION_EXECUTED", entity_type="verification_request", entity_id=vr.id, details=json.dumps({"fields": list(result.keys())})))
    db.commit()
    return {"requestId": vr.id, "apaar_id": vr.apaar_id, "result": result, "consent": True}

@router.get("/credential/{cid}")
def get_credential(cid: str, db: Session = Depends(get_db)):
    c = db.get(VerifiableCredential, cid)
    if not c:
        raise HTTPException(404, "not found")
    return {"credentialId": c.id, "apaar_id": c.apaar_id, "institution_id": c.institution_id, "payload": json.loads(c.payload), "hash": c.hash, "issued_at": c.issued_at.isoformat() if c.issued_at else None}

@router.post("/credential/{cid}/verify")
def verify_credential(cid: str, db: Session = Depends(get_db)):
    c = db.get(VerifiableCredential, cid)
    if not c:
        raise HTTPException(404, "not found")
    payload = json.loads(c.payload)
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return {"valid": h == c.hash, "recomputed": h, "stored": c.hash}