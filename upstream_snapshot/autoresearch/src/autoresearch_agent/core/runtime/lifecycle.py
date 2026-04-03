from __future__ import annotations

from dataclasses import dataclass


class RuntimeStatus:
    CREATED = "created"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    CONTINUED = "continued"


@dataclass(frozen=True)
class StatusTransition:
    before: str
    after: str
    reason: str = ""
