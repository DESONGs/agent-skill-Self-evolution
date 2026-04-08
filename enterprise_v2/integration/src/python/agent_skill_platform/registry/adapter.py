from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from orchestrator.runtime.envelope import RunFeedbackEnvelope

from ..models import PromotionSubmission
from .service import LocalDevRegistryService


def _json_dumps(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


class RemoteRegistryService:
    def __init__(self, base_url: str, *, timeout_sec: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = float(timeout_sec)

    def _request(self, method: str, path: str, payload: Any | None = None) -> Any:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method.upper())
        with urlopen(request, timeout=self.timeout_sec) as response:
            body = response.read().decode("utf-8")
        return json.loads(body) if body else None

    def publish_package(self, source: str | Path) -> dict[str, Any]:
        return dict(self._request("POST", "/publish", {"source": str(Path(source).resolve())}))

    def resolve_install_bundle(self, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
        query = urlencode({"version_id": version_id}) if version_id else ""
        suffix = f"?{query}" if query else ""
        return dict(self._request("GET", f"/skills/{skill_id}/install-bundle{suffix}"))

    def ingest_feedback(self, envelope: RunFeedbackEnvelope | dict[str, Any]) -> dict[str, Any]:
        payload = envelope.to_dict() if isinstance(envelope, RunFeedbackEnvelope) else dict(envelope)
        return dict(self._request("POST", "/feedback", payload))

    def submit_promotion(self, submission: PromotionSubmission | dict[str, Any]) -> dict[str, Any]:
        payload = submission.to_dict() if isinstance(submission, PromotionSubmission) else dict(submission)
        return dict(self._request("POST", "/promotions", payload))

    def list_skills(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/skills")
        return list(payload or [])

    def get_skill(self, skill_id: str) -> dict[str, Any]:
        return dict(self._request("GET", f"/skills/{skill_id}"))

    def get_skill_projection(self, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
        query = urlencode({"version_id": version_id}) if version_id else ""
        suffix = f"?{query}" if query else ""
        return dict(self._request("GET", f"/skills/{skill_id}/projection{suffix}"))

    def list_skill_projections(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/skills/projections")
        return list(payload or [])

    def find_skill(self, request: dict[str, Any]) -> dict[str, Any]:
        return dict(self._request("POST", "/find-skill", request))

    def execute_skill(self, request: dict[str, Any]) -> dict[str, Any]:
        return dict(self._request("POST", "/execute-skill", request))


class RegistryAdapter:
    def __init__(
        self,
        root: str | Path | None = None,
        *,
        base_url: str | None = None,
        mode: str | None = None,
        timeout_sec: float = 10.0,
    ):
        resolved_mode = (mode or os.environ.get("AGENT_SKILL_PLATFORM_REGISTRY_MODE", "")).strip().lower()
        resolved_url = (base_url or os.environ.get("AGENT_SKILL_PLATFORM_REGISTRY_URL", "")).strip()
        if not resolved_mode:
            resolved_mode = "service"
        if resolved_mode == "service" and not resolved_url:
            resolved_url = "http://localhost:8080"
        self.mode = resolved_mode
        self.root = Path(root).resolve() if root is not None else None
        self.base_url = resolved_url or None
        if self.mode == "service":
            if not self.base_url:
                raise ValueError("registry mode 'service' requires AGENT_SKILL_PLATFORM_REGISTRY_URL or base_url")
            self.backend = RemoteRegistryService(self.base_url, timeout_sec=timeout_sec)
        elif self.mode in {"local_dev", "stub"}:
            if self.root is None:
                raise ValueError("registry mode 'local_dev' requires a registry root path")
            self.backend = LocalDevRegistryService(self.root)
            self.mode = "local_dev"
        else:
            raise ValueError(f"Unsupported registry mode: {self.mode}")

    def publish_package(self, source: str | Path) -> dict[str, Any]:
        return self.backend.publish_package(source)

    def resolve_install_bundle(self, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
        return self.backend.resolve_install_bundle(skill_id, version_id=version_id)

    def ingest_feedback(self, envelope: RunFeedbackEnvelope | dict[str, Any]) -> dict[str, Any]:
        return self.backend.ingest_feedback(envelope)

    def submit_promotion(self, submission: PromotionSubmission | dict[str, Any]) -> dict[str, Any]:
        return self.backend.submit_promotion(submission)

    def list_skills(self) -> list[dict[str, Any]]:
        return self.backend.list_skills()

    def get_skill(self, skill_id: str) -> dict[str, Any]:
        return self.backend.get_skill(skill_id)

    def get_skill_projection(self, skill_id: str, version_id: str | None = None) -> dict[str, Any]:
        return self.backend.get_skill_projection(skill_id, version_id=version_id)

    def list_skill_projections(self) -> list[dict[str, Any]]:
        return self.backend.list_skill_projections()

    def find_skill(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.backend.find_skill(request)

    def execute_skill(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.backend.execute_skill(request)
