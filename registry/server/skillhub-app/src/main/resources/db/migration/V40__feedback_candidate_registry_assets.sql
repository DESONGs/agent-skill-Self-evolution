-- V40__feedback_candidate_registry_assets.sql
-- Phase 1: feedback / candidate / governance signals

CREATE TABLE skill_candidate (
    id BIGSERIAL PRIMARY KEY,
    candidate_key VARCHAR(128) NOT NULL UNIQUE,
    candidate_slug VARCHAR(128) NOT NULL,
    candidate_spec_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_kind VARCHAR(32) NOT NULL,
    source_refs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    problem_statement TEXT,
    target_user VARCHAR(256),
    skill_boundary TEXT,
    trigger_description TEXT,
    anti_triggers_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    default_action_id VARCHAR(128),
    governance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_bundle_key VARCHAR(512),
    generated_manifest_key VARCHAR(512),
    report_index_key VARCHAR(512),
    latest_lab_run_id VARCHAR(128),
    promotion_state VARCHAR(32) NOT NULL DEFAULT 'CREATED',
    source_skill_id BIGINT REFERENCES skill(id) ON DELETE SET NULL,
    source_version_id BIGINT REFERENCES skill_version(id) ON DELETE SET NULL,
    published_skill_id BIGINT REFERENCES skill(id) ON DELETE SET NULL,
    published_version_id BIGINT REFERENCES skill_version(id) ON DELETE SET NULL,
    created_by VARCHAR(128) REFERENCES user_account(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skill_candidate_state_updated_at
    ON skill_candidate(promotion_state, updated_at DESC);

CREATE TABLE skill_promotion_decision (
    id BIGSERIAL PRIMARY KEY,
    skill_candidate_id BIGINT NOT NULL REFERENCES skill_candidate(id) ON DELETE CASCADE,
    decision VARCHAR(32) NOT NULL,
    decision_mode VARCHAR(32) NOT NULL,
    reasons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    scores_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence_index_key VARCHAR(512),
    decided_by VARCHAR(128) REFERENCES user_account(id),
    decided_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skill_promotion_decision_candidate_created_at
    ON skill_promotion_decision(skill_candidate_id, created_at DESC);

CREATE TABLE skill_score_snapshot (
    skill_id BIGINT PRIMARY KEY REFERENCES skill(id) ON DELETE CASCADE,
    latest_published_version_id BIGINT REFERENCES skill_version(id) ON DELETE SET NULL,
    trust_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    quality_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    feedback_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    success_rate_30d NUMERIC(10,4) NOT NULL DEFAULT 0,
    rating_bayes NUMERIC(10,4) NOT NULL DEFAULT 0,
    download_count_30d BIGINT NOT NULL DEFAULT 0,
    lab_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE skill_run_feedback (
    id BIGSERIAL PRIMARY KEY,
    dedupe_key VARCHAR(128) NOT NULL UNIQUE,
    feedback_source VARCHAR(32) NOT NULL,
    subject_type VARCHAR(32) NOT NULL,
    skill_id BIGINT REFERENCES skill(id) ON DELETE SET NULL,
    skill_version_id BIGINT REFERENCES skill_version(id) ON DELETE SET NULL,
    skill_action_id BIGINT,
    skill_candidate_id BIGINT REFERENCES skill_candidate(id) ON DELETE SET NULL,
    environment_profile_id BIGINT,
    source_run_id VARCHAR(128),
    feedback_type VARCHAR(32) NOT NULL,
    success BOOLEAN,
    rating INT,
    latency_ms BIGINT,
    error_code VARCHAR(128),
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    observed_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor_id VARCHAR(128) REFERENCES user_account(id)
);

CREATE INDEX idx_skill_run_feedback_skill_observed_at
    ON skill_run_feedback(skill_id, observed_at DESC);

CREATE INDEX idx_skill_run_feedback_version_observed_at
    ON skill_run_feedback(skill_version_id, observed_at DESC);

CREATE INDEX idx_skill_run_feedback_candidate_observed_at
    ON skill_run_feedback(skill_candidate_id, observed_at DESC);
