import csv, io, uuid, json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import UploadBatch, StagingRecord, ValidationError as VE, Flag, Student, Institution, ApprovedIntake, ApaarRegistry
from app.auth import current_user, require_roles
# validation logic inlined in process_upload
from app.services.anomaly import detect_anomalies
from app.services.rules import check_intake_batch

router = APIRouter()

def _require_inst_access(user, inst_id):
    if user.role == "institution" and user.institution_id != inst_id:
        raise HTTPException(403, "forbidden")
    if user.role == "regional":
        pass

@router.post("/csv")
async def upload_csv(institution_id: str = Form(...), file: UploadFile = File(...), user=Depends(current_user), db: Session = Depends(get_db)):
    _require_inst_access(user, institution_id)
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    records = [r for r in reader]
    result = process_upload(db, institution_id, records, file.filename)
    return result

@router.post("/json")
def upload_json(payload: dict = Body(...), user=Depends(current_user), db: Session = Depends(get_db)):
    inst_id = payload.get("institution_id")
    records = payload.get("records")
    if not inst_id or not isinstance(records, list):
        raise HTTPException(400, "institution_id and records required")
    _require_inst_access(user, inst_id)
    return process_upload(db, inst_id, records, payload.get("file_name", "api"))

def process_upload(db, institution_id, records, file_name):
    batch_id = str(uuid.uuid4())
    db.add(UploadBatch(id=batch_id, institution_id=institution_id, file_name=file_name, total_records=len(records), status="processing"))
    db.commit()

    # existing enrolments for cross-inst dup
    existing = db.query(Student).filter(Student.apaar_id.isnot(None)).all()
    existing_list = [{"apaar_id": s.apaar_id, "institution_id": s.institution_id, "status": s.status} for s in existing]

    # normalize records first
    norm_records = [normalize_record(r) for r in records]
    for r in norm_records:
        r["institution_id"] = r.get("institution_id") or institution_id

    # intake check groups
    intake_breaches = []
    groups = {}
    for i, r in enumerate(norm_records):
        key = (r.get("programme"), r.get("branch"), r.get("year"))
        groups.setdefault(key, []).append((i, r))

    for key, items in groups.items():
        prog, branch, year = key
        try:
            year_int = int(year)
        except (TypeError, ValueError):
            year_int = None
        res = check_intake_batch(db, institution_id, prog, branch, year_int, [r for _, r in items])
        if res.get("breach") or res.get("found") is False:
            intake_breaches.append({"programme": prog, "branch": branch, "year": year, **res})

    valid_count = 0
    rejected_count = 0
    all_errors = []

    for idx, rec in enumerate(norm_records):
        row_errors = []

        # APAAR validation
        from app.services.apaar import validate_apaar
        apaar_res = validate_apaar(db, rec.get("apaar_id"), rec)
        if not apaar_res["valid"]:
            row_errors.append({"code": apaar_res["reason"], "severity": "high", "message": f"APAAR validation failed: {apaar_res['reason']}", "field": "apaar_id"})
        elif apaar_res.get("soft"):
            row_errors.append({"code": apaar_res["reason"], "severity": "low", "message": "APAAR name/DOB mismatch with registry (soft)", "field": "apaar_id"})

        # rules
        from app.services.rules import run_rules
        rule_errs = run_rules(rec, norm_records, idx, institution_id, existing_list)
        row_errors.extend(rule_errs)

        # intake breach row-level
        breach = next((b for b in intake_breaches if b["programme"] == rec.get("programme") and b["branch"] == rec.get("branch") and str(b["year"]) == str(rec.get("year"))), None)
        if breach and (breach.get("breach") or breach.get("found") is False):
            row_errors.append({"code": "INTAKE_BREACH", "severity": "high",
                "message": "No approved intake found" if breach.get("found") is False else f"Intake breach: {breach['normal_used']}/{breach['sanctioned']} (supernumerary {breach['super_used']}/{breach['supernumerary_cap']})",
                "field": "programme"})

        status = "rejected" if any(e["severity"] == "high" for e in row_errors) else ("warning" if row_errors else "valid")
        if status == "valid":
            valid_count += 1
        else:
            rejected_count += 1

        db.add(StagingRecord(batch_id=batch_id, row_index=idx, record_json=json.dumps(rec), validation_status=status))
        for e in row_errors:
            db.add(VE(batch_id=batch_id, row_index=idx, apaar_id=rec.get("apaar_id"), student_name=rec.get("name"), error_code=e["code"], severity=e["severity"], message=e["message"], field=e["field"]))
            all_errors.append({"rowIndex": idx, "apaar_id": rec.get("apaar_id"), "name": rec.get("name"), **e})

        # cross-inst dup flag
        apaar = rec.get("apaar_id")
        if apaar:
            others = [e for e in existing_list if e["apaar_id"] == apaar and e["institution_id"] != institution_id and e["status"] == "admitted"]
            if others:
                db.add(Flag(institution_id=institution_id, batch_id=batch_id, apaar_id=apaar, student_name=rec.get("name"), flag_type="CROSS_INST_DUP", severity="high", reason=f"Active enrolment at {','.join(o['institution_id'] for o in others)}"))

    # intake breach flags
    for b in intake_breaches:
        if b.get("breach") or b.get("found") is False:
            db.add(Flag(institution_id=institution_id, batch_id=batch_id, flag_type="INTAKE_BREACH", severity="high",
                reason=f"{b['programme']}/{b['branch']}/{b['year']}: " + ("no approved intake" if b.get("found") is False else f"{b['normal_used']}/{b['sanctioned']}")))

    # anomaly detection
    anomalies = detect_anomalies(db, batch_id, institution_id, [normalize_record(r) for r in records])

    db.query(UploadBatch).filter(UploadBatch.id == batch_id).update({"valid_records": valid_count, "rejected_records": rejected_count, "status": "validated"})
    db.commit()

    return {
        "batchId": batch_id,
        "fileName": file_name,
        "total": len(records),
        "valid": valid_count,
        "rejected": rejected_count,
        "warnings": len(records) - valid_count - rejected_count,
        "errors": all_errors,
        "intakeBreaches": intake_breaches,
        "anomalies": anomalies,
    }

@router.get("/batch/{batch_id}")
def get_batch(batch_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    b = db.get(UploadBatch, batch_id)
    if not b:
        raise HTTPException(404, "not found")
    errors = db.query(VE).filter(VE.batch_id == batch_id).all()
    staging = db.query(StagingRecord).filter(StagingRecord.batch_id == batch_id).all()
    return {"batch": b, "errors": errors, "stagingCount": len(staging)}

@router.post("/batch/{batch_id}/confirm")
def confirm_batch(batch_id: str, payload: dict = Body(default={}), user=Depends(current_user), db: Session = Depends(get_db)):
    b = db.get(UploadBatch, batch_id)
    if not b:
        raise HTTPException(404, "not found")
    if b.status == "confirmed":
        raise HTTPException(400, "already confirmed")
    staging = db.query(StagingRecord).filter(StagingRecord.batch_id == batch_id).all()
    inserted = 0
    skipped = 0
    for s in staging:
        rec = json.loads(s.record_json)
        if s.validation_status == "rejected":
            skipped += 1
            continue
        from app.models import Student as St
        st = St(
            id=str(uuid.uuid4()),
            apaar_id=rec.get("apaar_id"),
            name=rec.get("name"),
            dob=rec.get("dob"),
            gender=rec.get("gender"),
            masked_aadhaar=rec.get("masked_aadhaar"),
            mobile=rec.get("mobile"),
            email=rec.get("email"),
            institution_id=rec.get("institution_id") or b.institution_id,
            programme=rec.get("programme"),
            branch=rec.get("branch"),
            year=int(rec.get("year")),
            admission_date=rec.get("admission_date"),
            admission_mode=rec.get("admission_mode"),
            quota=rec.get("quota"),
            entrance_exam=rec.get("entrance_exam"),
            entrance_rank=rec.get("entrance_rank"),
            social_category=rec.get("social_category"),
            is_nri=bool(rec.get("is_nri")),
            is_oci=bool(rec.get("is_oci")),
            is_foreign=bool(rec.get("is_foreign")),
            is_supernumerary=bool(rec.get("is_supernumerary")),
            supernumerary_scheme=rec.get("supernumerary_scheme"),
            doc_ref=rec.get("doc_ref"),
            status=rec.get("status", "admitted"),
            upload_batch_id=batch_id,
        )
        db.add(st)
        inserted += 1
    b.status = "confirmed"
    b.confirmed_at = datetime.utcnow()
    db.commit()

    # audit
    from app.models import AuditLog
    db.add(AuditLog(actor=user.email, role=user.role, action="BATCH_CONFIRMED", entity_type="upload_batch", entity_id=batch_id, details=json.dumps({"inserted": inserted, "skipped": skipped})))
    db.commit()
    return {"batchId": batch_id, "inserted": inserted, "skipped": skipped}

def normalize_record(r):
    # map common variants across various ERPs and AICTE templates
    mapping = {
        "apaar_id": ["apaar_id", "apaar", "APAAR ID", "APAAR_ID", "apaarId"],
        "name": ["name", "student_name", "student name", "Name", "student_full_name", "full_name", "studentFullName"],
        "dob": ["dob", "date_of_birth", "date of birth", "DOB", "dateOfBirth"],
        "gender": ["gender", "Gender"],
        "parent_name": ["parent_name", "parent name", "father_name", "fatherName"],
        "mobile": ["mobile", "phone", "contact"],
        "email": ["email", "e-mail"],
        "institution_id": ["institution_id", "institution", "inst_id", "institution_code", "college_code"],
        "programme": ["programme", "program", "course", "programme_code", "degree"],
        "branch": ["branch", "specialization", "specialisation", "programme_name", "discipline", "branch_name"],
        "year": ["year", "year_of_study", "study year", "admission_year", "academic_year"],
        "admission_date": ["admission_date", "admission date"],
        "admission_mode": ["admission_mode", "admission mode", "admission_type"],
        "quota": ["quota", "admission_quota"],
        "social_category": ["social_category", "category"],
        "is_nri": ["is_nri", "nri", "is_nri_oci_fn"],
        "is_oci": ["is_oci", "oci"],
        "is_foreign": ["is_foreign", "foreign_national", "fn"],
        "is_supernumerary": ["is_supernumerary", "supernumerary"],
        "supernumerary_scheme": ["supernumerary_scheme", "scheme"],
        "masked_aadhaar": ["masked_aadhaar", "aadhaar_ref", "masked aadhaar"],
        "entrance_exam": ["entrance_exam", "entrance exam"],
        "entrance_rank": ["entrance_rank", "rank"],
        "doc_ref": ["doc_ref", "document_ref", "supporting_doc"],
        "status": ["status", "enrollment_status"],
    }
    out = {}
    for canon, variants in mapping.items():
        for v in variants:
            if v in r and r[v] not in (None, ""):
                out[canon] = r[v]
                break
        if canon not in out:
            out[canon] = r.get(canon)

    # Heuristic: if programme looks like a branch code (e.g. ZCOE-CSE) and programme_name is present
    if out.get("programme") and str(out["programme"]).startswith("ZCOE-"):
        out["branch"] = out.get("branch") or r.get("programme_name")
        out["programme"] = "B.Tech"
    elif not out.get("programme") and out.get("branch"):
        out["programme"] = "B.Tech"

    # type conversions
    if out.get("is_nri") is not None:
        out["is_nri"] = str(out["is_nri"]).strip().lower() in ("true", "1", "yes", "y")
    if out.get("is_oci") is not None:
        out["is_oci"] = str(out["is_oci"]).strip().lower() in ("true", "1", "yes", "y")
    if out.get("is_foreign") is not None:
        out["is_foreign"] = str(out["is_foreign"]).strip().lower() in ("true", "1", "yes", "y")
    if out.get("is_supernumerary") is not None:
        out["is_supernumerary"] = str(out["is_supernumerary"]).strip().lower() in ("true", "1", "yes", "y")
    if out.get("year") is not None:
        try:
            val = str(out["year"]).split("-")[0].strip()
            out["year"] = int(val)
        except (ValueError, TypeError):
            pass
    if out.get("entrance_rank") not in (None, ""):
        try:
            out["entrance_rank"] = int(out["entrance_rank"])
        except (ValueError, TypeError):
            out["entrance_rank"] = None
    return out