from __future__ import annotations

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SkillRecord(Base):
    __tablename__ = "skills"

    skill_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    latest_version_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)


class SkillVersionRecord(Base):
    __tablename__ = "skill_versions"

    version_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.skill_id"), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    package_object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    bundle_object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    bundle_sha256: Mapped[str] = mapped_column(String(128), nullable=False)
    bundle_size: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class SkillProjectionRecord(Base):
    __tablename__ = "skill_projections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.skill_id"), index=True, nullable=False)
    version_id: Mapped[str] = mapped_column(ForeignKey("skill_versions.version_id"), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    skill_type: Mapped[str] = mapped_column(String(64), nullable=False)
    inner_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outer_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    parameter_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    default_action_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class FeedbackEventRecord(Base):
    __tablename__ = "feedback_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    skill_id: Mapped[str] = mapped_column(String(255), nullable=False)
    version_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    event_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class PromotionRequestRecord(Base):
    __tablename__ = "promotion_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    run_id: Mapped[str] = mapped_column(String(255), nullable=False)
    case_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    proposal_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision_mode: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lineage_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    submission_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    submission_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class CaseRecordRow(Base):
    __tablename__ = "cases"

    case_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class CandidateProposalRecord(Base):
    __tablename__ = "candidate_proposals"

    proposal_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    candidate_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class OutcomeRecordRow(Base):
    __tablename__ = "outcomes"

    outcome_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(255), nullable=False)
    proposal_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class JobRunRecord(Base):
    __tablename__ = "job_runs"

    job_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(128), nullable=False)
    queue_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)
