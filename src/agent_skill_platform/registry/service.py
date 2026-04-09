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
from ..models import PromotionSubmission, _as_dict
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


class RegistryService:
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
                    case_id text,
                    proposal_id text,
                    decision_mode text,
                    lineage_json text,
                    submission_json text not null,
                    state text not null,
                    created_at text not null
                );
                """
            )
            self._ensure_promotion_request_columns(conn)

    def _ensure_promotion_request_columns(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("pragma table_info(promotion_requests)").fetchall()}
        for column_name, ddl in (
            ("case_id", "case_id text"),
            ("proposal_id", "proposal_id text"),
            ("decision_mode", "decision_mode text"),
            ("lineage_json", "lineage_json text"),
        ):
            if column_name not in columns:
                conn.execute(f"alter table promotion_requests add column {ddl}")

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

    def _load_skill_package(self, package_root: str | Path) -> Any:
        return load_skill_package(Path(package_root))

    def _infer_skill_type(self, package: Any) -> str:
        manifest_extra = dict(getattr(package.manifest, "model_extra", {}) or {})
        frontmatter_metadata = dict(getattr(package.skill_md.frontmatter, "metadata", {}) or {})
        explicit = frontmatter_metadata.get("type") or manifest_extra.get("type")
        if isinstance(explicit, str) and explicit.strip():
            normalized = explicit.strip().lower()
            if normalized in {"script", "agent", "ai_decision"}:
                return normalized

        action_kinds = {str(action.kind).split(".")[-1].lower() for action in package.actions.actions}
        if "subagent" in action_kinds:
            return "agent"
        if "mcp" in action_kinds and "script" not in action_kinds:
            return "agent"

        default_runtime_profile = str(getattr(package.manifest, "default_runtime_profile", "") or "").lower()
        if "ai" in default_runtime_profile:
            return "ai_decision"
        if "agent" in default_runtime_profile:
            return "agent"
        return "script"

    def _infer_parameter_schema(self, package: Any) -> dict[str, Any]:
        default_action_id = getattr(package.actions, "default_action", None) or (package.actions.actions[0].id if package.actions.actions else None)
        if not default_action_id:
            return {}
        default_action = next((action for action in package.actions.actions if action.id == default_action_id), None)
        if default_action is None:
            return {}
        return dict(default_action.input_schema or {})

    def _infer_default_action_id(self, package: Any) -> str | None:
        return getattr(package.actions, "default_action", None) or (package.actions.actions[0].id if package.actions.actions else None)

    def _unique_strings(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            normalized = str(value).strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(normalized)
        return ordered

    def _build_projection(self, skill_row: sqlite3.Row, version_row: sqlite3.Row) -> dict[str, Any]:
        package = self._load_skill_package(version_row["package_root"])
        frontmatter = package.skill_md.frontmatter
        manifest = package.manifest
        default_action_id = self._infer_default_action_id(package)
        parameter_schema = self._infer_parameter_schema(package)
        outer_description = str(frontmatter.description or "").strip()
        inner_description = "\n".join(
            part for part in [outer_description, package.skill_md.body.strip()] if part
        ).strip()
        tags = self._unique_strings(
            [
                *list(frontmatter.tags or []),
                *list(getattr(manifest, "target_platforms", []) or []),
            ]
        )
        owner = str(getattr(manifest, "owner", "") or frontmatter.owner or "").strip() or None
        risk_level = getattr(manifest, "risk_level", None) or frontmatter.metadata.get("risk_level")
        maturity_tier = str(getattr(manifest, "maturity_tier", "") or "").strip().lower()
        status = str(getattr(manifest, "status", "") or "").strip().lower()
        is_official = bool(owner) and maturity_tier in {"production", "governed"} and status == "active"
        metadata = {
            "status": getattr(manifest, "status", None),
            "maturity_tier": getattr(manifest, "maturity_tier", None),
            "lifecycle_stage": getattr(manifest, "lifecycle_stage", None),
            "default_runtime_profile": getattr(manifest, "default_runtime_profile", None),
            "action_count": len(package.actions.actions),
        }
        return {
            "skill_id": skill_row["skill_id"],
            "display_name": frontmatter.name or manifest.name,
            "type": self._infer_skill_type(package),
            "inner_description": inner_description,
            "outer_description": outer_description,
            "parameter_schema": parameter_schema,
            "default_action_id": default_action_id,
            "risk_level": risk_level,
            "tags": tags,
            "version_id": version_row["version_id"],
            "latest_version_id": skill_row["latest_version_id"],
            "owner": owner,
            "updated_at": skill_row["updated_at"],
            "is_official": is_official,
            "metadata": metadata,
        }

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

    def _promotion_submission_lineage(self, payload: dict[str, Any]) -> dict[str, Any]:
        metadata = _as_dict(payload.get("metadata"))
        lineage = _as_dict(payload.get("lineage")) or _as_dict(metadata.get("lineage"))
        resolved = {
            "case_id": str(lineage.get("case_id") or metadata.get("case_id") or "").strip(),
            "proposal_id": str(lineage.get("proposal_id") or metadata.get("proposal_id") or "").strip(),
            "decision_mode": str(lineage.get("decision_mode") or metadata.get("decision_mode") or "").strip(),
            "candidate_id": str(lineage.get("candidate_id") or metadata.get("candidate_id") or payload.get("candidate_id") or "").strip(),
            "candidate_slug": str(lineage.get("candidate_slug") or metadata.get("candidate_slug") or payload.get("candidate_slug") or "").strip(),
            "run_id": str(lineage.get("run_id") or payload.get("run_id") or "").strip(),
        }
        return {key: value for key, value in resolved.items() if value}

    def submit_promotion(self, submission: PromotionSubmission | dict[str, Any]) -> dict[str, Any]:
        normalized = submission if isinstance(submission, PromotionSubmission) else PromotionSubmission.from_dict(submission)
        payload = normalized.to_dict()
        lineage = self._promotion_submission_lineage(payload)
        payload["lineage"] = lineage
        metadata = _as_dict(payload.get("metadata"))
        metadata["lineage"] = lineage
        payload["metadata"] = metadata
        request_root = self.promotions_root / normalized.candidate_slug / normalized.run_id
        request_root.mkdir(parents=True, exist_ok=True)
        payload_path = request_root / "promotion_submission.json"
        payload_path.write_text(_json_dumps(payload) + "\n", encoding="utf-8")
        with self._connect() as conn:
            conn.execute(
                """
                insert into promotion_requests(candidate_id, candidate_slug, run_id, case_id, proposal_id, decision_mode, lineage_json, submission_json, state, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized.candidate_id,
                    normalized.candidate_slug,
                    normalized.run_id,
                    lineage.get("case_id"),
                    lineage.get("proposal_id"),
                    lineage.get("decision_mode"),
                    _json_dumps(lineage) if lineage else None,
                    _json_dumps(payload),
                    "PENDING_REVIEW",
                    normalized.submitted_at,
                ),
            )
        return {"ok": True, "state": "PENDING_REVIEW", "submission_path": str(payload_path), "submission": payload, "lineage": lineage}

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

    def get_skill_projection(self, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
        with self._connect() as conn:
            skill = conn.execute("select * from skills where skill_id = ?", (skill_id,)).fetchone()
            if not skill:
                raise KeyError(f"Unknown skill: {skill_id}")
            if version_id:
                version = conn.execute(
                    "select * from versions where skill_id = ? and version_id = ?",
                    (skill_id, version_id),
                ).fetchone()
            else:
                version = conn.execute(
                    "select * from versions where skill_id = ? and version_id = ?",
                    (skill_id, skill["latest_version_id"]),
                ).fetchone()
        if not version:
            raise KeyError(f"Unknown published version for skill {skill_id}")
        return self._build_projection(skill, version)

    def list_skill_projections(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "select skill_id, latest_version_id, updated_at from skills order by skill_id asc"
            ).fetchall()
        projections: list[dict[str, Any]] = []
        for row in rows:
            try:
                projections.append(self.get_skill_projection(row["skill_id"], version_id=row["latest_version_id"]))
            except KeyError:
                continue
        return projections

    def find_skill(self, request: dict[str, Any] | str) -> dict[str, Any]:
        from ..engine.service import EngineService

        return EngineService(self).find_skill(request).to_dict()

    def execute_skill(self, request: dict[str, Any] | str) -> dict[str, Any]:
        from ..engine.service import EngineService

        return EngineService(self).execute_skill(request).to_dict()

    def list_skills(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("select skill_id, slug, latest_version_id, updated_at from skills order by skill_id asc").fetchall()
        return [dict(row) for row in rows]
