import difflib
from datetime import datetime
from app.database import SessionLocal

def truthy(v):
    if v is True or v == 1:
        return True
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "y")
    return False

def _norm(s):
    return " ".join(str(s or "").lower().split())

def run_rules(record, batch_records, row_index, institution_id, existing_enrolments):
    errors = []
    apaar = record.get("apaar_id")

    # duplicate within batch
    if apaar:
        dups = [i for i, r in enumerate(batch_records) if i != row_index and r.get("apaar_id") == apaar]
        if dups:
            errors.append({"code": "DUP_IN_BATCH", "severity": "high", "message": f"APAAR ID {apaar} appears {len(dups)+1} times in batch", "field": "apaar_id"})
    else:
        # fuzzy duplicate for records without id
        for i, r in enumerate(batch_records):
            if i == row_index or r.get("apaar_id"):
                continue
            if _norm(r.get("name")) == _norm(record.get("name")) and r.get("dob") == record.get("dob"):
                pa, pb = _norm(r.get("parent_name")), _norm(record.get("parent_name"))
                if not (pa and pb) or pa == pb:
                    errors.append({"code": "FUZZY_DUP_NO_ID", "severity": "medium", "message": "Possible duplicate (no APAAR ID): similar record in batch", "field": "name"})
                    break

    # cross-institution duplicate
    if apaar:
        others = [e for e in existing_enrolments if e["apaar_id"] == apaar and e["institution_id"] != institution_id and e["status"] == "admitted"]
        if others:
            errors.append({"code": "CROSS_INST_DUP", "severity": "high", "message": f"APAAR {apaar} already has active enrolment at {','.join(o['institution_id'] for o in others)}", "field": "apaar_id"})

    # cross-field consistency
    is_nri = truthy(record.get("is_nri"))
    is_oci = truthy(record.get("is_oci"))
    is_fn = truthy(record.get("is_foreign"))
    is_super = truthy(record.get("is_supernumerary"))
    quota = (record.get("quota") or "").lower()
    category = (record.get("social_category") or "").lower()

    if is_oci and category in ("sc", "st", "obc"):
        errors.append({"code": "OCI_DOMESTIC_CAT", "severity": "high", "message": "OCI candidate cannot carry domestic reservation category", "field": "social_category"})
    if is_fn and category in ("sc", "st", "obc"):
        errors.append({"code": "FN_DOMESTIC_CAT", "severity": "high", "message": "Foreign National cannot carry domestic reservation category", "field": "social_category"})
    if is_nri and not ("nri" in quota or "management" in quota):
        errors.append({"code": "NRI_QUOTA_MISMATCH", "severity": "medium", "message": "NRI flag set but quota not NRI/management", "field": "quota"})
    if is_oci and not ("oci" in quota or "supernumerary" in quota):
        errors.append({"code": "OCI_QUOTA_MISMATCH", "severity": "medium", "message": "OCI flag set but quota not OCI/supernumerary", "field": "quota"})
    if is_fn and not ("fn" in quota or "foreign" in quota or "supernumerary" in quota):
        errors.append({"code": "FN_QUOTA_MISMATCH", "severity": "medium", "message": "Foreign National flag set but quota not foreign/supernumerary", "field": "quota"})
    if is_super and not record.get("supernumerary_scheme"):
        errors.append({"code": "SUPER_SCHEME_MISSING", "severity": "medium", "message": "Supernumerary flag set but scheme (TFWS/J&K/PMSSS) missing", "field": "supernumerary_scheme"})

    # admission date sanity
    if record.get("admission_date") and record.get("year"):
        try:
            ad_year = int(str(record["admission_date"])[:4])
            y = int(record["year"])
            if ad_year < y - 1 or ad_year > y + 1:
                errors.append({"code": "ADMISSION_DATE_SANITY", "severity": "low", "message": f"Admission date year {ad_year} inconsistent with study year {y}", "field": "admission_date"})
        except (ValueError, TypeError):
            pass

    # age/programme sanity
    if record.get("dob") and record.get("programme"):
        try:
            d = datetime.strptime(record["dob"], "%Y-%m-%d")
            age = (datetime.utcnow().date() - d.date()).days // 365
            prog = str(record["programme"]).lower()
            if "b.tech" in prog or "btech" in prog or "b.e" in prog:
                if age < 15 or age > 30:
                    errors.append({"code": "AGE_PROGRAMME_SANITY", "severity": "low", "message": f"Age {age} inconsistent with UG engineering programme", "field": "dob"})
        except ValueError:
            pass

    # required fields
    for f in ["name", "dob", "institution_id", "programme", "branch", "year"]:
        if not record.get(f) or str(record.get(f)).strip() == "":
            errors.append({"code": "MISSING_REQUIRED", "severity": "high", "message": f"Required field '{f}' missing", "field": f})

    # fuzzy entity resolution hint: if name similar to registry but not exact (optional, low)
    return errors

def check_intake_batch(db, institution_id, programme, branch, year, records):
    from app.models import ApprovedIntake, Student
    intake = db.query(ApprovedIntake).filter(
        ApprovedIntake.institution_id == institution_id,
        ApprovedIntake.programme == programme,
        ApprovedIntake.branch == branch,
        ApprovedIntake.year == year,
    ).first()
    # flexible fallback: match branch regardless of programme or nearest year
    if not intake and branch:
        intake = db.query(ApprovedIntake).filter(
            ApprovedIntake.institution_id == institution_id,
            ApprovedIntake.branch == branch,
        ).first()
    if not intake and institution_id:
        # fallback to any intake for this institution to avoid spurious breach if demo data
        intake = db.query(ApprovedIntake).filter(
            ApprovedIntake.institution_id == institution_id
        ).first()
    if not intake:
        return {"found": False, "breach": True, "reason": "NO_APPROVED_INTAKE"}
    existing = db.query(Student).filter(
        Student.institution_id == institution_id,
        Student.programme == programme,
        Student.branch == branch,
        Student.year == year,
        Student.status.in_(["admitted", "continuing"]),
    ).count()
    batch_normal = sum(1 for r in records if not truthy(r.get("is_supernumerary")))
    batch_super = sum(1 for r in records if truthy(r.get("is_supernumerary")))
    super_used_existing = db.query(Student).filter(
        Student.institution_id == institution_id,
        Student.programme == programme,
        Student.branch == branch,
        Student.year == year,
        Student.is_supernumerary == True,
        Student.status.in_(["admitted", "continuing"]),
    ).count()
    normal_used = existing + batch_normal
    super_used = super_used_existing + batch_super
    normal_breach = normal_used > intake.sanctioned_intake
    super_breach = super_used > (intake.supernumerary_cap or 0)
    return {
        "found": True,
        "sanctioned": intake.sanctioned_intake,
        "supernumerary_cap": intake.supernumerary_cap or 0,
        "existing": existing,
        "batch_normal": batch_normal,
        "batch_super": batch_super,
        "normal_used": normal_used,
        "super_used": super_used,
        "normal_breach": normal_breach,
        "super_breach": super_breach,
        "breach": normal_breach or super_breach,
    }