"""Orchestration layer package.

Keep package import lightweight so registry discovery can inspect the package
without importing every engine dependency up front.
"""

from .base import EngineMeta, EngineRequest, ExecutionEngine, ExecutionResult
from .registry import create_engine, get_engine_execution_meta, list_engines, resolve_engine_alias

__all__ = [
    "EngineMeta",
    "EngineRequest",
    "ExecutionEngine",
    "ExecutionResult",
    "create_engine",
    "get_engine_execution_meta",
    "list_engines",
    "resolve_engine_alias",
]
