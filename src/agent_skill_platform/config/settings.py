from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EnterpriseSettings:
    app_env: str
    host: str
    port: int
    database_url: str
    redis_url: str
    registry_mode: str
    registry_url: str
    s3_bucket: str
    s3_endpoint_url: str
    s3_access_key: str
    s3_secret_key: str
    s3_region: str
    s3_secure: bool
    s3_auto_create_bucket: bool
    scratch_root: Path
    feedback_queue: str
    promotion_queue: str
    projection_queue: str

    @classmethod
    def from_env(cls) -> "EnterpriseSettings":
        scratch_root = Path(_env("AGENT_SKILL_PLATFORM_SCRATCH_ROOT", "/tmp/agent-skill-platform-enterprise")).resolve()
        scratch_root.mkdir(parents=True, exist_ok=True)
        return cls(
            app_env=_env("AGENT_SKILL_PLATFORM_APP_ENV", "development"),
            host=_env("AGENT_SKILL_PLATFORM_HOST", "0.0.0.0"),
            port=int(_env("AGENT_SKILL_PLATFORM_PORT", "8080")),
            database_url=_env("AGENT_SKILL_PLATFORM_DB_URL", "sqlite+pysqlite:///enterprise_v2.db"),
            redis_url=_env("AGENT_SKILL_PLATFORM_REDIS_URL", "redis://localhost:6379/0"),
            registry_mode=_env("AGENT_SKILL_PLATFORM_REGISTRY_MODE", "service"),
            registry_url=_env("AGENT_SKILL_PLATFORM_REGISTRY_URL", "http://localhost:8080"),
            s3_bucket=_env("AGENT_SKILL_PLATFORM_S3_BUCKET", "agent-skill-platform"),
            s3_endpoint_url=_env("AGENT_SKILL_PLATFORM_S3_ENDPOINT_URL", "http://localhost:9000"),
            s3_access_key=_env("AGENT_SKILL_PLATFORM_S3_ACCESS_KEY", "minioadmin"),
            s3_secret_key=_env("AGENT_SKILL_PLATFORM_S3_SECRET_KEY", "minioadmin"),
            s3_region=_env("AGENT_SKILL_PLATFORM_S3_REGION", "us-east-1"),
            s3_secure=_env_bool("AGENT_SKILL_PLATFORM_S3_SECURE", False),
            s3_auto_create_bucket=_env_bool("AGENT_SKILL_PLATFORM_S3_AUTO_CREATE_BUCKET", True),
            scratch_root=scratch_root,
            feedback_queue=_env("AGENT_SKILL_PLATFORM_FEEDBACK_QUEUE", "feedback"),
            promotion_queue=_env("AGENT_SKILL_PLATFORM_PROMOTION_QUEUE", "promotion"),
            projection_queue=_env("AGENT_SKILL_PLATFORM_PROJECTION_QUEUE", "projection"),
        )
