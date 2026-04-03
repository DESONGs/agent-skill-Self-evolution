from __future__ import annotations

from pathlib import Path
from typing import Any

from .bootstrap import ensure_vendor_paths


def build_runtime_install_bundle(
    package_root: str | Path,
    *,
    skill_id: str | None = None,
    version_id: str | None = None,
    strict_actions: bool = True,
) -> Any:
    ensure_vendor_paths()
    from orchestrator.runtime.install import RuntimeInstallBundle

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
    ensure_vendor_paths()
    from orchestrator.runtime.install import hydrate_skill_install

    return hydrate_skill_install(
        Path(package_root),
        install_root=Path(install_root),
        install_id=install_id,
        strict_actions=strict_actions,
        copy_tree=copy_tree,
    )


def feedback_from_dict(payload: dict[str, Any]) -> Any:
    ensure_vendor_paths()
    from orchestrator.runtime.envelope import RunFeedbackEnvelope

    return RunFeedbackEnvelope.from_dict(payload)


def feedback_to_dict(envelope: Any) -> dict[str, Any]:
    if hasattr(envelope, "to_dict"):
        return envelope.to_dict()
    return dict(envelope)
