import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.services.rules import run_rules, check_intake_batch, truthy

def test_truthy():
    assert truthy("true") and truthy("1") and truthy(True)
    assert not truthy("false")

def test_missing_required():
    rec = {"name": "", "dob": "2004-01-01", "institution_id": "I", "programme": "B.Tech", "branch": "CS", "year": 2025}
    errs = run_rules(rec, [rec], 0, "I", [])
    codes = [e["code"] for e in errs]
    assert "MISSING_REQUIRED" in codes

def test_dup_in_batch():
    r1 = {"apaar_id": "111111111111", "name": "A", "dob": "2004-01-01", "institution_id": "I", "programme": "B.Tech", "branch": "CS", "year": 2025}
    r2 = dict(r1)
    errs = run_rules(r2, [r1, r2], 1, "I", [])
    assert any(e["code"] == "DUP_IN_BATCH" for e in errs)

def test_oci_domestic_cat():
    rec = {"apaar_id": "222222222222", "name": "B", "dob": "2004-01-01", "institution_id": "I", "programme": "B.Tech", "branch": "CS", "year": 2025, "is_oci": True, "social_category": "SC", "quota": "OCI"}
    errs = run_rules(rec, [rec], 0, "I", [])
    assert any(e["code"] == "OCI_DOMESTIC_CAT" for e in errs)

def test_nri_quota_mismatch():
    rec = {"apaar_id": "333333333333", "name": "C", "dob": "2004-01-01", "institution_id": "I", "programme": "B.Tech", "branch": "CS", "year": 2025, "is_nri": True, "quota": "CAP"}
    errs = run_rules(rec, [rec], 0, "I", [])
    assert any(e["code"] == "NRI_QUOTA_MISMATCH" for e in errs)

def test_super_scheme_missing():
    rec = {"apaar_id": "444444444444", "name": "D", "dob": "2004-01-01", "institution_id": "I", "programme": "B.Tech", "branch": "CS", "year": 2025, "is_supernumerary": True}
    errs = run_rules(rec, [rec], 0, "I", [])
    assert any(e["code"] == "SUPER_SCHEME_MISSING" for e in errs)

def test_cross_inst_dup():
    rec = {"apaar_id": "555555555555", "name": "E", "dob": "2004-01-01", "institution_id": "I", "programme": "B.Tech", "branch": "CS", "year": 2025}
    existing = [{"apaar_id": "555555555555", "institution_id": "OTHER", "status": "admitted"}]
    errs = run_rules(rec, [rec], 0, "I", existing)
    assert any(e["code"] == "CROSS_INST_DUP" for e in errs)