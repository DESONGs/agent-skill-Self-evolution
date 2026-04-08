-- V41__expand_skill_search_document_asset_fields.sql
-- Expand the search projection to carry registry-facing asset metadata and ranking signals.

ALTER TABLE skill_search_document
    ADD COLUMN IF NOT EXISTS latest_published_version_id BIGINT,
    ADD COLUMN IF NOT EXISTS latest_published_version VARCHAR(64),
    ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS label_slugs JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS runtime_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS tool_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS action_kinds JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS trust_score NUMERIC(10,4) NOT NULL DEFAULT 0.5000,
    ADD COLUMN IF NOT EXISTS quality_score NUMERIC(10,4) NOT NULL DEFAULT 0.5000,
    ADD COLUMN IF NOT EXISTS feedback_score NUMERIC(10,4) NOT NULL DEFAULT 0.5000,
    ADD COLUMN IF NOT EXISTS success_rate_30d NUMERIC(10,4) NOT NULL DEFAULT 0.5000,
    ADD COLUMN IF NOT EXISTS scan_verdict VARCHAR(32),
    ADD COLUMN IF NOT EXISTS review_state VARCHAR(32);

CREATE INDEX IF NOT EXISTS idx_skill_search_document_published_trust
    ON skill_search_document(published_at DESC, trust_score DESC, skill_id DESC);

CREATE INDEX IF NOT EXISTS idx_skill_search_document_label_slugs
    ON skill_search_document USING GIN (label_slugs);
