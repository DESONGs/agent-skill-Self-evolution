from __future__ import annotations

import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.runtime.envelope import RunFeedbackEnvelope

from ..contracts import build_source_bundle, load_skill_package, validate_skill_package
from ..engine.models import SkillProjection
from ..models import PromotionSubmission, _as_dict
from ..storage.object_store.client import ObjectStoreClient
from ..storage.repositories.registry_repository import RegistryRepository


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EnterpriseRegistryService:
    def __init__(self, repository: RegistryRepository, object_store: ObjectStoreClient):
        self.repository = repository
        self.object_store = object_store

    def _extract_bundle(self, bundle_path: Path) -> Path:
        tmp_root = Path(tempfile.mkdtemp(prefix="asp-enterprise-publish-"))
        with zipfile.ZipFile(bundle_path) as archive:
            archive.extractall(tmp_root)
        roots = [path for path in tmp_root.iterdir() if path.is_dir()]
        if len(roots) != 1:
            raise ValueError("bundle archive must contain exactly one root directory")
        return roots[0]

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

    def _build_projection(self, package: Any) -> SkillProjection:
        frontmatter = package.skill_md.frontmatter
        manifest = package.manifest
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
        return SkillProjection(
            skill_id=manifest.name,
            display_name=frontmatter.name or manifest.name,
            skill_type=self._infer_skill_type(package),
            inner_description=inner_description,
            outer_description=outer_description,
            parameter_schema=self._infer_parameter_schema(package),
            default_action_id=self._infer_default_action_id(package),
            risk_level=risk_level,
            tags=tuple(tags),
            version_id=manifest.version,
            latest_version_id=manifest.version,
            owner=owner,
            updated_at=_utc_now(),
            is_official=is_official,
            metadata=metadata,
        )

    def publish_package(self, source: str | Path) -> dict[str, Any]:
        source_path = Path(source).resolve()
        temp_root: Path | None = None
        package_root = source_path
        if source_path.is_file() and source_path.suffix.lower() == ".zip":
            temp_root = self._extract_bundle(source_path)
            package_root = temp_root
        elif not source_path.is_dir():
            raise ValueError(f"Unsupported publish source: {source_path}")

        report = validate_skill_package(package_root)
        if not report.ok:
            raise ValueError(str(report))
        package = load_skill_package(package_root)
        slug = package.manifest.name
        version = package.manifest.version
        bundle_output_dir = Path(tempfile.mkdtemp(prefix="asp-enterprise-bundle-"))
        bundle_artifact = build_source_bundle(package_root, bundle_output_dir)
        package_key = f"packages/{slug}/{version}/{bundle_artifact.path.name}"
        bundle_key = f"bundles/{slug}/{version}/{bundle_artifact.path.name}"
        bundle_size = bundle_artifact.path.stat().st_size
        package_uri = self.object_store.upload_file(bundle_artifact.path, package_key, content_type="application/zip")
        bundle_uri = self.object_store.upload_file(bundle_artifact.path, bundle_key, content_type="application/zip")
        projection = self._build_projection(package)
        created_at = _utc_now()
        self.repository.upsert_skill(
            skill_id=slug,
            slug=slug,
            version_id=version,
            created_at=created_at,
            package_object_key=package_key,
            bundle_object_key=bundle_key,
            bundle_sha256=bundle_artifact.sha256,
            bundle_size=bundle_size,
            manifest_json=package.manifest.model_dump(mode="json"),
            projection=projection,
        )
        shutil.rmtree(bundle_output_dir, ignore_errors=True)
        if temp_root is not None:
            shutil.rmtree(temp_root.parent, ignore_errors=True)
        return {
            "ok": True,
            "skill_id": slug,
            "version_id": version,
            "package_root": package_uri,
            "bundle_path": bundle_uri,
            "bundle_sha256": bundle_artifact.sha256,
            "bundle_size": bundle_size,
            "install_bundle": self.resolve_install_bundle(slug, version_id=version),
        }

    def resolve_install_bundle(self, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
        version_payload = self.repository.get_version_payload(skill_id, version_id=version_id)
        projection = self.repository.get_skill_projection(skill_id, version_id=version_payload["version_id"])
        return {
            "skill_id": version_payload["skill_id"],
            "version_id": version_payload["version_id"],
            "bundle_root": self.object_store.uri_for(version_payload["package_object_key"]),
            "bundle_path": self.object_store.uri_for(version_payload["bundle_object_key"]),
            "bundle_sha256": version_payload["bundle_sha256"],
            "bundle_size": version_payload["bundle_size"],
            "skill_type": projection["type"],
            "default_action": projection["default_action_id"],
            "source_uri": self.object_store.uri_for(version_payload["package_object_key"]),
            "actions": {"default_action": projection["default_action_id"]},
            "metadata": {
                "storage_backend": "s3",
                "package_object_key": version_payload["package_object_key"],
                "bundle_object_key": version_payload["bundle_object_key"],
            },
        }

    def ingest_feedback(self, envelope: RunFeedbackEnvelope | dict[str, Any]) -> dict[str, Any]:
        normalized = envelope if isinstance(envelope, RunFeedbackEnvelope) else RunFeedbackEnvelope.from_dict(envelope)
        payload = normalized.to_dict()
        event_key = f"feedback/{normalized.skill_id}/{normalized.run_id}.json"
        event_ref = self.object_store.upload_json(payload, event_key)
        self.repository.record_feedback(payload, event_ref)
        return {"ok": True, "event_path": event_ref, "feedback": payload}

    def submit_promotion(self, submission: PromotionSubmission | dict[str, Any]) -> dict[str, Any]:
        normalized = submission if isinstance(submission, PromotionSubmission) else PromotionSubmission.from_dict(submission)
        payload = normalized.to_dict()
        lineage = _as_dict(payload.get("lineage"))
        request_key = f"promotions/{normalized.candidate_slug}/{normalized.run_id}/promotion_submission.json"
        request_ref = self.object_store.upload_json(payload, request_key)
        self.repository.record_promotion(payload, request_ref, state="PENDING_REVIEW")
        return {
            "ok": True,
            "state": "PENDING_REVIEW",
            "submission_path": request_ref,
            "submission": payload,
            "lineage": lineage,
        }

    def list_skills(self) -> list[dict[str, Any]]:
        return self.repository.list_skills()

    def get_skill(self, skill_id: str) -> dict[str, Any]:
        return self.repository.get_skill(skill_id)

    def get_skill_projection(self, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
        return self.repository.get_skill_projection(skill_id, version_id=version_id)

    def list_skill_projections(self) -> list[dict[str, Any]]:
        return self.repository.list_skill_projections()
