from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AuditLog, User
from app.auth import current_user

router = APIRouter()

@router.get("/logs")
def audit_logs(limit: int = Query(200, le=1000), user=Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(AuditLog)
    return q.order_by(AuditLog.created_at.desc()).limit(limit).all()