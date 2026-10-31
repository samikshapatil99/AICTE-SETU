from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON, Date
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

def now(): return datetime.utcnow()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, nullable=False)  # admin, regional, institution, verifier, student, auditor
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=True)
    state = Column(String, nullable=True)  # for regional officers
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)

class Institution(Base):
    __tablename__ = "institutions"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    state = Column(String, nullable=False)
    type = Column(String, default="Technical")
    nodal_officer = Column(String)
    email = Column(String)
    risk_score = Column(Integer, default=0)
    compliance_score = Column(Integer, default=100)
    data_completeness = Column(Integer, default=0)
    created_at = Column(DateTime, default=now)

class ApprovedIntake(Base):
    __tablename__ = "approved_intake"
    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False)
    programme = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    sanctioned_intake = Column(Integer, nullable=False)
    supernumerary_cap = Column(Integer, default=0)

class ApaarRegistry(Base):
    __tablename__ = "apaar_registry"
    apaar_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    dob = Column(String, nullable=False)
    gender = Column(String)
    parent_name = Column(String)
    mobile = Column(String)
    email = Column(String)
    status = Column(String, default="active")

class Student(Base):
    __tablename__ = "students"
    id = Column(String, primary_key=True)
    apaar_id = Column(String, index=True, nullable=True)
    name = Column(String, nullable=False)
    dob = Column(String, nullable=False)
    gender = Column(String)
    masked_aadhaar = Column(String)
    mobile = Column(String)
    email = Column(String)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False)
    programme = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    admission_date = Column(String)
    admission_mode = Column(String)
    quota = Column(String)
    entrance_exam = Column(String)
    entrance_rank = Column(Integer)
    social_category = Column(String)
    is_nri = Column(Boolean, default=False)
    is_oci = Column(Boolean, default=False)
    is_foreign = Column(Boolean, default=False)
    is_supernumerary = Column(Boolean, default=False)
    supernumerary_scheme = Column(String)
    doc_ref = Column(String)
    status = Column(String, default="admitted")
    exit_date = Column(String)
    certificate_no = Column(String)
    degree_body = Column(String)
    upload_batch_id = Column(String)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

class UploadBatch(Base):
    __tablename__ = "upload_batches"
    id = Column(String, primary_key=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False)
    file_name = Column(String)
    total_records = Column(Integer, default=0)
    valid_records = Column(Integer, default=0)
    rejected_records = Column(Integer, default=0)
    status = Column(String, default="processing")
    created_at = Column(DateTime, default=now)
    confirmed_at = Column(DateTime, nullable=True)

class StagingRecord(Base):
    __tablename__ = "staging_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String, ForeignKey("upload_batches.id"), nullable=False)
    row_index = Column(Integer, nullable=False)
    record_json = Column(Text, nullable=False)
    validation_status = Column(String, default="pending")

class ValidationError(Base):
    __tablename__ = "validation_errors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String, ForeignKey("upload_batches.id"), nullable=False)
    row_index = Column(Integer)
    apaar_id = Column(String)
    student_name = Column(String)
    error_code = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    message = Column(String, nullable=False)
    field = Column(String)

class Flag(Base):
    __tablename__ = "flags"
    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=True)
    batch_id = Column(String, ForeignKey("upload_batches.id"), nullable=True)
    apaar_id = Column(String)
    student_name = Column(String)
    flag_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="open")
    assigned_to = Column(String)
    comment = Column(Text)
    created_at = Column(DateTime, default=now)
    resolved_at = Column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String, nullable=False)
    role = Column(String)
    action = Column(String, nullable=False)
    entity_type = Column(String)
    entity_id = Column(String)
    details = Column(Text)
    created_at = Column(DateTime, default=now)

class VerificationRequest(Base):
    __tablename__ = "verification_requests"
    id = Column(String, primary_key=True)
    apaar_id = Column(String, nullable=False)
    requester = Column(String, nullable=False)
    purpose = Column(String)
    fields = Column(JSON)
    consent_granted = Column(Boolean, default=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=now)
    expires_at = Column(DateTime, nullable=True)

class ConsentLedger(Base):
    __tablename__ = "consent_ledger"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_apaar = Column(String, nullable=False)
    requester = Column(String, nullable=False)
    purpose = Column(String)
    fields = Column(JSON)
    granted = Column(Boolean, default=False)
    granted_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

class VerifiableCredential(Base):
    __tablename__ = "verifiable_credentials"
    id = Column(String, primary_key=True)
    apaar_id = Column(String, nullable=False)
    institution_id = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    hash = Column(String, nullable=False)
    signature = Column(Text)
    issued_at = Column(DateTime, default=now)

class Grievance(Base):
    __tablename__ = "grievances"
    id = Column(Integer, primary_key=True, autoincrement=True)
    apaar_id = Column(String)
    student_name = Column(String)
    issue = Column(Text, nullable=False)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=now)
    resolved_at = Column(DateTime, nullable=True)

class PendingOtp(Base):
    __tablename__ = "pending_otps"
    id = Column(String, primary_key=True)
    email = Column(String, nullable=False)
    otp = Column(String, nullable=False)
    created_at = Column(DateTime, default=now)
    expires_at = Column(DateTime, nullable=False)

# ---------- Explainable Compliance Workflow ----------

class StudentVersion(Base):
    __tablename__ = "student_versions"
    id = Column(String, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    version_no = Column(Integer, nullable=False)
    snapshot = Column(Text, nullable=False)  # JSON of full record
    changed_by = Column(String)
    change_reason = Column(String)
    created_at = Column(DateTime, default=now)

class ChangeEvent(Base):
    __tablename__ = "change_events"
    id = Column(String, primary_key=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    field = Column(String, nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    actor = Column(String, nullable=False)
    actor_role = Column(String)
    reason = Column(String)
    created_at = Column(DateTime, default=now)

class RuleSet(Base):
    __tablename__ = "rule_sets"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    academic_year = Column(String, nullable=False)
    scope = Column(String, nullable=False)  # national/institution/programme
    effective_from = Column(String, nullable=False)
    effective_to = Column(String, nullable=True)
    source_reference = Column(String)
    approval_status = Column(String, default="approved")
    description = Column(Text)
    config = Column(Text)  # JSON thresholds
    created_at = Column(DateTime, default=now)

class ValidationResult(Base):
    __tablename__ = "validation_results"
    id = Column(String, primary_key=True)
    student_id = Column(String, nullable=True)
    batch_id = Column(String, nullable=True)
    apaar_id = Column(String, nullable=True)
    rule_set_id = Column(String, ForeignKey("rule_sets.id"), nullable=False)
    rule_version = Column(String, nullable=False)
    timestamp = Column(DateTime, default=now)
    input_snapshot_ref = Column(String)
    outcome = Column(String, nullable=False)  # valid/warning/rejected
    errors_json = Column(Text)
    triggered_rules = Column(Text)  # JSON list of rule ids

class ComplianceCase(Base):
    __tablename__ = "compliance_cases"
    id = Column(String, primary_key=True)
    source_flag_id = Column(Integer, nullable=True)
    institution_id = Column(String, nullable=True)
    apaar_id = Column(String, nullable=True)
    student_id = Column(String, nullable=True)
    status = Column(String, default="open")  # open, evidence_requested, under_review, resolved, escalated
    title = Column(String)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

class CaseDecision(Base):
    __tablename__ = "case_decisions"
    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("compliance_cases.id"), nullable=False)
    reviewer = Column(String, nullable=False)
    reviewer_role = Column(String)
    rationale = Column(Text, nullable=False)
    outcome = Column(String, nullable=False)
    decided_at = Column(DateTime, default=now)

class CaseEvidence(Base):
    __tablename__ = "case_evidence"
    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("compliance_cases.id"), nullable=False)
    kind = Column(String, nullable=False)  # observed_fact, rule_evidence, system_inference, impact, recommended_action
    label = Column(String)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=now)

class Dependency(Base):
    __tablename__ = "dependencies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    from_type = Column(String, nullable=False)
    from_id = Column(String, nullable=False)
    to_type = Column(String, nullable=False)
    to_id = Column(String, nullable=False)
    reason = Column(String)
    created_at = Column(DateTime, default=now)

class IssueClassification(Base):
    __tablename__ = "issue_classifications"
    id = Column(String, primary_key=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    issue_type = Column(String, nullable=False)  # missing_field, inconsistent_value, suspected_duplicate, manual_review
    severity = Column(String, nullable=False)
    deadline = Column(String)
    downstream_impact = Column(Integer, default=0)
    priority_score = Column(Integer, default=0)
    status = Column(String, default="open")  # open, resolved
    created_at = Column(DateTime, default=now)
    resolved_at = Column(DateTime, nullable=True)

class RecoveryAction(Base):
    __tablename__ = "recovery_actions"
    id = Column(String, primary_key=True)
    issue_id = Column(String, ForeignKey("issue_classifications.id"), nullable=False)
    action_type = Column(String, nullable=False)  # normalise, fill, merge, manual
    preview_diff = Column(Text)
    applied = Column(Boolean, default=False)
    applied_by = Column(String)
    applied_at = Column(DateTime, nullable=True)
    reverted = Column(Boolean, default=False)