import uuid, json, hashlib, io
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Student, VerifiableCredential, Institution
from app.schemas import StudentIn, StudentOut
from app.auth import current_user, require_roles

router = APIRouter()

@router.get("")
def list_students(institution_id: str = None, apaar_id: str = None, status: str = None, programme: str = None, year: int = None, user=Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Student)
    if user.role == "institution":
        q = q.filter(Student.institution_id == user.institution_id)
    elif user.role == "regional":
        inst_ids = [i.id for i in db.query(Institution).filter(Institution.state == user.state).all()]
        q = q.filter(Student.institution_id.in_(inst_ids))
    elif user.role == "student":
        # own record only
        pass
    if institution_id: q = q.filter(Student.institution_id == institution_id)
    if apaar_id: q = q.filter(Student.apaar_id == apaar_id)
    if status: q = q.filter(Student.status == status)
    if programme: q = q.filter(Student.programme == programme)
    if year: q = q.filter(Student.year == year)
    return q.order_by(Student.created_at.desc()).limit(500).all()

@router.get("/{sid}")
def get_student(sid: str, user=Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(Student, sid)
    if not s: raise HTTPException(404, "not found")
    if user.role == "institution" and user.institution_id != s.institution_id:
        raise HTTPException(403, "forbidden")
    if user.role == "student":
        # allow if apaar matches user? simplified: deny
        raise HTTPException(403, "forbidden")
    return s

@router.patch("/{sid}")
def update_student(sid: str, payload: dict = Body(...), user=Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(Student, sid)
    if not s: raise HTTPException(404, "not found")
    if user.role == "institution" and user.institution_id != s.institution_id:
        raise HTTPException(403, "forbidden")
    allowed = ["name","dob","gender","masked_aadhaar","mobile","email","programme","branch","year","admission_date","admission_mode","quota","entrance_exam","entrance_rank","social_category","is_nri","is_oci","is_foreign","is_supernumerary","supernumerary_scheme","doc_ref","status","exit_date","certificate_no","degree_body"]
    for k in allowed:
        if k in payload:
            setattr(s, k, payload[k])
    from datetime import datetime
    s.updated_at = datetime.utcnow()
    db.commit()
    from app.models import AuditLog
    db.add(AuditLog(actor=user.email, role=user.role, action="STUDENT_UPDATED", entity_type="student", entity_id=sid, details=json.dumps(payload)))
    db.commit()
    return s

@router.post("/{sid}/credential")
def issue_credential(sid: str, user=Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(Student, sid)
    if not s: raise HTTPException(404, "not found")
    payload = {"id": s.id, "apaar_id": s.apaar_id, "name": s.name, "institution_id": s.institution_id, "programme": s.programme, "branch": s.branch, "year": s.year, "status": s.status, "issued_at": __import__("datetime").datetime.utcnow().isoformat()}
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    cred_id = str(uuid.uuid4())
    vc = VerifiableCredential(id=cred_id, apaar_id=s.apaar_id, institution_id=s.institution_id, payload=json.dumps(payload), hash=h, signature=h)
    db.add(vc)
    db.commit()
    return {"credentialId": cred_id, "hash": h, "payload": payload, "verifyUrl": f"/verify/{cred_id}"}

@router.get("/{sid}/certificate.pdf")
def certificate_pdf(sid: str, user=Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(Student, sid)
    if not s:
        raise HTTPException(404, "not found")
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    buf = io.BytesIO() if False else None
    import io
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w/2, h-60, "AICTE-SETU — Sample Degree Certificate")
    c.setFont("Helvetica", 12)
    y = h-120
    for line in [
        f"Student Name: {s.name}",
        f"APAAR ID: {s.apaar_id}",
        f"Student ID: {s.id}",
        f"Institution: {s.institution_id}",
        f"Programme: {s.programme} ({s.branch})",
        f"Year: {s.year}",
        f"Status: {s.status}",
        f"Degree-awarding body: {s.degree_body or 'N/A'}",
        f"Certificate No: {s.certificate_no or 'N/A'}",
    ]:
        c.drawString(60, y, line)
        y -= 22
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(w/2, 80, "Verify via QR / verification URL (credential hash on file)")
    c.rect(60, 100, 120, 120)
    c.drawString(65, 160, "QR placeholder")
    c.showPage()
    c.save()
    buffer.seek(0)
    return Response(content=buffer.read(), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=certificate_{sid}.pdf"})