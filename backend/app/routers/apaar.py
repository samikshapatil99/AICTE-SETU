from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ApaarRegistry
from app.auth import current_user

router = APIRouter()

@router.get("/{apaar_id}")
def get_apaar(apaar_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(ApaarRegistry, apaar_id)
    if not r:
        from fastapi import HTTPException
        raise HTTPException(404, "not found")
    return {"apaar_id": r.apaar_id, "name": r.name, "dob": r.dob, "gender": r.gender, "parent_name": r.parent_name}