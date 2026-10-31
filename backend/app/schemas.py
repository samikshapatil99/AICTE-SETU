from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime

class LoginIn(BaseModel):
    email: str
    password: str

class OtpIn(BaseModel):
    session_id: str
    otp: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: Optional[str] = None
    institution_id: Optional[str] = None

class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: str
    institution_id: Optional[str]
    state: Optional[str]

class InstitutionOut(BaseModel):
    id: str
    name: str
    state: str
    type: str
    risk_score: int
    compliance_score: int
    data_completeness: int

class ApprovedIntakeOut(BaseModel):
    id: int
    institution_id: str
    programme: str
    branch: str
    year: int
    sanctioned_intake: int
    supernumerary_cap: int

class StudentIn(BaseModel):
    apaar_id: Optional[str] = None
    name: str
    dob: str
    gender: Optional[str] = None
    masked_aadhaar: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    institution_id: str
    programme: str
    branch: str
    year: int
    admission_date: Optional[str] = None
    admission_mode: Optional[str] = None
    quota: Optional[str] = None
    entrance_exam: Optional[str] = None
    entrance_rank: Optional[int] = None
    social_category: Optional[str] = None
    is_nri: bool = False
    is_oci: bool = False
    is_foreign: bool = False
    is_supernumerary: bool = False
    supernumerary_scheme: Optional[str] = None
    doc_ref: Optional[str] = None
    status: str = "admitted"
    exit_date: Optional[str] = None
    certificate_no: Optional[str] = None
    degree_body: Optional[str] = None

class StudentOut(StudentIn):
    id: str
    upload_batch_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class FlagOut(BaseModel):
    id: int
    institution_id: Optional[str]
    batch_id: Optional[str]
    apaar_id: Optional[str]
    student_name: Optional[str]
    flag_type: str
    severity: str
    reason: str
    status: str
    assigned_to: Optional[str]
    comment: Optional[str]
    created_at: Optional[datetime]

class BatchOut(BaseModel):
    id: str
    institution_id: str
    file_name: Optional[str]
    total_records: int
    valid_records: int
    rejected_records: int
    status: str
    created_at: Optional[datetime]