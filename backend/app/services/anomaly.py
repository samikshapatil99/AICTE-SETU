from datetime import datetime
from collections import Counter
from sklearn.ensemble import IsolationForest
import numpy as np
from app.models import Flag

def truthy(v):
    if v is True or v == 1: return True
    if isinstance(v, str): return v.strip().lower() in ("true","1","yes","y")
    return False

def detect_anomalies(db, batch_id, institution_id, records):
    anomalies = []
    # 1. spike single day
    by_date = Counter(r.get("admission_date") or "unknown" for r in records)
    for d, c in by_date.items():
        if c >= 5 and d != "unknown":
            anomalies.append({"type": "SPIKE_SINGLE_DAY", "severity": "medium", "detail": f"{c} admissions recorded on {d}"})

    # 2. high nri / management share
    total = len(records) or 1
    nri = sum(1 for r in records if truthy(r.get("is_nri")))
    mgmt = sum(1 for r in records if "management" in str(r.get("quota") or "").lower())
    if nri / total > 0.4:
        anomalies.append({"type": "HIGH_NRI_SHARE", "severity": "medium", "detail": f"NRI share {nri/total*100:.1f}% exceeds 40%"})
    if mgmt / total > 0.5:
        anomalies.append({"type": "HIGH_MGMT_SHARE", "severity": "medium", "detail": f"Management quota share {mgmt/total*100:.1f}% exceeds 50%"})

    # 3. last-minute upload
    now = datetime.utcnow()
    last_minute = 0
    for r in records:
        ad = r.get("admission_date")
        if not ad: continue
        try:
            d = datetime.strptime(str(ad)[:10], "%Y-%m-%d")
            if 0 <= (now - d).days <= 3:
                last_minute += 1
        except ValueError:
            pass
    if last_minute >= 3:
        anomalies.append({"type": "LAST_MINUTE_UPLOAD", "severity": "low", "detail": f"{last_minute} records with admission dates within last 3 days"})

    # 4. duplicate rate
    apaars = [r.get("apaar_id") for r in records if r.get("apaar_id")]
    unique = set(apaars)
    if apaars and (len(apaars) - len(unique)) / len(apaars) > 0.1:
        anomalies.append({"type": "HIGH_DUP_RATE", "severity": "high", "detail": "Duplicate APAAR rate > 10% in batch"})

    # 5. Isolation Forest on simple features (admissions per day, nri flag, mgmt flag)
    try:
        if len(records) >= 10:
            X = np.array([
                [by_date.get(r.get("admission_date") or "unknown", 0),
                 1 if truthy(r.get("is_nri")) else 0,
                 1 if "management" in str(r.get("quota") or "").lower() else 0,
                 1 if truthy(r.get("is_supernumerary")) else 0]
                for r in records
            ], dtype=float)
            iso = IsolationForest(contamination=0.05, random_state=42)
            preds = iso.fit_predict(X)
            n_anom = int((preds == -1).sum())
            if n_anom >= 3:
                anomalies.append({"type": "ML_ANOMALY", "severity": "medium", "detail": f"Isolation Forest flagged {n_anom} anomalous records in batch"})
    except Exception:
        pass

    for a in anomalies:
        db.add(Flag(institution_id=institution_id, batch_id=batch_id, flag_type=a["type"], severity=a["severity"], reason=a["detail"], status="open"))
    db.commit()
    return anomalies