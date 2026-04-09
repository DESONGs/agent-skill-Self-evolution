CREATE TABLE skill_bundle_artifact (
    id BIGSERIAL PRIMARY KEY,
    skill_version_id BIGINT NOT NULL REFERENCES skill_version(id) ON DELETE CASCADE UNIQUE,
    storage_key VARCHAR(512) NOT NULL,
    content_type VARCHAR(128),
    sha256 VARCHAR(64),
    size_bytes BIGINT NOT NULL DEFAULT 0,
    build_status VARCHAR(32) NOT NULL,
    manifest_digest VARCHAR(64),
    built_by VARCHAR(128) REFERENCES user_account(id),
    built_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skill_bundle_artifact_build_status
    ON skill_bundle_artifact(build_status, built_at DESC);

CREATE TABLE skill_environment_profile (
    id BIGSERIAL PRIMARY KEY,
    skill_version_id BIGINT NOT NULL REFERENCES skill_version(id) ON DELETE CASCADE,
    profile_key VARCHAR(64) NOT NULL,
    display_name VARCHAR(128),
    runtime_family VARCHAR(64),
    runtime_version_range VARCHAR(64),
    tool_requirements_json JSONB,
    capability_tags_json JSONB,
    os_constraints_json JSONB,
    network_policy VARCHAR(32),
    filesystem_policy VARCHAR(32),
    sandbox_mode VARCHAR(32),
    resource_limits_json JSONB,
    env_schema_json JSONB,
    is_default_profile BOOLEAN NOT NULL DEFAULT FALSE,
    created_by VARCHAR(128) REFERENCES user_account(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(skill_version_id, profile_key)
);

CREATE INDEX idx_skill_environment_profile_skill_id
    ON skill_environment_profile(skill_version_id);

CREATE TABLE skill_action (
    id BIGSERIAL PRIMARY KEY,
    skill_version_id BIGINT NOT NULL REFERENCES skill_version(id) ON DELETE CASCADE,
    action_id VARCHAR(64) NOT NULL,
    display_name VARCHAR(128),
    action_kind VARCHAR(32) NOT NULL,
    entry_path VARCHAR(512) NOT NULL,
    runtime_family VARCHAR(64),
    environment_profile_id BIGINT REFERENCES skill_environment_profile(id),
    timeout_sec INTEGER,
    sandbox_mode VARCHAR(32),
    allow_network BOOLEAN NOT NULL DEFAULT FALSE,
    input_schema_json JSONB,
    output_schema_json JSONB,
    side_effects_json JSONB,
    idempotency_mode VARCHAR(32),
    is_default_action BOOLEAN NOT NULL DEFAULT FALSE,
    created_by VARCHAR(128) REFERENCES user_account(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(skill_version_id, action_id)
);

CREATE INDEX idx_skill_action_skill_id
    ON skill_action(skill_version_id);

CREATE INDEX idx_skill_action_kind
    ON skill_action(action_kind);

CREATE TABLE skill_eval_suite (
    id BIGSERIAL PRIMARY KEY,
    skill_version_id BIGINT NOT NULL REFERENCES skill_version(id) ON DELETE CASCADE,
    suite_key VARCHAR(64) NOT NULL,
    display_name VARCHAR(128),
    suite_type VARCHAR(32) NOT NULL,
    entry_path VARCHAR(512),
    gate_level VARCHAR(32) NOT NULL,
    config_json JSONB,
    success_criteria_json JSONB,
    latest_report_key VARCHAR(512),
    created_by VARCHAR(128) REFERENCES user_account(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(skill_version_id, suite_key)
);

CREATE INDEX idx_skill_eval_suite_skill_id
    ON skill_eval_suite(skill_version_id);
