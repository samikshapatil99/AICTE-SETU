import csv
from app.database import SessionLocal
from app.models import Institution, ApprovedIntake, ApaarRegistry

def seed_zeal():
    db = SessionLocal()
    try:
        # 1. Institution
        inst = db.query(Institution).filter(Institution.id == "ZCOE-DEMO").first()
        if not inst:
            inst = Institution(
                id="ZCOE-DEMO",
                name="Zeal College of Engineering and Research, Pune",
                state="Maharashtra",
                type="Affiliated",
                nodal_officer="Dr. A. B. More",
                email="nodal@zcoepune.edu",
                risk_score=0,
                compliance_score=100,
                data_completeness=100
            )
            db.add(inst)
            db.commit()
            print("Added Zeal College institution")

        # 2. Approved Intakes for 2026 and 2025
        branches = [
            "Computer Engineering",
            "Artificial Intelligence and Data Science",
            "Mechanical Engineering",
            "Computer Science"
        ]
        for yr in [2025, 2026, 2027]:
            for b in branches:
                exists = db.query(ApprovedIntake).filter(
                    ApprovedIntake.institution_id == "ZCOE-DEMO",
                    ApprovedIntake.branch == b,
                    ApprovedIntake.year == yr
                ).first()
                if not exists:
                    db.add(ApprovedIntake(
                        institution_id="ZCOE-DEMO",
                        programme="B.Tech",
                        branch=b,
                        year=yr,
                        sanctioned_intake=60,
                        supernumerary_cap=6
                    ))
        db.commit()
        print("Added Zeal College approved intakes")

        # 3. Seed APAAR registry for the students from the CSV
        import os
        from pathlib import Path
        csv_path = Path(__file__).resolve().parent.parent / "zeal_college_apaar_valid_invalid_mixed_2026_27.csv"
        seen_apaars = set()
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                apaar = (row.get("apaar_id") or "").strip()
                if not apaar or not apaar.isdigit() or len(apaar) != 12:
                    continue
                if apaar in seen_apaars:
                    continue
                seen_apaars.add(apaar)
                name = row.get("student_full_name") or row.get("name")
                dob = row.get("date_of_birth") or row.get("dob")
                gender = "M" if (row.get("gender") or "").lower().startswith("m") else "F"
                
                # Check if exists
                reg = db.get(ApaarRegistry, apaar)
                if not reg:
                    db.add(ApaarRegistry(
                        apaar_id=apaar,
                        name=name,
                        dob=dob,
                        gender=gender,
                        mobile="9876543210",
                        email=f"{apaar}@demo.apaar.gov.in",
                        parent_name="Parent",
                        status="active"
                    ))
                    count += 1
            db.commit()
            print(f"Added {count} student records to mock APAAR registry")

        # 4. Seed Audit Logs if empty
        from app.models import AuditLog
        from datetime import datetime, timedelta
        if db.query(AuditLog).count() == 0:
            now = datetime.utcnow()
            demo_logs = [
                ("admin@aicte.gov.in", "admin", "SYSTEM_INITIALIZED", "system", "AICTE-SETU", '{"version": "1.0.0", "status": "active"}', 120),
                ("admin@aicte.gov.in", "admin", "RULE_SET_ACTIVATED", "rule_set", "RULESET-A-2025", '{"jurisdiction": "National", "rules": 12}', 90),
                ("nodal@zcoepune.edu", "institution", "BATCH_UPLOADED", "upload_batch", "BATCH-ZCOE-2026", '{"institution": "ZCOE-DEMO", "records": 30, "valid": 27, "flagged": 3}', 60),
                ("system@aicte.gov.in", "system", "APAAR_REGISTRY_CROSSCHECK", "apaar_registry", "900000000001", '{"status": "MATCH", "hash": "sha256:7f83b1657ff1"}', 55),
                ("system@aicte.gov.in", "system", "ANOMALY_DETECTED", "flag", "FLAG-ZCOE-01", '{"type": "DUP_IN_BATCH", "severity": "high"}', 50),
                ("regional@aicte.gov.in", "regional", "CASE_CREATED", "compliance_case", "CASE-2026-042", '{"institution": "INST002", "type": "INTAKE_BREACH"}', 40),
                ("nodal@inst001.edu", "institution", "BATCH_CONFIRMED", "upload_batch", "BATCH-INST001-01", '{"inserted": 60, "skipped": 0}', 30),
                ("verifier@company.com", "verifier", "VERIFICATION_EXECUTED", "verification_request", "REQ-2026-881", '{"apaar_id": "110000000000", "consent": true}', 20),
                ("auditor@aicte.gov.in", "auditor", "REPLAY_AUDIT_VERIFIED", "audit_ledger", "AUDIT-ROOT", '{"determinism": true, "integrity_hash": "sha256:4a9c8b7e"}', 10),
            ]
            for actor, role, action, et, eid, det, mins in demo_logs:
                db.add(AuditLog(
                    actor=actor,
                    role=role,
                    action=action,
                    entity_type=et,
                    entity_id=eid,
                    details=det,
                    created_at=now - timedelta(minutes=mins)
                ))
            db.commit()
            print("Seeded demo audit logs")
    finally:
        db.close()

if __name__ == "__main__":
    seed_zeal()
