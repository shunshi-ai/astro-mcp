"""主相位：合 / 六合 / 刑 / 拱 / 冲，含入相（applying）/ 出相（separating）。"""
from __future__ import annotations

from .constants import ASPECT_ORBS, ASPECTS, ORB_BONUS

# 轴点之间的角度由宫位制决定，不是相位（astro.com 也不列）
_ANGLES = {"asc", "mc"}


def _sep(a: float, b: float) -> float:
    """两点黄经夹角，0–180。"""
    d = abs(a - b) % 360.0
    return 360.0 - d if d > 180.0 else d


def find_aspects(points: dict[str, dict]) -> list[dict]:
    """points: 名 → {"lon": 度, "speed": 度/天（可缺省，视为 0）}。"""
    names = list(points)
    out = []
    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            if n1 in _ANGLES and n2 in _ANGLES:
                continue
            p1, p2 = points[n1], points[n2]
            sep = _sep(p1["lon"], p2["lon"])
            for kind, angle in ASPECTS:
                orb_limit = ASPECT_ORBS[kind] + max(ORB_BONUS.get(n1, 0.0), ORB_BONUS.get(n2, 0.0))
                orb = abs(sep - angle)
                if orb > orb_limit:
                    continue
                # 0.01 天后的容许度变小 = 入相
                dt = 0.01
                sep_later = _sep(
                    p1["lon"] + p1.get("speed", 0.0) * dt,
                    p2["lon"] + p2.get("speed", 0.0) * dt,
                )
                applying = abs(sep_later - angle) < orb
                out.append({
                    "p1": n1,
                    "p2": n2,
                    "aspect": kind,
                    "angle": angle,
                    "orb": round(orb, 4),
                    "applying": applying,
                })
                break
    out.sort(key=lambda a: a["orb"])
    return out
