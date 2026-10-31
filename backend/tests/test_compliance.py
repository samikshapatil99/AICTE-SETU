import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.database import SessionLocal, engine, Base
from app.models import Student, RuleSet, ValidationResult, ChangeEvent, StudentVersion, Dependency, ComplianceCase, Flag
from app.services.compliance import seed_rule_sets, update_student_versioned, run_validation_for_student, run_validation_for_batch, replay_batch, diff_results, traverse_impact, add_dependency, preview_correction, build_dependencies_for_batch

Base.metadata.create_all(bind=engine)

def setup_module():
    db = SessionLocal()
    seed_rule_sets(db)
    db.close()

def test_rule_sets_seeded():
    db = SessionLocal()
    assert db.query(RuleSet).count() >= 2
    db.close()

def test_history_preservation():
    db = SessionLocal()
    s = db.query(Student).first()
    assert s is not None
    sid = s.id
    update_student_versioned(db, sid, {"admission_date": "2025-08-15"}, "tester", "admin", "test correction")
    s2 = db.get(Student, s.id)
    # new version created
    assert db.query(StudentVersion).filter(StudentVersion.student_id == s.id).count() >= 1
    # change event recorded
    ce = db.query(ChangeEvent).filter(ChangeEvent.entity_id == sid, ChangeEvent.field == "admission_date").first()
    assert ce is not None
    assert ce.old_value != ce.new_value
    db.close()

def test_replay_determinism():
    db = SessionLocal()
    # need a batch; create a minimal one
    from app.models import UploadBatch, StagingRecord
    bid = "BATCH-TEST"
    if not db.get(UploadBatch, bid):
        db.add(UploadBatch(id=bid, institution_id="T1", file_name="t.csv", total_records=1, status="validated"))
        db.add(StagingRecord(batch_id=bid, row_index=0, record_json='{"name":"X","dob":"2004-01-01","institution_id":"T1","programme":"B.Tech","branch":"CS","year":2025,"apaar_id":"111111111111"}', validation_status="valid"))
        db.commit()
    r1 = run_validation_for_batch(db, bid, "RULESET-A-2025")
    r2 = run_validation_for_batch(db, bid, "RULESET-A-2025")
    # determinism: same outcomes
    assert [x["outcome"] for x in r1] == [x["outcome"] for x in r2]
    assert [x["errors"] for x in r1] == [x["errors"] for x in r2]
    db.close()

def test_replay_diff():
    db = SessionLocal()
    bid = "BATCH-TEST"
    res_a = run_validation_for_batch(db, bid, "RULESET-A-2025")
    res_b = run_validation_for_batch(db, bid, "RULESET-B-2025")
    diff = diff_results(res_a, res_b)
    assert isinstance(diff, list)
    assert len(diff) == len(res_a)
    db.close()

def test_impact_calculation():
    db = SessionLocal()
    add_dependency(db, "student_record", "X", "validation_result", "VR1", "test")
    add_dependency(db, "validation_result", "VR1", "compliance_case", "CASE1", "test")
    affected = traverse_impact(db, "student_record", "X", depth=3)
    ids = [a["id"] for a in affected]
    assert "VR1" in ids
    assert "CASE1" in ids
    db.close()

def test_preview_correction_no_commit():
    db = SessionLocal()
    s = db.query(Student).first()
    before_val = s.admission_date
    res = preview_correction(db, s.id, {"admission_date": "2025-09-01"}, "RULESET-A-2025")
    assert res is not None
    assert res["original_preserved"] is True
    # student not committed
    s2 = db.get(Student, s.id)
    assert s2.admission_date == before_val or s2.admission_date != "2025-09-01"
    db.close()