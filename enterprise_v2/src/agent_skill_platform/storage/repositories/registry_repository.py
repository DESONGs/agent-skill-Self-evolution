from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from ...engine.models import SkillProjection
from ..postgres.models import (
    FeedbackEventRecord,
    PromotionRequestRecord,
    SkillProjectionRecord,
    SkillRecord,
    SkillVersionRecord,
)
from ..postgres.session import session_scope


class RegistryRepository:
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def upsert_skill(
        self,
        *,
        skill_id: str,
        slug: str,
        version_id: str,
        created_at: str,
        package_object_key: str,
        bundle_object_key: str,
        bundle_sha256: str,
        bundle_size: int,
        manifest_json: dict[str, Any],
        projection: SkillProjection,
    ) -> None:
        with session_scope(self.session_factory) as session:
            skill = session.get(SkillRecord, skill_id)
            if skill is None:
                skill = SkillRecord(
                    skill_id=skill_id,
                    slug=slug,
                    latest_version_id=version_id,
                    created_at=created_at,
                    updated_at=created_at,
                )
                session.add(skill)
            else:
                skill.slug = slug
                skill.latest_version_id = version_id
                skill.updated_at = projection.updated_at or created_at
            session.flush()

            version = session.get(SkillVersionRecord, version_id)
            if version is None:
                version = SkillVersionRecord(
                    version_id=version_id,
                    skill_id=skill_id,
                    slug=slug,
                    package_object_key=package_object_key,
                    bundle_object_key=bundle_object_key,
                    bundle_sha256=bundle_sha256,
                    bundle_size=bundle_size,
                    manifest_json=manifest_json,
                    created_at=created_at,
                )
                session.add(version)
            else:
                version.package_object_key = package_object_key
                version.bundle_object_key = bundle_object_key
                version.bundle_sha256 = bundle_sha256
                version.bundle_size = bundle_size
                version.manifest_json = manifest_json
            session.flush()

            existing_projection = session.scalar(
                select(SkillProjectionRecord).where(SkillProjectionRecord.version_id == version_id)
            )
            payload = projection.to_dict()
            if existing_projection is None:
                existing_projection = SkillProjectionRecord(
                    skill_id=skill_id,
                    version_id=version_id,
                    display_name=payload["display_name"],
                    skill_type=payload["type"],
                    inner_description=payload["inner_description"],
                    outer_description=payload["outer_description"],
                    parameter_schema=payload["parameter_schema"],
                    default_action_id=payload["default_action_id"],
                    risk_level=payload["risk_level"],
                    tags=payload["tags"],
                    owner=payload["owner"],
                    updated_at=payload["updated_at"],
                    is_official=payload["is_official"],
                    metadata_json=payload["metadata"],
                )
                session.add(existing_projection)
            else:
                existing_projection.display_name = payload["display_name"]
                existing_projection.skill_type = payload["type"]
                existing_projection.inner_description = payload["inner_description"]
                existing_projection.outer_description = payload["outer_description"]
                existing_projection.parameter_schema = payload["parameter_schema"]
                existing_projection.default_action_id = payload["default_action_id"]
                existing_projection.risk_level = payload["risk_level"]
                existing_projection.tags = payload["tags"]
                existing_projection.owner = payload["owner"]
                existing_projection.updated_at = payload["updated_at"]
                existing_projection.is_official = payload["is_official"]
                existing_projection.metadata_json = payload["metadata"]

    def list_skills(self) -> list[dict[str, Any]]:
        with session_scope(self.session_factory) as session:
            rows = session.scalars(select(SkillRecord).order_by(SkillRecord.skill_id.asc())).all()
            return [
                {
                    "skill_id": row.skill_id,
                    "slug": row.slug,
                    "latest_version_id": row.latest_version_id,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]

    def get_skill(self, skill_id: str) -> dict[str, Any]:
        with session_scope(self.session_factory) as session:
            skill = session.get(SkillRecord, skill_id)
            if skill is None:
                raise KeyError(f"Unknown skill: {skill_id}")
            versions = session.scalars(
                select(SkillVersionRecord)
                .where(SkillVersionRecord.skill_id == skill_id)
                .order_by(SkillVersionRecord.created_at.desc())
            ).all()
            return {
                "skill_id": skill.skill_id,
                "slug": skill.slug,
                "latest_version_id": skill.latest_version_id,
                "versions": [
                    {
                        "version_id": row.version_id,
                        "bundle_path": row.bundle_object_key,
                        "bundle_sha256": row.bundle_sha256,
                        "bundle_size": row.bundle_size,
                        "created_at": row.created_at,
                    }
                    for row in versions
                ],
            }

    def _projection_to_dict(self, row: SkillProjectionRecord, latest_version_id: str | None) -> dict[str, Any]:
        return {
            "skill_id": row.skill_id,
            "display_name": row.display_name,
            "type": row.skill_type,
            "inner_description": row.inner_description,
            "outer_description": row.outer_description,
            "parameter_schema": dict(row.parameter_schema or {}),
            "default_action_id": row.default_action_id,
            "risk_level": row.risk_level,
            "tags": list(row.tags or []),
            "version_id": row.version_id,
            "latest_version_id": latest_version_id,
            "owner": row.owner,
            "updated_at": row.updated_at,
            "is_official": bool(row.is_official),
            "metadata": dict(row.metadata_json or {}),
        }

    def get_skill_projection(self, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
        with session_scope(self.session_factory) as session:
            skill = session.get(SkillRecord, skill_id)
            if skill is None:
                raise KeyError(f"Unknown skill: {skill_id}")
            resolved_version_id = version_id or skill.latest_version_id
            if not resolved_version_id:
                raise KeyError(f"Skill {skill_id!r} has no published version")
            row = session.scalar(
                select(SkillProjectionRecord).where(
                    SkillProjectionRecord.skill_id == skill_id,
                    SkillProjectionRecord.version_id == resolved_version_id,
                )
            )
            if row is None:
                raise KeyError(f"Unknown published version for skill {skill_id}")
            return self._projection_to_dict(row, skill.latest_version_id)

    def list_skill_projections(self) -> list[dict[str, Any]]:
        with session_scope(self.session_factory) as session:
            rows = session.scalars(select(SkillProjectionRecord).order_by(SkillProjectionRecord.skill_id.asc())).all()
            latest_by_skill = {
                row.skill_id: row.latest_version_id
                for row in session.scalars(select(SkillRecord)).all()
            }
            return [self._projection_to_dict(row, latest_by_skill.get(row.skill_id)) for row in rows]

    def get_version_payload(self, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
        with session_scope(self.session_factory) as session:
            skill = session.get(SkillRecord, skill_id)
            if skill is None:
                raise KeyError(f"Unknown skill: {skill_id}")
            resolved_version_id = version_id or skill.latest_version_id
            if not resolved_version_id:
                raise KeyError(f"Skill {skill_id!r} has no published version")
            row = session.get(SkillVersionRecord, resolved_version_id)
            if row is None or row.skill_id != skill_id:
                raise KeyError(f"Unknown published version for skill {skill_id}")
            return {
                "skill_id": row.skill_id,
                "version_id": row.version_id,
                "package_object_key": row.package_object_key,
                "bundle_object_key": row.bundle_object_key,
                "bundle_sha256": row.bundle_sha256,
                "bundle_size": row.bundle_size,
                "manifest": dict(row.manifest_json or {}),
                "created_at": row.created_at,
            }

    def record_feedback(self, payload: dict[str, Any], event_ref: str | None) -> None:
        with session_scope(self.session_factory) as session:
            session.add(
                FeedbackEventRecord(
                    run_id=str(payload.get("run_id", "")),
                    skill_id=str(payload.get("skill_id", "")),
                    version_id=payload.get("version_id"),
                    action_id=str(payload.get("action_id", "")),
                    payload_json=payload,
                    event_ref=event_ref,
                    created_at=str(payload.get("created_at", "")),
                )
            )

    def record_promotion(self, payload: dict[str, Any], submission_ref: str | None, state: str) -> None:
        lineage = dict(payload.get("lineage") or {})
        with session_scope(self.session_factory) as session:
            session.add(
                PromotionRequestRecord(
                    candidate_id=str(payload.get("candidate_id", "")),
                    candidate_slug=str(payload.get("candidate_slug", "")),
                    run_id=str(payload.get("run_id", "")),
                    case_id=lineage.get("case_id"),
                    proposal_id=lineage.get("proposal_id"),
                    decision_mode=lineage.get("decision_mode"),
                    lineage_json=lineage,
                    submission_json=payload,
                    submission_ref=submission_ref,
                    state=state,
                    created_at=str(payload.get("submitted_at", "")),
                )
            )
