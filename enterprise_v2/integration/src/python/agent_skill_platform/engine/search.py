from __future__ import annotations

import re
from datetime import datetime, timezone
from dataclasses import replace
from typing import Any, Iterable, Sequence

from .models import FindSkillRequest, FindSkillResponse, SkillProjection


def _normalize_tokens(value: str) -> tuple[str, ...]:
    return tuple(token for token in re.findall(r"[a-z0-9]+", value.lower()) if token)


def _coerce_projection(item: Any) -> SkillProjection:
    if isinstance(item, SkillProjection):
        return item
    if isinstance(item, dict):
        return SkillProjection.from_dict(item)
    raise TypeError(f"Unsupported projection payload: {type(item)!r}")


def _match_all(values: Iterable[str], candidates: Sequence[str]) -> bool:
    pool = {value.strip().lower() for value in values if str(value).strip()}
    return pool.issubset({candidate.strip().lower() for candidate in candidates if str(candidate).strip()})


def _coerce_skill_items(result: Any) -> list[Any]:
    if result is None:
        return []
    if hasattr(result, "selected_skills"):
        result = getattr(result, "selected_skills")
    elif hasattr(result, "skills"):
        result = getattr(result, "skills")
    elif isinstance(result, dict):
        if "selected_skills" in result:
            result = result["selected_skills"]
        elif "skills" in result:
            result = result["skills"]
    if isinstance(result, list):
        return result
    if isinstance(result, tuple):
        return list(result)
    return []


def _extract_skill_id(item: Any) -> str:
    if isinstance(item, dict):
        for key in ("skill_id", "id", "slug"):
            value = item.get(key)
            if value:
                return str(value).strip()
    else:
        for key in ("skill_id", "id", "slug"):
            value = getattr(item, key, None)
            if value:
                return str(value).strip()
    return ""


def _extract_item_score(item: Any) -> float | None:
    score_value: Any = None
    if isinstance(item, dict):
        score_value = item.get("score", item.get("similarity"))
        distance = item.get("distance")
    else:
        score_value = getattr(item, "score", None)
        if score_value is None:
            score_value = getattr(item, "similarity", None)
        distance = getattr(item, "distance", None)
    if isinstance(distance, (int, float)) and not isinstance(distance, bool):
        return 1.0 / (1.0 + max(0.0, float(distance)))
    if isinstance(score_value, (int, float)) and not isinstance(score_value, bool):
        value = float(score_value)
        if value < 0:
            return 0.0
        if value <= 1.0:
            return value
        return value / (1.0 + value)
    return None


def _rank_boost(rank: int, raw_score: float | None) -> float:
    base = 1.0 / float(rank + 1)
    if raw_score is None:
        return base
    return max(base, raw_score)


def _normalize_score(value: float) -> float:
    return max(0.0, min(1.0, round(float(value), 6)))


def _parse_updated_at(value: str | None) -> float:
    if not value:
        return float("-inf")
    candidate = value.strip()
    if not candidate:
        return float("-inf")
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return float("-inf")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


class EngineSearchService:
    def __init__(
        self,
        registry_service: Any,
        *,
        tree_searcher: Any | None = None,
        vector_searcher: Any | None = None,
    ):
        self.registry_service = registry_service
        self.tree_searcher = tree_searcher if tree_searcher is not None else self._load_default_tree_searcher()
        self.vector_searcher = vector_searcher if vector_searcher is not None else self._load_default_vector_searcher()

    def search(self, request: FindSkillRequest | dict[str, Any] | str, **kwargs: Any) -> FindSkillResponse:
        normalized_request = self._coerce_request(request, **kwargs)
        projections = [_coerce_projection(item) for item in self.registry_service.list_skill_projections()]
        if normalized_request.skill_ids:
            allowed = {skill_id.lower() for skill_id in normalized_request.skill_ids}
            projections = [projection for projection in projections if projection.skill_id.lower() in allowed]

        filtered = [projection for projection in projections if self._matches_filters(projection, normalized_request)]
        enhancer_scores = self._collect_enhancer_scores(normalized_request.query, normalized_request.limit, filtered)
        scored = []
        for projection in filtered:
            components = self._score_components(projection, normalized_request.query)
            skill_key = projection.skill_id.lower()
            tree_score = enhancer_scores["tree"].get(skill_key, 0.0)
            vector_score = enhancer_scores["vector"].get(skill_key, 0.0)
            final_score = _normalize_score(
                0.45 * components["base_score"]
                + 0.15 * components["exact_bonus"]
                + 0.20 * tree_score
                + 0.20 * vector_score
            )
            metadata = dict(projection.metadata)
            metadata["score_components"] = {
                **components,
                "tree_score": tree_score,
                "vector_score": vector_score,
                "final_score": final_score,
            }
            scored.append(replace(projection, score=final_score, metadata=metadata))
        scored.sort(key=self._sort_key)
        limited = tuple(scored[: normalized_request.limit])
        return FindSkillResponse(request=normalized_request, skills=limited, total_count=len(filtered))

    def _coerce_request(self, request: FindSkillRequest | dict[str, Any] | str, **kwargs: Any) -> FindSkillRequest:
        if isinstance(request, FindSkillRequest):
            if kwargs:
                payload = request.to_dict()
                payload.update(kwargs)
                return FindSkillRequest.from_dict(payload)
            return request
        if isinstance(request, str):
            payload = {"query": request, **kwargs}
            return FindSkillRequest.from_dict(payload)
        payload = dict(request)
        payload.update(kwargs)
        return FindSkillRequest.from_dict(payload)

    def _matches_filters(self, projection: SkillProjection, request: FindSkillRequest) -> bool:
        if request.skill_type and projection.skill_type.lower() != request.skill_type.lower():
            return False
        if request.owner and (projection.owner or "").lower() != request.owner.lower():
            return False
        if request.risk_level and (projection.risk_level or "").lower() != request.risk_level.lower():
            return False
        if request.official_only is True and not projection.is_official:
            return False
        if request.tags and not _match_all(request.tags, projection.tags):
            return False
        return True

    def _load_default_tree_searcher(self) -> Any | None:
        try:
            from manager.tree import TreeManager

            return TreeManager()
        except Exception:
            return None

    def _load_default_vector_searcher(self) -> Any | None:
        try:
            from manager.vector import VectorManager

            return VectorManager()
        except Exception:
            return None

    def _search_enhancer(self, enhancer: Any, query: str, *, limit: int, source_name: str) -> list[Any]:
        if enhancer is None:
            return []
        search_fn = getattr(enhancer, "search", None)
        if search_fn is None and callable(enhancer):
            search_fn = enhancer
        if search_fn is None:
            return []

        attempts: tuple[tuple[tuple[Any, ...], dict[str, Any]], ...]
        if source_name == "vector":
            attempts = (
                ((query,), {"top_k": max(5, limit * 2)}),
                ((query,), {}),
            )
        else:
            attempts = (
                ((query,), {"verbose": False}),
                ((query,), {}),
            )

        for args, kwargs in attempts:
            try:
                return _coerce_skill_items(search_fn(*args, **kwargs))
            except TypeError:
                continue
            except Exception:
                return []
        return []

    def _collect_enhancer_scores(self, query: str, limit: int, projections: Sequence[SkillProjection]) -> dict[str, dict[str, float]]:
        allowed_ids = {projection.skill_id.lower() for projection in projections}
        scores: dict[str, dict[str, float]] = {"tree": {}, "vector": {}}
        for source_name, enhancer in (
            ("tree", self.tree_searcher),
            ("vector", self.vector_searcher),
        ):
            for rank, item in enumerate(self._search_enhancer(enhancer, query, limit=limit, source_name=source_name)):
                skill_id = _extract_skill_id(item).lower()
                if not skill_id or skill_id not in allowed_ids:
                    continue
                contribution = _normalize_score(_rank_boost(rank, _extract_item_score(item)))
                scores[source_name][skill_id] = max(scores[source_name].get(skill_id, 0.0), contribution)
        return scores

    def _score_components(self, projection: SkillProjection, query: str) -> dict[str, float]:
        tokens = _normalize_tokens(query)
        query_text = query.lower().strip()
        display_name = projection.display_name.lower()
        skill_id = projection.skill_id.lower()
        tags_text = " ".join(projection.tags).lower()
        outer_text = projection.outer_description.lower()
        inner_text = projection.inner_description.lower()

        base_raw = 0.0
        if not tokens:
            base_raw = 0.0
        else:
            haystack = " ".join(
                [
                    projection.skill_id,
                    projection.display_name,
                    projection.inner_description,
                    projection.outer_description,
                    " ".join(projection.tags),
                    projection.owner or "",
                    projection.risk_level or "",
                ]
            ).lower()
            if query_text and query_text in haystack:
                base_raw += 0.2
            for token in tokens:
                if token in skill_id:
                    base_raw += 0.25
                if token in display_name:
                    base_raw += 0.2
                if token in tags_text:
                    base_raw += 0.15
                if token in outer_text:
                    base_raw += 0.1
                if token in inner_text:
                    base_raw += 0.05
        base_score = _normalize_score(base_raw)
        exact_bonus = 1.0 if query_text and query_text in {skill_id, display_name} else 0.0
        return {
            "base_score": base_score,
            "exact_bonus": exact_bonus,
        }

    def _sort_key(self, item: SkillProjection) -> tuple[float, int, float, str]:
        return (
            -item.score,
            0 if item.is_official else 1,
            -_parse_updated_at(item.updated_at),
            item.skill_id.lower(),
        )
