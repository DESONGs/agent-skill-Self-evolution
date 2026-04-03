from __future__ import annotations

from pathlib import Path

from ...core.packs.loader import load_pack_manifest


PACK_DIR = Path(__file__).resolve().parent
MANIFEST = load_pack_manifest(PACK_DIR / "pack.yaml")


def get_manifest():
    return MANIFEST
