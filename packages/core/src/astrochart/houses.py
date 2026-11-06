"""上升 / 天顶 / 宫位。

- ASC、MC：球面天文解析公式。
- Placidus：按半昼弧 / 半夜弧三等分迭代（11、12、2、3 宫），对宫 +180°。
- 整宫制：上升所在星座 0° 起每宫 30°。
- Porphyry：ASC–MC 四个象限各按黄经三等分。
- |纬度| ≥ 90° − 黄赤交角 时 Placidus 无解（极圈内有不升不落的黄道段），自动退 Porphyry
  （同 Swiss Ephemeris / astro.com 的回退）。
"""
from __future__ import annotations

import math

_D2R = math.pi / 180.0
_R2D = 180.0 / math.pi


def _norm(x: float) -> float:
    return x % 360.0


def asc_mc(ramc: float, eps: float, lat: float) -> tuple[float, float]:
    """ramc=地方恒星时（度），eps=真黄赤交角，lat=地理纬度。返回 (ASC, MC) 黄经。"""
    r, e, f = ramc * _D2R, eps * _D2R, lat * _D2R
    mc = math.atan2(math.sin(r), math.cos(r) * math.cos(e)) * _R2D
    asc = math.atan2(math.cos(r), -(math.sin(r) * math.cos(e) + math.tan(f) * math.sin(e))) * _R2D
    return _norm(asc), _norm(mc)


def _ra_to_ecl_lon(ra: float, eps: float) -> float:
    """黄道上一点：赤经 → 黄经。"""
    a, e = ra * _D2R, eps * _D2R
    return _norm(math.atan2(math.sin(a), math.cos(a) * math.cos(e)) * _R2D)


def _decl_of_ecl_lon(lon: float, eps: float) -> float:
    return math.asin(math.sin(eps * _D2R) * math.sin(lon * _D2R)) * _R2D


def placidus_supported(lat: float, eps: float) -> bool:
    return abs(lat) < 90.0 - eps


def _placidus_cusp(ramc: float, eps: float, lat: float, frac: float, above: bool) -> float:
    """above=True：从 MC 往东取半昼弧的 frac（11 宫 1/3，12 宫 2/3）。
    above=False：从 IC 往回取半夜弧的 frac（3 宫 1/3，2 宫 2/3）。"""
    tan_phi = math.tan(lat * _D2R)
    ra = ramc + (90.0 * frac if above else 180.0 - 90.0 * frac)
    lon = _ra_to_ecl_lon(ra, eps)
    for _ in range(100):
        decl = _decl_of_ecl_lon(lon, eps)
        x = tan_phi * math.tan(decl * _D2R)
        x = max(-1.0, min(1.0, x))
        ad = math.asin(x) * _R2D  # 上升差
        if above:
            ra = ramc + frac * (90.0 + ad)
        else:
            ra = ramc + 180.0 - frac * (90.0 - ad)
        new_lon = _ra_to_ecl_lon(ra, eps)
        if abs(((new_lon - lon + 180.0) % 360.0) - 180.0) < 1e-9:
            return new_lon
        lon = new_lon
    raise ArithmeticError(f"Placidus 未收敛 ramc={ramc} lat={lat} frac={frac}")


def placidus(ramc: float, eps: float, lat: float) -> list[float]:
    asc, mc = asc_mc(ramc, eps, lat)
    c11 = _placidus_cusp(ramc, eps, lat, 1.0 / 3.0, above=True)
    c12 = _placidus_cusp(ramc, eps, lat, 2.0 / 3.0, above=True)
    c2 = _placidus_cusp(ramc, eps, lat, 2.0 / 3.0, above=False)
    c3 = _placidus_cusp(ramc, eps, lat, 1.0 / 3.0, above=False)
    cusps = [asc, c2, c3, mc + 180.0, c11 + 180.0, c12 + 180.0,
             asc + 180.0, c2 + 180.0, c3 + 180.0, mc, c11, c12]
    return [_norm(c) for c in cusps]


def porphyry(asc: float, mc: float) -> list[float]:
    ic, dsc = mc + 180.0, asc + 180.0
    q1 = (ic - asc) % 360.0      # 1→4 宫
    q2 = (dsc - ic) % 360.0      # 4→7 宫
    cusps = [asc, asc + q1 / 3, asc + 2 * q1 / 3,
             ic, ic + q2 / 3, ic + 2 * q2 / 3]
    cusps += [c + 180.0 for c in cusps]
    return [_norm(c) for c in cusps]


def whole_sign(asc: float) -> list[float]:
    start = math.floor(asc / 30.0) * 30.0
    return [_norm(start + 30.0 * i) for i in range(12)]


def compute_houses(ramc: float, eps: float, lat: float, system: str = "placidus") -> dict:
    asc, mc = asc_mc(ramc, eps, lat)
    used = system
    if system == "placidus" and not placidus_supported(lat, eps):
        used = "porphyry"
    if used == "placidus":
        cusps = placidus(ramc, eps, lat)
    elif used == "porphyry":
        cusps = porphyry(asc, mc)
    elif used == "whole_sign":
        cusps = whole_sign(asc)
    else:
        raise ValueError(f"不支持的宫位制: {system}")
    return {
        "system": used,
        "requested_system": system,
        "asc": asc,
        "mc": mc,
        "cusps": cusps,
    }


def house_of(lon: float, cusps: list[float]) -> int:
    """黄经落在第几宫（1–12）。"""
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        span = (b - a) % 360.0
        if (lon - a) % 360.0 < span:
            return i + 1
    return 12
