from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_enterprise_v2_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("skill_id", sa.String(length=255), primary_key=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("latest_version_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.String(length=64), nullable=False),
    )
    op.create_table(
        "skill_versions",
        sa.Column("version_id", sa.String(length=255), primary_key=True),
        sa.Column("skill_id", sa.String(length=255), sa.ForeignKey("skills.skill_id"), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("package_object_key", sa.String(length=1024), nullable=False),
        sa.Column("bundle_object_key", sa.String(length=1024), nullable=False),
        sa.Column("bundle_sha256", sa.String(length=128), nullable=False),
        sa.Column("bundle_size", sa.BigInteger(), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_table(
        "skill_projections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("skill_id", sa.String(length=255), sa.ForeignKey("skills.skill_id"), nullable=False),
        sa.Column("version_id", sa.String(length=255), sa.ForeignKey("skill_versions.version_id"), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("skill_type", sa.String(length=64), nullable=False),
        sa.Column("inner_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("outer_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("parameter_schema", sa.JSON(), nullable=False),
        sa.Column("default_action_id", sa.String(length=255), nullable=True),
        sa.Column("risk_level", sa.String(length=64), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.String(length=64), nullable=True),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_table(
        "feedback_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=255), nullable=False),
        sa.Column("skill_id", sa.String(length=255), nullable=False),
        sa.Column("version_id", sa.String(length=255), nullable=True),
        sa.Column("action_id", sa.String(length=255), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("event_ref", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_table(
        "promotion_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("candidate_id", sa.String(length=255), nullable=False),
        sa.Column("candidate_slug", sa.String(length=255), nullable=False),
        sa.Column("run_id", sa.String(length=255), nullable=False),
        sa.Column("case_id", sa.String(length=255), nullable=True),
        sa.Column("proposal_id", sa.String(length=255), nullable=True),
        sa.Column("decision_mode", sa.String(length=255), nullable=True),
        sa.Column("lineage_json", sa.JSON(), nullable=False),
        sa.Column("submission_json", sa.JSON(), nullable=False),
        sa.Column("submission_ref", sa.String(length=1024), nullable=True),
        sa.Column("state", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_table(
        "cases",
        sa.Column("case_id", sa.String(length=255), primary_key=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_table(
        "candidate_proposals",
        sa.Column("proposal_id", sa.String(length=255), primary_key=True),
        sa.Column("case_id", sa.String(length=255), nullable=False),
        sa.Column("candidate_id", sa.String(length=255), nullable=True),
        sa.Column("candidate_slug", sa.String(length=255), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("candidate_ref", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_table(
        "outcomes",
        sa.Column("outcome_id", sa.String(length=255), primary_key=True),
        sa.Column("case_id", sa.String(length=255), nullable=False),
        sa.Column("proposal_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_table(
        "job_runs",
        sa.Column("job_id", sa.String(length=255), primary_key=True),
        sa.Column("job_type", sa.String(length=128), nullable=False),
        sa.Column("queue_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_feedback_events_run_id", "feedback_events", ["run_id"])
    op.create_index("ix_job_runs_status", "job_runs", ["status"])
    op.create_index("ix_skill_projections_skill_id", "skill_projections", ["skill_id"])
    op.create_index("ix_skill_versions_skill_id", "skill_versions", ["skill_id"])


def downgrade() -> None:
    op.drop_index("ix_skill_versions_skill_id", table_name="skill_versions")
    op.drop_index("ix_skill_projections_skill_id", table_name="skill_projections")
    op.drop_index("ix_job_runs_status", table_name="job_runs")
    op.drop_index("ix_feedback_events_run_id", table_name="feedback_events")
    op.drop_table("job_runs")
    op.drop_table("outcomes")
    op.drop_table("candidate_proposals")
    op.drop_table("cases")
    op.drop_table("promotion_requests")
    op.drop_table("feedback_events")
    op.drop_table("skill_projections")
    op.drop_table("skill_versions")
    op.drop_table("skills")
