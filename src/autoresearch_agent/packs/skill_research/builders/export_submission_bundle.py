from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import hashlib
import zipfile


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def export_submission_bundle(
    run_dir: str | Path,
    candidate_slug: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    run_root = Path(run_dir)
    artifacts_dir = run_root / "artifacts"
    run_manifest = _read_json(run_root / "run_manifest.json")
    summary = _read_json(run_root / "summary.json")
    result = _read_json(run_root / "result.json")

    resolved_candidate_slug = candidate_slug or str(
        run_manifest.get("candidate_slug")
        or summary.get("candidate_slug")
        or result.get("candidate_slug")
        or "candidate"
    )
    resolved_run_id = run_id or str(run_manifest.get("run_id") or summary.get("run_id") or run_root.name)
    resolved_candidate_id = str(
        run_manifest.get("candidate_id")
        or summary.get("candidate_id")
        or result.get("candidate_id")
        or ""
    )

    submission_dir = run_root / "submissions" / f"{resolved_candidate_slug}-{resolved_run_id}"
    submission_dir.mkdir(parents=True, exist_ok=True)

    generated_package = artifacts_dir / "generated_skill_package"
    if not generated_package.exists():
        raise FileNotFoundError(f"generated package missing: {generated_package}")

    bundle_zip = submission_dir / "skill-package.zip"
    with zipfile.ZipFile(bundle_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(p for p in generated_package.rglob("*") if p.is_file()):
            zf.write(path, arcname=str(path.relative_to(generated_package)))

    submission_manifest = {
        "schema_version": "skill.lab.submission.v1",
        "run_id": resolved_run_id,
        "candidate_id": resolved_candidate_id,
        "candidate_slug": resolved_candidate_slug,
        "package_path": str(bundle_zip.relative_to(run_root)),
        "package_sha256": _sha256(bundle_zip),
        "artifacts_dir": str(artifacts_dir.relative_to(run_root)),
        "generated_package_dir": str(generated_package.relative_to(run_root)),
        "submitted_at": _now_iso(),
        "source_run_manifest": str((run_root / "run_manifest.json").relative_to(run_root)),
    }
    submission_manifest_path = submission_dir / "submission_manifest.json"
    submission_manifest_path.write_text(
        json.dumps(submission_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "ok": True,
        "run_id": resolved_run_id,
        "candidate_id": resolved_candidate_id,
        "candidate_slug": resolved_candidate_slug,
        "submission_dir": str(submission_dir),
        "submission_root": str(submission_dir),
        "bundle_path": str(bundle_zip),
        "package_path": str(bundle_zip),
        "submission_manifest_path": str(submission_manifest_path),
        "submission_manifest": submission_manifest,
        "package_sha256": submission_manifest["package_sha256"],
        "generated_package_dir": str(generated_package),
        "artifacts_dir": str(artifacts_dir),
    }
