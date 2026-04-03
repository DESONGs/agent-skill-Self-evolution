from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_skill_platform import AgentSkillPlatform, detect_platform_paths


def test_detect_platform_paths() -> None:
    paths = detect_platform_paths()
    paths.ensure_exists()
    assert paths.agent_skill_os_src.exists()
    assert paths.autoresearch_src.exists()


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
