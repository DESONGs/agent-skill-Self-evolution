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


def _load_payload(value: str) -> Any:
    candidate = Path(value)
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    return json.loads(value)


def _add_registry_backend_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--registry-mode", default=None)
    parser.add_argument("--registry-url", default=None)
    parser.add_argument("--root", default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    integration = subparsers.add_parser("integration")
    integration_subparsers = integration.add_subparsers(dest="integration_command", required=True)
    integration_subparsers.add_parser("paths")

    contracts = subparsers.add_parser("contracts")
    contracts_subparsers = contracts.add_subparsers(dest="contracts_command", required=True)
    contracts_validate = contracts_subparsers.add_parser("validate-package")
    contracts_validate.add_argument("package_root")

    runtime = subparsers.add_parser("runtime")
    runtime_subparsers = runtime.add_subparsers(dest="runtime_command", required=True)
    runtime_bundle = runtime_subparsers.add_parser("build-install-bundle")
    runtime_bundle.add_argument("package_root")
    runtime_bundle.add_argument("--skill-id", default=None)
    runtime_bundle.add_argument("--version-id", default=None)
    runtime_run = runtime_subparsers.add_parser("run")
    runtime_run.add_argument("package_root")
    runtime_run.add_argument("--action-id", default=None)
    runtime_run.add_argument("--workspace-dir", default=None)
    runtime_run.add_argument("--run-id", default=None)
    runtime_run.add_argument("--install-root", default=None)
    runtime_run.add_argument("--action-input", default=None)
    runtime_run.add_argument("--action-input-file", default=None)
    runtime_run.add_argument("--max-sandbox", default=None)
    runtime_run.add_argument("--allow-network", action="store_true")

    factory = subparsers.add_parser("factory")
    factory_subparsers = factory.add_subparsers(dest="factory_command", required=True)
    factory_prepare = factory_subparsers.add_parser("prepare-candidate")
    factory_prepare.add_argument("project_root")
    factory_prepare.add_argument("--skill-name", required=True)
    factory_prepare.add_argument("--workflow", default=None)
    factory_prepare.add_argument("--workflow-file", default=None)
    factory_prepare.add_argument("--transcript", default=None)
    factory_prepare.add_argument("--transcript-file", default=None)
    factory_prepare.add_argument("--failure", default=None)
    factory_prepare.add_argument("--failure-file", default=None)
    factory_prepare.add_argument("--owner", default="agent-skill-platform")
    factory_prepare.add_argument("--overwrite", action="store_true")
    factory_run = factory_subparsers.add_parser("run-pipeline")
    factory_run.add_argument("project_root")
    factory_run.add_argument("--skill-name", required=True)
    factory_run.add_argument("--workflow", default=None)
    factory_run.add_argument("--workflow-file", default=None)
    factory_run.add_argument("--transcript", default=None)
    factory_run.add_argument("--transcript-file", default=None)
    factory_run.add_argument("--failure", default=None)
    factory_run.add_argument("--failure-file", default=None)
    factory_run.add_argument("--owner", default="agent-skill-platform")
    factory_run.add_argument("--overwrite", action="store_true")

    lab = subparsers.add_parser("lab")
    lab_subparsers = lab.add_subparsers(dest="lab_command", required=True)
    lab_init = lab_subparsers.add_parser("init")
    lab_init.add_argument("project_root")
    lab_init.add_argument("--project-name", default=None)
    lab_init.add_argument("--overwrite", action="store_true")
    lab_validate = lab_subparsers.add_parser("validate")
    lab_validate.add_argument("project_root")
    lab_run = lab_subparsers.add_parser("run")
    lab_run.add_argument("project_root")
    lab_run.add_argument("--run-id", default=None)
    lab_submit = lab_subparsers.add_parser("build-promotion-submission")
    lab_submit.add_argument("project_root")
    lab_submit.add_argument("run_id")

    registry = subparsers.add_parser("registry")
    registry_subparsers = registry.add_subparsers(dest="registry_command", required=True)
    registry_serve = registry_subparsers.add_parser("serve")
    registry_serve.add_argument("--root", default=None)
    registry_serve.add_argument("--host", default="127.0.0.1")
    registry_serve.add_argument("--port", type=int, default=8000)
    registry_publish = registry_subparsers.add_parser("publish")
    registry_publish.add_argument("source")
    _add_registry_backend_args(registry_publish)
    registry_bundle = registry_subparsers.add_parser("install-bundle")
    registry_bundle.add_argument("skill_id")
    registry_bundle.add_argument("--version-id", default=None)
    _add_registry_backend_args(registry_bundle)
    registry_feedback = registry_subparsers.add_parser("ingest-feedback")
    registry_feedback.add_argument("payload")
    _add_registry_backend_args(registry_feedback)
    registry_promotion = registry_subparsers.add_parser("submit-promotion")
    registry_promotion.add_argument("payload")
    _add_registry_backend_args(registry_promotion)
    registry_list = registry_subparsers.add_parser("list-skills")
    _add_registry_backend_args(registry_list)
    registry_get = registry_subparsers.add_parser("get-skill")
    registry_get.add_argument("skill_id")
    _add_registry_backend_args(registry_get)

    legacy_paths = subparsers.add_parser("paths")
    legacy_validate = subparsers.add_parser("validate-package")
    legacy_validate.add_argument("package_root")
    legacy_bundle = subparsers.add_parser("build-install-bundle")
    legacy_bundle.add_argument("package_root")
    legacy_bundle.add_argument("--skill-id", default=None)
    legacy_bundle.add_argument("--version-id", default=None)
    legacy_runtime = subparsers.add_parser("run-runtime")
    legacy_runtime.add_argument("package_root")
    legacy_runtime.add_argument("--action-id", default=None)
    legacy_runtime.add_argument("--workspace-dir", default=None)
    legacy_runtime.add_argument("--run-id", default=None)
    legacy_runtime.add_argument("--install-root", default=None)
    legacy_runtime.add_argument("--action-input", default=None)
    legacy_runtime.add_argument("--action-input-file", default=None)
    legacy_runtime.add_argument("--max-sandbox", default=None)
    legacy_runtime.add_argument("--allow-network", action="store_true")
    legacy_lab_init = subparsers.add_parser("init-skill-lab")
    legacy_lab_init.add_argument("project_root")
    legacy_lab_init.add_argument("--project-name", default=None)
    legacy_lab_init.add_argument("--overwrite", action="store_true")
    legacy_lab_validate = subparsers.add_parser("validate-skill-lab")
    legacy_lab_validate.add_argument("project_root")
    legacy_lab_run = subparsers.add_parser("run-skill-lab")
    legacy_lab_run.add_argument("project_root")
    legacy_lab_run.add_argument("--run-id", default=None)
    legacy_submission = subparsers.add_parser("build-promotion-submission")
    legacy_submission.add_argument("project_root")
    legacy_submission.add_argument("run_id")

    return parser


def _registry_root(platform: AgentSkillPlatform, value: str | None) -> Path:
    return Path(value).resolve() if value else platform.registry_root()


def _factory_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "skill_name": args.skill_name,
        "workflow": _load_json_argument(getattr(args, "workflow", None), getattr(args, "workflow_file", None)),
        "transcript": _load_json_argument(getattr(args, "transcript", None), getattr(args, "transcript_file", None)),
        "failure": _load_json_argument(getattr(args, "failure", None), getattr(args, "failure_file", None)),
        "owner": args.owner,
        "overwrite": args.overwrite,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    platform = AgentSkillPlatform()

    if args.command == "integration" and args.integration_command == "paths":
        return _print(detect_platform_payload(platform))

    if args.command == "contracts" and args.contracts_command == "validate-package":
        return _print(platform.validate_package(args.package_root))

    if args.command == "runtime":
        if args.runtime_command == "build-install-bundle":
            return _print(platform.build_install_bundle(args.package_root, skill_id=args.skill_id, version_id=args.version_id))
        if args.runtime_command == "run":
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

    if args.command == "factory":
        if args.factory_command == "prepare-candidate":
            return _print(platform.prepare_candidate_for_lab(args.project_root, **_factory_kwargs(args)))
        if args.factory_command == "run-pipeline":
            return _print(platform.run_factory_pipeline(args.project_root, **_factory_kwargs(args)))

    if args.command == "lab":
        if args.lab_command == "init":
            return _print(platform.init_skill_lab_project(args.project_root, project_name=args.project_name, overwrite=args.overwrite))
        if args.lab_command == "validate":
            return _print(platform.validate_skill_lab_project(args.project_root))
        if args.lab_command == "run":
            return _print(platform.run_skill_lab_project(args.project_root, run_id=args.run_id))
        if args.lab_command == "build-promotion-submission":
            return _print(platform.build_promotion_submission(args.project_root, args.run_id))

    if args.command == "registry":
        registry_root = _registry_root(platform, getattr(args, "root", None))
        if args.registry_command == "serve":
            import uvicorn

            uvicorn.run(platform.build_registry_app(registry_root=registry_root), host=args.host, port=args.port)
            return 0
        if args.registry_command == "publish":
            return _print(
                platform.publish_package(
                    args.source,
                    registry_root=registry_root,
                    registry_mode=args.registry_mode,
                    registry_base_url=args.registry_url,
                )
            )
        if args.registry_command == "install-bundle":
            return _print(
                platform.resolve_install_bundle(
                    args.skill_id,
                    version_id=args.version_id,
                    registry_root=registry_root,
                    registry_mode=args.registry_mode,
                    registry_base_url=args.registry_url,
                )
            )
        if args.registry_command == "ingest-feedback":
            return _print(
                platform.ingest_feedback(
                    _load_payload(args.payload),
                    registry_root=registry_root,
                    registry_mode=args.registry_mode,
                    registry_base_url=args.registry_url,
                )
            )
        if args.registry_command == "submit-promotion":
            return _print(
                platform.submit_promotion(
                    _load_payload(args.payload),
                    registry_root=registry_root,
                    registry_mode=args.registry_mode,
                    registry_base_url=args.registry_url,
                )
            )
        if args.registry_command == "list-skills":
            return _print(
                platform.list_registry_skills(
                    registry_root=registry_root,
                    registry_mode=args.registry_mode,
                    registry_base_url=args.registry_url,
                )
            )
        if args.registry_command == "get-skill":
            return _print(
                platform.get_registry_skill(
                    args.skill_id,
                    registry_root=registry_root,
                    registry_mode=args.registry_mode,
                    registry_base_url=args.registry_url,
                )
            )

    if args.command == "paths":
        return _print(detect_platform_payload(platform))
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

    parser.error(f"unsupported command: {args.command}")
    return 2


def detect_platform_payload(platform: AgentSkillPlatform) -> dict[str, Any]:
    payload = platform.paths.to_dict()
    payload["registry_local_dev_root"] = str(platform.registry_root())
    payload["registry_server_root"] = str(platform.registry_server_root())
    payload["python_source_roots"] = [str(path) for path in platform.paths.python_source_roots()]
    return payload
