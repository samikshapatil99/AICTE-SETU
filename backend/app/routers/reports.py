import csv, io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Student, Institution, Flag
from app.auth import current_user

router = APIRouter()

@router.get("/intake-vs-enrolment")
def report_intake(user=Depends(current_user), db: Session = Depends(get_db), format: str = "json"):
    from app.services.intake import intake_summary
    insts = db.query(Institution).all()
    if user.role == "institution":
        insts = [i for i in insts if i.id == user.institution_id]
    if user.role == "regional":
        insts = [i for i in insts if i.state == user.state]
    rows = []
    for inst in insts:
        for it in intake_summary(db, inst.id):
            rows.append({"institution": inst.name, "state": inst.state, **it})
    if format == "csv":
        buf = io.StringIO()
        if rows:
            w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=intake_vs_enrolment.csv"})
    return rows

@router.get("/category-wise")
def report_category(user=Depends(current_user), db: Session = Depends(get_db)):
    from sqlalchemy import func
    q = db.query(Student.is_nri, Student.is_oci, Student.is_foreign, Student.is_supernumerary, func.count(Student.id))
    if user.role == "institution":
        q = q.filter(Student.institution_id == user.institution_id)
    rows = q.group_by(Student.is_nri, Student.is_oci, Student.is_foreign, Student.is_supernumerary).all()
    return [{"nri": r[0], "oci": r[1], "foreign": r[2], "supernumerary": r[3], "count": r[4]} for r in rows]

@router.get("/duplicates")
def report_duplicates(user=Depends(current_user), db: Session = Depends(get_db)):
    from sqlalchemy import func
    sub = db.query(Student.apaar_id, func.count(Student.id).label("c")).group_by(Student.apaar_id).having(func.count(Student.id) > 1).all()
    out = []
    for apaar, c in sub:
        recs = db.query(Student).filter(Student.apaar_id == apaar).all()
        out.append({"apaar_id": apaar, "count": c, "institutions": list({r.institution_id for r in recs})})
    return out

@router.get("/risk")
def report_risk(user=Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Institution)
    if user.role == "regional":
        q = q.filter(Institution.state == user.state)
    if user.role == "institution":
        q = q.filter(Institution.id == user.institution_id)
    return [{"id": i.id, "name": i.name, "state": i.state, "risk_score": i.risk_score, "compliance_score": i.compliance_score} for i in q.all()]