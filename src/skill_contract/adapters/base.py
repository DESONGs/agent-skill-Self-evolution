from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from skill_contract.bundler.contracts import AdapterArtifact, SkillPackage

TARGET_CONTRACTS: dict[str, dict[str, Any]] = {
    "openai": {
        "required_fields": [
            "name",
            "description",
            "version",
            "display_name",
            "short_description",
            "default_prompt",
            "canonical_metadata",
            "canonical_format",
            "activation_mode",
            "execution_context",
            "shell",
            "trust_level",
            "remote_inline_execution",
            "degradation_strategy",
            "portable_semantics",
        ],
        "required_files": ["adapter.json", "agents/openai.yaml"],
    },
    "claude": {
        "required_fields": [
            "name",
            "description",
            "version",
            "display_name",
            "short_description",
            "default_prompt",
            "canonical_metadata",
            "canonical_format",
            "activation_mode",
            "execution_context",
            "shell",
            "trust_level",
            "remote_inline_execution",
            "degradation_strategy",
            "portable_semantics",
        ],
        "required_files": ["adapter.json", "README.md"],
    },
    "generic": {
        "required_fields": [
            "name",
            "description",
            "version",
            "display_name",
            "short_description",
            "default_prompt",
            "canonical_metadata",
            "canonical_format",
            "activation_mode",
            "execution_context",
            "shell",
            "trust_level",
            "remote_inline_execution",
            "degradation_strategy",
            "portable_semantics",
        ],
        "required_files": ["adapter.json"],
    },
}


def _common_payload(package: SkillPackage, platform: str, degradation_strategy: str) -> dict[str, Any]:
    compatibility = package.interface.get("compatibility", {})
    activation = compatibility.get("activation", {})
    execution = compatibility.get("execution", {})
    trust = compatibility.get("trust", {})
    return {
        "schema_version": "skill-adapter.v1",
        "platform": platform,
        "name": package.slug,
        "description": package.description,
        "version": package.version,
        "display_name": package.interface.get("interface", {}).get("display_name", package.slug),
        "short_description": package.interface.get("interface", {}).get("short_description", ""),
        "default_prompt": package.interface.get("interface", {}).get("default_prompt", ""),
        "canonical_metadata": "agents/interface.yaml",
        "canonical_format": compatibility.get("canonical_format", "agent-skills"),
        "adapter_targets": list(package.adapter_targets),
        "activation_mode": activation.get("mode", "manual"),
        "activation_paths": list(activation.get("paths", [])),
        "execution_context": execution.get("context", "inline"),
        "shell": execution.get("shell", "bash"),
        "trust_level": trust.get("source_tier", "local"),
        "remote_inline_execution": trust.get("remote_inline_execution", "forbid"),
        "remote_metadata_policy": trust.get("remote_metadata_policy", "allow-metadata-only"),
        "degradation_strategy": degradation_strategy,
        "portable_semantics": package.portable_semantics,
        "source_files": [str(path.relative_to(package.root)) for path in package.source_files],
        "target_platforms": list(package.manifest.get("target_platforms", [])) if isinstance(package.manifest.get("target_platforms"), list) else [],
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def build_openai_adapter(package: SkillPackage, target_root: Path) -> AdapterArtifact:
    payload = _common_payload(package, "openai", "metadata-adapter")
    adapter_json = target_root / "adapter.json"
    openai_yaml = target_root / "agents" / "openai.yaml"
    _write_yaml(
        openai_yaml,
        {
            "interface": {
                "display_name": payload["display_name"],
                "short_description": payload["short_description"],
                "default_prompt": payload["default_prompt"],
            },
            "compatibility": {
                "canonical_format": payload["canonical_format"],
                "activation_mode": payload["activation_mode"],
                "activation_paths": payload["activation_paths"],
                "execution_context": payload["execution_context"],
                "shell": payload["shell"],
                "trust_level": payload["trust_level"],
                "remote_inline_execution": payload["remote_inline_execution"],
                "remote_metadata_policy": payload["remote_metadata_policy"],
                "degradation_strategy": payload["degradation_strategy"],
            },
        },
    )
    _write_json(adapter_json, payload | {"contract": TARGET_CONTRACTS["openai"], "install_hint": "Include agents/openai.yaml for OpenAI-compatible clients."})
    return AdapterArtifact(
        platform="openai",
        root=target_root,
        adapter_json=adapter_json,
        generated_files=(adapter_json, openai_yaml),
        payload=payload | {"contract": TARGET_CONTRACTS["openai"], "install_hint": "Include agents/openai.yaml for OpenAI-compatible clients."},
        contract=TARGET_CONTRACTS["openai"],
    )


def build_claude_adapter(package: SkillPackage, target_root: Path) -> AdapterArtifact:
    payload = _common_payload(package, "claude", "neutral-source-plus-adapter")
    adapter_json = target_root / "adapter.json"
    readme = target_root / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text(
        f"# Claude-Compatible Package\n\nUse `{package.slug}` with the neutral source files and the declared action contract.\n",
        encoding="utf-8",
    )
    _write_json(adapter_json, payload | {"contract": TARGET_CONTRACTS["claude"], "install_hint": "Use the neutral source files with the declared action contract."})
    return AdapterArtifact(
        platform="claude",
        root=target_root,
        adapter_json=adapter_json,
        generated_files=(adapter_json, readme),
        payload=payload | {"contract": TARGET_CONTRACTS["claude"], "install_hint": "Use the neutral source files with the declared action contract."},
        contract=TARGET_CONTRACTS["claude"],
    )


def build_generic_adapter(package: SkillPackage, target_root: Path) -> AdapterArtifact:
    payload = _common_payload(package, "generic", "neutral-source")
    adapter_json = target_root / "adapter.json"
    _write_json(adapter_json, payload | {"contract": TARGET_CONTRACTS["generic"], "install_hint": f"Use {package.slug} as a generic Agent Skills package."})
    return AdapterArtifact(
        platform="generic",
        root=target_root,
        adapter_json=adapter_json,
        generated_files=(adapter_json,),
        payload=payload | {"contract": TARGET_CONTRACTS["generic"], "install_hint": f"Use {package.slug} as a generic Agent Skills package."},
        contract=TARGET_CONTRACTS["generic"],
    )
