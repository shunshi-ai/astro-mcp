"""比较盘（synastry）：两张本命盘之间的相位 + 叠宫。纯计算，好坏标签在服务层。

输入是两张 natal_chart() 的结果。约定：
- 只算主相位；外行星（天/海/冥）之间不算 —— 同龄人共有，不是这两个人的事；北交点 × 外行星同理不算。
- 轴点之间要算（上升合上升、天顶合天顶在合盘里有意义；本命盘里轴点间是宫制决定的才不算）。
- 容许度对齐爱星盘默认（10-09 同盘逐条比对：位置 / 叠宫 / 共有相位全一致，差异只在容许度）。
- 无时辰的一方：月亮一天走 ~13°，位置不可信 → 不参与相位也不参与叠宫；
  它没有宫位 → 别人的星落不进它的宫（叠宫只出另一个方向）。
"""
from __future__ import annotations

from .constants import ASPECTS
from .houses import house_of

# 比较盘容许度：合冲拱刑 6、六合 4，日月参与 +1（同爱星盘默认）；北交点只看紧的（3°）
SYN_ORBS = {
    "conjunction": 6.0,
    "opposition": 6.0,
    "square": 6.0,
    "trine": 6.0,
    "sextile": 4.0,
}
SYN_LUMINARY_BONUS = 1.0
NODE_ORB = 3.0
GENERATIONAL = frozenset({"uranus", "neptune", "pluto"})
_ANGLES = ("asc", "mc")


def _sep(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return 360.0 - d if d > 180.0 else d


def _points(chart: dict) -> dict[str, float]:
    hour_unknown = (chart.get("input") or {}).get("hour_unknown")
    pts = {k: v["lon"] for k, v in chart["planets"].items() if not (hour_unknown and k == "moon")}
    if chart.get("angles"):
        for k in _ANGLES:
            pts[k] = chart["angles"][k]["lon"]
    node = (chart.get("nodes") or {}).get("north_node")
    if node:
        pts["north_node"] = node["lon"]
    return pts


def synastry_aspects(a: dict, b: dict) -> list[dict]:
    """A 的点 × B 的点。返回 [{a, b, aspect, angle, orb}]，按容许度从紧到松。"""
    out = []
    for ka, la in _points(a).items():
        for kb, lb in _points(b).items():
            slow = GENERATIONAL | {"north_node"}
            if ka in slow and kb in slow:
                continue
            sep = _sep(la, lb)
            node = "north_node" in (ka, kb)
            bonus = SYN_LUMINARY_BONUS if {ka, kb} & {"sun", "moon"} and not node else 0.0
            for kind, angle in ASPECTS:
                orb = abs(sep - angle)
                if orb <= (NODE_ORB if node else SYN_ORBS[kind] + bonus):
                    out.append({"a": ka, "b": kb, "aspect": kind, "angle": angle, "orb": round(orb, 4)})
                    break
    out.sort(key=lambda x: x["orb"])
    return out


def house_overlay(src: dict, dst: dict) -> list[dict]:
    """src 的行星（+ 上升 / 天顶 / 北交点）落在 dst 的第几宫。dst 没有宫位（无时辰 / 地点不详）→ []。"""
    houses = dst.get("houses")
    if not houses:
        return []
    cusps = [c["lon"] for c in houses["cusps"]]
    return [{"planet": k, "house": house_of(lon, cusps)} for k, lon in _points(src).items()]


# ── 组合盘 / 马盘（10-09 合盘报告用）──────────────────────────────────────
# 组合盘 = 两人每个点取中点（走短弧），宫头也取中点（中点法，测测 / 爱星盘默认）；
# 马盘（Marks）= 组合盘与某一方本命盘再取中点 —— 读「这一方在关系里的感受」。
# 某个点只有一方有（无时辰没有月亮 / 轴点）就不出这个点；宫头要两边都有才出。

def midpoint(l1: float, l2: float) -> float:
    d = ((l2 - l1 + 540.0) % 360.0) - 180.0
    return (l1 + d / 2.0) % 360.0


def _cusps(chart: dict) -> list[float] | None:
    h = chart.get("houses")
    if h and h.get("cusps"):
        return [c["lon"] if isinstance(c, dict) else c for c in h["cusps"]]
    return chart.get("cusps")          # 组合盘 / 马盘自己的形状


def _mid_chart(pa: dict[str, float], pb: dict[str, float], ca: list[float] | None, cb: list[float] | None) -> dict:
    from .aspects import find_aspects
    pts = {k: midpoint(pa[k], pb[k]) for k in pa if k in pb}
    cusps = [midpoint(x, y) for x, y in zip(ca, cb)] if ca and cb else None
    houses = {k: house_of(v, cusps) for k, v in pts.items()} if cusps else {}
    aspect_pts = {k: {"lon": v} for k, v in pts.items() if k != "north_node"}
    return {"points": pts, "cusps": cusps, "houses": houses, "aspects": find_aspects(aspect_pts)}


def composite_chart(a: dict, b: dict) -> dict:
    return _mid_chart(_points(a), _points(b), _cusps(a), _cusps(b))


def marks_chart(composite: dict, natal: dict) -> dict:
    return _mid_chart(composite["points"], _points(natal), composite.get("cusps"), _cusps(natal))
