import uuid, random, string
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import (User, Institution, ApprovedIntake, ApaarRegistry, Student)
from app.auth import hash_password

random.seed(42)

STATES = ["Maharashtra", "Tamil Nadu", "Karnataka", "Delhi", "Uttar Pradesh", "Gujarat", "West Bengal", "Rajasthan"]
INSTITUTION_NAMES = [
    "IIT Bombay", "VJTI Mumbai", "COEP Pune", "NIT Trichy", "Anna University", "VIT Vellore",
    "IISc Bangalore", "RVCE Bangalore", "IIT Delhi", "DTU Delhi", "NSUT Delhi",
    "IIT Kanpur", "MNNIT Allahabad", "IET Lucknow", "IIT Gandhinagar", "Nirma University",
    "Jadavpur University", "IIT Kharagpur", "BITS Pilani", "MNIT Jaipur",
    "SPPU Pune", "Thapar University", "PEC Chandigarh", "IIT Roorkee", "NIT Surathkal",
]

PROGRAMMES = ["B.Tech", "M.Tech", "MBA", "MCA"]
BRANCHES = {
    "B.Tech": ["Computer Science", "Electronics", "Mechanical", "Civil", "Information Technology"],
    "M.Tech": ["Computer Science", "VLSI", "Thermal"],
    "MBA": ["Finance", "Marketing", "HR"],
    "MCA": ["Computer Applications"],
}
FIRST_NAMES_M = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan", "Shaurya", "Atharv"]
FIRST_NAMES_F = ["Ananya", "Diya", "Myra", "Sara", "Aadhya", "Pari", "Anika", "Riya", "Kavya", "Meera", "Ira", "Tara"]
LAST_NAMES = ["Sharma", "Patel", "Singh", "Gupta", "Reddy", "Kumar", "Joshi", "Khan", "Iyer", "Nair", "Verma", "Mehta", "Shah", "Ali", "Rao", "Jain", "Das", "Bose", "Pillai"]
PARENTS = ["Rajesh", "Suresh", "Mahesh", "Ramesh", "Kiran", "Srinivas", "Anil", "Imran", "Venkat", "Mohan", "Sunil", "Prakash"]
CATEGORIES = ["General", "OBC", "SC", "ST", "EWS"]
QUOTAS = ["CAP", "Institute Level", "Management", "NRI", "Supernumerary"]
SCHEMES = ["TFWS", "J&K", "PMSSS", None]

def run_seed():
    db = SessionLocal()
    try:
        if db.query(Institution).count() > 0:
            print("Seed already present, skipping.")
            return
        # institutions (25)
        insts = []
        for i, name in enumerate(INSTITUTION_NAMES[:25]):
            st = STATES[i % len(STATES)]
            inst = Institution(id=f"INST{i+1:03d}", name=name + " (Mock)", state=st, type="Technical", nodal_officer=f"Nodal Officer {i+1}", email=f"nodal{i+1}@inst.edu", risk_score=0, compliance_score=100, data_completeness=0)
            insts.append(inst)
        db.add_all(insts)
        db.commit()

        # approved intake
        intakes = []
        for inst in insts:
            for prog in ["B.Tech", "M.Tech", "MBA", "MCA"]:
                for branch in BRANCHES[prog][: (3 if prog == "B.Tech" else 2)]:
                    cap = random.choice([60, 90, 120, 180])
                    intakes.append(ApprovedIntake(institution_id=inst.id, programme=prog, branch=branch, year=2025, sanctioned_intake=cap, supernumerary_cap=random.choice([5, 8, 10, 15])))
        db.add_all(intakes)
        db.commit()

        # APAAR registry ~8500
        apaar_ids = []
        n_reg = 8500
        for i in range(n_reg):
            aid = "1" + str(10000000000 + i).zfill(11)
            apaar_ids.append(aid)
            fn = random.choice(FIRST_NAMES_M + FIRST_NAMES_F)
            ln = random.choice(LAST_NAMES)
            name = f"{fn} {ln}"
            dob = (date(2002, 1, 1) + timedelta(days=random.randint(0, 365*4))).isoformat()
            gender = "M" if fn in FIRST_NAMES_M else "F"
            parent = random.choice(PARENTS) + " " + ln
            db.add(ApaarRegistry(apaar_id=aid, name=name, dob=dob, gender=gender, parent_name=parent, mobile=f"9{random.randint(100000000, 999999999)}", email=f"stu{i}@mail.com", status="active"))
        db.commit()

        # users
        users = []
        users.append(User(id=str(uuid.uuid4()), email="admin@aicte.gov.in", password_hash=hash_password("admin123"), full_name="AICTE Admin", role="admin"))
        users.append(User(id=str(uuid.uuid4()), email="regional@aicte.gov.in", password_hash=hash_password("regional123"), full_name="Regional Officer Maharashtra", role="regional", state="Maharashtra"))
        users.append(User(id=str(uuid.uuid4()), email="auditor@aicte.gov.in", password_hash=hash_password("auditor123"), full_name="Auditor", role="auditor"))
        users.append(User(id=str(uuid.uuid4()), email="verifier@company.com", password_hash=hash_password("verifier123"), full_name="Verifier (Employer)", role="verifier"))
        # institution nodal officers
        for inst in insts:
            users.append(User(id=str(uuid.uuid4()), email=f"nodal@{inst.id.lower()}.edu", password_hash=hash_password("inst123"), full_name=f"Nodal {inst.id}", role="institution", institution_id=inst.id))
        # student user (linked to first student later)
        db.add_all(users)
        db.commit()

        # students ~8000
        students = []
        target = 8000
        # planted: over-intake for a couple institutions: we'll just generate counts; ensure some exceed by not capping strictly
        # We'll assign institution randomly but weight first few
        weights = [3] + [1] * (len(insts) - 1)
        # admission spike: for INST001, many on same day
        spike_inst = insts[0].id
        all_apaar = list(apaar_ids)
        used_apaar_idx = 0

        def make_student(aid, inst, prog, branch, year, planted=None):
            fn = random.choice(FIRST_NAMES_M + FIRST_NAMES_F)
            ln = random.choice(LAST_NAMES)
            name = f"{fn} {ln}"
            # sometimes use registry name for planted dup consistency
            reg = db.get(ApaarRegistry, aid)
            if reg:
                name = reg.name
                dob = reg.dob
                gender = reg.gender
                parent = reg.parent_name
            else:
                dob = (date(2002, 1, 1) + timedelta(days=random.randint(0, 365*4))).isoformat()
                gender = "M" if fn in FIRST_NAMES_M else "F"
                parent = None
            cat = random.choice(CATEGORIES)
            is_nri = random.random() < 0.08
            is_oci = random.random() < 0.03
            is_fn = random.random() < 0.04
            is_super = random.random() < 0.06
            scheme = random.choice(SCHEMES) if is_super else None
            quota = "CAP"
            if is_nri: quota = "NRI"
            elif is_oci: quota = "Supernumerary"
            elif is_fn: quota = "Supernumerary"
            elif is_super: quota = "Supernumerary"
            elif random.random() < 0.15: quota = "Management"
            # planted inconsistencies
            if planted == "nri_quota":
                is_nri = True
                quota = "CAP"  # inconsistent
            if planted == "oci_cat":
                is_oci = True
                cat = "SC"  # inconsistent
            if planted == "fn_cat":
                is_fn = True
                cat = "OBC"
            status = "admitted"
            if random.random() < 0.05:
                status = random.choice(["continuing", "withdrawn", "graduated"])
            adm_date = (date(2025, 7, 15) + timedelta(days=random.randint(0, 60))).isoformat()
            # spike: many on same day for inst0
            if inst == spike_inst and random.random() < 0.3:
                adm_date = "2025-08-01"
            return Student(
                id=str(uuid.uuid4()),
                apaar_id=aid,
                name=name,
                dob=dob,
                gender=gender,
                masked_aadhaar=f"XXXX-XXXX-{random.randint(1000,9999)}",
                mobile=f"9{random.randint(100000000,999999999)}",
                email=f"{aid}@mail.com",
                institution_id=inst,
                programme=prog,
                branch=branch,
                year=2025,
                admission_date=adm_date,
                admission_mode=random.choice(["CAP", "Institute Level", "Management"]),
                quota=quota,
                entrance_exam=random.choice(["JEE Main", "State CET", "None"]),
                entrance_rank=random.randint(1, 50000) if random.random() < 0.7 else None,
                social_category=cat,
                is_nri=is_nri,
                is_oci=is_oci,
                is_foreign=is_fn,
                is_supernumerary=is_super,
                supernumerary_scheme=scheme,
                doc_ref=f"DOC-{aid[-6:]}",
                status=status,
                upload_batch_id=None,
            )

        # generate students
        idx = 0
        # planted invalid apaar: use a few bad ids
        bad_ids = ["123", "000000000000", "999999999999", "ABCDEFGHIJKL"]
        # planted cross-institution duplicates: take 15 apaar ids, enrol at two insts
        cross_dup_ids = apaar_ids[100:115]

        # Build list of (apaar_id, inst, prog, branch) assignments
        assignments = []
        # normal
        for _ in range(target - 200):
            aid = random.choice(all_apaar)
            inst = random.choices([i.id for i in insts], weights=weights, k=1)[0]
            prog = random.choice(PROGRAMMES)
            branch = random.choice(BRANCHES[prog])
            assignments.append((aid, inst, prog, branch, None))
        # planted over-intake: push extra into INST002 CS to exceed
        for _ in range(40):
            assignments.append((random.choice(all_apaar), insts[1].id, "B.Tech", "Computer Science", None))
        # planted invalid ids
        for bid in bad_ids:
            assignments.append((bid, insts[2].id, "B.Tech", "Electronics", None))
        # planted cross-inst dups
        for aid in cross_dup_ids:
            assignments.append((aid, insts[0].id, "B.Tech", "Computer Science", None))
            assignments.append((aid, insts[3].id, "B.Tech", "Electronics", None))
        # planted inconsistencies
        for _ in range(20):
            assignments.append((random.choice(all_apaar), insts[4].id, "B.Tech", "Mechanical", "nri_quota"))
        for _ in range(15):
            assignments.append((random.choice(all_apaar), insts[5].id, "B.Tech", "Civil", "oci_cat"))
        for _ in range(15):
            assignments.append((random.choice(all_apaar), insts[6].id, "B.Tech", "Civil", "fn_cat"))

        for aid, inst, prog, branch, planted in assignments:
            # ensure apaar exists in registry unless bad
            if aid not in apaar_ids and aid not in bad_ids:
                aid = random.choice(all_apaar)
            prog_branches = BRANCHES.get(prog, BRANCHES["B.Tech"])
            if branch not in prog_branches:
                branch = prog_branches[0]
            st = make_student(aid, inst, prog, branch, 2025, planted)
            students.append(st)

        # bulk insert in chunks
        chunk = 500
        for i in range(0, len(students), chunk):
            db.add_all(students[i:i+chunk])
            db.commit()
        print(f"Seeded {len(students)} students")

        # planted flags: cross-inst dup detection already via data; add a few anomaly flags
        # risk scores
        from app.services.intake import institution_risk_score, data_completeness
        for inst in insts:
            institution_risk_score(db, inst.id)
            inst.data_completeness = data_completeness(db, inst.id)
        db.commit()

        # student user linked to first student
        first_st = students[0]
        su = User(id=str(uuid.uuid4()), email="student@aicte.gov.in", password_hash=hash_password("student123"), full_name=first_st.name, role="student")
        # store apaar in institution_id? use a field; we'll just leave. Student can view own by apaar via email lookup not implemented; demo uses consent flow.
        db.add(su)
        db.commit()
        print("Seed complete.")
    finally:
        db.close()

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    run_seed()