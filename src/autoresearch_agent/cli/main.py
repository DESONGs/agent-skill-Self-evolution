from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable

from autoresearch_agent.cli.runtime import (
    continue_project_run,
    get_run_artifacts,
    get_run_status,
    init_project,
    install_pack_snapshot,
    json_dumps,
    list_packs,
    project_root_from_input,
    run_project,
    submit_promotion,
    validate_project,
)
from autoresearch_agent.mcp.server import serve_stdio


CommandFn = Callable[[argparse.Namespace], Any]


def _print(payload: Any) -> int:
    if payload is None:
        return 0
    print(json_dumps(payload))
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    return _print(
        init_project(
            args.project_root,
            project_name=args.name,
            pack_id=args.pack,
            data_source=args.data_source,
            overwrite=args.overwrite,
        )
    )


def cmd_validate(args: argparse.Namespace) -> int:
    return _print(validate_project(args.project_root))


def cmd_run(args: argparse.Namespace) -> int:
    return _print(run_project(args.project_root, run_id=args.run_id))


def cmd_continue(args: argparse.Namespace) -> int:
    return _print(continue_project_run(args.project_root, args.run_id, next_run_id=args.next_run_id or None))


def cmd_status(args: argparse.Namespace) -> int:
    return _print(get_run_status(args.project_root, args.run_id))


def cmd_artifacts(args: argparse.Namespace) -> int:
    return _print(get_run_artifacts(args.project_root, args.run_id))


def cmd_submit_promotion(args: argparse.Namespace) -> int:
    return _print(submit_promotion(args.project_root, args.run_id))


def cmd_pack_list(args: argparse.Namespace) -> int:
    return _print({"packs": list_packs()})


def cmd_pack_install(args: argparse.Namespace) -> int:
    root = project_root_from_input(args.project_root)
    snapshot = install_pack_snapshot(root, args.pack_id)
    return _print({"ok": True, "project_root": str(root), "pack_id": args.pack_id, "snapshot": str(snapshot)})


def cmd_mcp_serve(args: argparse.Namespace) -> int:
    serve_stdio(project_root=Path(args.project_root).resolve())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ar", description="Autoresearch Agent CLI")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="initialize a local research project")
    init_parser.add_argument("project_root")
    init_parser.add_argument("--name", default="")
    init_parser.add_argument("--pack", default="prediction_market")
    init_parser.add_argument("--data-source", default="./datasets/input.json")
    init_parser.add_argument("--overwrite", action="store_true")
    init_parser.set_defaults(handler=cmd_init)

    validate_parser = subparsers.add_parser("validate", help="validate research.yaml, pack, and dataset")
    validate_parser.add_argument("project_root", nargs="?", default=".")
    validate_parser.set_defaults(handler=cmd_validate)

    run_parser = subparsers.add_parser("run", help="run the local research project")
    run_parser.add_argument("project_root", nargs="?", default=".")
    run_parser.add_argument("--run-id", default="")
    run_parser.set_defaults(handler=cmd_run)

    continue_parser = subparsers.add_parser("continue", help="continue from an existing run")
    continue_parser.add_argument("run_id")
    continue_parser.add_argument("--project-root", default=".")
    continue_parser.add_argument("--next-run-id", default="")
    continue_parser.set_defaults(handler=cmd_continue)

    status_parser = subparsers.add_parser("status", help="show run status")
    status_parser.add_argument("run_id")
    status_parser.add_argument("--project-root", default=".")
    status_parser.set_defaults(handler=cmd_status)

    artifacts_parser = subparsers.add_parser("artifacts", help="list run artifacts")
    artifacts_parser.add_argument("run_id")
    artifacts_parser.add_argument("--project-root", default=".")
    artifacts_parser.set_defaults(handler=cmd_artifacts)

    submit_parser = subparsers.add_parser("submit-promotion", help="create a promotion submission bundle")
    submit_parser.add_argument("run_id")
    submit_parser.add_argument("--project-root", default=".")
    submit_parser.set_defaults(handler=cmd_submit_promotion)

    pack_parser = subparsers.add_parser("pack", help="pack management commands")
    pack_subparsers = pack_parser.add_subparsers(dest="pack_command")

    pack_list_parser = pack_subparsers.add_parser("list", help="list bundled packs")
    pack_list_parser.set_defaults(handler=cmd_pack_list)

    pack_install_parser = pack_subparsers.add_parser("install", help="install a pack snapshot into a project")
    pack_install_parser.add_argument("pack_id")
    pack_install_parser.add_argument("--project-root", default=".")
    pack_install_parser.set_defaults(handler=cmd_pack_install)

    mcp_parser = subparsers.add_parser("mcp", help="MCP utilities")
    mcp_subparsers = mcp_parser.add_subparsers(dest="mcp_command")
    mcp_serve_parser = mcp_subparsers.add_parser("serve", help="serve the stdio MCP server")
    mcp_serve_parser.add_argument("--project-root", default=".")
    mcp_serve_parser.set_defaults(handler=cmd_mcp_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: CommandFn | None = getattr(args, "handler", None)
    if handler is None:
        parser.print_help(sys.stderr)
        return 2
    try:
        return int(handler(args) or 0)
    except Exception as exc:
        print(json_dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
