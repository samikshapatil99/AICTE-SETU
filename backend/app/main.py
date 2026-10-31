from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS
from app.database import engine, Base
from app import models  # noqa
from app.routers import auth, institutions, students, upload, dashboard, verification, reports, audit, apaar, compliance

app = FastAPI(title="AICTE-SETU API", version="1.0.0", description="APAAR-based Student Data Management & Verification System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.pages\.dev|http://localhost:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    # seed if empty
    from app.seed import run_seed
    run_seed()
    try:
        from seed_zeal import seed_zeal
        seed_zeal()
    except Exception as e:
        print("seed_zeal error:", e)
    from app.services.compliance import seed_rule_sets
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        seed_rule_sets(db)
    finally:
        db.close()

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(institutions.router, prefix="/api/institutions", tags=["institutions"])
app.include_router(students.router, prefix="/api/students", tags=["students"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(verification.router, prefix="/api/verification", tags=["verification"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(apaar.router, prefix="/api/apaar", tags=["apaar"])
app.include_router(compliance.router, prefix="/api/compliance", tags=["compliance"])

@app.get("/api/health")
def health():
    return {"ok": True, "service": "aicte-setu"}