from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path
from typing import Any, Mapping

from ..bootstrap import ensure_source_layout

ensure_source_layout()

from orchestrator.runtime.envelope import RunFeedbackEnvelope
from orchestrator.runtime.execution import scan_workspace_artifacts
from orchestrator.runtime.feedback import RunFeedbackReporter
from orchestrator.runtime.install import RuntimeInstallBundle, hydrate_skill_install
from orchestrator.runtime.resolve import ActionResolver
from orchestrator.runtime.runners import RunnerRegistry


def build_runtime_install_bundle(
    package_root: str | Path,
    *,
    skill_id: str | None = None,
    version_id: str | None = None,
    strict_actions: bool = True,
) -> RuntimeInstallBundle:
    return RuntimeInstallBundle.from_package_root(
        Path(package_root),
        skill_id=skill_id,
        version_id=version_id,
        strict_actions=strict_actions,
    )


def hydrate_runtime_install(
    package_root: str | Path,
    *,
    install_root: str | Path,
    install_id: str | None = None,
    strict_actions: bool = True,
    copy_tree: bool = True,
) -> Any:
    return hydrate_skill_install(
        Path(package_root),
        install_root=Path(install_root),
        install_id=install_id,
        strict_actions=strict_actions,
        copy_tree=copy_tree,
    )


def feedback_from_dict(payload: dict[str, Any]) -> RunFeedbackEnvelope:
    return RunFeedbackEnvelope.from_dict(payload)


def report_feedback(envelope: RunFeedbackEnvelope, *, feedback_endpoint: str = "", auth_token: str = "") -> RunFeedbackEnvelope:
    reporter = RunFeedbackReporter(feedback_endpoint=feedback_endpoint, auth_token=auth_token)
    return reporter.report(envelope)


def run_runtime(
    package_root: str | Path,
    *,
    action_id: str | None = None,
    action_input: Any = None,
    workspace_dir: str | Path | None = None,
    run_id: str | None = None,
    install_root: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    max_sandbox: str | None = None,
    allow_network: bool = False,
) -> dict[str, Any]:
    package_path = Path(package_root).resolve()
    resolved_run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"

    with tempfile.TemporaryDirectory(prefix="asp-runtime-") as tempdir:
        install_base = Path(install_root or tempdir)
        install = hydrate_skill_install(
            package_path,
            install_root=install_base,
            strict_actions=True,
            copy_tree=True,
        )
        resolver = ActionResolver(max_sandbox=max_sandbox, allow_network=allow_network)
        resolved_action = resolver.resolve_install(install, action_id=action_id)
        workspace_path = Path(workspace_dir).resolve() if workspace_dir is not None else install.mounted_path
        runner_registry = RunnerRegistry()
        result = asyncio.run(
            runner_registry.run(
                resolved_action,
                action_input,
                workspace_dir=workspace_path,
                env=env,
            )
        )
        artifacts = list(result.artifacts)
        if workspace_path is not None:
            artifacts.extend(scan_workspace_artifacts(workspace_path, producer=resolved_action.action_id, role="workspace"))
        feedback = RunFeedbackEnvelope.from_action_result(
            run_id=resolved_run_id,
            mode="direct",
            layer_source="active",
            resolved_action=resolved_action,
            result=result,
            metadata={"workspace_dir": str(workspace_path) if workspace_path else None},
        )
        return {
            "run_id": resolved_run_id,
            "resolved_action": resolved_action.to_dict(),
            "result": result.to_dict(),
            "artifacts": [artifact.to_dict() for artifact in artifacts],
            "feedback": feedback.to_dict(),
        }


__all__ = [
    "RuntimeInstallBundle",
    "RunFeedbackEnvelope",
    "build_runtime_install_bundle",
    "feedback_from_dict",
    "hydrate_runtime_install",
    "report_feedback",
    "run_runtime",
]
