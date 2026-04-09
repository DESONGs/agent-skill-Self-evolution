from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..models import CandidateProposal


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = str(value)
    safe = text and all(ch.isalnum() or ch in {"-", "_", ".", "/", ":"} for ch in text)
    if safe:
        return text
    escaped = text.replace('"', '\\"')
    return f'"{escaped}"'


class ProposalAdapter:
    def to_candidate_payload(
        self,
        proposal: CandidateProposal,
        *,
        owner: str = "agent-skill-platform",
        target_user: str = "platform engineer",
        recurring_job: str | None = None,
        source_kind: str = "case-proposal",
    ) -> dict[str, Any]:
        case = proposal.case
        case_metadata = dict(case.metadata)
        proposal_metadata = dict(proposal.metadata)
        evidence_metadata = dict(case.evidence.metadata)
        summary = case.pattern.summary or proposal.change_summary or case.pattern.problem_type
        trigger_description = (
            case_metadata.get("trigger_description")
            or evidence_metadata.get("trigger_description")
            or summary
        )
        problem_statement = case_metadata.get("problem_statement") or summary
        candidate_id = proposal_metadata.get("candidate_id") or proposal.proposal_id.replace("proposal-", "candidate-")
        candidate_slug = proposal_metadata.get("candidate_slug") or candidate_id.replace("_", "-").lower()
        skill_name = proposal.target_skill_name or case.source.skill_id or case.pattern.problem_type
        normalized_recurring_job = recurring_job or case.pattern.problem_type or proposal.change_summary
        return {
            "schema_version": "skill.candidate.v1",
            "candidate": {
                "id": candidate_id,
                "slug": candidate_slug,
                "title": proposal_metadata.get("candidate_title") or skill_name,
                "source_kind": source_kind,
                "created_at": proposal.created_at,
                "status": "normalized",
                "editable_target": "workspace/candidate.yaml",
            },
            "sources": {
                "refs": list(case.evidence.artifact_refs),
                "normalized_summary": {
                    "recurring_job": normalized_recurring_job,
                    "outputs": list(proposal_metadata.get("outputs") or ["generated package", "gate summary", "submission bundle"]),
                    "exclusions": list(
                        proposal_metadata.get("exclusions")
                        or ["runtime execution internals", "registry schema internals"]
                    ),
                    "evidence_tags": list(case.pattern.tags) or list(proposal_metadata.get("evidence_tags") or []),
                },
            },
            "qualification": {
                "should_be_skill": proposal.decision.mode != "ignore",
                "reasons": list(proposal_metadata.get("reasons") or [proposal.decision.reason, case.pattern.problem_type]),
                "target_user": target_user,
                "problem_statement": problem_statement,
            },
            "skill": {
                "name": skill_name,
                "description": proposal_metadata.get("skill_description") or summary,
                "trigger_description": trigger_description,
                "anti_triggers": list(proposal_metadata.get("anti_triggers") or ["one-off explanation", "translation only", "brainstorm only"]),
                "boundary": {
                    "owns": list(proposal_metadata.get("boundary_owns") or ["skill packaging", "trigger routing", "eval bundle generation"]),
                    "does_not_own": list(
                        proposal_metadata.get("boundary_does_not_own")
                        or ["runtime execution internals", "registry schema internals"]
                    ),
                },
                "workflow": {
                    "inputs": list(proposal_metadata.get("workflow_inputs") or ["candidate spec", "source refs", "gate cases"]),
                    "steps": list(proposal_metadata.get("workflow_steps") or ["normalize", "materialize", "evaluate", "promote"]),
                    "outputs": list(proposal_metadata.get("workflow_outputs") or ["generated package", "gate summary", "submission bundle"]),
                },
            },
            "actions": {
                "default_action": proposal_metadata.get("default_action") or "materialize_package",
                "items": [
                    {
                        "id": "materialize_package",
                        "kind": "script",
                        "entry": "scripts/materialize_package.py",
                        "runtime": "python3",
                        "timeout_sec": 120,
                        "sandbox": "workspace-write",
                    },
                    {
                        "id": "evaluate_package",
                        "kind": "script",
                        "entry": "scripts/evaluate_package.py",
                        "runtime": "python3",
                        "timeout_sec": 120,
                        "sandbox": "workspace-write",
                    },
                ],
            },
            "package": {
                "target_platforms": list(proposal_metadata.get("target_platforms") or ["openai", "claude", "generic"]),
                "include_references": True,
                "include_scripts": True,
                "include_evals": True,
                "include_reports": False,
                "layout_profile": "standard_skill_package",
            },
            "governance": {
                "owner": owner,
                "maturity_tier": proposal_metadata.get("maturity_tier") or "production",
                "lifecycle_stage": proposal_metadata.get("lifecycle_stage") or "library",
                "review_cadence": proposal_metadata.get("review_cadence") or "quarterly",
                "context_budget_tier": proposal_metadata.get("context_budget_tier") or "production",
                "risk_level": proposal_metadata.get("risk_level") or "medium",
                "trust": {
                    "source_tier": proposal_metadata.get("source_tier") or "local",
                    "remote_inline_execution": proposal_metadata.get("remote_inline_execution") or "forbid",
                    "remote_metadata_policy": proposal_metadata.get("remote_metadata_policy") or "allow-metadata-only",
                },
            },
            "lab": {
                "pack_id": "skill_research",
                "gate_profile": proposal_metadata.get("gate_profile") or "balanced",
                "mutation_axes": list(
                    proposal_metadata.get("mutation_axes")
                    or ["trigger_description", "boundary", "actions", "eval_coverage", "governance"]
                ),
                "baseline_refs": list(proposal_metadata.get("baseline_refs") or case.evidence.artifact_refs),
                "metrics": dict(proposal_metadata.get("metrics") or {}),
                "last_run_id": case.source.run_id,
            },
            "promotion": {
                "state": proposal_metadata.get("promotion_state") or "draft",
                "mode": proposal_metadata.get("promotion_mode") or "automatic_or_manual",
                "submission_bundle": proposal_metadata.get("submission_bundle") or "",
                "published_skill_ref": proposal_metadata.get("published_skill_ref") or "",
            },
        }

    def to_candidate_yaml(
        self,
        proposal: CandidateProposal,
        *,
        owner: str = "agent-skill-platform",
        target_user: str = "platform engineer",
        recurring_job: str | None = None,
        source_kind: str = "case-proposal",
    ) -> str:
        payload = self.to_candidate_payload(
            proposal,
            owner=owner,
            target_user=target_user,
            recurring_job=recurring_job,
            source_kind=source_kind,
        )
        lines: list[str] = ["schema_version: skill.candidate.v1", "candidate:"]
        candidate = payload["candidate"]
        for key in ("id", "slug", "title", "source_kind", "created_at", "status", "editable_target"):
            lines.append(f"  {key}: {_yaml_scalar(candidate[key])}")
        lines.extend(["", "sources:", "  refs:"])
        refs = payload["sources"]["refs"]
        if refs:
            for ref in refs:
                lines.append(f"    - {_yaml_scalar(ref)}")
        else:
            lines.append("    []")
        lines.extend(
            [
                "  normalized_summary:",
                f"    recurring_job: {_yaml_scalar(payload['sources']['normalized_summary']['recurring_job'])}",
                "    outputs:",
            ]
        )
        for item in payload["sources"]["normalized_summary"]["outputs"]:
            lines.append(f"      - {_yaml_scalar(item)}")
        lines.append("    exclusions:")
        for item in payload["sources"]["normalized_summary"]["exclusions"]:
            lines.append(f"      - {_yaml_scalar(item)}")
        lines.append("    evidence_tags:")
        tags = payload["sources"]["normalized_summary"]["evidence_tags"]
        if tags:
            for item in tags:
                lines.append(f"      - {_yaml_scalar(item)}")
        else:
            lines.append("      []")
        lines.extend(
            [
                "",
                "qualification:",
                f"  should_be_skill: {_yaml_scalar(payload['qualification']['should_be_skill'])}",
                "  reasons:",
            ]
        )
        for item in payload["qualification"]["reasons"]:
            lines.append(f"    - {_yaml_scalar(item)}")
        lines.extend(
            [
                f"  target_user: {_yaml_scalar(payload['qualification']['target_user'])}",
                f"  problem_statement: {_yaml_scalar(payload['qualification']['problem_statement'])}",
                "",
                "skill:",
                f"  name: {_yaml_scalar(payload['skill']['name'])}",
                f"  description: {_yaml_scalar(payload['skill']['description'])}",
                f"  trigger_description: {_yaml_scalar(payload['skill']['trigger_description'])}",
                "  anti_triggers:",
            ]
        )
        for item in payload["skill"]["anti_triggers"]:
            lines.append(f"    - {_yaml_scalar(item)}")
        lines.extend(["  boundary:", "    owns:"])
        for item in payload["skill"]["boundary"]["owns"]:
            lines.append(f"      - {_yaml_scalar(item)}")
        lines.append("    does_not_own:")
        for item in payload["skill"]["boundary"]["does_not_own"]:
            lines.append(f"      - {_yaml_scalar(item)}")
        lines.extend(["  workflow:", "    inputs:"])
        for item in payload["skill"]["workflow"]["inputs"]:
            lines.append(f"      - {_yaml_scalar(item)}")
        lines.append("    steps:")
        for item in payload["skill"]["workflow"]["steps"]:
            lines.append(f"      - {_yaml_scalar(item)}")
        lines.append("    outputs:")
        for item in payload["skill"]["workflow"]["outputs"]:
            lines.append(f"      - {_yaml_scalar(item)}")
        lines.extend(["", "actions:", f"  default_action: {_yaml_scalar(payload['actions']['default_action'])}", "  items:"])
        for action in payload["actions"]["items"]:
            lines.extend(
                [
                    f"    - id: {_yaml_scalar(action['id'])}",
                    f"      kind: {_yaml_scalar(action['kind'])}",
                    f"      entry: {_yaml_scalar(action['entry'])}",
                    f"      runtime: {_yaml_scalar(action['runtime'])}",
                    f"      timeout_sec: {_yaml_scalar(action['timeout_sec'])}",
                    f"      sandbox: {_yaml_scalar(action['sandbox'])}",
                ]
            )
        lines.extend(
            [
                "",
                "package:",
                "  target_platforms:",
            ]
        )
        for item in payload["package"]["target_platforms"]:
            lines.append(f"    - {_yaml_scalar(item)}")
        lines.extend(
            [
                f"  include_references: {_yaml_scalar(payload['package']['include_references'])}",
                f"  include_scripts: {_yaml_scalar(payload['package']['include_scripts'])}",
                f"  include_evals: {_yaml_scalar(payload['package']['include_evals'])}",
                f"  include_reports: {_yaml_scalar(payload['package']['include_reports'])}",
                f"  layout_profile: {_yaml_scalar(payload['package']['layout_profile'])}",
                "",
                "governance:",
                f"  owner: {_yaml_scalar(payload['governance']['owner'])}",
                f"  maturity_tier: {_yaml_scalar(payload['governance']['maturity_tier'])}",
                f"  lifecycle_stage: {_yaml_scalar(payload['governance']['lifecycle_stage'])}",
                f"  review_cadence: {_yaml_scalar(payload['governance']['review_cadence'])}",
                f"  context_budget_tier: {_yaml_scalar(payload['governance']['context_budget_tier'])}",
                f"  risk_level: {_yaml_scalar(payload['governance']['risk_level'])}",
                "  trust:",
                f"    source_tier: {_yaml_scalar(payload['governance']['trust']['source_tier'])}",
                f"    remote_inline_execution: {_yaml_scalar(payload['governance']['trust']['remote_inline_execution'])}",
                f"    remote_metadata_policy: {_yaml_scalar(payload['governance']['trust']['remote_metadata_policy'])}",
                "",
                "lab:",
                f"  pack_id: {_yaml_scalar(payload['lab']['pack_id'])}",
                f"  gate_profile: {_yaml_scalar(payload['lab']['gate_profile'])}",
                "  mutation_axes:",
            ]
        )
        for item in payload["lab"]["mutation_axes"]:
            lines.append(f"    - {_yaml_scalar(item)}")
        lines.append("  baseline_refs:")
        if payload["lab"]["baseline_refs"]:
            for item in payload["lab"]["baseline_refs"]:
                lines.append(f"    - {_yaml_scalar(item)}")
        else:
            lines.append("    []")
        lines.extend(
            [
                f"  metrics: {_yaml_scalar(payload['lab']['metrics'])}",
                f"  last_run_id: {_yaml_scalar(payload['lab']['last_run_id'])}",
                "",
                "promotion:",
                f"  state: {_yaml_scalar(payload['promotion']['state'])}",
                f"  mode: {_yaml_scalar(payload['promotion']['mode'])}",
                f"  submission_bundle: {_yaml_scalar(payload['promotion']['submission_bundle'])}",
                f"  published_skill_ref: {_yaml_scalar(payload['promotion']['published_skill_ref'])}",
            ]
        )
        return "\n".join(lines) + "\n"

    def write_candidate_file(
        self,
        proposal: CandidateProposal,
        output_path: str | Path,
        *,
        owner: str = "agent-skill-platform",
        target_user: str = "platform engineer",
        recurring_job: str | None = None,
        source_kind: str = "case-proposal",
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self.to_candidate_yaml(
                proposal,
                owner=owner,
                target_user=target_user,
                recurring_job=recurring_job,
                source_kind=source_kind,
            ),
            encoding="utf-8",
        )
        return path


def adapt_proposal_to_candidate(
    proposal: CandidateProposal,
    *,
    owner: str = "agent-skill-platform",
    target_user: str = "platform engineer",
    recurring_job: str | None = None,
    source_kind: str = "case-proposal",
) -> dict[str, Any]:
    return ProposalAdapter().to_candidate_payload(
        proposal,
        owner=owner,
        target_user=target_user,
        recurring_job=recurring_job,
        source_kind=source_kind,
    )
