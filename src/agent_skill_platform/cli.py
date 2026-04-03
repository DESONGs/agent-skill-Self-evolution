from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .lab import build_promotion_submission, init_skill_lab_project, run_skill_lab_project, validate_skill_lab_project
from .paths import detect_platform_paths
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-skill-platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("paths")

    validate_package = subparsers.add_parser("validate-package")
    validate_package.add_argument("package_root")

    build_install_bundle = subparsers.add_parser("build-install-bundle")
    build_install_bundle.add_argument("package_root")

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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    platform = AgentSkillPlatform()

    if args.command == "paths":
        return _print(detect_platform_paths().to_dict())
    if args.command == "validate-package":
        return _print(platform.validate_package(args.package_root))
    if args.command == "build-install-bundle":
        return _print(platform.build_install_bundle(args.package_root))
    if args.command == "init-skill-lab":
        return _print(init_skill_lab_project(args.project_root, project_name=args.project_name, overwrite=args.overwrite))
    if args.command == "validate-skill-lab":
        return _print(validate_skill_lab_project(args.project_root))
    if args.command == "run-skill-lab":
        return _print(run_skill_lab_project(args.project_root, run_id=args.run_id))
    if args.command == "build-promotion-submission":
        return _print(build_promotion_submission(args.project_root, args.run_id))

    parser.error(f"unsupported command: {args.command}")
    return 2
