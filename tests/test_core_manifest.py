"""Guard against accidental changes in the bundled calculation snapshot."""
import hashlib
import json
from pathlib import Path

def test_core_snapshot():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "core-manifest.json").read_text())
    assert manifest
    for path, digest in manifest.items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, path
