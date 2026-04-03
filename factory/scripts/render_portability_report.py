#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def band_for(score: int) -> str:
    if score >= 97:
        return "world-class"
    if score >= 93:
        return "excellent"
    if score >= 85:
        return "strong"
    return "developing"


def build_report(root: Path) -> dict:
    interface_doc = load_yaml(root / "agents" / "interface.yaml")
    compatibility = interface_doc.get("compatibility", {})
    activation = compatibility.get("activation", {})
    execution = compatibility.get("execution", {})
    trust = compatibility.get("trust", {})
    degradation = compatibility.get("degradation", {})
    targets = compatibility.get("adapter_targets", [])
    expectations = load_json(root / "evals" / "packaging_expectations.json")
    contracts_doc = (root / "references" / "packaging-contracts.md").exists()
    matrix_doc = (root / "references" / "platform-capability-matrix.md").exists()
    snapshot_files = list((root / "tests" / "snapshots").glob("*_adapter.json"))

    breakdown = {
        "canonical_neutral_source": 15 if (root / "SKILL.md").exists() and (root / "agents" / "interface.yaml").exists() else 0,
        "adapter_target_coverage": 15 if len(targets) >= 3 else 10 if len(targets) >= 2 else 5 if len(targets) >= 1 else 0,
        "activation_metadata": 10
        if activation.get("mode") and activation.get("paths") is not None
        else 5
        if activation.get("mode")
        else 0,
        "execution_metadata": 10
        if execution.get("context") and execution.get("shell")
        else 0,
        "trust_boundary_metadata": 15
        if trust.get("source_tier") and trust.get("remote_inline_execution") and trust.get("remote_metadata_policy")
        else 0,
        "degradation_strategy_coverage": 10 if all(degradation.get(target) for target in targets) else 0,
        "contract_and_expectation_coverage": 15
        if contracts_doc and expectations.get("required_targets") == targets
        else 5
        if contracts_doc
        else 0,
    }

    snapshot_score = 0
    if matrix_doc:
        snapshot_score += 5
    if len(snapshot_files) >= len(targets):
        snapshot_score += 5
    breakdown["consumer_validation_and_snapshots"] = snapshot_score

    score = sum(breakdown.values())
    return {
        "ok": score >= 95,
        "score": score,
        "band": band_for(score),
        "summary": {
            "adapter_target_count": len(targets),
            "activation_mode": activation.get("mode"),
            "execution_context": execution.get("context"),
            "shell": execution.get("shell"),
            "trust_level": trust.get("source_tier"),
            "remote_inline_execution": trust.get("remote_inline_execution"),
            "degradation_coverage": sum(1 for target in targets if degradation.get(target)),
            "snapshot_count": len(snapshot_files),
        },
        "breakdown": breakdown,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Portability Score",
        "",
        f"- score: `{report['score']}/100`",
        f"- band: `{report['band']}`",
        f"- adapter targets: `{report['summary']['adapter_target_count']}`",
        f"- activation mode: `{report['summary']['activation_mode']}`",
        f"- execution context: `{report['summary']['execution_context']}`",
        f"- shell: `{report['summary']['shell']}`",
        f"- trust level: `{report['summary']['trust_level']}`",
        f"- remote inline execution: `{report['summary']['remote_inline_execution']}`",
        "",
        "| Component | Score |",
        "| --- | ---: |",
    ]
    for name, value in report["breakdown"].items():
        lines.append(f"| `{name}` | {value} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a portability score from neutral metadata, contracts, and snapshots.")
    parser.add_argument("--output-json", default="reports/portability_score.json")
    parser.add_argument("--output-md", default="reports/portability_score.md")
    args = parser.parse_args()

    report = build_report(ROOT)
    output_json = ROOT / args.output_json
    output_md = ROOT / args.output_md
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
