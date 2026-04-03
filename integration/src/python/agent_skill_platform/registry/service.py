from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from orchestrator.runtime.envelope import RunFeedbackEnvelope

from ..contracts import build_source_bundle, load_skill_package, validate_skill_package
from ..models import PromotionSubmission
from ..runtime import build_runtime_install_bundle


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)


@dataclass(frozen=True)
class PublishedSkillVersion:
    skill_id: str
    version_id: str
    slug: str
    package_root: Path
    bundle_path: Path
    bundle_sha256: str
    bundle_size: int
    created_at: str


class LocalDevRegistryService:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.db_path = self.root / "registry.db"
        self.storage_root = self.root / "storage"
        self.packages_root = self.storage_root / "packages"
        self.bundles_root = self.storage_root / "bundles"
        self.feedback_root = self.storage_root / "feedback"
        self.promotions_root = self.storage_root / "promotions"
        self.root.mkdir(parents=True, exist_ok=True)
        self.packages_root.mkdir(parents=True, exist_ok=True)
        self.bundles_root.mkdir(parents=True, exist_ok=True)
        self.feedback_root.mkdir(parents=True, exist_ok=True)
        self.promotions_root.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                create table if not exists skills (
                    skill_id text primary key,
                    slug text not null,
                    latest_version_id text,
                    created_at text not null,
                    updated_at text not null
                );

                create table if not exists versions (
                    version_id text primary key,
                    skill_id text not null,
                    slug text not null,
                    package_root text not null,
                    bundle_path text not null,
                    bundle_sha256 text not null,
                    bundle_size integer not null,
                    manifest_json text not null,
                    created_at text not null,
                    foreign key(skill_id) references skills(skill_id)
                );

                create table if not exists feedback_events (
                    id integer primary key autoincrement,
                    run_id text not null,
                    skill_id text not null,
                    version_id text,
                    action_id text not null,
                    payload_json text not null,
                    created_at text not null
                );

                create table if not exists promotion_requests (
                    id integer primary key autoincrement,
                    candidate_id text not null,
                    candidate_slug text not null,
                    run_id text not null,
                    submission_json text not null,
                    state text not null,
                    created_at text not null
                );
                """
            )

    def _stage_package_dir(self, package_root: Path) -> Path:
        package = load_skill_package(package_root)
        slug = package.manifest.name
        version = package.manifest.version
        target_root = self.packages_root / slug / version / slug
        if target_root.exists():
            shutil.rmtree(target_root)
        target_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(package_root, target_root)
        return target_root

    def _extract_bundle(self, bundle_path: Path) -> Path:
        with tempfile.TemporaryDirectory(prefix="asp-registry-publish-") as tmpdir:
            tmp_root = Path(tmpdir)
            with zipfile.ZipFile(bundle_path) as archive:
                archive.extractall(tmp_root)
            roots = [path for path in tmp_root.iterdir() if path.is_dir()]
            if len(roots) != 1:
                raise ValueError("bundle archive must contain exactly one root directory")
            staged_root = roots[0]
            report = validate_skill_package(staged_root)
            if not report.ok:
                raise ValueError(_json_dumps(report.model_dump()))
            final_root = self._stage_package_dir(staged_root)
        return final_root

    def publish_package(self, source: str | Path) -> dict[str, Any]:
        source_path = Path(source).resolve()
        if source_path.is_dir():
            report = validate_skill_package(source_path)
            if not report.ok:
                raise ValueError(_json_dumps(report.model_dump()))
            package_root = self._stage_package_dir(source_path)
        elif source_path.is_file() and source_path.suffix.lower() == ".zip":
            package_root = self._extract_bundle(source_path)
        else:
            raise ValueError(f"Unsupported publish source: {source_path}")

        package = load_skill_package(package_root)
        slug = package.manifest.name
        version = package.manifest.version
        bundle_dir = self.bundles_root / slug / version
        bundle_artifact = build_source_bundle(package_root, bundle_dir)
        bundle = build_runtime_install_bundle(package_root, skill_id=slug, version_id=version)

        with self._connect() as conn:
            now = bundle.metadata.get("created_at") or package.manifest.updated_at.isoformat()
            conn.execute(
                """
                insert into skills(skill_id, slug, latest_version_id, created_at, updated_at)
                values (?, ?, ?, ?, ?)
                on conflict(skill_id) do update set
                    slug=excluded.slug,
                    latest_version_id=excluded.latest_version_id,
                    updated_at=excluded.updated_at
                """,
                (slug, slug, version, now, now),
            )
            conn.execute(
                """
                insert or replace into versions(version_id, skill_id, slug, package_root, bundle_path, bundle_sha256, bundle_size, manifest_json, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version,
                    slug,
                    slug,
                    str(package_root),
                    str(bundle_artifact.path),
                    bundle.bundle_sha256,
                    bundle.bundle_size,
                    _json_dumps(package.manifest.model_dump()),
                    now,
                ),
            )

        return {
            "ok": True,
            "skill_id": slug,
            "version_id": version,
            "package_root": str(package_root),
            "bundle_path": str(bundle_artifact.path),
            "bundle_sha256": bundle.bundle_sha256,
            "bundle_size": bundle.bundle_size,
            "install_bundle": bundle.to_dict(),
        }

    def resolve_install_bundle(self, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
        with self._connect() as conn:
            if version_id:
                row = conn.execute(
                    "select * from versions where skill_id = ? and version_id = ?",
                    (skill_id, version_id),
                ).fetchone()
            else:
                skill = conn.execute(
                    "select latest_version_id from skills where skill_id = ?",
                    (skill_id,),
                ).fetchone()
                if not skill:
                    raise KeyError(f"Unknown skill: {skill_id}")
                row = conn.execute(
                    "select * from versions where skill_id = ? and version_id = ?",
                    (skill_id, skill["latest_version_id"]),
                ).fetchone()
        if not row:
            raise KeyError(f"Unknown published version for skill {skill_id}")
        bundle = build_runtime_install_bundle(
            row["package_root"],
            skill_id=row["skill_id"],
            version_id=row["version_id"],
        )
        payload = bundle.to_dict()
        payload["bundle_path"] = row["bundle_path"]
        return payload

    def ingest_feedback(self, envelope: RunFeedbackEnvelope | dict[str, Any]) -> dict[str, Any]:
        normalized = envelope if isinstance(envelope, RunFeedbackEnvelope) else RunFeedbackEnvelope.from_dict(envelope)
        payload = normalized.to_dict()
        with self._connect() as conn:
            conn.execute(
                """
                insert into feedback_events(run_id, skill_id, version_id, action_id, payload_json, created_at)
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized.run_id,
                    normalized.skill_id,
                    normalized.version_id,
                    normalized.action_id,
                    _json_dumps(payload),
                    normalized.created_at,
                ),
            )
        event_path = self.feedback_root / f"{normalized.run_id}.json"
        event_path.write_text(_json_dumps(payload) + "\n", encoding="utf-8")
        return {"ok": True, "event_path": str(event_path), "feedback": payload}

    def submit_promotion(self, submission: PromotionSubmission | dict[str, Any]) -> dict[str, Any]:
        normalized = submission if isinstance(submission, PromotionSubmission) else PromotionSubmission(**submission)
        payload = normalized.to_dict()
        request_root = self.promotions_root / normalized.candidate_slug / normalized.run_id
        request_root.mkdir(parents=True, exist_ok=True)
        payload_path = request_root / "promotion_submission.json"
        payload_path.write_text(_json_dumps(payload) + "\n", encoding="utf-8")
        with self._connect() as conn:
            conn.execute(
                """
                insert into promotion_requests(candidate_id, candidate_slug, run_id, submission_json, state, created_at)
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized.candidate_id,
                    normalized.candidate_slug,
                    normalized.run_id,
                    _json_dumps(payload),
                    "PENDING_REVIEW",
                    normalized.submitted_at,
                ),
            )
        return {"ok": True, "state": "PENDING_REVIEW", "submission_path": str(payload_path), "submission": payload}

    def get_skill(self, skill_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            skill = conn.execute("select * from skills where skill_id = ?", (skill_id,)).fetchone()
            if not skill:
                raise KeyError(f"Unknown skill: {skill_id}")
            versions = conn.execute(
                "select version_id, bundle_path, bundle_sha256, bundle_size, created_at from versions where skill_id = ? order by created_at desc",
                (skill_id,),
            ).fetchall()
        return {
            "skill_id": skill["skill_id"],
            "slug": skill["slug"],
            "latest_version_id": skill["latest_version_id"],
            "versions": [dict(row) for row in versions],
        }

    def list_skills(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("select skill_id, slug, latest_version_id, updated_at from skills order by skill_id asc").fetchall()
        return [dict(row) for row in rows]
