"""从 NASA JPL Horizons 拉测试盘行星视黄经，冻结为 golden_horizons.json。

Horizons 是与 Skyfield 完全独立的实现，作为第一把尺子。
QUANTITIES=31：地心、黄道与春分点 of date、含光行时/光行差/引力偏折的视位置。

用法（只在改测试盘清单时跑）：
    python packages/astro/tests/tools/fetch_horizons_golden.py
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent / "src"))

from charts import CHARTS  # noqa: E402
from astrochart.timeconv import local_to_utc, tz_name_at  # noqa: E402

BODIES = {
    "sun": "10", "moon": "301", "mercury": "199", "venus": "299", "mars": "499",
    "jupiter": "599", "saturn": "699", "uranus": "799", "neptune": "899", "pluto": "999",
}
API = "https://ssd.jpl.nasa.gov/api/horizons.api"


def jd_ut(dt):
    return dt.timestamp() / 86400.0 + 2440587.5


def fetch(body_id, jds):
    params = {
        "format": "json",
        "COMMAND": f"'{body_id}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "'500@399'",
        "TLIST": "'" + " ".join(f"{j:.8f}" for j in jds) + "'",
        "TLIST_TYPE": "JD",
        "TIME_TYPE": "UT",
        "QUANTITIES": "'31'",
        "ANG_FORMAT": "DEG",
        "CSV_FORMAT": "YES",
        "EXTRA_PREC": "YES",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=120) as r:
        res = json.loads(r.read())["result"]
    rows = res.split("$$SOE")[1].split("$$EOE")[0].strip().splitlines()
    out = []
    for row in rows:
        cols = [c.strip() for c in row.split(",")]
        nums = [c for c in cols if c and _isnum(c)]
        # CSV 列：日期, (标志列), ObsEcLon, ObsEcLat
        out.append((float(nums[-2]), float(nums[-1])))
    if len(out) != len(jds):
        raise RuntimeError(f"{body_id}: 期望 {len(jds)} 行，拿到 {len(out)}")
    return out


def _isnum(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def main():
    meta = []
    for name, local, lat, lon in CHARTS:
        conv = local_to_utc(local, tz_name_at(lat, lon))
        meta.append({"name": name, "local": local.isoformat(), "lat": lat, "lon": lon,
                     "tz_name": conv.tz_name, "utc": conv.utc.isoformat()})
    from datetime import datetime
    jds = [jd_ut(datetime.fromisoformat(m["utc"])) for m in meta]
    for m in meta:
        m["planets"] = {}
    # Horizons 按时间先后重排 TLIST 后返回，按排序后的下标对回去
    order = sorted(range(len(jds)), key=lambda i: jds[i])
    for body, bid in BODIES.items():
        rows = fetch(bid, [jds[i] for i in order])
        for i, (elon, elat) in zip(order, rows):
            meta[i]["planets"][body] = {"lon": elon, "lat": elat}
        time.sleep(1)
    out = HERE.parent / "golden_horizons.json"
    out.write_text(json.dumps({
        "source": "NASA JPL Horizons API, QUANTITIES=31 (geocentric apparent ecliptic of date)",
        "charts": meta,
    }, ensure_ascii=False, indent=1))
    print(f"wrote {out} ({len(meta)} charts)")


if __name__ == "__main__":
    main()
