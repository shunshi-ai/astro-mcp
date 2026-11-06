"""本命盘组装：时间换算 → 行星 → 交点 → 宫位 → 相位。"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from . import ephemeris
from .aspects import find_aspects
from .constants import DEFAULT_HOUSE_SYSTEM, DEFAULT_NODE, SIGNS
from .houses import compute_houses, house_of
from .timeconv import local_to_utc, tz_name_at


class AstroInputError(ValueError):
    pass


def sign_of(lon: float) -> dict:
    """度分四舍五入到角分（同测测：14 项逐一吻合）。29°59.6′ 进位为下一座 0°00′。"""
    lon = lon % 360.0
    total_min = int(round(lon * 60.0)) % (360 * 60)
    idx = (total_min // 1800) % 12
    d, m = divmod(total_min % 1800, 60)
    deg_in_sign = lon - idx * 30.0 if lon >= idx * 30.0 else 0.0
    return {"sign": SIGNS[idx], "sign_index": idx, "deg": d, "min": m, "deg_in_sign": deg_in_sign}


def _point(lon: float, **extra) -> dict:
    return {"lon": lon % 360.0, **sign_of(lon), **extra}


# 一天内可能换座的行星（外行星一天移动 <0.25°，换座日照样标，但几率极低）
_DAY_RANGE_BODIES = ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
                     "uranus", "neptune", "pluto")


def _day_sign_ranges(local_date: datetime, tz_name: str) -> dict:
    """无时辰：当地 00:00 与 23:59 各排一次，标出当天换座的行星（太阳换座日、月亮每 2 天多）。"""
    start = local_to_utc(datetime.combine(local_date.date(), time(0, 0)), tz_name).utc
    end = local_to_utc(datetime.combine(local_date.date(), time(23, 59)), tz_name).utc
    ps, pe = ephemeris.planet_positions(start), ephemeris.planet_positions(end)
    out = {}
    for b in _DAY_RANGE_BODIES:
        s, e = sign_of(ps[b]["lon"])["sign"], sign_of(pe[b]["lon"])["sign"]
        out[b] = {"start_sign": s, "end_sign": e, "ambiguous": s != e}
    return out


def natal_chart(
    *,
    local: datetime,
    lat: float | None,
    lon: float | None,
    hour_unknown: bool = False,
    place_known: bool = True,
    tz_name: str | None = None,
    house_system: str = DEFAULT_HOUSE_SYSTEM,
) -> dict:
    """
    local: 出生地钟表时间（naive）。hour_unknown=True 时按当地 12:00 排行星，不出上升/宫位。
    lat/lon: 用于定时区与宫位；place_known=False（地点是兜底坐标）时只用来定时区，不出上升/宫位。
    tz_name: 显式时区（优先于坐标反查）。
    """
    if local.tzinfo is not None:
        raise AstroInputError("local 必须是 naive datetime")
    tz_source = "explicit"
    if tz_name is None:
        if lat is None or lon is None:
            raise AstroInputError("缺少坐标，无法确定时区")
        tz_name = tz_name_at(lat, lon)
        tz_source = "coords"

    calc_local = datetime.combine(local.date(), time(12, 0)) if hour_unknown else local
    conv = local_to_utc(calc_local, tz_name)
    utc = conv.utc
    if not (1850 <= utc.year <= 2149):
        raise AstroInputError("DE440s 星历只覆盖 1850–2149 年")

    raw = ephemeris.planet_positions(utc)
    nodes = ephemeris.lunar_nodes(utc)

    houses = None
    has_angles = (not hour_unknown) and place_known and lat is not None and lon is not None
    if has_angles:
        eps, gast = ephemeris.obliquity_and_gast(utc)
        ramc = (gast + lon) % 360.0
        houses = compute_houses(ramc, eps, lat, house_system)

    planets = {}
    for name, p in raw.items():
        extra = {"lat": p["lat"], "speed": p["speed"], "retrograde": p["retrograde"]}
        if houses:
            extra["house"] = house_of(p["lon"], houses["cusps"])
        planets[name] = _point(p["lon"], **extra)

    node_points = {
        # 默认交点（DEFAULT_NODE），展示与解读用这一对
        "north_node": _point(nodes[DEFAULT_NODE]),
        "south_node": _point(nodes[DEFAULT_NODE] + 180.0),
        "north_node_true": _point(nodes["true"]),
        "north_node_mean": _point(nodes["mean"]),
        "south_node_true": _point(nodes["true"] + 180.0),
        "south_node_mean": _point(nodes["mean"] + 180.0),
    }
    if houses:
        for v in node_points.values():
            v["house"] = house_of(v["lon"], houses["cusps"])

    aspect_points = {n: {"lon": p["lon"], "speed": p["speed"]} for n, p in planets.items()}
    angles = None
    if houses:
        angles = {
            "asc": _point(houses["asc"]),
            "mc": _point(houses["mc"]),
            "dsc": _point(houses["asc"] + 180.0),
            "ic": _point(houses["mc"] + 180.0),
        }
        # 上升/天顶参与相位（日速约 360°/天，近似视为固定点）
        aspect_points["asc"] = {"lon": houses["asc"], "speed": 0.0}
        aspect_points["mc"] = {"lon": houses["mc"], "speed": 0.0}

    return {
        "input": {
            "local": local.isoformat(),
            "calc_local": calc_local.isoformat(),
            "lat": lat,
            "lon": lon,
            "hour_unknown": hour_unknown,
            "place_known": place_known,
        },
        "time": {
            "utc": utc.isoformat(),
            "tz_name": conv.tz_name,
            "tz_source": tz_source,
            "utc_offset_hours": conv.utc_offset_hours,
            "ambiguity": conv.ambiguity,
        },
        "zodiac": "tropical",
        "node_type": DEFAULT_NODE,
        "planets": planets,
        "nodes": node_points,
        "angles": angles,
        "houses": (
            {
                "system": houses["system"],
                "requested_system": houses["requested_system"],
                "cusps": [_point(c) for c in houses["cusps"]],
            }
            if houses else None
        ),
        "aspects": find_aspects(aspect_points),
        # 无时辰时：每颗行星当天的落座区间；ambiguous=True 的那颗不能下定论
        "day_sign_ranges": _day_sign_ranges(local, tz_name) if hour_unknown else None,
    }
