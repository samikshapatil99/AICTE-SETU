import json, uuid, hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import (
    Student, StudentVersion, ChangeEvent, RuleSet, ValidationResult, ComplianceCase,
    CaseDecision, CaseEvidence, Dependency, IssueClassification, RecoveryAction, Flag, UploadBatch, Institution, StagingRecord
)
from app.services.rules import run_rules, truthy
from app.services.apaar import validate_apaar
# check_intake_batch lives in app.services.rules
from app.services.anomaly import detect_anomalies

# ---------- Rule sets seed ----------
def seed_rule_sets(db: Session):
    if db.query(RuleSet).count() > 0:
        return
    cfg_a = {"age_max": 30, "nri_share_threshold": 0.4, "mgmt_share_threshold": 0.5, "dup_rate_threshold": 0.1, "intake_hard_block": True}
    cfg_b = {"age_max": 28, "nri_share_threshold": 0.3, "mgmt_share_threshold": 0.4, "dup_rate_threshold": 0.05, "intake_hard_block": True}
    rs_a = RuleSet(id="RULESET-A-2025", name="AICTE Demo Rule Set A", version="A-2025.1", academic_year="2025-26", scope="national", effective_from="2025-07-01", effective_to="2025-12-31", source_reference="Demo policy note vA (fictional)", approval_status="approved", description="Baseline demo rules. Labelled FICTIONAL, not official AICTE policy.", config=json.dumps(cfg_a))
    rs_b = RuleSet(id="RULESET-B-2025", name="AICTE Demo Rule Set B", version="B-2025.1", academic_year="2025-26", scope="national", effective_from="2025-07-01", effective_to="2025-12-31", source_reference="Demo policy note vB (fictional)", approval_status="approved", description="Stricter demo rules (lower age limit, lower NRI/management thresholds). Labelled FICTIONAL.", config=json.dumps(cfg_b))
    db.add_all([rs_a, rs_b])
    db.commit()

# ---------- Versioning ----------
def snapshot_student(s: Student):
    return {c.name: getattr(s, c.name) for c in s.__table__.columns}

def create_student_version(db: Session, student: Student, changed_by: str, reason: str = None):
    last = db.query(StudentVersion).filter(StudentVersion.student_id == student.id).order_by(StudentVersion.version_no.desc()).first()
    vno = (last.version_no + 1) if last else 1
    sv = StudentVersion(id=str(uuid.uuid4()), student_id=student.id, version_no=vno, snapshot=json.dumps(snapshot_student(student), default=str), changed_by=changed_by, change_reason=reason)
    db.add(sv)
    db.commit()
    return sv

def record_change_event(db: Session, entity_type, entity_id, field, old_value, new_value, actor, actor_role=None, reason=None):
    ce = ChangeEvent(id=str(uuid.uuid4()), entity_type=entity_type, entity_id=entity_id, field=field, old_value=None if old_value is None else str(old_value), new_value=None if new_value is None else str(new_value), actor=actor, actor_role=actor_role, reason=reason)
    db.add(ce)
    db.commit()
    return ce

def update_student_versioned(db: Session, student_id: str, payload: dict, actor: str, actor_role: str = None, reason: str = None):
    s = db.get(Student, student_id)
    if not s:
        return None
    # record change events for changed fields
    allowed = list(payload.keys())
    for k in allowed:
        if hasattr(s, k) and k in payload and payload[k] != getattr(s, k):
            record_change_event(db, "student", student_id, k, getattr(s, k), payload[k], actor, actor_role, reason)
    # apply
    for k in allowed:
        if hasattr(s, k):
            setattr(s, k, payload[k])
    s.updated_at = datetime.utcnow()
    db.commit()
    create_student_version(db, s, actor, reason)
    return s

# ---------- Rule execution with version awareness ----------
def rules_with_config(config: dict):
    # returns a function that adjusts run_rules? We'll post-process: run base rules then apply config thresholds as extra checks via anomaly-style.
    return config

def run_validation_for_student(db: Session, student: Student, rule_set_id: str, batch_id: str = None):
    rs = db.get(RuleSet, rule_set_id)
    cfg = json.loads(rs.config) if rs else {}
    # build a pseudo-record
    rec = snapshot_student(student)
    rec["institution_id"] = student.institution_id
    rec["programme"] = student.programme
    rec["branch"] = student.branch
    rec["year"] = student.year
    rec["social_category"] = student.social_category
    rec["is_nri"] = student.is_nri
    rec["is_oci"] = student.is_oci
    rec["is_foreign"] = student.is_foreign
    rec["is_supernumerary"] = student.is_supernumerary
    rec["supernumerary_scheme"] = student.supernumerary_scheme
    rec["quota"] = student.quota
    rec["admission_date"] = student.admission_date
    rec["dob"] = student.dob
    rec["name"] = student.name
    rec["apaar_id"] = student.apaar_id

    # base rules
    errs = run_rules(rec, [rec], 0, student.institution_id, [])
    # config-driven extra checks
    # age max
    try:
        if rec.get("dob"):
            from datetime import datetime as dt
            d = dt.strptime(rec["dob"], "%Y-%m-%d")
            age = (datetime.utcnow().date() - d.date()).days // 365
            if age > cfg.get("age_max", 30):
                errs.append({"code": "AGE_LIMIT_EXCEEDED", "severity": "low", "message": f"Age {age} exceeds rule-set max {cfg.get('age_max')}", "field": "dob"})
    except ValueError:
        pass

    outcome = "rejected" if any(e["severity"] == "high" for e in errs) else ("warning" if errs else "valid")

    # input snapshot ref
    snap_ref = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest()[:16]

    vr = ValidationResult(
        id=str(uuid.uuid4()),
        student_id=student.id,
        batch_id=batch_id,
        apaar_id=student.apaar_id,
        rule_set_id=rule_set_id,
        rule_version=rs.version if rs else rule_set_id,
        input_snapshot_ref=snap_ref,
        outcome=outcome,
        errors_json=json.dumps(errs),
        triggered_rules=json.dumps([e["code"] for e in errs]),
    )
    db.add(vr)
    db.commit()
    return vr, errs

def run_validation_for_batch(db: Session, batch_id: str, rule_set_id: str):
    batch = db.get(UploadBatch, batch_id)
    if not batch:
        return []
    staging = db.query(StagingRecord).filter(StagingRecord.batch_id == batch_id).all()
    results = []
    for s in staging:
        rec = json.loads(s.record_json)
        # find or create student? For replay on staging, we validate the record directly
        # We'll create a transient validation result keyed by batch+row
        rs = db.get(RuleSet, rule_set_id)
        cfg = json.loads(rs.config) if rs else {}
        errs = run_rules(rec, [json.loads(x.record_json) for x in staging], s.row_index, batch.institution_id, [])
        # age max
        try:
            if rec.get("dob"):
                from datetime import datetime as dt
                d = dt.strptime(rec["dob"], "%Y-%m-%d")
                age = (datetime.utcnow().date() - d.date()).days // 365
                if age > cfg.get("age_max", 30):
                    errs.append({"code": "AGE_LIMIT_EXCEEDED", "severity": "low", "message": f"Age {age} exceeds rule-set max {cfg.get('age_max')}", "field": "dob"})
        except ValueError:
            pass
        outcome = "rejected" if any(e["severity"] == "high" for e in errs) else ("warning" if errs else "valid")
        snap_ref = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest()[:16]
        vr = ValidationResult(id=str(uuid.uuid4()), student_id=None, batch_id=batch_id, apaar_id=rec.get("apaar_id"), rule_set_id=rule_set_id, rule_version=rs.version if rs else rule_set_id, input_snapshot_ref=snap_ref, outcome=outcome, errors_json=json.dumps(errs), triggered_rules=json.dumps([e["code"] for e in errs]))
        db.add(vr)
        db.commit()
        results.append({"row": s.row_index, "outcome": outcome, "errors": errs, "result_id": vr.id})
    return results

# ---------- Replay ----------
def replay_batch(db: Session, batch_id: str, rule_set_id: str):
    return run_validation_for_batch(db, batch_id, rule_set_id)

def diff_results(res_a, res_b):
    # res: list of {row, outcome, errors}
    diff = []
    by_row_a = {r["row"]: r for r in res_a}
    by_row_b = {r["row"]: r for r in res_b}
    for row in sorted(set(by_row_a) | set(by_row_b)):
        a = by_row_a.get(row)
        b = by_row_b.get(row)
        changed = (a and b and (a["outcome"] != b["outcome"] or [e["code"] for e in a["errors"]] != [e["code"] for e in b["errors"]]))
        diff.append({"row": row, "a": a, "b": b, "changed": bool(changed)})
    return diff

# ---------- Cases ----------
def create_case_from_flag(db: Session, flag_id: int, institution_id=None, apaar_id=None, student_id=None, title=None):
    flag = db.get(Flag, flag_id)
    if flag:
        institution_id = institution_id or flag.institution_id
        apaar_id = apaar_id or flag.apaar_id
        student_id = student_id or None
        title = title or f"Case from flag: {flag.flag_type}"
    case = ComplianceCase(id=str(uuid.uuid4()), source_flag_id=flag_id, institution_id=institution_id, apaar_id=apaar_id, student_id=student_id, status="open", title=title)
    db.add(case)
    db.commit()
    # evidence panels
    if flag:
        db.add(CaseEvidence(id=str(uuid.uuid4()), case_id=case.id, kind="observed_fact", label="Flag raised", content=json.dumps({"flag_type": flag.flag_type, "severity": flag.severity, "reason": flag.reason, "created_at": str(flag.created_at), "institution_id": flag.institution_id, "apaar_id": flag.apaar_id})))
        db.add(CaseEvidence(id=str(uuid.uuid4()), case_id=case.id, kind="rule_evidence", label="Rule that fired", content=json.dumps({"rule_id": flag.flag_type, "rule_version": "see validation result", "check": flag.reason})))
        db.add(CaseEvidence(id=str(uuid.uuid4()), case_id=case.id, kind="system_inference", label="SYSTEM INFERENCE (not a finding)", content="The system flags this pattern for human review. It is a signal, not an automatic finding of fraud or non-compliance."))
        db.add(CaseEvidence(id=str(uuid.uuid4()), case_id=case.id, kind="impact", label="Impact", content="Affected: institution record, programme intake summary, downstream reports."))
        db.add(CaseEvidence(id=str(uuid.uuid4()), case_id=case.id, kind="recommended_action", label="Recommended action", content="Review evidence, request documents if needed, decide resolve/escalate."))
    db.commit()
    return case

def update_case_status(db: Session, case_id: str, status: str, actor: str, rationale: str = None):
    case = db.get(ComplianceCase, case_id)
    if not case:
        return None
    case.status = status
    case.updated_at = datetime.utcnow()
    db.commit()
    if rationale:
        db.add(CaseDecision(id=str(uuid.uuid4()), case_id=case_id, reviewer=actor, reviewer_role=None, rationale=rationale, outcome=status))
        db.commit()
    return case

def resolve_case(db: Session, case_id: str, reviewer: str, reviewer_role: str, rationale: str, outcome: str):
    case = db.get(ComplianceCase, case_id)
    if not case:
        return None
    case.status = outcome  # resolved/escalated
    case.updated_at = datetime.utcnow()
    db.add(CaseDecision(id=str(uuid.uuid4()), case_id=case_id, reviewer=reviewer, reviewer_role=reviewer_role, rationale=rationale, outcome=outcome))
    db.commit()
    return case

# ---------- Dependency graph ----------
def add_dependency(db: Session, from_type, from_id, to_type, to_id, reason=None):
    dep = Dependency(from_type=from_type, from_id=from_id, to_type=to_type, to_id=to_id, reason=reason)
    db.add(dep)
    db.commit()
    return dep

def build_dependencies_for_batch(db: Session, batch_id: str):
    # student_record -> validation_result -> programme_intake_summary -> case -> institutional_report
    batch = db.get(UploadBatch, batch_id)
    if not batch:
        return
    inst_id = batch.institution_id
    # gather students in this batch (via staging)
    staging = db.query(StagingRecord).filter(StagingRecord.batch_id == batch_id).all()
    for s in staging:
        rec = json.loads(s.record_json)
        apaar = rec.get("apaar_id")
        # find student record if exists
        # validation result: find VR for this batch+row? We store by batch only. Use latest VR for batch.
        vrs = db.query(ValidationResult).filter(ValidationResult.batch_id == batch_id).all()
        for vr in vrs:
            if vr.input_snapshot_ref == hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest()[:16]:
                add_dependency(db, "student_record", apaar or f"row_{s.row_index}", "validation_result", vr.id, "validation of uploaded record")
        # programme intake summary dependency: represent as institution+programme+branch+year
        key = f"{inst_id}|{rec.get('programme')}|{rec.get('branch')}|{rec.get('year')}"
        add_dependency(db, "validation_result", f"batch_{batch_id}", "programme_intake_summary", key, "affects intake counts")
    # cases from flags
    flags = db.query(Flag).filter(Flag.batch_id == batch_id).all()
    for f in flags:
        cases = db.query(ComplianceCase).filter(ComplianceCase.source_flag_id == f.id).all()
        for c in cases:
            add_dependency(db, "validation_result", f"batch_{batch_id}", "compliance_case", c.id, "flag escalated to case")
    # institutional report
    add_dependency(db, "programme_intake_summary", f"{inst_id}", "institutional_report", f"report_{inst_id}", "feeds reports")

def traverse_impact(db: Session, from_type: str, from_id: str, depth: int = 3):
    # BFS over dependencies
    visited = set()
    result = []
    frontier = [(from_type, from_id, 0)]
    while frontier:
        ft, fid, d = frontier.pop(0)
        if d > depth:
            continue
        key = (ft, fid)
        if key in visited:
            continue
        visited.add(key)
        if d > 0:
            result.append({"type": ft, "id": fid, "depth": d})
        # outgoing edges
        edges = db.query(Dependency).filter(Dependency.from_type == ft, Dependency.from_id == fid).all()
        for e in edges:
            frontier.append((e.to_type, e.to_id, d + 1))
        # also incoming? impact = downstream, so outgoing only
    return result

def preview_correction(db: Session, student_id: str, proposed: dict, rule_set_id: str):
    s = db.get(Student, student_id)
    if not s:
        return None
    before_vr, before_errs = run_validation_for_student(db, s, rule_set_id)
    # proposed state (not committed): work on a dict copy
    base = snapshot_student(s)
    for k, v in proposed.items():
        if k in base:
            base[k] = v
    rec = dict(base)
    rec["institution_id"] = base.get("institution_id") or s.institution_id
    rec["programme"] = base.get("programme") or s.programme
    rec["branch"] = base.get("branch") or s.branch
    rec["year"] = base.get("year") or s.year
    rec["social_category"] = base.get("social_category") or s.social_category
    rec["is_nri"] = base.get("is_nri") if base.get("is_nri") is not None else s.is_nri
    rec["is_oci"] = base.get("is_oci") if base.get("is_oci") is not None else s.is_oci
    rec["is_foreign"] = base.get("is_foreign") if base.get("is_foreign") is not None else s.is_foreign
    rec["is_supernumerary"] = base.get("is_supernumerary") if base.get("is_supernumerary") is not None else s.is_supernumerary
    rec["supernumerary_scheme"] = base.get("supernumerary_scheme") or s.supernumerary_scheme
    rec["quota"] = base.get("quota") or s.quota
    rec["admission_date"] = base.get("admission_date") or s.admission_date
    rec["dob"] = base.get("dob") or s.dob
    rec["name"] = base.get("name") or s.name
    rec["apaar_id"] = base.get("apaar_id") or s.apaar_id
    rs = db.get(RuleSet, rule_set_id)
    cfg = json.loads(rs.config) if rs else {}
    after_errs = run_rules(rec, [rec], 0, s.institution_id, [])
    try:
        if rec.get("dob"):
            from datetime import datetime as dt
            d = dt.strptime(rec["dob"], "%Y-%m-%d")
            age = (datetime.utcnow().date() - d.date()).days // 365
            if age > cfg.get("age_max", 30):
                after_errs.append({"code": "AGE_LIMIT_EXCEEDED", "severity": "low", "message": f"Age {age} exceeds rule-set max {cfg.get('age_max')}", "field": "dob"})
    except ValueError:
        pass
    after_outcome = "rejected" if any(e["severity"] == "high" for e in after_errs) else ("warning" if after_errs else "valid")

    # intake counts before/after (same programme, no change in count since not committed) - show current
    from app.services.intake import intake_summary
    intake = intake_summary(db, s.institution_id)

    return {
        "before": {"outcome": before_vr.outcome, "errors": before_errs, "result_id": before_vr.id},
        "after": {"outcome": after_outcome, "errors": after_errs},
        "proposed": proposed,
        "original_preserved": True,
        "intake_summary": intake,
        "open_cases_before": db.query(ComplianceCase).filter(ComplianceCase.student_id == student_id, ComplianceCase.status.in_(["open", "evidence_requested", "under_review"])).count(),
    }

# ---------- Recovery planner ----------
def classify_issue(entity_type, entity_id, record, field=None):
    # transparent classification
    if field and (record.get(field) is None or str(record.get(field)).strip() == ""):
        return "missing_field"
    # inconsistent value: nri without nri quota etc.
    if record.get("is_nri") and "nri" not in str(record.get("quota") or "").lower() and "management" not in str(record.get("quota") or "").lower():
        return "inconsistent_value"
    if record.get("is_oci") and str(record.get("social_category") or "").lower() in ("sc", "st", "obc"):
        return "inconsistent_value"
    # suspected duplicate handled separately
    return "manual_review"

def priority_score(severity, downstream_impact, days_to_deadline):
    sev_map = {"high": 30, "medium": 20, "low": 10}
    base = sev_map.get(severity, 10)
    impact = min(40, downstream_impact * 5)
    urgency = 0
    if days_to_deadline is not None:
        if days_to_deadline <= 7:
            urgency = 20
        elif days_to_deadline <= 30:
            urgency = 10
    return base + impact + urgency

def build_recovery_plan(db: Session, institution_id: str = None):
    # classify open issues from flags + validation errors
    issues = []
    fq = db.query(Flag).filter(Flag.status == "open")
    if institution_id:
        fq = fq.filter(Flag.institution_id == institution_id)
    for f in fq.all():
        # Check if already classified
        ic = db.query(IssueClassification).filter(IssueClassification.entity_id == str(f.id)).first()
        if ic:
            if ic.status == "resolved":
                continue
        else:
            sev = f.severity or "medium"
            downstream = 3 if f.flag_type in ("INTAKE_BREACH", "CROSS_INST_DUP") else 1
            ps = priority_score(sev, downstream, 14)
            itype = "suspected_duplicate" if "DUP" in (f.flag_type or "") else ("inconsistent_value" if "MISMATCH" in (f.flag_type or "") or "QUOTA" in (f.flag_type or "") else "manual_review")
            ic = IssueClassification(id=str(uuid.uuid4()), entity_type="flag", entity_id=str(f.id), issue_type=itype, severity=sev, deadline=None, downstream_impact=downstream, priority_score=ps, status="open")
            db.add(ic)
            db.commit()
        issues.append({
            "id": ic.id,
            "flag_id": f.id,
            "type": ic.issue_type,
            "severity": ic.severity,
            "priority": ic.priority_score,
            "reason": f.reason or f.flag_type,
            "flag_type": f.flag_type,
            "student_name": f.student_name,
            "apaar_id": f.apaar_id
        })
    issues.sort(key=lambda x: -x["priority"])
    return issues

def normalise_preview(db: Session, issue_id: str, proposed: dict):
    ic = db.get(IssueClassification, issue_id) if issue_id else None
    if not ic and issue_id:
        # Fallback: maybe issue_id is flag.id
        flag = db.query(Flag).filter((Flag.id == issue_id) | (Flag.id == str(issue_id))).first()
        if flag:
            ic = db.query(IssueClassification).filter(IssueClassification.entity_id == str(flag.id)).first()
            if not ic:
                ic = IssueClassification(id=str(uuid.uuid4()), entity_type="flag", entity_id=str(flag.id), issue_type="inconsistent_value", severity=flag.severity or "medium", priority_score=30, status="open")
                db.add(ic)
                db.commit()

    ic_id = ic.id if ic else (issue_id or str(uuid.uuid4()))
    ra = RecoveryAction(id=str(uuid.uuid4()), issue_id=ic_id, action_type="normalise", preview_diff=json.dumps(proposed), applied=False)
    db.add(ra)
    db.commit()

    flag = db.query(Flag).filter(Flag.id == ic.entity_id).first() if ic else None
    return {
        "action_id": ra.id,
        "issue_id": ic_id,
        "reason": flag.reason if flag else "Inconsistent student admission record",
        "student_name": flag.student_name if flag else "Student Record",
        "apaar_id": flag.apaar_id if flag else "N/A",
        "before": {"quota": "Mismatch", "social_category": "Inconsistent"},
        "preview": proposed,
        "reversible": True
    }

def apply_recovery(db: Session, action_id: str, actor: str):
    ra = db.get(RecoveryAction, action_id)
    if not ra:
        return None
    ra.applied = True
    ra.applied_by = actor
    ra.applied_at = datetime.utcnow()
    ic = db.get(IssueClassification, ra.issue_id)
    if ic:
        ic.status = "resolved"
        ic.resolved_at = datetime.utcnow()
    # Add audit log
    from app.models import AuditLog
    db.add(AuditLog(actor=actor or "admin@aicte.gov.in", role="admin", action="RECOVERY_APPLIED", entity_type="recovery_action", entity_id=action_id, details=json.dumps({"issue_id": ra.issue_id, "status": "resolved"})))
    db.commit()
    return {"action_id": action_id, "applied": True}

def revert_recovery(db: Session, action_id: str):
    ra = db.get(RecoveryAction, action_id)
    if not ra:
        return None
    ra.applied = False
    ra.reverted = True
    ic = db.get(IssueClassification, ra.issue_id)
    if ic:
        ic.status = "open"
        ic.resolved_at = None
    # Add audit log
    from app.models import AuditLog
    db.add(AuditLog(actor="admin@aicte.gov.in", role="admin", action="RECOVERY_REVERTED", entity_type="recovery_action", entity_id=action_id, details=json.dumps({"action_id": action_id, "status": "reverted"})))
    db.commit()
    return {"action_id": action_id, "reverted": True}

def resolved_trend(db: Session):
    # count resolved issues per day (last 7 days)
    from datetime import timedelta
    today = datetime.utcnow().date()
    out = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        cnt = db.query(IssueClassification).filter(IssueClassification.status == "resolved").count()
        out.append({"date": d.isoformat(), "resolved": cnt})
    return out