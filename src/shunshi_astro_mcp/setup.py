"""Explicit, bounded and atomic NASA ephemeris setup."""
import hashlib
import os
from pathlib import Path
import tempfile
import urllib.request

URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440s.bsp"
SHA256 = "c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2"
MAX_BYTES = 64 * 1024 * 1024

def _sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def download_ephemeris():
    path = Path(os.environ.get("ASTRO_EPHEMERIS_PATH") or Path.home() / ".cache/shunshi-astro/de440s.bsp")
    if path.exists():
        if _sha(path) != SHA256:
            raise ValueError("existing ephemeris checksum mismatch; choose another ASTRO_EPHEMERIS_PATH")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as target:
            tmp = Path(target.name)
            with urllib.request.urlopen(URL, timeout=30) as response:
                if not response.url.startswith("https://ssd.jpl.nasa.gov/"):
                    raise ValueError("unexpected ephemeris redirect")
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError("ephemeris download exceeds size limit")
                    target.write(chunk)
        if _sha(tmp) != SHA256:
            raise ValueError("NASA ephemeris checksum mismatch")
        os.replace(tmp, path)
        return path
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
