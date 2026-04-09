from __future__ import annotations

import ast
import importlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Iterable

import autoresearch_agent.packs as builtin_packs

from .schema import PackManifest, build_default_research_spec, normalize_pack_manifest


PACKS_ROOT = Path(builtin_packs.__file__).resolve().parent


def _strip_comment_line(line: str) -> str:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return ""
    return line.rstrip("\n")


def _coerce_scalar(value: str) -> Any:
    text = value.strip()
    if text in {"", "null", "Null", "NULL", "~"}:
        return None
    if text in {"true", "True", "TRUE"}:
        return True
    if text in {"false", "False", "FALSE"}:
        return False
    if text.startswith(("'", '"')) and text.endswith(("'", '"')):
        return ast.literal_eval(text)
    if text.startswith("[") or text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return ast.literal_eval(text)
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _parse_simple_yaml(text: str) -> Any:
    lines = [line for line in (_strip_comment_line(raw) for raw in text.splitlines()) if line]
    if not lines:
        return {}
    if lines[0].lstrip().startswith("- "):
        return _parse_yaml_block(lines, 0, 0)[0]
    return _parse_yaml_block(lines, 0, 0)[0]


def _parse_yaml_block(lines: list[str], index: int, indent: int) -> tuple[Any, int]:
    result: Any = None
    is_list = False
    is_dict = False

    while index < len(lines):
        current = lines[index]
        current_indent = len(current) - len(current.lstrip(" "))
        if current_indent < indent:
            break
        if current_indent > indent and result is None:
            indent = current_indent
            current_indent = indent
        if current_indent > indent:
            raise ValueError("unsupported YAML nesting shape")
        content = current.strip()
        if content.startswith("- "):
            if result is None:
                result = []
                is_list = True
            elif not is_list:
                raise ValueError("mixed YAML list and mapping content")
            item_text = content[2:].strip()
            index += 1
            if not item_text:
                if index < len(lines) and len(lines[index]) - len(lines[index].lstrip(" ")) > indent:
                    nested, index = _parse_yaml_block(lines, index, len(lines[index]) - len(lines[index].lstrip(" ")))
                    result.append(nested)
                else:
                    result.append(None)
                continue
            if ":" in item_text and not item_text.startswith("{") and not item_text.startswith("["):
                key, value = item_text.split(":", 1)
                item: dict[str, Any] = {key.strip(): _coerce_scalar(value)}
                if index < len(lines) and len(lines[index]) - len(lines[index].lstrip(" ")) > indent:
                    nested, index = _parse_yaml_block(lines, index, len(lines[index]) - len(lines[index].lstrip(" ")))
                    if isinstance(nested, dict):
                        item.update(nested)
                result.append(item)
            else:
                result.append(_coerce_scalar(item_text))
            continue

        if result is None:
            result = {}
            is_dict = True
        elif not is_dict:
            raise ValueError("mixed YAML list and mapping content")

        if ":" not in content:
            raise ValueError(f"invalid YAML line: {content}")
        key, value = content.split(":", 1)
        key = key.strip()
        value = value.strip()
        index += 1
        if value == "":
            if index < len(lines) and len(lines[index]) - len(lines[index].lstrip(" ")) > indent:
                nested, index = _parse_yaml_block(lines, index, len(lines[index]) - len(lines[index].lstrip(" ")))
                result[key] = nested
            else:
                result[key] = None
        else:
            result[key] = _coerce_scalar(value)
    return result if result is not None else {}, index


def load_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    payload: Any
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = _parse_simple_yaml(text)
    if not isinstance(payload, dict):
        raise ValueError(f"expected mapping document at {path}")
    return payload


def dump_document(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def normalize_pack_id(pack_id: str) -> str:
    return str(pack_id).strip().replace("-", "_")


def load_pack_manifest(manifest_path: Path) -> PackManifest:
    payload = load_document(manifest_path)
    return normalize_pack_manifest(payload, manifest_path=str(manifest_path))


def discover_pack_manifests(packs_root: Path | None = None) -> list[PackManifest]:
    root = packs_root or PACKS_ROOT
    if not root.exists():
        return []
    manifests: list[PackManifest] = []
    for manifest_path in sorted(root.glob("*/pack.yaml")):
        try:
            manifests.append(load_pack_manifest(manifest_path))
        except Exception:
            continue
    return sorted(manifests, key=lambda item: item.pack_id)


def list_pack_ids(packs_root: Path | None = None) -> list[str]:
    return [manifest.pack_id for manifest in discover_pack_manifests(packs_root)]


def find_pack_manifest(pack_id: str, packs_root: Path | None = None) -> PackManifest:
    root = packs_root or PACKS_ROOT
    normalized = normalize_pack_id(pack_id)
    candidate = root / normalized / "pack.yaml"
    if candidate.exists():
        return load_pack_manifest(candidate)
    for manifest in discover_pack_manifests(root):
        if manifest.pack_id == pack_id or manifest.pack_id == normalized:
            return manifest
    raise FileNotFoundError(f"pack manifest not found: {pack_id}")


class PackLoader:
    def __init__(self, packs_root: Path | None = None) -> None:
        self.packs_root = packs_root or PACKS_ROOT

    def list_packs(self) -> list[PackManifest]:
        return discover_pack_manifests(self.packs_root)

    def load(self, pack_id: str) -> PackManifest:
        return find_pack_manifest(pack_id, self.packs_root)

    def default_research_spec(
        self,
        *,
        project_name: str,
        pack_id: str,
        data_source: str,
        allowed_axes: list[str] | None = None,
        pack_config: dict[str, Any] | None = None,
    ):
        return build_default_research_spec(
            project_name=project_name,
            pack_id=pack_id,
            data_source=data_source,
            allowed_axes=allowed_axes,
            pack_config=pack_config,
        )


def resolve_pack_file(manifest: PackManifest, relative_path: str) -> Path:
    base = Path(manifest.manifest_path).resolve().parent
    return (base / relative_path).resolve()


def load_pack_entrypoint_module(manifest: PackManifest, entrypoint_key: str):
    target = str(manifest.entrypoints.get(entrypoint_key, "") or "").strip()
    if not target:
        raise KeyError(f"missing pack entrypoint: {entrypoint_key}")
    if target.endswith(".py") or "/" in target:
        path = resolve_pack_file(manifest, target)
        module_name = f"autoresearch_agent.packs.{manifest.pack_id}.{entrypoint_key}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"failed to load pack entrypoint module: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return importlib.import_module(target)
