from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import yaml

SCHEMA_VERSION = "actions.v1"

VALID_ACTION_KINDS = {"script", "mcp", "instruction", "subagent"}
VALID_SCRIPT_RUNTIMES = {"python3", "python", "bash", "node", "sh"}
VALID_SANDBOXES = {"read-only", "workspace-write", "network-allowed"}
VALID_EXECUTION_CONTEXTS = {"inline", "fork"}
VALID_SHELLS = {"bash", "powershell"}
VALID_SOURCE_TIERS = {"local", "managed", "plugin", "remote"}
VALID_STATUS = {"experimental", "active", "deprecated"}
VALID_MATURITY = {"scaffold", "production", "library", "governed"}
VALID_REVIEW_CADENCE = {"monthly", "quarterly", "semiannual", "annual", "per-release"}
VALID_RUNTIME_EXCLUDES = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "tests",
    "reports",
}
VALID_BUNDLE_EXCLUDES = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: str = ""

    def to_dict(self) -> dict[str, str]:
        payload = {"code": self.code, "message": self.message}
        if self.path:
            payload["path"] = self.path
        return payload


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    failures: tuple[ValidationIssue, ...] = ()
    warnings: tuple[ValidationIssue, ...] = ()

    def raise_for_failures(self) -> None:
        if self.ok:
            return
        joined = "; ".join(issue.message for issue in self.failures)
        raise ContractValidationError(joined, report=self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "failures": [issue.to_dict() for issue in self.failures],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


class ContractError(RuntimeError):
    pass


class ContractLoadError(ContractError):
    pass


class ContractValidationError(ContractError):
    def __init__(self, message: str, report: ValidationReport | None = None):
        super().__init__(message)
        self.report = report


@dataclass(frozen=True)
class SkillPackage:
    root: Path
    skill_md_path: Path
    frontmatter: dict[str, Any]
    skill_body: str
    manifest: dict[str, Any]
    actions: dict[str, Any]
    interface: dict[str, Any]

    @property
    def slug(self) -> str:
        return str(self.frontmatter.get("name", self.root.name))

    @property
    def description(self) -> str:
        return str(self.frontmatter.get("description", ""))

    @property
    def version(self) -> str:
        value = self.manifest.get("version") or self.frontmatter.get("version") or "1.0.0"
        return str(value)

    @property
    def adapter_targets(self) -> tuple[str, ...]:
        compatibility = self.interface.get("compatibility", {})
        targets = compatibility.get("adapter_targets", [])
        if not isinstance(targets, list):
            return ()
        return tuple(str(item) for item in targets)

    @property
    def portable_semantics(self) -> dict[str, Any]:
        compatibility = self.interface.get("compatibility", {})
        activation = compatibility.get("activation", {})
        execution = compatibility.get("execution", {})
        trust = compatibility.get("trust", {})
        degradation = compatibility.get("degradation", {})
        return {
            "activation": {
                "mode": activation.get("mode", ""),
                "paths": list(activation.get("paths", [])),
            },
            "execution": {
                "context": execution.get("context", ""),
                "shell": execution.get("shell", ""),
            },
            "trust": {
                "source_tier": trust.get("source_tier", ""),
                "remote_inline_execution": trust.get("remote_inline_execution", ""),
                "remote_metadata_policy": trust.get("remote_metadata_policy", ""),
            },
            "degradation": dict(degradation),
        }

    @property
    def source_files(self) -> list[Path]:
        return _iter_package_files(self.root, excludes=VALID_BUNDLE_EXCLUDES)

    @property
    def runtime_files(self) -> list[Path]:
        return _iter_runtime_files(self.root)

    @classmethod
    def from_root(cls, root: Path | str) -> "SkillPackage":
        root_path = Path(root).resolve()
        skill_md_path = root_path / "SKILL.md"
        manifest_path = root_path / "manifest.json"
        actions_path = root_path / "actions.yaml"
        interface_path = root_path / "agents" / "interface.yaml"

        missing = [path for path in (skill_md_path, manifest_path, actions_path, interface_path) if not path.exists()]
        if missing:
            raise ContractLoadError(
                "Missing required package files: " + ", ".join(str(path) for path in missing)
            )

        skill_frontmatter, skill_body = parse_skill_markdown(skill_md_path.read_text(encoding="utf-8"))
        manifest = _read_json(manifest_path)
        actions = _read_yaml(actions_path)
        interface = _read_yaml(interface_path)
        return cls(
            root=root_path,
            skill_md_path=skill_md_path,
            frontmatter=skill_frontmatter,
            skill_body=skill_body,
            manifest=manifest,
            actions=actions,
            interface=interface,
        )


@dataclass(frozen=True)
class BundleArtifact:
    path: Path
    root_name: str
    file_count: int
    sha256: str
    included_files: tuple[str, ...] = ()

    def to_manifest_entry(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "root_name": self.root_name,
            "file_count": self.file_count,
            "sha256": self.sha256,
            "included_files": list(self.included_files),
        }


@dataclass(frozen=True)
class RuntimeInstallArtifact:
    root: Path
    slug: str
    compat_root: str
    copied_files: tuple[str, ...] = ()

    def to_manifest_entry(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "slug": self.slug,
            "compat_root": self.compat_root,
            "copied_files": list(self.copied_files),
        }


@dataclass(frozen=True)
class AdapterArtifact:
    platform: str
    root: Path
    adapter_json: Path
    generated_files: tuple[Path, ...]
    payload: dict[str, Any]
    contract: dict[str, Any]

    def to_manifest_entry(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "root": str(self.root),
            "adapter_json": str(self.adapter_json),
            "generated_files": [str(path) for path in self.generated_files],
            "payload": _json_safe(self.payload),
            "contract": _json_safe(self.contract),
        }


@dataclass(frozen=True)
class ExportManifestArtifact:
    path: Path
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(self.payload)


def parse_skill_markdown(text: str) -> tuple[dict[str, Any], str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not match:
        raise ContractLoadError("SKILL.md is missing YAML frontmatter")
    raw_frontmatter = yaml.safe_load(match.group(1)) or {}
    if not isinstance(raw_frontmatter, dict):
        raise ContractLoadError("SKILL.md frontmatter must parse to a mapping")
    body = match.group(2)
    return raw_frontmatter, body


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ContractLoadError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContractLoadError(f"YAML document must parse to a mapping: {path}")
    return payload


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractLoadError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContractLoadError(f"JSON document must parse to a mapping: {path}")
    return payload


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(subvalue) for key, subvalue in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _is_safe_relative_path(entry: str) -> bool:
    candidate = Path(entry)
    return not candidate.is_absolute() and ".." not in candidate.parts


def _path_within_root(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _iter_package_files(root: Path, excludes: set[str]) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in excludes for part in relative.parts):
            continue
        files.append(path)
    return files


def _iter_runtime_files(root: Path) -> list[Path]:
    files: list[Path] = []
    top_level = ("SKILL.md", "manifest.json", "actions.yaml")
    for name in top_level:
        candidate = root / name
        if candidate.exists():
            files.append(candidate)
    for dirname in ("agents", "references", "scripts", "assets", "evals", "adapters"):
        candidate = root / dirname
        if candidate.exists():
            for path in sorted(candidate.rglob("*")):
                if path.is_file():
                    files.append(path)
    return files


def validate_skill_package(package: SkillPackage) -> ValidationReport:
    failures: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    _require_file(package.root / "SKILL.md", "missing_skill_md", failures)
    _require_file(package.root / "manifest.json", "missing_manifest", failures)
    _require_file(package.root / "actions.yaml", "missing_actions", failures)
    _require_file(package.root / "agents" / "interface.yaml", "missing_interface", failures)

    if not package.frontmatter.get("name"):
        failures.append(ValidationIssue("missing_frontmatter_name", "SKILL.md frontmatter requires name"))
    if not package.frontmatter.get("description"):
        failures.append(ValidationIssue("missing_frontmatter_description", "SKILL.md frontmatter requires description"))

    if package.manifest.get("name") != package.frontmatter.get("name"):
        failures.append(
            ValidationIssue(
                "manifest_name_mismatch",
                "manifest.json.name must match SKILL.md frontmatter name",
            )
        )

    if package.manifest.get("status") and package.manifest["status"] not in VALID_STATUS:
        failures.append(
            ValidationIssue(
                "invalid_manifest_status",
                f"manifest.json.status must be one of {sorted(VALID_STATUS)}",
            )
        )
    if package.manifest.get("maturity_tier") and package.manifest["maturity_tier"] not in VALID_MATURITY:
        failures.append(
            ValidationIssue(
                "invalid_manifest_maturity",
                f"manifest.json.maturity_tier must be one of {sorted(VALID_MATURITY)}",
            )
        )
    if package.manifest.get("review_cadence") and package.manifest["review_cadence"] not in VALID_REVIEW_CADENCE:
        failures.append(
            ValidationIssue(
                "invalid_review_cadence",
                f"manifest.json.review_cadence must be one of {sorted(VALID_REVIEW_CADENCE)}",
            )
        )
    updated_at = package.manifest.get("updated_at")
    if updated_at and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(updated_at)):
        failures.append(ValidationIssue("invalid_updated_at", "manifest.json.updated_at must use YYYY-MM-DD"))

    compatibility = package.interface.get("compatibility", {})
    interface_meta = package.interface.get("interface", {})
    for field_name in ("display_name", "short_description", "default_prompt"):
        if not interface_meta.get(field_name):
            failures.append(
                ValidationIssue(
                    f"missing_interface_{field_name}",
                    f"agents/interface.yaml interface.{field_name} is required",
                )
            )

    if compatibility.get("canonical_format") != "agent-skills":
        failures.append(
            ValidationIssue(
                "invalid_canonical_format",
                "agents/interface.yaml compatibility.canonical_format must be agent-skills",
            )
        )

    adapter_targets = compatibility.get("adapter_targets", [])
    if not isinstance(adapter_targets, list) or not adapter_targets:
        failures.append(
            ValidationIssue(
                "missing_adapter_targets",
                "agents/interface.yaml compatibility.adapter_targets must be a non-empty list",
            )
        )
        adapter_targets = []

    activation = compatibility.get("activation", {})
    execution = compatibility.get("execution", {})
    trust = compatibility.get("trust", {})
    degradation = compatibility.get("degradation", {})

    if activation.get("mode") not in {"manual", "path_scoped"}:
        failures.append(
            ValidationIssue(
                "invalid_activation_mode",
                "agents/interface.yaml compatibility.activation.mode must be manual or path_scoped",
            )
        )
    if activation.get("mode") == "path_scoped" and not activation.get("paths"):
        failures.append(
            ValidationIssue(
                "missing_activation_paths",
                "agents/interface.yaml compatibility.activation.paths is required for path_scoped mode",
            )
        )

    if execution.get("context") not in VALID_EXECUTION_CONTEXTS:
        failures.append(
            ValidationIssue(
                "invalid_execution_context",
                f"agents/interface.yaml compatibility.execution.context must be one of {sorted(VALID_EXECUTION_CONTEXTS)}",
            )
        )
    if execution.get("shell") not in VALID_SHELLS:
        failures.append(
            ValidationIssue(
                "invalid_execution_shell",
                f"agents/interface.yaml compatibility.execution.shell must be one of {sorted(VALID_SHELLS)}",
            )
        )
    if trust.get("source_tier") not in VALID_SOURCE_TIERS:
        failures.append(
            ValidationIssue(
                "invalid_source_tier",
                f"agents/interface.yaml compatibility.trust.source_tier must be one of {sorted(VALID_SOURCE_TIERS)}",
            )
        )
    if trust.get("remote_inline_execution") not in {"forbid", "allow"}:
        failures.append(
            ValidationIssue(
                "invalid_remote_inline_execution",
                "agents/interface.yaml compatibility.trust.remote_inline_execution must be forbid or allow",
            )
        )
    if not trust.get("remote_metadata_policy"):
        failures.append(
            ValidationIssue(
                "missing_remote_metadata_policy",
                "agents/interface.yaml compatibility.trust.remote_metadata_policy is required",
            )
        )

    for target in adapter_targets:
        if target not in degradation:
            failures.append(
                ValidationIssue(
                    "missing_degradation_target",
                    f"agents/interface.yaml compatibility.degradation must define a strategy for {target}",
                    path=f"compatibility.degradation.{target}",
                )
            )
        target_platforms = package.manifest.get("target_platforms")
        if isinstance(target_platforms, list) and target not in target_platforms:
            warnings.append(
                ValidationIssue(
                    "adapter_target_missing_from_manifest",
                    f"manifest.json.target_platforms does not mention {target}",
                )
            )

    actions_doc = package.actions
    if actions_doc.get("schema_version") != SCHEMA_VERSION:
        failures.append(
            ValidationIssue(
                "invalid_actions_schema_version",
                f"actions.yaml.schema_version must be {SCHEMA_VERSION}",
            )
        )

    actions = actions_doc.get("actions", [])
    if not isinstance(actions, list) or not actions:
        failures.append(
            ValidationIssue(
                "missing_actions_list",
                "actions.yaml.actions must be a non-empty list",
            )
        )
        actions = []

    seen_ids: set[str] = set()
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            failures.append(ValidationIssue("invalid_action_entry", "each action must be a mapping", path=f"actions[{index}]"))
            continue

        action_id = str(action.get("id", "")).strip()
        if not action_id:
            failures.append(ValidationIssue("missing_action_id", "action id is required", path=f"actions[{index}]"))
            continue
        if action_id in seen_ids:
            failures.append(
                ValidationIssue(
                    "duplicate_action_id",
                    f"duplicate action id: {action_id}",
                    path=f"actions[{index}].id",
                )
            )
        seen_ids.add(action_id)

        kind = str(action.get("kind", "")).strip()
        if kind not in VALID_ACTION_KINDS:
            failures.append(
                ValidationIssue(
                    "invalid_action_kind",
                    f"action kind must be one of {sorted(VALID_ACTION_KINDS)}",
                    path=f"actions[{index}].kind",
                )
            )
            continue

        timeout_sec = action.get("timeout_sec")
        if not isinstance(timeout_sec, int) or timeout_sec <= 0:
            failures.append(
                ValidationIssue(
                    "invalid_timeout",
                    "action timeout_sec must be a positive integer",
                    path=f"actions[{index}].timeout_sec",
                )
            )

        sandbox = action.get("sandbox")
        if sandbox not in VALID_SANDBOXES:
            failures.append(
                ValidationIssue(
                    "invalid_sandbox",
                    f"action sandbox must be one of {sorted(VALID_SANDBOXES)}",
                    path=f"actions[{index}].sandbox",
                )
            )

        allow_network = action.get("allow_network")
        if not isinstance(allow_network, bool):
            failures.append(
                ValidationIssue(
                    "invalid_allow_network",
                    "action allow_network must be a boolean",
                    path=f"actions[{index}].allow_network",
                )
            )

        entry = str(action.get("entry", "")).strip()
        if kind in {"script", "instruction"} and not entry:
            failures.append(
                ValidationIssue(
                    "missing_action_entry",
                    f"action entry is required for {kind} actions",
                    path=f"actions[{index}].entry",
                )
            )
        if entry:
            if not _is_safe_relative_path(entry):
                failures.append(
                    ValidationIssue(
                        "unsafe_action_entry",
                        "action entry must be a relative path under the package root",
                        path=f"actions[{index}].entry",
                    )
                )
            else:
                candidate = (package.root / entry).resolve()
                if not _path_within_root(package.root, candidate):
                    failures.append(
                        ValidationIssue(
                            "action_entry_escapes_root",
                            "action entry must stay within the package root",
                            path=f"actions[{index}].entry",
                        )
                    )
                elif kind in {"script", "instruction"} and not candidate.exists():
                    failures.append(
                        ValidationIssue(
                            "missing_action_entry_file",
                            f"action entry file does not exist: {entry}",
                            path=f"actions[{index}].entry",
                        )
                    )

        if kind == "script":
            runtime = str(action.get("runtime", "")).strip()
            if runtime not in VALID_SCRIPT_RUNTIMES:
                failures.append(
                    ValidationIssue(
                        "invalid_script_runtime",
                        f"script runtime must be one of {sorted(VALID_SCRIPT_RUNTIMES)}",
                        path=f"actions[{index}].runtime",
                    )
                )

        if "input_schema" in action and not isinstance(action["input_schema"], dict):
            failures.append(
                ValidationIssue(
                    "invalid_input_schema",
                    "action input_schema must be a mapping when present",
                    path=f"actions[{index}].input_schema",
                )
            )
        if "output_schema" in action and not isinstance(action["output_schema"], dict):
            failures.append(
                ValidationIssue(
                    "invalid_output_schema",
                    "action output_schema must be a mapping when present",
                    path=f"actions[{index}].output_schema",
                )
            )
        if "side_effects" in action and not isinstance(action["side_effects"], list):
            failures.append(
                ValidationIssue(
                    "invalid_side_effects",
                    "action side_effects must be a list when present",
                    path=f"actions[{index}].side_effects",
                )
            )
        if "idempotency" in action and str(action["idempotency"]) not in {"exact", "best_effort", "none"}:
            failures.append(
                ValidationIssue(
                    "invalid_idempotency",
                    "action idempotency must be exact, best_effort, or none",
                    path=f"actions[{index}].idempotency",
                )
            )

    return ValidationReport(ok=not failures, failures=tuple(failures), warnings=tuple(warnings))


def _require_file(path: Path, code: str, failures: list[ValidationIssue]) -> None:
    if not path.exists():
        failures.append(ValidationIssue(code, f"missing required file: {path}"))


def build_bundle_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_tree_with_excludes(source_root: Path, target_root: Path, excludes: set[str]) -> list[str]:
    copied: list[str] = []
    for path in sorted(source_root.rglob("*")):
        relative = path.relative_to(source_root)
        if any(part in excludes for part in relative.parts):
            continue
        if not path.is_file():
            continue
        destination = target_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied.append(str(relative))
    return copied

