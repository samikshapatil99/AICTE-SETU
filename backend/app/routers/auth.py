import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, PendingOtp
from app.schemas import LoginIn, OtpIn, TokenOut, UserOut
from app.auth import verify_password, create_token, hash_password, current_user
from app.config import OTP_DEMO

router = APIRouter()

@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    otp = OTP_DEMO
    sess = str(uuid.uuid4())
    db.add(PendingOtp(id=sess, email=body.email, otp=otp, expires_at=datetime.utcnow() + timedelta(minutes=5)))
    db.commit()
    return {"otp_required": True, "session_id": sess, "demo_otp": otp}

@router.post("/verify-otp", response_model=TokenOut)
def verify_otp(body: OtpIn, db: Session = Depends(get_db)):
    po = db.get(PendingOtp, body.session_id)
    if not po or po.otp != body.otp or po.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    user = db.query(User).filter(User.email == po.email).first()
    db.delete(po)
    db.commit()
    token = create_token(user)
    return TokenOut(access_token=token, role=user.role, full_name=user.full_name, institution_id=user.institution_id)

@router.get("/me", response_model=UserOut)
def me(user=Depends(current_user)):
    return UserOut(id=user.id, email=user.email, full_name=user.full_name, role=user.role, institution_id=user.institution_id, state=user.state)