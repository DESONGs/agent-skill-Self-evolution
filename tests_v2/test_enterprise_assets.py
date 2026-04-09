from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_enterprise_top_level_assets_exist() -> None:
    expected = [
        ROOT / "pyproject.toml",
        ROOT / ".env.example",
        ROOT / "docker-compose.yml",
        ROOT / "Dockerfile.api",
        ROOT / "Dockerfile.worker",
        ROOT / "alembic.ini",
        ROOT / "deploy" / "README.md",
        ROOT / "deploy" / "nginx.conf",
    ]
    for path in expected:
        assert path.exists(), f"missing expected enterprise asset: {path}"


def test_enterprise_service_tree_exists() -> None:
    expected = [
        ROOT / "src" / "agent_skill_platform" / "config" / "settings.py",
        ROOT / "src" / "agent_skill_platform" / "storage" / "postgres" / "models.py",
        ROOT / "src" / "agent_skill_platform" / "storage" / "object_store" / "client.py",
        ROOT / "src" / "agent_skill_platform" / "services" / "registry_service.py",
        ROOT / "src" / "agent_skill_platform" / "services" / "execution_service.py",
        ROOT / "src" / "agent_skill_platform" / "services" / "promotion_service.py",
        ROOT / "src" / "agent_skill_platform" / "jobs" / "worker.py",
    ]
    for path in expected:
        assert path.exists(), f"missing expected enterprise source file: {path}"
