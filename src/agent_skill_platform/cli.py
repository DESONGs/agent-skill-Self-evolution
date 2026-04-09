from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .platform import AgentSkillPlatform


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _print(payload: Any) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default))
    return 0


def _load_json_argument(value: str | None, value_file: str | None) -> Any:
    if value_file:
        return json.loads(Path(value_file).read_text(encoding="utf-8"))
    if value:
        return json.loads(value)
    return None


def _load_submission(value: str) -> Any:
    candidate = Path(value)
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    return json.loads(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("paths")

    validate_package = subparsers.add_parser("validate-package")
    validate_package.add_argument("package_root")

    build_install_bundle = subparsers.add_parser("build-install-bundle")
    build_install_bundle.add_argument("package_root")
    build_install_bundle.add_argument("--skill-id", default=None)
    build_install_bundle.add_argument("--version-id", default=None)

    run_runtime = subparsers.add_parser("run-runtime")
    run_runtime.add_argument("package_root")
    run_runtime.add_argument("--action-id", default=None)
    run_runtime.add_argument("--workspace-dir", default=None)
    run_runtime.add_argument("--run-id", default=None)
    run_runtime.add_argument("--install-root", default=None)
    run_runtime.add_argument("--action-input", default=None)
    run_runtime.add_argument("--action-input-file", default=None)
    run_runtime.add_argument("--max-sandbox", default=None)
    run_runtime.add_argument("--allow-network", action="store_true")

    init_lab = subparsers.add_parser("init-skill-lab")
    init_lab.add_argument("project_root")
    init_lab.add_argument("--project-name", default=None)
    init_lab.add_argument("--overwrite", action="store_true")

    validate_lab = subparsers.add_parser("validate-skill-lab")
    validate_lab.add_argument("project_root")

    run_lab = subparsers.add_parser("run-skill-lab")
    run_lab.add_argument("project_root")
    run_lab.add_argument("--run-id", default=None)

    submit = subparsers.add_parser("build-promotion-submission")
    submit.add_argument("project_root")
    submit.add_argument("run_id")

    registry = subparsers.add_parser("registry")
    registry_subparsers = registry.add_subparsers(dest="registry_command", required=True)

    registry_serve = registry_subparsers.add_parser("serve")
    registry_serve.add_argument("--root", default=None)
    registry_serve.add_argument("--host", default="127.0.0.1")
    registry_serve.add_argument("--port", type=int, default=8000)

    registry_publish = registry_subparsers.add_parser("publish")
    registry_publish.add_argument("source")
    registry_publish.add_argument("--root", default=None)

    registry_install_bundle = registry_subparsers.add_parser("install-bundle")
    registry_install_bundle.add_argument("skill_id")
    registry_install_bundle.add_argument("--version-id", default=None)
    registry_install_bundle.add_argument("--root", default=None)

    registry_feedback = registry_subparsers.add_parser("ingest-feedback")
    registry_feedback.add_argument("payload")
    registry_feedback.add_argument("--root", default=None)

    registry_promotion = registry_subparsers.add_parser("submit-promotion")
    registry_promotion.add_argument("payload")
    registry_promotion.add_argument("--root", default=None)

    registry_list = registry_subparsers.add_parser("list-skills")
    registry_list.add_argument("--root", default=None)

    registry_get = registry_subparsers.add_parser("get-skill")
    registry_get.add_argument("skill_id")
    registry_get.add_argument("--root", default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    platform = AgentSkillPlatform()

    if args.command == "paths":
        payload = detect_platform_payload(platform)
        return _print(payload)
    if args.command == "validate-package":
        return _print(platform.validate_package(args.package_root))
    if args.command == "build-install-bundle":
        return _print(platform.build_install_bundle(args.package_root, skill_id=args.skill_id, version_id=args.version_id))
    if args.command == "run-runtime":
        action_input = _load_json_argument(args.action_input, args.action_input_file)
        return _print(
            platform.run_runtime(
                args.package_root,
                action_id=args.action_id,
                action_input=action_input,
                workspace_dir=args.workspace_dir,
                run_id=args.run_id,
                install_root=args.install_root,
                max_sandbox=args.max_sandbox,
                allow_network=args.allow_network,
            )
        )
    if args.command == "init-skill-lab":
        return _print(platform.init_skill_lab_project(args.project_root, project_name=args.project_name, overwrite=args.overwrite))
    if args.command == "validate-skill-lab":
        return _print(platform.validate_skill_lab_project(args.project_root))
    if args.command == "run-skill-lab":
        return _print(platform.run_skill_lab_project(args.project_root, run_id=args.run_id))
    if args.command == "build-promotion-submission":
        return _print(platform.build_promotion_submission(args.project_root, args.run_id))
    if args.command == "registry":
        registry_root = Path(args.root).resolve() if getattr(args, "root", None) else platform.registry_root()
        if args.registry_command == "serve":
            import uvicorn

            uvicorn.run(platform.build_registry_app(registry_root=registry_root), host=args.host, port=args.port)
            return 0
        if args.registry_command == "publish":
            return _print(platform.publish_package(args.source, registry_root=registry_root))
        if args.registry_command == "install-bundle":
            return _print(platform.resolve_install_bundle(args.skill_id, version_id=args.version_id, registry_root=registry_root))
        if args.registry_command == "ingest-feedback":
            return _print(platform.ingest_feedback(_load_submission(args.payload), registry_root=registry_root))
        if args.registry_command == "submit-promotion":
            return _print(platform.submit_promotion(_load_submission(args.payload), registry_root=registry_root))
        if args.registry_command == "list-skills":
            return _print(platform.list_registry_skills(registry_root=registry_root))
        if args.registry_command == "get-skill":
            return _print(platform.get_registry_skill(args.skill_id, registry_root=registry_root))

    parser.error(f"unsupported command: {args.command}")
    return 2


def detect_platform_payload(platform: AgentSkillPlatform) -> dict[str, Any]:
    payload = platform.paths.to_dict()
    payload["registry_root"] = str(platform.registry_root())
    return payload
