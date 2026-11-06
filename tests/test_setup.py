import hashlib
from pathlib import Path
import pytest
from shunshi_astro_mcp import setup


class Response:
    url = setup.URL
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, size):
        payload, self.payload = self.payload, b""
        return payload


def test_verified_download_and_cached_reuse(tmp_path, monkeypatch):
    target = tmp_path / "ephemeris.bsp"
    payload = b"test ephemeris"
    calls = []
    monkeypatch.setenv("ASTRO_EPHEMERIS_PATH", str(target))
    monkeypatch.setattr(setup, "SHA256", hashlib.sha256(payload).hexdigest())
    def fetch(url, timeout):
        calls.append((url, timeout))
        return Response(payload)
    monkeypatch.setattr(setup.urllib.request, "urlopen", fetch)
    assert setup.download_ephemeris() == target
    assert target.read_bytes() == payload
    assert setup.download_ephemeris() == target
    assert calls == [(setup.URL, 30)]


def test_bad_download_never_installs_and_cleans_temporary_file(tmp_path, monkeypatch):
    target = tmp_path / "ephemeris.bsp"
    monkeypatch.setenv("ASTRO_EPHEMERIS_PATH", str(target))
    monkeypatch.setattr(setup.urllib.request, "urlopen", lambda *a, **kw: Response(b"corrupt"))
    with pytest.raises(ValueError, match="checksum"):
        setup.download_ephemeris()
    assert not target.exists()
    assert not list(tmp_path.iterdir())


def test_existing_unknown_file_is_preserved(tmp_path, monkeypatch):
    target = tmp_path / "ephemeris.bsp"
    target.write_bytes(b"user file")
    monkeypatch.setenv("ASTRO_EPHEMERIS_PATH", str(target))
    with pytest.raises(ValueError, match="checksum"):
        setup.download_ephemeris()
    assert target.read_bytes() == b"user file"
