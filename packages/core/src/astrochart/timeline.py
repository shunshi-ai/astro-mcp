"""区间扫描：行运时间线（入相 / 精确 / 离相日期）、逆行站点、换座日。

给 chat 回答「2027 年有什么行运」「水逆是哪几天」「土星哪天进白羊」用。
做法：每天 00:00 UTC 采样一次（向量化），在相邻两天之间找过零点，再二分细化到 ≈1 分钟。
日采样对行运足够：最快的行运体火星 ≤0.8°/天，慢行星 ≤0.25°/天，不会一天跨过整个容许度。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import ephemeris
from .constants import ASPECTS, PLANETS, SIGNS

_TARGET = dict(PLANETS)
SLOW_BODIES = ("jupiter", "saturn", "uranus", "neptune", "pluto")
STATION_BODIES = ("mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto")
MAX_SPAN_DAYS = 366 * 3 + 1
TIMELINE_PAD_DAYS = 160


def _signed(a: float) -> float:
    """归一到 (-180, 180]。"""
    d = a % 360.0
    return d - 360.0 if d > 180.0 else d


def _days(start: datetime, end: datetime, pad_days: int = 0) -> list[datetime]:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start/end 必须带时区（UTC）")
    if end <= start:
        raise ValueError("end 必须晚于 start")
    if (end - start).days > MAX_SPAN_DAYS:
        raise ValueError("区间最长 3 年")
    d0 = start.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    d0 -= timedelta(days=pad_days)
    n = (end - d0).days + 2 + pad_days
    return [d0 + timedelta(days=i) for i in range(n)]


def _bisect(f, a: datetime, b: datetime, fa: float, minutes: float = 1.0) -> datetime:
    """f(a) 与 f(b) 异号，二分到区间 < minutes。"""
    while (b - a) > timedelta(minutes=minutes):
        m = a + (b - a) / 2
        fm = f(m)
        if (fm < 0) == (fa < 0):
            a, fa = m, fm
        else:
            b = m
    return a + (b - a) / 2


def _natal_points(natal: dict) -> dict[str, float]:
    # 无出生时间：本命月亮 ±6°，不做行运对象（与 transits_to_natal 同口径）
    hour_unknown = (natal.get("input") or {}).get("hour_unknown")
    pts = {k: v["lon"] for k, v in natal["planets"].items() if not (hour_unknown and k == "moon")}
    if natal.get("angles"):
        pts["asc"] = natal["angles"]["asc"]["lon"]
        pts["mc"] = natal["angles"]["mc"]["lon"]
    return pts


def transit_timeline(natal: dict, start: datetime, end: datetime,
                     bodies: tuple[str, ...] = SLOW_BODIES, orb: float = 1.0) -> list[dict]:
    """区间内行运体对本命点的相位：每段「进入容许度 → 精确（逆行可多次）→ 离开」。

    返回按 start 排序；跨区间边界的段落标 starts_before / ends_after。
    """
    # 两头各多扫一段：跨边界的那一段也拿到真实的入相 / 精确 / 离相日（慢行星逆行一轮 < 160 天）
    days = _days(start, end, pad_days=TIMELINE_PAD_DAYS)
    points = _natal_points(natal)
    out: list[dict] = []
    for body in bodies:
        target = _TARGET[body]
        lons = ephemeris.body_longitudes(target, days)
        for nk, nlon in points.items():
            for kind, angle in ASPECTS:
                # 正负两侧各是一个精确点（合 / 冲只有一个）
                for side in ((angle,) if angle in (0, 180) else (angle, -angle)):
                    devs = [_signed(l - nlon - side) for l in lons]
                    out.extend(_segments(body, target, nk, nlon, kind, side, days, devs, orb, start, end))
    out.sort(key=lambda x: (x["start"], x["transit"], x["natal"]))
    return out


def _segments(body, target, nk, nlon, kind, side, days, devs, orb, start, end):
    def f(t):  # 偏离精确相位的有号角度
        return _signed(ephemeris.body_longitude(target, t) - nlon - side)

    def g(t):  # |偏离| - orb：过零 = 进出容许度
        return abs(f(t)) - orb

    segs, cur = [], None
    for i in range(len(days)):
        inside = abs(devs[i]) <= orb
        if inside and cur is None:
            if i == 0:
                cur = {"start": days[0], "starts_before": True, "exact": []}
            else:
                cur = {"start": _bisect(g, days[i - 1], days[i], abs(devs[i - 1]) - orb), "starts_before": False, "exact": []}
        if cur is not None and i > 0 and abs(devs[i - 1]) <= orb + 5 and (devs[i - 1] < 0) != (devs[i] < 0) \
                and abs(devs[i - 1] - devs[i]) < 90:
            cur["exact"].append(_bisect(f, days[i - 1], days[i], devs[i - 1]))
        if not inside and cur is not None:
            cur["end"] = _bisect(g, days[i - 1], days[i], abs(devs[i - 1]) - orb)
            cur["ends_after"] = False
            segs.append(cur)
            cur = None
    if cur is not None:
        cur["end"] = days[-1]
        cur["ends_after"] = True
        segs.append(cur)
    res = []
    for s in segs:
        if s["end"] < start or s["start"] > end:
            continue
        res.append({
            "transit": body, "natal": nk, "aspect": kind,
            "start": s["start"], "end": s["end"],
            # open_start / open_end：扫描窗口边缘仍在容许度内，真实起止更早 / 更晚
            "open_start": s["starts_before"], "open_end": s["ends_after"],
            "starts_before": s["start"] < start, "ends_after": s["end"] > end,
            "exact": s["exact"],
            "passes": len(s["exact"]),
        })
    return res


def _speed(target: str, t: datetime) -> float:
    a = ephemeris.body_longitude(target, t - timedelta(hours=12))
    b = ephemeris.body_longitude(target, t + timedelta(hours=12))
    return _signed(b - a)


def stations(start: datetime, end: datetime, bodies: tuple[str, ...] = STATION_BODIES) -> list[dict]:
    """区间内的留（站点）：kind=retrograde（转逆）/ direct（转顺），附当时黄经与星座。"""
    days = _days(start, end)
    out = []
    for body in bodies:
        target = _TARGET[body]
        lons = ephemeris.body_longitudes(target, days)
        sp = [_signed(lons[i + 1] - lons[i]) for i in range(len(lons) - 1)]
        for i in range(1, len(sp)):
            if (sp[i - 1] < 0) == (sp[i] < 0):
                continue
            # sp[i] 是 days[i]→days[i+1] 的平均速度，换向点落在 days[i-1]+12h ~ days[i+1]
            a, b = days[i - 1] + timedelta(hours=12), days[i] + timedelta(hours=12)
            t = _bisect(lambda x: _speed(target, x), a, b, _speed(target, a), minutes=10)
            if not (start <= t <= end):
                continue
            lon = ephemeris.body_longitude(target, t)
            out.append({"body": body, "kind": "retrograde" if sp[i] < 0 else "direct", "at": t,
                        "lon": lon, "sign": SIGNS[int(lon // 30)]})
    out.sort(key=lambda x: x["at"])
    return out


def ingresses(start: datetime, end: datetime, bodies: tuple[str, ...] = STATION_BODIES) -> list[dict]:
    """区间内的换座：body 在 at 时刻进入 sign（逆行退回上一个星座也算一次，retrograde=True）。"""
    days = _days(start, end)
    out = []
    for body in bodies:
        target = _TARGET[body]
        lons = ephemeris.body_longitudes(target, days)
        for i in range(1, len(lons)):
            s0, s1 = int(lons[i - 1] // 30), int(lons[i] // 30)
            if s0 == s1:
                continue
            forward = _signed(lons[i] - lons[i - 1]) > 0
            boundary = (s1 if forward else s0) * 30.0
            t = _bisect(lambda x: _signed(ephemeris.body_longitude(target, x) - boundary),
                        days[i - 1], days[i], _signed(lons[i - 1] - boundary))
            if not (start <= t <= end):
                continue
            out.append({"body": body, "at": t, "sign": SIGNS[s1], "from_sign": SIGNS[s0],
                        "retrograde": not forward})
    out.sort(key=lambda x: x["at"])
    return out
