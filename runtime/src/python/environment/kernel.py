"""Environment Kernel for runtime mode and skill selection."""

from __future__ import annotations

from typing import Any, Mapping

from .models import (
    AUTO_MODE_NAMES,
    EnvironmentDecision,
    EnvironmentProfile,
    EnvironmentRuntimeDefaults,
    ModeDecision,
    RetrievalSnapshot,
    TaskContext,
    VALID_MODES,
    extract_task_context,
    normalize_mode_name,
)


_SANDBOX_ORDER = {
    "read-only": 0,
    "workspace-write": 1,
    "network-allowed": 2,
}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _normalize_sandbox(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized or None


class EnvironmentKernel:
    """Classify a task/environment and decide the execution mode."""

    def __init__(self, defaults: EnvironmentRuntimeDefaults | None = None):
        self.defaults = defaults or EnvironmentRuntimeDefaults()

    def build_profile(
        self,
        request: Any,
        *,
        runtime_defaults: EnvironmentRuntimeDefaults | None = None,
        registry_metadata: Mapping[str, Any] | None = None,
        retrieval: RetrievalSnapshot | None = None,
    ) -> EnvironmentProfile:
        """Build an EnvironmentProfile from a TaskRequest-like object."""

        defaults = runtime_defaults or self.defaults
        context = extract_task_context(request)
        registry_metadata = _as_mapping(registry_metadata)

        requested_mode = context.mode
        selected_skill_ids = self._selected_skill_ids(context, retrieval)
        effective_mode, mode_source = self._derive_mode(
            requested_mode=requested_mode,
            selected_skill_ids=selected_skill_ids,
            registry_metadata=registry_metadata,
        )
        max_sandbox = self._resolve_max_sandbox(
            context=context,
            defaults=defaults,
            registry_metadata=registry_metadata,
            selected_skill_ids=selected_skill_ids,
        )
        allow_network = self._resolve_allow_network(
            context=context,
            defaults=defaults,
            registry_metadata=registry_metadata,
            selected_skill_ids=selected_skill_ids,
        )

        return EnvironmentProfile(
            task=context.task,
            request_mode=requested_mode,
            effective_mode=effective_mode,
            mode_source=mode_source,
            skill_group=context.skill_group or defaults.skill_group,
            manager_name=str(registry_metadata.get("manager_name", defaults.manager_name)),
            orchestrator_name=str(
                registry_metadata.get("orchestrator_name", defaults.orchestrator_name)
            ),
            selected_skill_ids=selected_skill_ids,
            file_paths=context.file_paths,
            copy_all_skills=context.copy_all_skills,
            allowed_tools=context.allowed_tools or defaults.default_allowed_tools or None,
            layering_mode=str(registry_metadata.get("layering_mode", defaults.layering_mode)),
            execution_timeout=registry_metadata.get("execution_timeout", defaults.execution_timeout),
            max_sandbox=max_sandbox,
            allow_network=allow_network,
            retrieval_metadata=dict(retrieval.metadata) if retrieval else {},
        )

    def select_mode(
        self,
        profile: EnvironmentProfile,
        *,
        retrieval: RetrievalSnapshot | None = None,
        registry_metadata: Mapping[str, Any] | None = None,
    ) -> ModeDecision:
        """Produce an explicit mode decision for the orchestrator layer."""

        registry_metadata = _as_mapping(registry_metadata)
        selected_skill_ids = self._selected_skill_ids_from_profile(profile, retrieval)

        if profile.request_mode in VALID_MODES:
            return ModeDecision(
                mode=profile.request_mode,
                rationale="explicit request.mode",
                selected_skill_ids=selected_skill_ids,
                copy_all_skills=profile.copy_all_skills,
                allowed_tools=profile.allowed_tools,
                max_sandbox=profile.max_sandbox,
                allow_network=profile.allow_network,
            )

        if profile.mode_source == "registry_override":
            override = normalize_mode_name(registry_metadata.get("mode"))
            if override in VALID_MODES:
                return ModeDecision(
                    mode=override,
                    rationale="registry metadata override",
                    selected_skill_ids=selected_skill_ids,
                    copy_all_skills=profile.copy_all_skills,
                    allowed_tools=profile.allowed_tools,
                    max_sandbox=profile.max_sandbox,
                    allow_network=profile.allow_network,
                )

        mode = profile.effective_mode
        if mode not in VALID_MODES:
            mode = self._auto_mode(selected_skill_ids=selected_skill_ids, registry_metadata=registry_metadata)

        return ModeDecision(
            mode=mode,
            rationale=profile.mode_source or "auto-derived",
            selected_skill_ids=selected_skill_ids,
            copy_all_skills=profile.copy_all_skills,
            allowed_tools=profile.allowed_tools,
            max_sandbox=profile.max_sandbox,
            allow_network=profile.allow_network,
        )

    def classify(
        self,
        request: Any,
        *,
        runtime_defaults: EnvironmentRuntimeDefaults | None = None,
        registry_metadata: Mapping[str, Any] | None = None,
        retrieval: RetrievalSnapshot | None = None,
    ) -> EnvironmentDecision:
        """Return both the profile and the mode decision."""

        profile = self.build_profile(
            request,
            runtime_defaults=runtime_defaults,
            registry_metadata=registry_metadata,
            retrieval=retrieval,
        )
        mode_decision = self.select_mode(
            profile,
            retrieval=retrieval,
            registry_metadata=registry_metadata,
        )
        return EnvironmentDecision(profile=profile, mode_decision=mode_decision, retrieval=retrieval)

    def _selected_skill_ids(
        self,
        context: TaskContext,
        retrieval: RetrievalSnapshot | None,
    ) -> tuple[str, ...]:
        if context.mode == "no-skill":
            return ()
        if context.selected_skill_ids:
            return context.selected_skill_ids
        if retrieval is None:
            return ()
        return tuple(candidate.skill_id for candidate in retrieval.candidates)

    def _selected_skill_ids_from_profile(
        self,
        profile: EnvironmentProfile,
        retrieval: RetrievalSnapshot | None,
    ) -> tuple[str, ...]:
        if profile.selected_skill_ids:
            return profile.selected_skill_ids
        if retrieval is None:
            return ()
        return tuple(candidate.skill_id for candidate in retrieval.candidates)

    def _derive_mode(
        self,
        *,
        requested_mode: str,
        selected_skill_ids: tuple[str, ...],
        registry_metadata: Mapping[str, Any],
    ) -> tuple[str, str]:
        if requested_mode in VALID_MODES:
            return requested_mode, "explicit request.mode"

        if requested_mode in AUTO_MODE_NAMES or requested_mode == "auto":
            override = normalize_mode_name(registry_metadata.get("mode"))
            if override in VALID_MODES:
                return override, "registry_override"
            return self._auto_mode(
                selected_skill_ids=selected_skill_ids,
                registry_metadata=registry_metadata,
            ), "auto-derived"

        raise ValueError(f"Unknown execution mode: {requested_mode!r}")

    def _auto_mode(
        self,
        *,
        selected_skill_ids: tuple[str, ...],
        registry_metadata: Mapping[str, Any],
    ) -> str:
        if not selected_skill_ids:
            return "no-skill"

        if self._has_dag_hint(registry_metadata):
            return "dag"

        return "free-style"

    def _has_dag_hint(self, registry_metadata: Mapping[str, Any]) -> bool:
        if registry_metadata.get("mode_hint") == "dag":
            return True

        action_graph = registry_metadata.get("action_graph")
        if isinstance(action_graph, Mapping):
            return bool(action_graph.get("edges"))

        candidates = registry_metadata.get("candidates")
        if isinstance(candidates, list):
            for candidate in candidates:
                if isinstance(candidate, Mapping) and candidate.get("requires_dag"):
                    return True
        return False

    def _resolve_max_sandbox(
        self,
        *,
        context: TaskContext,
        defaults: EnvironmentRuntimeDefaults,
        registry_metadata: Mapping[str, Any],
        selected_skill_ids: tuple[str, ...],
    ) -> str:
        if context.max_sandbox is not None:
            return context.max_sandbox

        registry_value = _normalize_sandbox(registry_metadata.get("max_sandbox"))
        if registry_value is None:
            registry_value = self._candidate_max_sandbox(
                registry_metadata=registry_metadata,
                selected_skill_ids=selected_skill_ids,
            )
        return registry_value or defaults.max_sandbox

    def _resolve_allow_network(
        self,
        *,
        context: TaskContext,
        defaults: EnvironmentRuntimeDefaults,
        registry_metadata: Mapping[str, Any],
        selected_skill_ids: tuple[str, ...],
    ) -> bool:
        if context.allow_network is not None:
            return context.allow_network

        registry_value = _as_optional_bool(registry_metadata.get("allow_network"))
        if registry_value is None:
            registry_value = self._candidate_allow_network(
                registry_metadata=registry_metadata,
                selected_skill_ids=selected_skill_ids,
            )
        if registry_value is None:
            return defaults.allow_network
        return registry_value

    def _candidate_max_sandbox(
        self,
        *,
        registry_metadata: Mapping[str, Any],
        selected_skill_ids: tuple[str, ...],
    ) -> str | None:
        restrictive_rank: int | None = None
        restrictive_value: str | None = None
        selected_ids = set(selected_skill_ids)
        for candidate in registry_metadata.get("candidates", []) or []:
            if not isinstance(candidate, Mapping):
                continue
            skill_id = str(candidate.get("skill_id") or candidate.get("id") or "").strip()
            if selected_ids and skill_id and skill_id not in selected_ids:
                continue
            sandbox = _normalize_sandbox(candidate.get("max_sandbox"))
            if sandbox is None:
                continue
            rank = _SANDBOX_ORDER.get(sandbox, 0)
            if restrictive_rank is None or rank < restrictive_rank:
                restrictive_rank = rank
                restrictive_value = sandbox
        return restrictive_value

    def _candidate_allow_network(
        self,
        *,
        registry_metadata: Mapping[str, Any],
        selected_skill_ids: tuple[str, ...],
    ) -> bool | None:
        selected_ids = set(selected_skill_ids)
        values: list[bool] = []
        for candidate in registry_metadata.get("candidates", []) or []:
            if not isinstance(candidate, Mapping):
                continue
            skill_id = str(candidate.get("skill_id") or candidate.get("id") or "").strip()
            if selected_ids and skill_id and skill_id not in selected_ids:
                continue
            value = _as_optional_bool(candidate.get("allow_network"))
            if value is not None:
                values.append(value)
        if not values:
            return None
        return all(values)
