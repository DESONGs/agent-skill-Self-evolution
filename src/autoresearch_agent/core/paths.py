from __future__ import annotations

from pathlib import Path


DEFAULT_PROJECT_FILE = "research.yaml"
DEFAULT_ARTIFACTS_DIR = "artifacts"
DEFAULT_WORKSPACE_DIR = "workspace"
DEFAULT_STATE_DIR = ".autoresearch"
DEFAULT_RUNS_DIR = ".autoresearch/runs"
DEFAULT_CACHE_DIR = ".autoresearch/cache"
DEFAULT_DATASETS_DIR = "datasets"
DEFAULT_SECRETS_FILE = ".secrets.local"


def resolve_project_root(start: str | Path) -> Path:
    candidate = Path(start).expanduser().resolve()
    if candidate.is_file():
        return candidate.parent
    return candidate


def project_file_path(project_root: str | Path) -> Path:
    return resolve_project_root(project_root) / DEFAULT_PROJECT_FILE


def state_dir_path(project_root: str | Path) -> Path:
    return resolve_project_root(project_root) / DEFAULT_STATE_DIR


def runs_dir_path(project_root: str | Path) -> Path:
    return resolve_project_root(project_root) / DEFAULT_RUNS_DIR


def artifacts_dir_path(project_root: str | Path) -> Path:
    return resolve_project_root(project_root) / DEFAULT_ARTIFACTS_DIR


def workspace_dir_path(project_root: str | Path) -> Path:
    return resolve_project_root(project_root) / DEFAULT_WORKSPACE_DIR


def datasets_dir_path(project_root: str | Path) -> Path:
    return resolve_project_root(project_root) / DEFAULT_DATASETS_DIR
