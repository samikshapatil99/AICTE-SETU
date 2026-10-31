from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_db
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

def hash_password(pw): return pwd_context.hash(pw)
def verify_password(pw, hashed): return pwd_context.verify(pw, hashed)

def create_token(user: User) -> str:
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "inst": user.institution_id,
        "state": user.state,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(tok: str):
    try:
        return jwt.decode(tok, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = decode_token(creds.credentials)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.get(User, data["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")
    return user

def require_roles(*roles):
    def dep(user: User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dep

# scope helpers
def scope_institution(user: User, institution_id: str):
    if user.role == "admin" or user.role == "auditor":
        return True
    if user.role == "regional":
        return None  # handled separately
    if user.role == "institution":
        return user.institution_id == institution_id
    return False

def is_admin_or_auditor(user): return user.role in ("admin", "auditor")
def is_regional(user): return user.role == "regional"