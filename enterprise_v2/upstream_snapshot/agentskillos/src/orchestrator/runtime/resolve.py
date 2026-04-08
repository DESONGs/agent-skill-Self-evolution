"""Action resolution for runtime execution.

This module converts a hydrated skill package/install into a concrete action
selection that a runner can execute. It intentionally does not perform any
execution itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .actions import ActionContractError, ActionKind, ActionManifest, ActionSpec
from .install import LocalSkillPackage, RuntimeInstallBundle, SkillInstall, hydrate_skill_install


class ActionResolutionError(ValueError):
    """Raised when an action cannot be resolved safely."""


_SCRIPT_RUNTIME_ALLOWLIST = {"python3", "python", "bash", "sh", "node"}
_SANDBOX_ORDER = {
    "read-only": 0,
    "workspace-write": 1,
    "network-allowed": 2,
}


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _normalize_runtime(runtime: str | None) -> str:
    return (runtime or "").strip().lower()


def _extract_runner_config(spec: ActionSpec) -> dict[str, Any]:
    kind_key = spec.kind.value if hasattr(spec.kind, "value") else str(spec.kind)
    if kind_key == ActionKind.MCP.value and isinstance(spec.mcp, Mapping):
        return dict(spec.mcp)
    if kind_key == ActionKind.SUBAGENT.value and isinstance(spec.subagent, Mapping):
        return dict(spec.subagent)

    telemetry = spec.telemetry if isinstance(spec.telemetry, Mapping) else {}
    runner_config: Any = {}
    for key in (kind_key, "runner", "config"):
        candidate = telemetry.get(key) if isinstance(telemetry, Mapping) else None
        if isinstance(candidate, Mapping):
            runner_config = candidate
            break

    if not isinstance(runner_config, Mapping):
        runner_config = {}
    return dict(runner_config)


def _coerce_install_source(
    source: ActionManifest | RuntimeInstallBundle | SkillInstall | LocalSkillPackage | str | Path,
    *,
    install_root: str | Path | None = None,
    strict_actions: bool = False,
) -> SkillInstall:
    if isinstance(source, SkillInstall):
        return source
    if isinstance(source, LocalSkillPackage):
        root = Path(install_root or source.root.parent / ".runtime-installs")
        return hydrate_skill_install(source, install_root=root, strict_actions=strict_actions)
    if isinstance(source, RuntimeInstallBundle):
        package = LocalSkillPackage(
            root=source.bundle_root,
            skill_md=source.bundle_root / "SKILL.md",
            actions_path=source.bundle_root / "actions.yaml",
            bundle=source,
            manifest_path=source.bundle_root / "manifest.json" if (source.bundle_root / "manifest.json").exists() else None,
            files=tuple(sorted(p for p in source.bundle_root.rglob("*") if p.is_file())),
        )
        root = Path(install_root or source.bundle_root.parent / ".runtime-installs")
        return hydrate_skill_install(package, install_root=root, strict_actions=strict_actions)
    if isinstance(source, ActionManifest):
        source_path = source.source_path
        if source_path is None:
            raise TypeError(
                "ActionManifest sources require source_path or a packaged install for hydration"
            )
        package_root = source_path.parent
        package = LocalSkillPackage.from_root(package_root, strict_actions=strict_actions)
        root = Path(install_root or package.root.parent / ".runtime-installs")
        return hydrate_skill_install(package, install_root=root, strict_actions=strict_actions)
    if isinstance(source, (str, Path)):
        package = LocalSkillPackage.from_root(source, strict_actions=strict_actions)
        root = Path(install_root or package.root.parent / ".runtime-installs")
        return hydrate_skill_install(package, install_root=root, strict_actions=strict_actions)
    raise TypeError(f"Unsupported install source: {type(source)!r}")


@dataclass(frozen=True)
class ResolvedAction:
    """A validated, runnable action selection."""

    install_id: str
    skill_id: str
    version_id: str | None
    action_id: str
    kind: ActionKind
    runner_name: str
    entry: str | None
    runtime: str | None
    sandbox: str | None
    allow_network: bool
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    side_effects: tuple[str, ...] = ()
    idempotency: str = "best_effort"
    description: str = ""
    package_root: Path | None = None
    install_root: Path | None = None
    mounted_path: Path | None = None
    runner_config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    is_default: bool = False
    spec: ActionSpec | None = None

    @property
    def entry_path(self) -> Path | None:
        if not self.entry or self.package_root is None:
            return None
        return self.package_root / self.entry

    def to_dict(self) -> dict[str, Any]:
        return {
            "install_id": self.install_id,
            "skill_id": self.skill_id,
            "version_id": self.version_id,
            "action_id": self.action_id,
            "kind": self.kind.value,
            "runner_name": self.runner_name,
            "entry": self.entry,
            "runtime": self.runtime,
            "sandbox": self.sandbox,
            "allow_network": self.allow_network,
            "input_schema": dict(self.input_schema),
            "output_schema": dict(self.output_schema),
            "side_effects": list(self.side_effects),
            "idempotency": self.idempotency,
            "description": self.description,
            "package_root": str(self.package_root) if self.package_root else None,
            "install_root": str(self.install_root) if self.install_root else None,
            "mounted_path": str(self.mounted_path) if self.mounted_path else None,
            "runner_config": dict(self.runner_config),
            "metadata": dict(self.metadata),
            "is_default": self.is_default,
        }


class ActionResolver:
    """Resolve declared actions from an install into runnable selections."""

    def __init__(
        self,
        *,
        allow_script_runtimes: Iterable[str] | None = None,
        max_sandbox: str | None = None,
        allow_network: bool = True,
    ):
        self.allow_script_runtimes = {item.strip().lower() for item in (allow_script_runtimes or _SCRIPT_RUNTIME_ALLOWLIST)}
        self.max_sandbox = max_sandbox
        self.allow_network = allow_network

    def resolve(
        self,
        source: ActionManifest | RuntimeInstallBundle | SkillInstall | LocalSkillPackage | str | Path,
        action_id: str | None = None,
        *,
        install_root: str | Path | None = None,
        strict_actions: bool = False,
    ) -> ResolvedAction:
        install = _coerce_install_source(
            source,
            install_root=install_root,
            strict_actions=strict_actions,
        )
        return self.resolve_install(install, action_id=action_id)

    def resolve_install(
        self,
        install: SkillInstall,
        action_id: str | None = None,
    ) -> ResolvedAction:
        manifest = install.action_manifest
        candidate_id = action_id or install.selected_action or manifest.default_action
        if not candidate_id:
            raise ActionResolutionError(f"No default action available for install {install.install_id!r}")

        try:
            spec = install.resolve_action(candidate_id)
        except KeyError as exc:
            raise ActionResolutionError(
                f"Action {candidate_id!r} is not declared for install {install.install_id!r}"
            ) from exc

        self._validate_spec(spec, install)
        runner_name = self._runner_name(spec)
        runner_config = _extract_runner_config(spec)
        is_default = candidate_id == manifest.default_action

        return ResolvedAction(
            install_id=install.install_id,
            skill_id=install.package.bundle.skill_id,
            version_id=install.package.bundle.version_id,
            action_id=spec.id,
            kind=spec.kind,
            runner_name=runner_name,
            entry=spec.entry,
            runtime=spec.runtime,
            sandbox=spec.sandbox,
            allow_network=bool(spec.allow_network),
            input_schema=dict(spec.input_schema),
            output_schema=dict(spec.output_schema),
            side_effects=tuple(spec.side_effects),
            idempotency=spec.idempotency,
            description=spec.description,
            package_root=install.mounted_path,
            install_root=install.install_root,
            mounted_path=install.mounted_path,
            runner_config=runner_config,
            metadata=dict(install.metadata),
            is_default=is_default,
            spec=spec,
        )

    def catalog(
        self,
        source: ActionManifest | RuntimeInstallBundle | SkillInstall | LocalSkillPackage | str | Path,
        *,
        install_root: str | Path | None = None,
        strict_actions: bool = False,
    ) -> tuple[ResolvedAction, ...]:
        install = _coerce_install_source(
            source,
            install_root=install_root,
            strict_actions=strict_actions,
        )
        manifest = install.action_manifest
        return tuple(self.resolve_install(install, action_id=spec.id) for spec in manifest.actions)

    def _validate_spec(self, spec: ActionSpec, install: SkillInstall) -> None:
        if not spec.id:
            raise ActionResolutionError("Action id must be non-empty")

        if spec.kind == ActionKind.SCRIPT:
            if not spec.entry:
                raise ActionResolutionError(f"Script action {spec.id!r} requires an entry path")
            runtime = _normalize_runtime(spec.runtime)
            if runtime not in self.allow_script_runtimes:
                raise ActionResolutionError(
                    f"Unsupported script runtime {spec.runtime!r}; allowed: {sorted(self.allow_script_runtimes)}"
                )
        elif spec.kind == ActionKind.MCP:
            self._require_runner_config(spec, ("server", "tool", "method"))
        elif spec.kind == ActionKind.SUBAGENT:
            self._require_runner_config(spec, ("model", "allowed_tools", "system_prompt"))
        elif spec.kind == ActionKind.INSTRUCTION:
            pass
        else:  # pragma: no cover - ActionKind currently exhausts all cases
            raise ActionResolutionError(f"Unsupported action kind: {spec.kind!r}")

        if spec.entry:
            entry_path = Path(spec.entry)
            if entry_path.is_absolute():
                raise ActionResolutionError(f"Action {spec.id!r} entry must be relative")
            if ".." in entry_path.parts:
                raise ActionResolutionError(f"Action {spec.id!r} entry may not escape the package root")
            package_root = install.mounted_path
            if package_root is not None and not (package_root / entry_path).exists():
                raise ActionResolutionError(
                    f"Action {spec.id!r} entry does not exist inside install root: {spec.entry!r}"
                )

        if self.max_sandbox is not None:
            requested = _SANDBOX_ORDER.get(spec.sandbox or "read-only", 0)
            allowed = _SANDBOX_ORDER.get(self.max_sandbox, 0)
            if requested > allowed:
                raise ActionResolutionError(
                    f"Action {spec.id!r} requires sandbox {spec.sandbox!r}, "
                    f"which exceeds resolver limit {self.max_sandbox!r}"
                )

        if spec.allow_network and not self.allow_network:
            raise ActionResolutionError(
                f"Action {spec.id!r} requires network access but resolver policy forbids it"
            )

    def _require_runner_config(self, spec: ActionSpec, required_keys: tuple[str, ...]) -> dict[str, Any]:
        config = _extract_runner_config(spec)
        missing = [key for key in required_keys if not config.get(key)]
        if missing:
            raise ActionResolutionError(
                f"Action {spec.id!r} is missing required runner config keys: {missing}"
            )
        return config

    def _runner_name(self, spec: ActionSpec) -> str:
        return spec.kind.value
