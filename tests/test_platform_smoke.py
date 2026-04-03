from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "integration" / "src" / "python"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_skill_platform import AgentSkillPlatform, detect_platform_paths


def test_detect_platform_paths() -> None:
    paths = detect_platform_paths()
    paths.ensure_exists()
    assert paths.source_root.exists()
    assert paths.engineering_docs_root.exists()
    assert paths.contracts_root.exists()
    assert paths.runtime_root.exists()
    assert paths.lab_root.exists()
    assert paths.factory_root.exists()
    assert paths.registry_root_dir.exists()
    assert paths.upstream_snapshot_root.exists()


def test_validate_fixture_package() -> None:
    platform = AgentSkillPlatform()
    package_root = ROOT / "tests" / "fixtures" / "github-pr-review"
    report = platform.validate_package(package_root)
    assert report.ok is True


def test_build_install_bundle_fixture() -> None:
    platform = AgentSkillPlatform()
    package_root = ROOT / "tests" / "fixtures" / "github-pr-review"
    bundle = platform.build_install_bundle(package_root)
    assert bundle.default_action == "run"
    assert bundle.actions.has("validate") is True


def test_run_runtime_fixture() -> None:
    platform = AgentSkillPlatform()
    package_root = ROOT / "tests" / "fixtures" / "github-pr-review"
    payload = platform.run_runtime(package_root, action_input={"task": "review-pr"})
    assert payload["result"]["status"] == "completed"
    assert payload["feedback"]["skill_id"] == "github-pr-review"
    assert payload["result"]["payload"]["summary"] == "review-pr"


def test_skill_lab_project_smoke(tmp_path: Path) -> None:
    platform = AgentSkillPlatform()
    project_root = tmp_path / "skill-lab-project"

    init_payload = platform.init_skill_lab_project(project_root, project_name="Smoke Project", overwrite=True)
    assert Path(init_payload["project_root"]).exists()

    validate_payload = platform.validate_skill_lab_project(project_root)
    assert "candidate" in validate_payload

    run_payload = platform.run_skill_lab_project(project_root)
    assert run_payload["run_id"]

    submission = platform.build_promotion_submission(project_root, run_payload["run_id"])
    assert submission.candidate_slug
    assert Path(submission.bundle_path).exists()


def test_factory_pipeline_prepares_candidate_and_bundle(tmp_path: Path) -> None:
    platform = AgentSkillPlatform()
    project_root = tmp_path / "factory-lab-project"
    payload = platform.run_factory_pipeline(
        project_root,
        skill_name="Regression Candidate",
        workflow={
            "description": "Package repeatable regression handling into a governed skill.",
            "inputs": ["failure summary", "workflow notes"],
            "outputs": ["generated package", "gate summary"],
        },
        failure={
            "summary": "Users keep getting one-off responses instead of reusable skill packaging.",
            "tags": ["regression", "packaging"],
        },
        overwrite=True,
    )
    assert payload["ok"] is True
    assert Path(payload["candidate_path"]).exists()
    assert Path(payload["generated_dir"]).exists()
    assert Path(payload["bundle_path"]).exists()
    assert payload["gate_summary"]["ok"] is True


def test_registry_publish_install_feedback_and_promotion(tmp_path: Path) -> None:
    platform = AgentSkillPlatform()
    package_root = ROOT / "tests" / "fixtures" / "github-pr-review"
    registry_root = tmp_path / "registry"

    publish_payload = platform.publish_package(package_root, registry_root=registry_root)
    assert publish_payload["ok"] is True
    assert Path(publish_payload["bundle_path"]).exists()

    install_bundle = platform.resolve_install_bundle("github-pr-review", registry_root=registry_root)
    assert install_bundle["default_action"] == "run"

    runtime_payload = platform.run_runtime(package_root, action_input={"task": "registry-review"})
    feedback_payload = platform.ingest_feedback(runtime_payload["feedback"], registry_root=registry_root)
    assert feedback_payload["ok"] is True
    assert Path(feedback_payload["event_path"]).exists()

    project_root = tmp_path / "skill-lab-project"
    platform.init_skill_lab_project(project_root, project_name="Registry Smoke", overwrite=True)
    run_payload = platform.run_skill_lab_project(project_root)
    submission = platform.build_promotion_submission(project_root, run_payload["run_id"])
    promotion_payload = platform.submit_promotion(submission, registry_root=registry_root)
    assert promotion_payload["state"] == "PENDING_REVIEW"

    skill_payload = platform.get_registry_skill("github-pr-review", registry_root=registry_root)
    assert skill_payload["latest_version_id"] == "1.0.0"
    listed = platform.list_registry_skills(registry_root=registry_root)
    assert json.loads(json.dumps(listed))


def test_self_evolution_loop_smoke(tmp_path: Path) -> None:
    platform = AgentSkillPlatform()
    registry_root = tmp_path / "registry"
    project_root = tmp_path / "self-evolution-project"

    factory_payload = platform.run_factory_pipeline(
        project_root,
        skill_name="Skill Evolution Candidate",
        workflow={
            "description": "Convert repeated failure handling into a reusable governed skill package.",
            "target_user": "platform manager",
            "outputs": ["generated package", "gate summary", "submission bundle"],
        },
        failure={"summary": "A repeated failure needs to become a reusable skill candidate."},
        overwrite=True,
    )
    assert factory_payload["ok"] is True

    validate_payload = platform.validate_skill_lab_project(project_root)
    assert validate_payload["candidate"]["candidate_slug"] == "skill-evolution-candidate"

    run_payload = platform.run_skill_lab_project(project_root)
    assert run_payload["status"] in {"completed", "success", "finished"}

    submission = platform.build_promotion_submission(project_root, run_payload["run_id"])
    promotion_payload = platform.submit_promotion(submission, registry_root=registry_root)
    assert promotion_payload["state"] == "PENDING_REVIEW"

    publish_payload = platform.publish_package(factory_payload["generated_dir"], registry_root=registry_root)
    assert publish_payload["ok"] is True

    install_bundle = platform.resolve_install_bundle("skill-evolution-candidate", registry_root=registry_root)
    assert install_bundle["skill_id"] == "skill-evolution-candidate"
