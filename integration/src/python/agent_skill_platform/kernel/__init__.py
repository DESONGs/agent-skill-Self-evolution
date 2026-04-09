from __future__ import annotations

from typing import Any

from ..bootstrap import ensure_source_layout

ensure_source_layout()


def _manager_registry():
    from manager.registry import create_manager, list_plugins

    return create_manager, list_plugins


def _orchestrator_registry():
    from orchestrator.registry import create_engine, get_engine_execution_meta, list_engines

    return create_engine, get_engine_execution_meta, list_engines


def create_kernel_manager(name: str | None = None, **kwargs: Any) -> Any:
    create_manager, _ = _manager_registry()
    return create_manager(name=name, **kwargs)


def create_kernel_engine(name: str, **kwargs: Any) -> Any:
    create_engine, _, _ = _orchestrator_registry()
    return create_engine(name, **kwargs)


def list_plugins() -> dict[str, Any]:
    _, exported = _manager_registry()
    return exported()


def list_engines() -> list[str]:
    _, _, exported = _orchestrator_registry()
    return exported()


def get_engine_execution_meta(name: str) -> dict[str, Any]:
    _, exported, _ = _orchestrator_registry()
    return exported(name)


__all__ = [
    "create_kernel_engine",
    "create_kernel_manager",
    "get_engine_execution_meta",
    "list_engines",
    "list_plugins",
]
