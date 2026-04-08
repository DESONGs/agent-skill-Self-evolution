from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_skill_platform.engine.search import EngineSearchService

if str(SRC) in sys.path:
    sys.path.remove(str(SRC))


class FakeRegistryService:
    def __init__(self, projections: list[dict[str, object]]):
        self._projections = projections

    def list_skill_projections(self) -> list[dict[str, object]]:
        return list(self._projections)


class FakeSearchWorker:
    def __init__(self, results: list[dict[str, object]]):
        self.results = results
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def search(self, *args: object, **kwargs: object) -> list[dict[str, object]]:
        self.calls.append((args, dict(kwargs)))
        return list(self.results)


def _projection(
    skill_id: str,
    display_name: str,
    *,
    updated_at: str | None = None,
    is_official: bool = False,
    inner_description: str = "",
    outer_description: str = "",
    tags: list[str] | None = None,
) -> dict[str, object]:
    return {
        "skill_id": skill_id,
        "display_name": display_name,
        "type": "script",
        "inner_description": inner_description,
        "outer_description": outer_description,
        "tags": tags or [],
        "updated_at": updated_at,
        "is_official": is_official,
        "metadata": {"package_root": f"/tmp/{skill_id}"},
        "package_root": f"/tmp/{skill_id}",
    }


def test_find_skill_falls_back_to_registry_projection_when_enhancers_are_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(EngineSearchService, "_load_default_tree_searcher", lambda self: None)
    monkeypatch.setattr(EngineSearchService, "_load_default_vector_searcher", lambda self: None)

    service = EngineSearchService(
        FakeRegistryService([
            _projection("alpha", "Alpha"),
            _projection("beta", "Beta"),
        ])
    )

    response = service.search({"query": "", "limit": 10})

    assert response.total_count == 2
    assert [skill.skill_id for skill in response.skills] == ["alpha", "beta"]

    payload = response.to_dict()
    assert "package_root" not in payload["skills"][0]
    assert "package_root" not in payload["skills"][1]
    assert "package_root" not in payload["skills"][0]["metadata"]
    assert "package_root" not in payload["skills"][1]["metadata"]
    assert "score_components" in payload["skills"][0]["metadata"]


def test_find_skill_uses_lexical_scoring_when_enhancers_are_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(EngineSearchService, "_load_default_tree_searcher", lambda self: None)
    monkeypatch.setattr(EngineSearchService, "_load_default_vector_searcher", lambda self: None)

    service = EngineSearchService(
        FakeRegistryService([
            _projection("alpha", "Alpha Tool", outer_description="General tool for alpha workflows"),
            _projection("beta", "Beta Utility", outer_description="Beta workflows"),
        ])
    )

    response = service.search({"query": "tool", "limit": 10})

    assert [skill.skill_id for skill in response.skills] == ["alpha", "beta"]
    assert response.skills[0].score > response.skills[1].score
    assert response.skills[0].metadata["score_components"]["base_score"] > 0
    assert response.skills[0].metadata["score_components"]["exact_bonus"] == 0.0


def test_find_skill_prioritizes_exact_matches_over_partial_lexical_matches(monkeypatch) -> None:
    monkeypatch.setattr(EngineSearchService, "_load_default_tree_searcher", lambda self: None)
    monkeypatch.setattr(EngineSearchService, "_load_default_vector_searcher", lambda self: None)

    service = EngineSearchService(
        FakeRegistryService([
            _projection("alpha", "Alpha Tool", outer_description="alpha"),
            _projection("alphabet", "Alphabet Helper", outer_description="alpha"),
        ])
    )

    response = service.search({"query": "alpha", "limit": 10})

    assert [skill.skill_id for skill in response.skills] == ["alpha", "alphabet"]
    assert response.skills[0].metadata["score_components"]["exact_bonus"] == 1.0
    assert response.skills[1].metadata["score_components"]["exact_bonus"] == 0.0
    assert response.skills[0].score > response.skills[1].score


def test_find_skill_uses_injected_tree_and_vector_searchers_without_introducing_out_of_projection_skills() -> None:
    tree_searcher = FakeSearchWorker([
        {"skill_id": "outsider", "score": 1.0},
        {"skill_id": "beta", "score": 0.95},
    ])
    vector_searcher = FakeSearchWorker([
        {"skill_id": "outsider-vector", "similarity": 1.0},
        {"skill_id": "alpha", "similarity": 0.4},
    ])
    service = EngineSearchService(
        FakeRegistryService([
            _projection("alpha", "Alpha"),
            _projection("beta", "Beta"),
        ]),
        tree_searcher=tree_searcher,
        vector_searcher=vector_searcher,
    )

    response = service.search({"query": "", "limit": 10})

    assert tree_searcher.calls
    assert vector_searcher.calls
    assert [skill.skill_id for skill in response.skills] == ["beta", "alpha"]
    assert all(skill.skill_id != "outsider" for skill in response.skills)
    assert response.skills[0].score > response.skills[1].score
    assert response.skills[0].metadata["score_components"]["tree_score"] > 0
    assert response.skills[1].metadata["score_components"]["vector_score"] > 0
    assert "package_root" not in response.to_dict()["skills"][0]


def test_find_skill_uses_deterministic_tie_break_when_scores_match(monkeypatch) -> None:
    monkeypatch.setattr(EngineSearchService, "_load_default_tree_searcher", lambda self: None)
    monkeypatch.setattr(EngineSearchService, "_load_default_vector_searcher", lambda self: None)

    service = EngineSearchService(
        FakeRegistryService([
            _projection("gamma", "Gamma", updated_at="2025-01-03T00:00:00Z", is_official=False),
            _projection("alpha", "Alpha", updated_at="2025-01-02T00:00:00Z", is_official=True),
            _projection("delta", "Delta", updated_at="2025-01-01T00:00:00Z", is_official=True),
            _projection("beta", "Beta", updated_at="2025-01-01T00:00:00Z", is_official=True),
        ])
    )

    response = service.search({"query": "", "limit": 10})

    assert [skill.skill_id for skill in response.skills] == ["alpha", "beta", "delta", "gamma"]
    assert response.skills[0].metadata["score_components"]["final_score"] == response.skills[0].score
