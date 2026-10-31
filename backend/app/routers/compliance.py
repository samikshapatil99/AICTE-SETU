import json
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Student, RuleSet, ComplianceCase, CaseEvidence, CaseDecision, ValidationResult, ChangeEvent, StudentVersion
from app.auth import current_user, require_roles
from app.services.compliance import (
    seed_rule_sets, update_student_versioned, run_validation_for_student, run_validation_for_batch,
    replay_batch, diff_results, create_case_from_flag, update_case_status, resolve_case,
    build_dependencies_for_batch, traverse_impact, preview_correction, build_recovery_plan,
    normalise_preview, apply_recovery, revert_recovery, resolved_trend, add_dependency,
)

router = APIRouter()

@router.get("/rule-sets")
def list_rule_sets(user=Depends(current_user), db: Session = Depends(get_db)):
    seed_rule_sets(db)
    return db.query(RuleSet).all()

@router.post("/students/{sid}/update")
def update_student_versioned_ep(sid: str, payload: dict = Body(...), user=Depends(current_user), db: Session = Depends(get_db)):
    s = update_student_versioned(db, sid, payload.get("changes", {}), user.email, user.role, payload.get("reason"))
    if not s:
        raise HTTPException(404, "not found")
    return {"student": s, "preserved_original": True}

@router.get("/students/{sid}/versions")
def student_versions(sid: str, user=Depends(current_user), db: Session = Depends(get_db)):
    return db.query(StudentVersion).filter(StudentVersion.student_id == sid).order_by(StudentVersion.version_no.desc()).all()

@router.get("/students/{sid}/changes")
def student_changes(sid: str, user=Depends(current_user), db: Session = Depends(get_db)):
    return db.query(ChangeEvent).filter(ChangeEvent.entity_type == "student", ChangeEvent.entity_id == sid).order_by(ChangeEvent.created_at.desc()).all()

@router.post("/students/{sid}/preview-correction")
def preview_correction_ep(sid: str, payload: dict = Body(...), user=Depends(current_user), db: Session = Depends(get_db)):
    rule_set_id = payload.get("rule_set_id", "RULESET-A-2025")
    seed_rule_sets(db)
    return preview_correction(db, sid, payload.get("proposed", {}), rule_set_id)

@router.post("/students/{sid}/validate")
def validate_student_ep(sid: str, payload: dict = Body(default={}), user=Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(Student, sid)
    if not s:
        raise HTTPException(404, "not found")
    seed_rule_sets(db)
    rs_id = payload.get("rule_set_id", "RULESET-A-2025")
    vr, errs = run_validation_for_student(db, s, rs_id, payload.get("batch_id"))
    return {"result_id": vr.id, "outcome": vr.outcome, "errors": errs, "rule_version": vr.rule_version}

@router.post("/batches/{bid}/validate")
def validate_batch_ep(bid: str, payload: dict = Body(default={}), user=Depends(current_user), db: Session = Depends(get_db)):
    seed_rule_sets(db)
    rs_id = payload.get("rule_set_id", "RULESET-A-2025")
    res = run_validation_for_batch(db, bid, rs_id)
    return {"batch_id": bid, "rule_set_id": rs_id, "results": res}

@router.post("/batches/{bid}/replay")
def replay_batch_ep(bid: str, payload: dict = Body(...), user=Depends(current_user), db: Session = Depends(get_db)):
    seed_rule_sets(db)
    rs_a = payload.get("rule_set_a", "RULESET-A-2025")
    rs_b = payload.get("rule_set_b", "RULESET-B-2025")
    res_a = run_validation_for_batch(db, bid, rs_a)
    res_b = run_validation_for_batch(db, bid, rs_b)
    diff = diff_results(res_a, res_b)
    # explanation
    rsa = db.get(RuleSet, rs_a)
    rsb = db.get(RuleSet, rs_b)
    explanation = f"Replay compares outcomes under '{rsa.name}' ({rsa.version}) vs '{rsb.name}' ({rsb.version}). Differences arise from differing thresholds (age max, NRI/management share, duplicate rate) configured in each rule set. These are DEMO RULES, not official AICTE policy."
    return {"rule_set_a": rs_a, "rule_set_b": rs_b, "results_a": res_a, "results_b": res_b, "diff": diff, "explanation": explanation}

@router.get("/batches/{bid}/dependencies")
def batch_dependencies(bid: str, user=Depends(current_user), db: Session = Depends(get_db)):
    build_dependencies_for_batch(db, bid)
    # return all deps touching this batch
    deps = db.query(Dependency).filter(Dependency.from_id.contains(bid) | Dependency.to_id.contains(bid)).all() if False else db.query(Dependency).all()
    # filter relevant
    relevant = [d for d in deps if bid in (d.from_id or "") or bid in (d.to_id or "") or f"batch_{bid}" in (d.from_id or "") or f"batch_{bid}" in (d.to_id or "")]
    return [{"from": f"{d.from_type}:{d.from_id}", "to": f"{d.to_type}:{d.to_id}", "reason": d.reason} for d in relevant]

@router.get("/impact/{from_type}/{from_id}")
def impact_traversal(from_type: str, from_id: str, depth: int = 3, user=Depends(current_user), db: Session = Depends(get_db)):
    res = traverse_impact(db, from_type, from_id, depth)
    return {"from": f"{from_type}:{from_id}", "affected": res, "count": len(res)}

# ---------- Cases ----------
@router.post("/cases/from-flag/{flag_id}")
def case_from_flag(flag_id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    case = create_case_from_flag(db, flag_id)
    return {"case_id": case.id, "status": case.status}

@router.get("/cases")
def list_cases(status: str = None, user=Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(ComplianceCase)
    if status:
        q = q.filter(ComplianceCase.status == status)
    if user.role == "institution":
        q = q.filter(ComplianceCase.institution_id == user.institution_id)
    if user.role == "regional":
        pass
    return q.order_by(ComplianceCase.created_at.desc()).all()

@router.get("/cases/{case_id}")
def get_case(case_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    case = db.get(ComplianceCase, case_id)
    if not case:
        raise HTTPException(404, "not found")
    evidence = db.query(CaseEvidence).filter(CaseEvidence.case_id == case_id).all()
    decisions = db.query(CaseDecision).filter(CaseDecision.case_id == case_id).all()
    # group evidence by kind
    panels = {}
    for e in evidence:
        panels.setdefault(e.kind, []).append({"label": e.label, "content": e.content, "created_at": str(e.created_at)})
    return {"case": case, "panels": panels, "decisions": decisions}

@router.post("/cases/{case_id}/status")
def case_status(case_id: str, payload: dict = Body(...), user=Depends(current_user), db: Session = Depends(get_db)):
    c = update_case_status(db, case_id, payload.get("status"), user.email, payload.get("rationale"))
    if not c:
        raise HTTPException(404, "not found")
    return {"case_id": c.id, "status": c.status}

@router.post("/cases/{case_id}/resolve")
def case_resolve(case_id: str, payload: dict = Body(...), user=Depends(require_roles("admin", "regional", "auditor")), db: Session = Depends(get_db)):
    # closing a case after correction requires authorised reviewer approval
    c = resolve_case(db, case_id, user.email, user.role, payload.get("rationale", ""), payload.get("outcome", "resolved"))
    if not c:
        raise HTTPException(404, "not found")
    return {"case_id": c.id, "status": c.status}

# ---------- Recovery planner ----------
@router.get("/recovery/plan")
def recovery_plan(institution_id: str = None, user=Depends(current_user), db: Session = Depends(get_db)):
    iid = institution_id or (user.institution_id if user.role == "institution" else None)
    return build_recovery_plan(db, iid)

@router.post("/recovery/normalise-preview")
def recovery_preview(payload: dict = Body(...), user=Depends(current_user), db: Session = Depends(get_db)):
    return normalise_preview(db, payload.get("issue_id"), payload.get("proposed", {}))

@router.post("/recovery/apply/{action_id}")
def recovery_apply(action_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    return apply_recovery(db, action_id, user.email)

@router.post("/recovery/revert/{action_id}")
def recovery_revert(action_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    return revert_recovery(db, action_id)

@router.get("/recovery/trend")
def recovery_trend(user=Depends(current_user), db: Session = Depends(get_db)):
    return resolved_trend(db)