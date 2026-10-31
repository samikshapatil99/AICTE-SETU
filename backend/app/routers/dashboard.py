from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Institution, Student, UploadBatch, Flag, ApprovedIntake
from app.auth import current_user, require_roles
from app.services.intake import intake_summary, institution_risk_score, data_completeness

router = APIRouter()

@router.get("/aicte/overview")
def aicte_overview(user=Depends(current_user), db: Session = Depends(get_db)):
    # scope by regional
    inst_q = db.query(Institution)
    if user.role == "regional":
        inst_q = inst_q.filter(Institution.state == user.state)
    inst_ids = [i.id for i in inst_q.all()]
    students_q = db.query(Student)
    if user.role == "regional":
        students_q = students_q.filter(Student.institution_id.in_(inst_ids))
    total_students = students_q.count()
    total_institutions = inst_q.count()
    batches = db.query(UploadBatch).count() if user.role != "regional" else db.query(UploadBatch).filter(UploadBatch.institution_id.in_(inst_ids)).count()
    confirmed = db.query(UploadBatch).filter(UploadBatch.status == "confirmed").count() if user.role != "regional" else db.query(UploadBatch).filter(UploadBatch.institution_id.in_(inst_ids), UploadBatch.status == "confirmed").count()
    open_flags = db.query(Flag).filter(Flag.status == "open").count()
    if user.role == "regional":
        open_flags = db.query(Flag).filter(Flag.institution_id.in_(inst_ids), Flag.status == "open").count()
    high_flags = db.query(Flag).filter(Flag.status == "open", Flag.severity == "high").count()
    if user.role == "regional":
        high_flags = db.query(Flag).filter(Flag.institution_id.in_(inst_ids), Flag.status == "open", Flag.severity == "high").count()

    by_state = db.query(Institution.state, func.count(func.distinct(Institution.id)), func.count(Student.id)).outerjoin(Student, Student.institution_id == Institution.id).group_by(Institution.state).all()
    by_state_out = [{"state": s, "institutions": ic, "students": sc} for s, ic, sc in by_state]
    if user.role == "regional":
        by_state_out = [x for x in by_state_out if x["state"] == user.state]

    by_category = db.query(Student.social_category, func.count(Student.id)).group_by(Student.social_category).all()
    nri = db.query(Student).filter(Student.is_nri == True).count()
    oci = db.query(Student).filter(Student.is_oci == True).count()
    fn = db.query(Student).filter(Student.is_foreign == True).count()
    superc = db.query(Student).filter(Student.is_supernumerary == True).count()

    return {
        "institutions": total_institutions,
        "students": total_students,
        "batches": batches,
        "confirmed": confirmed,
        "openFlags": open_flags,
        "highFlags": high_flags,
        "byState": by_state_out,
        "byCategory": [{"category": c, "count": n} for c, n in by_category],
        "nriCount": nri, "ociCount": oci, "fnCount": fn, "superCount": superc,
    }

@router.get("/aicte/flagged")
def flagged_institutions(user=Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Institution)
    if user.role == "regional":
        q = q.filter(Institution.state == user.state)
    insts = q.all()
    out = []
    for inst in insts:
        oc = db.query(Flag).filter(Flag.institution_id == inst.id, Flag.status == "open").count()
        if oc > 0:
            out.append({"id": inst.id, "name": inst.name, "state": inst.state, "risk_score": inst.risk_score, "compliance_score": inst.compliance_score, "open_flags": oc})
    out.sort(key=lambda x: (-x["risk_score"], -x["open_flags"]))
    return out

@router.get("/aicte/flags")
def list_flags(status: str = None, severity: str = None, institution_id: str = None, user=Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Flag)
    if status: q = q.filter(Flag.status == status)
    if severity: q = q.filter(Flag.severity == severity)
    if institution_id: q = q.filter(Flag.institution_id == institution_id)
    if user.role == "institution":
        q = q.filter(Flag.institution_id == user.institution_id)
    if user.role == "regional":
        inst_ids = [i.id for i in db.query(Institution).filter(Institution.state == user.state).all()]
        q = q.filter(Flag.institution_id.in_(inst_ids))
    return q.order_by(Flag.created_at.desc()).limit(200).all()

@router.post("/aicte/flags/{flag_id}/resolve")
def resolve_flag(flag_id: int, payload: dict = None, user=Depends(current_user), db: Session = Depends(get_db)):
    f = db.get(Flag, flag_id)
    if not f:
        from fastapi import HTTPException
        raise HTTPException(404, "not found")
    f.status = "resolved"
    f.resolved_at = __import__("datetime").datetime.utcnow()
    if payload and payload.get("comment"):
        f.comment = payload.get("comment")
    if payload and payload.get("assigned_to"):
        f.assigned_to = payload.get("assigned_to")
    db.commit()
    return {"ok": True}

@router.get("/aicte/intake-utilisation")
def intake_utilisation(user=Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(ApprovedIntake)
    if user.role == "institution":
        q = q.filter(ApprovedIntake.institution_id == user.institution_id)
    if user.role == "regional":
        inst_ids = [i.id for i in db.query(Institution).filter(Institution.state == user.state).all()]
        q = q.filter(ApprovedIntake.institution_id.in_(inst_ids))
    out = []
    for it in q.all():
        inst = db.get(Institution, it.institution_id)
        used = db.query(Student).filter(Student.institution_id == it.institution_id, Student.programme == it.programme, Student.branch == it.branch, Student.year == it.year, Student.status.in_(["admitted", "continuing"])).count()
        super_used = db.query(Student).filter(Student.institution_id == it.institution_id, Student.programme == it.programme, Student.branch == it.branch, Student.year == it.year, Student.is_supernumerary == True, Student.status.in_(["admitted", "continuing"])).count()
        out.append({"institution_id": it.institution_id, "name": inst.name if inst else "", "state": inst.state if inst else "", "programme": it.programme, "branch": it.branch, "year": it.year, "sanctioned_intake": it.sanctioned_intake, "supernumerary_cap": it.supernumerary_cap or 0, "used": used, "supernumeraryUsed": super_used, "utilisation": round(used / it.sanctioned_intake * 100, 1) if it.sanctioned_intake else 0})
    return out

@router.get("/institution/{inst_id}")
def institution_dashboard(inst_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    if user.role == "institution" and user.institution_id != inst_id:
        from fastapi import HTTPException
        raise HTTPException(403, "forbidden")
    inst = db.get(Institution, inst_id)
    if not inst:
        from fastapi import HTTPException
        raise HTTPException(404, "not found")
    batches = db.query(UploadBatch).filter(UploadBatch.institution_id == inst_id).order_by(UploadBatch.created_at.desc()).all()
    students = db.query(Student).filter(Student.institution_id == inst_id).count()
    flags = db.query(Flag).filter(Flag.institution_id == inst_id).order_by(Flag.created_at.desc()).all()
    risk = institution_risk_score(db, inst_id)
    dc = data_completeness(db, inst_id)
    return {"institution": inst, "intake": intake_summary(db, inst_id), "batches": batches, "students": students, "flags": flags, "risk": risk, "dataCompleteness": dc}

@router.get("/batches")
def list_batches(institution_id: str = None, user=Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(UploadBatch)
    if institution_id:
        q = q.filter(UploadBatch.institution_id == institution_id)
    if user.role == "institution":
        q = q.filter(UploadBatch.institution_id == user.institution_id)
    return q.order_by(UploadBatch.created_at.desc()).limit(100).all()