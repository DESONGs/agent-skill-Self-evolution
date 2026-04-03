from __future__ import annotations

from typing import Any

from manager.registry import create_manager, list_plugins
from orchestrator.registry import create_engine, get_engine_execution_meta, list_engines


def create_kernel_manager(name: str | None = None, **kwargs: Any) -> Any:
    return create_manager(name=name, **kwargs)


def create_kernel_engine(name: str, **kwargs: Any) -> Any:
    return create_engine(name, **kwargs)


__all__ = [
    "create_kernel_engine",
    "create_kernel_manager",
    "create_engine",
    "create_manager",
    "get_engine_execution_meta",
    "list_engines",
    "list_plugins",
]
