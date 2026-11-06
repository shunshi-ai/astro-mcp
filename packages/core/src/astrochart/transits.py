"""行运：某一时刻天上的行星与本命盘的相位（「今日行运」）。

只取紧密相位（默认 ≤1.5°），不含行运月亮（几小时就换位置，日更页面意义不大）。
"""
from __future__ import annotations

from datetime import datetime

from . import ephemeris
from .constants import ASPECTS

TRANSIT_BODIES = ("sun", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto")
SLOW = {"jupiter", "saturn", "uranus", "neptune", "pluto"}


def _sep(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return 360.0 - d if d > 180.0 else d


def transits_to_natal(natal: dict, utc: datetime, orb_limit: float = 1.5) -> list[dict]:
    now = ephemeris.planet_positions(utc)
    # 无出生时间的盘按当地正午排：本命月亮可差 ±6°，远大于行运容许度，打月亮的相位不可信 → 不出
    hour_unknown = (natal.get("input") or {}).get("hour_unknown")
    targets = {k: {"lon": v["lon"]} for k, v in natal["planets"].items()
               if not (hour_unknown and k == "moon")}
    if natal.get("angles"):
        targets["asc"] = {"lon": natal["angles"]["asc"]["lon"]}
        targets["mc"] = {"lon": natal["angles"]["mc"]["lon"]}
    out = []
    for tb in TRANSIT_BODIES:
        tp = now[tb]
        for nk, npt in targets.items():
            sep = _sep(tp["lon"], npt["lon"])
            for kind, angle in ASPECTS:
                orb = abs(sep - angle)
                if orb > orb_limit:
                    continue
                later = _sep(tp["lon"] + tp["speed"] * 0.1, npt["lon"])
                out.append({
                    "transit": tb, "natal": nk, "aspect": kind, "orb": round(orb, 3),
                    "applying": abs(later - angle) < orb, "retrograde": tp["retrograde"],
                    "slow": tb in SLOW,
                })
                break
    # 慢行星优先（影响期长、更值得说），同档按容许度
    out.sort(key=lambda x: (not x["slow"], x["orb"]))
    return out
