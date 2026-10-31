import time, json, random
from sqlalchemy import text
from app.database import SessionLocal, engine, Base
from app.models import Institution, ApprovedIntake, ApaarRegistry, Student
from app.services.rules import run_rules
from app.services.apaar import validate_apaar

Base.metadata.create_all(bind=engine)
db = SessionLocal()

inst_id = "MEASURE-INST"
other_inst = "OTHER-INST"
for iid, name in [(inst_id, "Measure Inst"), (other_inst, "Other Inst")]:
    if not db.get(Institution, iid):
        db.add(Institution(id=iid, name=name, state="Delhi", type="Technical"))
db.add(ApprovedIntake(institution_id=inst_id, programme="B.Tech", branch="CS", year=2025, sanctioned_intake=10000, supernumerary_cap=1000)) if not db.query(ApprovedIntake).filter(ApprovedIntake.institution_id == inst_id).first() else None
db.commit()

# Insert fresh APAAR registry entries for test isolation
fresh_ids = []
for i in range(200):
    aid = "2" + str(20000000000 + i).zfill(11)
    if not db.get(ApaarRegistry, aid):
        db.add(ApaarRegistry(apaar_id=aid, name=f"Fresh Student {i}", dob=f"2004-{(i%12)+1:02d}-{(i%28)+1:02d}", gender="M" if i % 2 == 0 else "F", parent_name=f"Parent {i}", mobile=f"9{i:09d}", email=f"fresh{i}@mail.com", status="active"))
    fresh_ids.append(aid)
db.commit()

random.seed(7)

def make_clean(i):
    aid = fresh_ids[i % len(fresh_ids)]
    reg = db.get(ApaarRegistry, aid)
    return {
        "apaar_id": aid, "name": reg.name, "dob": reg.dob, "gender": reg.gender,
        "parent_name": reg.parent_name, "institution_id": inst_id, "programme": "B.Tech",
        "branch": "CS", "year": 2025, "admission_date": "2025-08-10", "quota": "CAP",
        "social_category": "General", "is_nri": False, "is_oci": False, "is_foreign": False,
        "is_supernumerary": False,
    }

records = []
labels = []
# 100 clean
for i in range(100):
    records.append(make_clean(i))
    labels.append("clean")
# 20 invalid apaar
for i in range(20):
    r = make_clean(100 + i)
    r["apaar_id"] = "999999999999"
    r["name"] = "Invalid" + str(i)
    records.append(r)
    labels.append("invalid_apaar")
# 10 duplicate within batch
for i in range(10):
    r = make_clean(150 + i)
    records.append(r)
    records.append(dict(r))
    labels.append("dup")
    labels.append("dup")
# 5 nri quota mismatch
for i in range(5):
    r = make_clean(170 + i)
    r["is_nri"] = True
    r["quota"] = "CAP"
    records.append(r)
    labels.append("nri_mismatch")
# 5 oci domestic cat
for i in range(5):
    r = make_clean(175 + i)
    r["is_oci"] = True
    r["social_category"] = "SC"
    r["quota"] = "OCI"
    records.append(r)
    labels.append("oci_cat")
# 5 fn domestic cat
for i in range(5):
    r = make_clean(180 + i)
    r["is_foreign"] = True
    r["social_category"] = "OBC"
    r["quota"] = "Supernumerary"
    records.append(r)
    labels.append("fn_cat")

# Cross-inst duplicates: 5 fresh students already admitted at other_inst
cross_aids = fresh_ids[190:195]
for aid in cross_aids:
    reg = db.get(ApaarRegistry, aid)
    if not db.query(Student).filter(Student.apaar_id == aid, Student.institution_id == other_inst).first():
        db.add(Student(id="X-" + aid, apaar_id=aid, name=reg.name, dob=reg.dob, gender=reg.gender, institution_id=other_inst, programme="B.Tech", branch="CS", year=2025, status="admitted", quota="CAP"))
        db.commit()
    r = make_clean(0)
    r["apaar_id"] = aid
    r["name"] = reg.name
    r["dob"] = reg.dob
    records.append(r)
    labels.append("cross_inst_dup")

# Legitimate transfers: 20 fresh students whose other_inst enrolment is withdrawn/graduated
for i in range(20):
    aid = fresh_ids[150 + (i % 30)]
    reg = db.get(ApaarRegistry, aid)
    if not db.query(Student).filter(Student.apaar_id == aid, Student.institution_id == other_inst).first():
        db.add(Student(id="W-" + aid, apaar_id=aid, name=reg.name, dob=reg.dob, gender=reg.gender, institution_id=other_inst, programme="B.Tech", branch="CS", year=2025, status="withdrawn", quota="CAP"))
        db.commit()
    r = make_clean(10 + i)
    r["apaar_id"] = aid
    r["name"] = reg.name
    r["dob"] = reg.dob
    records.append(r)
    labels.append("legit_transfer")

existing_enrolments = [{"apaar_id": s.apaar_id, "institution_id": s.institution_id, "status": s.status} for s in db.query(Student).filter(Student.apaar_id.isnot(None)).all()]

t0 = time.time()
outcomes = []
for idx, rec in enumerate(records):
    errs = run_rules(rec, records, idx, inst_id, existing_enrolments)
    apaar_res = validate_apaar(db, rec.get("apaar_id"), rec)
    if not apaar_res["valid"]:
        errs = [{"code": apaar_res["reason"], "severity": "high"}] + errs
    elif apaar_res.get("soft"):
        errs = [{"code": apaar_res["reason"], "severity": "low"}] + errs
    outcomes.append({"label": labels[idx], "has_high": any(e["severity"] == "high" for e in errs), "has_any": len(errs) > 0, "codes": [e["code"] for e in errs]})
elapsed = time.time() - t0

planted_labels = {"invalid_apaar", "dup", "nri_mismatch", "oci_cat", "fn_cat", "cross_inst_dup"}
tp = sum(1 for o in outcomes if o["label"] in planted_labels and o["has_any"])
fn = sum(1 for o in outcomes if o["label"] in planted_labels and not o["has_any"])
fp = sum(1 for o in outcomes if o["label"] in ("clean", "legit_transfer") and o["has_high"])
tn = sum(1 for o in outcomes if o["label"] in ("clean", "legit_transfer") and not o["has_high"])
precision = tp / (tp + fp) if (tp + fp) else 0
recall = tp / (tp + fn) if (tp + fn) else 0
fpr = fp / (fp + tn) if (fp + tn) else 0

cross_tp = sum(1 for o in outcomes if o["label"] == "cross_inst_dup" and "CROSS_INST_DUP" in o["codes"])
cross_fn = sum(1 for o in outcomes if o["label"] == "cross_inst_dup" and "CROSS_INST_DUP" not in o["codes"])
legit_flagged = sum(1 for o in outcomes if o["label"] == "legit_transfer" and "CROSS_INST_DUP" in o["codes"])

# processing time for 1000
big = [make_clean(i % 100) for i in range(1000)]
t1 = time.time()
for idx, rec in enumerate(big):
    run_rules(rec, big, idx, inst_id, existing_enrolments)
t_big = time.time() - t1

print("=== MEASURED RESULTS ===")
print(f"Test set size: {len(records)} records")
print(f"Planted errors: {sum(1 for l in labels if l in planted_labels)}")
print(f"Clean: {sum(1 for l in labels if l=='clean')}")
print(f"Legit transfers: {sum(1 for l in labels if l=='legit_transfer')}")
print(f"TP: {tp}; FN: {fn}; FP: {fp}; TN: {tn}")
print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")
# FP breakdown
from collections import Counter
fp_labels = Counter(o["label"] for o in outcomes if o["label"] in ("clean","legit_transfer") and o["has_high"])
fp_codes = Counter()
for o in outcomes:
    if o["label"] in ("clean","legit_transfer") and o["has_high"]:
        for c in o["codes"]:
            fp_codes[c]+=1
print("FP by label:", dict(fp_labels))
print("FP by code:", dict(fp_codes))
clean_fp = sum(1 for o in outcomes if o["label"] == "clean" and o["has_high"])
clean_total = sum(1 for o in outcomes if o["label"] == "clean")
print(f"False positive rate on clean records only: {clean_fp/clean_total:.4f} ({clean_fp}/{clean_total})")
print(f"False positive rate (high-severity on clean+legit): {fpr:.4f}")
print(f"Cross-inst dup TP: {cross_tp}; FN: {cross_fn}")
print(f"Legit transfers falsely flagged as cross-inst dup: {legit_flagged} / {sum(1 for l in labels if l=='legit_transfer')}")
print(f"Validation time for {len(records)} records: {elapsed:.4f}s ({elapsed/len(records)*1000:.2f} ms/record)")
print(f"Validation time for 1000 records: {t_big:.4f}s ({t_big/1000*1000:.2f} ms/record)")
print(f"Throughput: {1000/t_big:.1f} records/sec")
db.close()