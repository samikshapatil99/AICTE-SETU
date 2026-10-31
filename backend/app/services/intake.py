from app.models import Student, ApprovedIntake, Flag, Institution

def intake_summary(db, institution_id):
    intakes = db.query(ApprovedIntake).filter(ApprovedIntake.institution_id == institution_id).all()
    out = []
    for it in intakes:
        used = db.query(Student).filter(
            Student.institution_id == institution_id,
            Student.programme == it.programme,
            Student.branch == it.branch,
            Student.year == it.year,
            Student.status.in_(["admitted", "continuing"]),
        ).count()
        super_used = db.query(Student).filter(
            Student.institution_id == institution_id,
            Student.programme == it.programme,
            Student.branch == it.branch,
            Student.year == it.year,
            Student.is_supernumerary == True,
            Student.status.in_(["admitted", "continuing"]),
        ).count()
        out.append({
            "id": it.id, "programme": it.programme, "branch": it.branch, "year": it.year,
            "sanctioned_intake": it.sanctioned_intake, "supernumerary_cap": it.supernumerary_cap or 0,
            "used": used, "supernumerary_used": super_used,
            "utilisation": round(used / it.sanctioned_intake * 100, 1) if it.sanctioned_intake else 0,
            "breach": used > it.sanctioned_intake,
        })
    return out

def institution_risk_score(db, institution_id):
    flags = db.query(Flag).filter(Flag.institution_id == institution_id, Flag.status == "open").all()
    score = 0
    for f in flags:
        if f.severity == "high": score += 15
        elif f.severity == "medium": score += 8
        else: score += 3
    breaches = sum(1 for i in intake_summary(db, institution_id) if i["breach"])
    score += breaches * 20
    score = min(100, score)
    inst = db.get(Institution, institution_id)
    if inst:
        inst.risk_score = score
        db.commit()
    return score

def data_completeness(db, institution_id):
    students = db.query(Student).filter(Student.institution_id == institution_id).all()
    if not students:
        return 0
    fields = ["apaar_id", "name", "dob", "gender", "mobile", "email", "programme", "branch", "year", "admission_date", "quota", "social_category"]
    total = len(students) * len(fields)
    filled = sum(1 for s in students for f in fields if getattr(s, f, None) not in (None, ""))
    return round(filled / total * 100, 1) if total else 0