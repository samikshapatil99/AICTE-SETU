from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Institution, ApprovedIntake, User, Student
from app.schemas import InstitutionOut, ApprovedIntakeOut
from app.auth import current_user, require_roles

router = APIRouter()

def _scope_inst_query(user, db):
    q = db.query(Institution)
    if user.role == "institution":
        q = q.filter(Institution.id == user.institution_id)
    elif user.role == "regional":
        q = q.filter(Institution.state == user.state)
    return q

@router.get("", response_model=list[InstitutionOut])
def list_institutions(user=Depends(current_user), db: Session = Depends(get_db), q: str = None):
    query = _scope_inst_query(user, db)
    if q:
        query = query.filter(Institution.name.ilike(f"%{q}%"))
    return query.order_by(Institution.name).all()

@router.get("/{inst_id}", response_model=InstitutionOut)
def get_institution(inst_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    inst = db.get(Institution, inst_id)
    if not inst:
        raise HTTPException(404, "not found")
    if user.role == "institution" and user.institution_id != inst_id:
        raise HTTPException(403, "forbidden")
    if user.role == "regional" and user.state != inst.state:
        raise HTTPException(403, "forbidden")
    return inst

@router.get("/{inst_id}/intake", response_model=list[ApprovedIntakeOut])
def get_intake(inst_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    return db.query(ApprovedIntake).filter(ApprovedIntake.institution_id == inst_id).all()

@router.get("/{inst_id}/intake-summary")
def intake_summary(inst_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    intakes = db.query(ApprovedIntake).filter(ApprovedIntake.institution_id == inst_id).all()
    out = []
    for it in intakes:
        used = db.query(Student).filter(
            Student.institution_id == inst_id,
            Student.programme == it.programme,
            Student.branch == it.branch,
            Student.year == it.year,
            Student.status.in_(["admitted", "continuing"]),
        ).count()
        super_used = db.query(Student).filter(
            Student.institution_id == inst_id,
            Student.programme == it.programme,
            Student.branch == it.branch,
            Student.year == it.year,
            Student.is_supernumerary == True,
            Student.status.in_(["admitted", "continuing"]),
        ).count()
        out.append({
            "id": it.id,
            "programme": it.programme,
            "branch": it.branch,
            "year": it.year,
            "sanctioned_intake": it.sanctioned_intake,
            "supernumerary_cap": it.supernumerary_cap,
            "used": used,
            "supernumerary_used": super_used,
            "utilisation": round(used / it.sanctioned_intake * 100, 1) if it.sanctioned_intake else 0,
            "breach": used > it.sanctioned_intake,
        })
    return out