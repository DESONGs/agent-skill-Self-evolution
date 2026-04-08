"""Run feedback envelopes and reporter utilities."""

from __future__ import annotations

import json
import os
import threading
import time
from contextlib import suppress
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .envelope import RunFeedbackEnvelope


def _json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _json_read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _slugify(value: str, *, fallback: str) -> str:
    normalized = "".join(ch if ch.isalnum() else "-" for ch in value.strip().lower())
    normalized = "-".join(part for part in normalized.split("-") if part)
    return normalized or fallback


class RunFeedbackReporter:
    """Persist runtime feedback locally and optionally dispatch it."""

    def __init__(
        self,
        output_dir: str | Path,
        *,
        feedback_endpoint: str | None = None,
        feedback_auth_token_env: str | None = None,
        timeout_sec: float = 5.0,
        max_retries: int = 0,
        registry_endpoint: str | None = None,
        send_callable: Callable[[RunFeedbackEnvelope], Any] | None = None,
        async_send: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.feedback_endpoint = (feedback_endpoint or registry_endpoint or "").strip()
        self.feedback_auth_token_env = (feedback_auth_token_env or "").strip()
        self.timeout_sec = float(timeout_sec)
        self.max_retries = max(0, int(max_retries))
        self.send_callable = send_callable
        self.async_send = async_send
        self._threads: list[threading.Thread] = []
        self.last_feedback_path: Path | None = None
        self.last_outbox_path: Path | None = None
        self.last_send_error: str | None = None

    @property
    def outbox_dir(self) -> Path:
        return self.output_dir / "feedback_outbox"

    def report(self, envelope: RunFeedbackEnvelope) -> RunFeedbackEnvelope:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)

        feedback_path = self.output_dir / "feedback.json"
        outbox_path = self.outbox_dir / self._build_outbox_name(envelope)

        payload = envelope.to_dict()
        self._append_feedback(feedback_path, envelope)
        _json_write(outbox_path, payload)

        self.last_feedback_path = feedback_path
        self.last_outbox_path = outbox_path

        if self._delivery_enabled:
            if self.async_send:
                thread = threading.Thread(
                    target=self._attempt_send,
                    args=(envelope, outbox_path),
                    daemon=True,
                )
                thread.start()
                self._threads.append(thread)
            else:
                self._attempt_send(envelope, outbox_path)

        return envelope

    def wait_for_pending_sends(self, timeout: float | None = None) -> str:
        for thread in list(self._threads):
            thread.join(timeout=timeout)
        self._threads = [thread for thread in self._threads if thread.is_alive()]
        return self.delivery_status()

    def delivery_status(self) -> str:
        if self.last_feedback_path is None or not self.last_feedback_path.exists():
            return "not_applicable"
        if not self._delivery_enabled:
            return "persisted"
        if self._has_pending_outbox():
            return "queued"
        return "delivered"

    def _attempt_send(self, envelope: RunFeedbackEnvelope, outbox_path: Path) -> None:
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                success = self._send(envelope)
            except Exception as exc:  # pragma: no cover - defensive against sender bugs
                success = False
                self.last_send_error = str(exc)
            else:
                self.last_send_error = None if success else self.last_send_error

            if success:
                with suppress(FileNotFoundError):
                    outbox_path.unlink()
                self.last_send_error = None
                return

            if attempt + 1 < attempts:
                time.sleep(0.05)

    @property
    def _delivery_enabled(self) -> bool:
        return bool(self.feedback_endpoint or self.send_callable is not None)

    def _build_outbox_name(self, envelope: RunFeedbackEnvelope) -> str:
        timestamp = time.time_ns()
        skill_id = _slugify(envelope.skill_id, fallback="skill")
        action_id = _slugify(envelope.action_id, fallback="action")
        return f"{timestamp}-{skill_id}-{action_id}.json"

    def _append_feedback(self, feedback_path: Path, envelope: RunFeedbackEnvelope) -> None:
        payload = _json_read(feedback_path)
        items = payload.get("items")
        if not isinstance(items, list):
            items = []
        items.append(envelope.to_dict())
        _json_write(
            feedback_path,
            {
                "run_id": envelope.run_id,
                "items": items,
            },
        )

    def _has_pending_outbox(self) -> bool:
        if not self.outbox_dir.exists():
            return False
        return any(path.suffix == ".json" for path in self.outbox_dir.iterdir() if path.is_file())

    def _send(self, envelope: RunFeedbackEnvelope) -> bool:
        if self.send_callable is not None:
            delivered = self.send_callable(envelope)
            return bool(True if delivered is None else delivered)
        if not self.feedback_endpoint:
            return False

        body = json.dumps(envelope.to_dict()).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        auth_token = self._resolve_auth_token()
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        request = Request(
            self.feedback_endpoint,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_sec) as response:
                status = getattr(response, "status", None) or response.getcode()
        except HTTPError as exc:
            self.last_send_error = f"{exc.code} {exc.reason}"
            return False
        except URLError as exc:
            self.last_send_error = str(exc.reason)
            return False

        if 200 <= int(status) < 300:
            return True

        self.last_send_error = f"HTTP {status}"
        return False

    def _resolve_auth_token(self) -> str | None:
        if not self.feedback_auth_token_env:
            return None
        token = os.environ.get(self.feedback_auth_token_env, "").strip()
        return token or None
