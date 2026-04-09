from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _clear_modules(prefixes: tuple[str, ...]) -> None:
    for name in list(sys.modules):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
            sys.modules.pop(name, None)


def _prepare_modules():
    _clear_modules(("agent_skill_platform", "orchestrator"))

    pkg = types.ModuleType("agent_skill_platform")
    pkg.__path__ = [str(ROOT / "src" / "agent_skill_platform")]
    sys.modules["agent_skill_platform"] = pkg

    lab_pkg = types.ModuleType("agent_skill_platform.lab")
    lab_pkg.__path__ = [str(ROOT / "src" / "agent_skill_platform" / "lab")]
    sys.modules["agent_skill_platform.lab"] = lab_pkg

    orch_pkg = types.ModuleType("orchestrator")
    orch_pkg.__path__ = [str(ROOT / "src" / "orchestrator")]
    sys.modules["orchestrator"] = orch_pkg

    orch_runtime_pkg = types.ModuleType("orchestrator.runtime")
    orch_runtime_pkg.__path__ = [str(ROOT / "src" / "orchestrator" / "runtime")]
    sys.modules["orchestrator.runtime"] = orch_runtime_pkg

    models = _load_module("agent_skill_platform.models", ROOT / "src" / "agent_skill_platform" / "models.py")
    _load_module("agent_skill_platform.paths", ROOT / "src" / "agent_skill_platform" / "paths.py")
    case_store = _load_module("agent_skill_platform.lab.case_store", ROOT / "src" / "agent_skill_platform" / "lab" / "case_store.py")
    case_analyzer = _load_module("agent_skill_platform.lab.case_analyzer", ROOT / "src" / "agent_skill_platform" / "lab" / "case_analyzer.py")
    decider = _load_module("agent_skill_platform.lab.decider", ROOT / "src" / "agent_skill_platform" / "lab" / "decider.py")
    proposal_adapter = _load_module("agent_skill_platform.lab.proposal_adapter", ROOT / "src" / "agent_skill_platform" / "lab" / "proposal_adapter.py")
    promotion_orchestrator = _load_module(
        "agent_skill_platform.lab.promotion_orchestrator",
        ROOT / "src" / "agent_skill_platform" / "lab" / "promotion_orchestrator.py",
    )
    outcome_store = _load_module("agent_skill_platform.lab.outcome_store", ROOT / "src" / "agent_skill_platform" / "lab" / "outcome_store.py")
    envelope = _load_module("orchestrator.runtime.envelope", ROOT / "src" / "orchestrator" / "runtime" / "envelope.py")
    return models, case_store, case_analyzer, decider, proposal_adapter, promotion_orchestrator, outcome_store, envelope


def _feedback(envelope_module, *, success: bool = False):
    return envelope_module.RunFeedbackEnvelope(
        run_id="run-123",
        mode="direct",
        skill_id="github-pr-review",
        version_id="1.0.0",
        action_id="run",
        success=success,
        latency_ms=42,
        artifact_count=2,
        error_code="TIMEOUT",
        metadata={
            "summary": "runtime timed out while resolving the action",
            "artifact_refs": ["artifacts/report.md", "artifacts/log.txt"],
            "target_layer": "scripts",
            "patch_targets": ["scripts/run.py"],
            "tags": ["timeout", "regression"],
        },
    )


def test_feedback_to_case_and_patch_first_decision(tmp_path: pathlib.Path) -> None:
    models, case_store, case_analyzer, decider, proposal_adapter, _, outcome_store, envelope = _prepare_modules()

    feedback = _feedback(envelope)
    case = case_analyzer.analyze_feedback_case(feedback)

    assert case.case_id == "case-run-123-run"
    assert case.source.skill_id == "github-pr-review"
    assert case.pattern.problem_type == "execution_failure"
    assert case.delta.recommended_evolution == "patch"

    proposal = decider.Decider().decide(case)
    assert proposal.decision.mode == "patch"
    assert proposal.target_layer == "scripts"

    payload = proposal_adapter.adapt_proposal_to_candidate(proposal)
    assert payload["schema_version"] == "skill.candidate.v1"
    assert payload["candidate"]["editable_target"] == "workspace/candidate.yaml"
    assert payload["skill"]["name"] == "github-pr-review"
    assert payload["qualification"]["should_be_skill"] is True

    store = case_store.CaseStore(tmp_path / "backend")
    save_result = case_store.save_case_record(case, root=store.root)
    assert pathlib.Path(save_result["case_path"]).exists()
    loaded_case = store.load_case(case.case_id)
    assert loaded_case == case

    analyzer = case_analyzer.CaseAnalyzer()
    analyze_result = analyzer.analyze_and_store(feedback, store=store)
    assert analyze_result["ok"] is True
    assert pathlib.Path(analyze_result["case_path"]).exists()

    outcome = models.OutcomeRecord(
        outcome_id="outcome-run-123",
        case_id=case.case_id,
        proposal_id=proposal.proposal_id,
        status="patched",
        summary="prepared patch-first proposal",
        result_ref="reports/outcome.md",
        metadata={"case_id": case.case_id},
    )
    outcome_store_result = outcome_store.save_outcome_record(outcome, root=tmp_path / "backend")
    assert pathlib.Path(outcome_store_result["outcome_path"]).exists()
    assert outcome_store.OutcomeStore(tmp_path / "backend").load_outcome(outcome.outcome_id) == outcome


def test_decision_object_roundtrip_and_adapter_yaml_shape() -> None:
    models, _, case_analyzer, decider, proposal_adapter, _, _, envelope = _prepare_modules()

    feedback = _feedback(envelope)
    case = case_analyzer.analyze_feedback_case(feedback)
    decision = models.EvolutionDecision.patch_first(case)
    assert decision.mode == "patch"

    proposal = decider.Decider().decide(case)
    payload = proposal_adapter.ProposalAdapter().to_candidate_payload(proposal, owner="demo-owner", target_user="demo-user")
    assert payload["governance"]["owner"] == "demo-owner"
    assert payload["qualification"]["target_user"] == "demo-user"
    assert payload["lab"]["last_run_id"] == "run-123"
    assert "materialize_package" in {item["id"] for item in payload["actions"]["items"]}

    yaml_text = proposal_adapter.ProposalAdapter().to_candidate_yaml(proposal)
    assert "schema_version: skill.candidate.v1" in yaml_text
    assert "workspace/candidate.yaml" in yaml_text


def test_promotion_submission_lineage_roundtrip() -> None:
    models, *_ = _prepare_modules()

    submission = models.PromotionSubmission(
        candidate_id="candidate-123",
        candidate_slug="candidate-123",
        run_id="run-123",
        bundle_path="/tmp/candidate.zip",
        bundle_sha256="abc123",
        lineage={
            "case_id": "case-123",
            "proposal_id": "proposal-456",
            "decision_mode": "patch",
        },
        metadata={"submission_root": "/tmp/submission-root"},
    )

    payload = submission.to_dict()
    assert payload["lineage"]["case_id"] == "case-123"
    assert payload["lineage"]["proposal_id"] == "proposal-456"
    assert payload["lineage"]["decision_mode"] == "patch"
    assert payload["metadata"]["case_id"] == "case-123"
    assert payload["metadata"]["proposal_id"] == "proposal-456"
    assert payload["metadata"]["decision_mode"] == "patch"
    assert payload["metadata"]["lineage"]["case_id"] == "case-123"
    assert payload["metadata"]["submission_root"] == "/tmp/submission-root"

    roundtrip = models.PromotionSubmission.from_dict(payload)
    assert roundtrip.lineage == payload["lineage"]
    assert roundtrip.metadata["submission_root"] == "/tmp/submission-root"


def test_lab_promotion_orchestrator_ignored_branch_persists_ignored_outcome(tmp_path: pathlib.Path) -> None:
    models, _, _, _, _, promotion_orchestrator, _, envelope = _prepare_modules()

    orchestrator = promotion_orchestrator.LabPromotionOrchestrator(
        backend_root=tmp_path / "backend",
        registry_root=tmp_path / "registry",
    )
    result = orchestrator.promote_feedback(_feedback(envelope, success=True))

    assert result.status == "ignored"
    assert result.candidate_ref is None
    assert result.promotion_submission is None
    assert result.decision_mode == "ignore"
    assert pathlib.Path(result.case_path or "").exists()
    assert pathlib.Path(result.outcome_path or "").exists()
    loaded_outcome = models.OutcomeRecord.from_dict(
        json.loads((tmp_path / "backend" / "outcomes" / f"{result.outcome_id}.json").read_text(encoding="utf-8"))
    )
    assert loaded_outcome.status == "ignored"
    assert loaded_outcome.proposal_id == result.proposal_id


def test_lab_promotion_orchestrator_promotes_and_records_lineage(tmp_path: pathlib.Path) -> None:
    models, _, _, _, _, promotion_orchestrator, _, envelope = _prepare_modules()

    orchestrator = promotion_orchestrator.LabPromotionOrchestrator(
        backend_root=tmp_path / "backend",
        registry_root=tmp_path / "registry",
    )
    result = orchestrator.promote_feedback(_feedback(envelope, success=False))

    assert result.status == "promoted"
    assert result.candidate_ref is not None
    assert result.promotion_submission is not None
    assert result.decision_mode == "patch"
    assert result.promotion_submission["lineage"]["case_id"] == result.case_id
    assert result.promotion_submission["lineage"]["proposal_id"] == result.proposal_id
    assert result.promotion_submission["lineage"]["decision_mode"] == "patch"
    assert result.promotion_submission["submission"]["metadata"]["case_id"] == result.case_id
    assert result.promotion_submission["submission"]["metadata"]["proposal_id"] == result.proposal_id
    assert result.promotion_submission["submission"]["metadata"]["decision_mode"] == "patch"
    assert result.outcome_path is not None and pathlib.Path(result.outcome_path).exists()
    assert pathlib.Path(result.candidate_ref).exists()
    stored_outcome = models.OutcomeRecord.from_dict(
        json.loads(pathlib.Path(result.outcome_path).read_text(encoding="utf-8"))
    )
    assert stored_outcome.status == "promoted"
    assert stored_outcome.result_ref == result.promotion_submission["submission_path"] or stored_outcome.result_ref == result.candidate_ref


class _FailingRegistryService:
    def submit_promotion(self, submission):
        raise RuntimeError("registry intake unavailable")


def test_lab_promotion_orchestrator_records_failed_outcome_on_registry_error(tmp_path: pathlib.Path) -> None:
    models, _, _, _, _, promotion_orchestrator, _, envelope = _prepare_modules()

    orchestrator = promotion_orchestrator.LabPromotionOrchestrator(
        backend_root=tmp_path / "backend",
        registry_root=tmp_path / "registry",
        registry_service=_FailingRegistryService(),
    )
    result = orchestrator.promote_feedback(_feedback(envelope, success=False))

    assert result.status == "failed"
    assert result.error == "registry intake unavailable"
    assert result.candidate_ref is not None
    assert result.promotion_submission is None
    assert pathlib.Path(result.outcome_path or "").exists()
    failed_outcome = models.OutcomeRecord.from_dict(
        json.loads(pathlib.Path(result.outcome_path).read_text(encoding="utf-8"))
    )
    assert failed_outcome.status == "failed"
    assert failed_outcome.metadata["error"] == "registry intake unavailable"
