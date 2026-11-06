"""行星视黄经（真黄道 + 当日春分点，回归黄道）。

星历：NASA JPL DE440s（1849–2150）。文件 ≈32MB 不进 git，路径取
环境变量 ASTRO_EPHEMERIS_PATH，缺省 ~/.cache/shunshi-astro/de440s.bsp。
进程内只加载一次。
"""
from __future__ import annotations

import math
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path

from .constants import PLANETS

DEFAULT_EPHEMERIS_PATH = Path.home() / ".cache" / "shunshi-astro" / "de440s.bsp"

_lock = threading.Lock()
_state: dict = {}


def _load():
    if "eph" in _state:
        return _state["ts"], _state["eph"]
    with _lock:
        if "eph" not in _state:
            from skyfield.api import load

            path = Path(os.environ.get("ASTRO_EPHEMERIS_PATH") or DEFAULT_EPHEMERIS_PATH)
            if not path.exists():
                raise FileNotFoundError(
                    f"星历文件不存在: {path}。下载: "
                    "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440s.bsp"
                )
            # builtin=True：用内置 ΔT / 闰秒表，不联网
            _state["ts"] = load.timescale(builtin=True)
            _state["eph"] = load(str(path))
    return _state["ts"], _state["eph"]


def _t(utc: datetime):
    ts, _ = _load()
    return ts.from_datetime(utc)


def _apparent_lonlat(t, target: str) -> tuple[float, float]:
    from skyfield.framelib import ecliptic_frame

    _, eph = _load()
    lat, lon, _ = eph["earth"].at(t).observe(eph[target]).apparent().frame_latlon(ecliptic_frame)
    # 转 Python 原生 float：numpy 标量进 JSON 会序列化失败（numpy.bool 尤甚）
    return float(lon.degrees) % 360.0, float(lat.degrees)


def _signed_delta(a: float, b: float) -> float:
    """a - b 归一到 (-180, 180]。"""
    d = (a - b) % 360.0
    return d - 360.0 if d > 180.0 else d


def planet_positions(utc: datetime) -> dict[str, dict]:
    """10 大行星：黄经、黄纬、日速度（度/天）、是否逆行。"""
    t0 = _t(utc)
    t_minus = _t(utc - timedelta(hours=12))
    t_plus = _t(utc + timedelta(hours=12))
    out = {}
    for name, target in PLANETS:
        lon, lat = _apparent_lonlat(t0, target)
        lon_m, _ = _apparent_lonlat(t_minus, target)
        lon_p, _ = _apparent_lonlat(t_plus, target)
        speed = _signed_delta(lon_p, lon_m)  # 跨度正好 1 天
        out[name] = {
            "lon": lon,
            "lat": lat,
            "speed": speed,
            "retrograde": bool(speed < 0),
        }
    return out


def lunar_nodes(utc: datetime) -> dict[str, float]:
    """北交点：mean（平均）与 true（密切，osculating）两种。南交点 = +180°。"""
    from skyfield.framelib import ecliptic_frame

    t = _t(utc)
    _, eph = _load()

    # 平均交点：Meeus《天文算法》47.7
    T = (t.tt - 2451545.0) / 36525.0
    mean = (125.0445479 - 1934.1362891 * T + 0.0020754 * T**2
            + T**3 / 467441.0 - T**4 / 60616000.0) % 360.0

    # 密切交点：月球地心几何位置 × 速度 = 轨道法向量 h，升交点黄经 = atan2(hx, -hy)
    rel = (eph["moon"] - eph["earth"]).at(t)
    r, v = rel.frame_xyz_and_velocity(ecliptic_frame)
    rx, ry, rz = r.au
    vx, vy, vz = v.au_per_d
    hx = ry * vz - rz * vy
    hy = rz * vx - rx * vz
    true = math.degrees(math.atan2(float(hx), float(-hy))) % 360.0

    return {"mean": float(mean), "true": float(true)}


def obliquity_and_gast(utc: datetime) -> tuple[float, float]:
    """真黄赤交角（度）与格林尼治视恒星时（度）。"""
    t = _t(utc)
    _dpsi, deps = t._nutation_angles_radians
    eps = math.degrees(float(t._mean_obliquity_radians + deps))
    return eps, float(t.gast * 15.0) % 360.0


def sun_longitude(utc: datetime) -> float:
    """只算太阳视黄经（名人库批量算太阳星座用，比 planet_positions 便宜 30 倍）。"""
    return _apparent_lonlat(_t(utc), "sun")[0]


def sun_longitudes(utcs: list[datetime]) -> list[float]:
    """批量算太阳视黄经：一次向量化调用（名人库 4000+ 个时刻 <1s；逐个调用要 40s+）。"""
    from skyfield.framelib import ecliptic_frame

    if not utcs:
        return []
    ts, eph = _load()
    t = ts.from_datetimes(utcs)
    _, lon, _ = eph["earth"].at(t).observe(eph["sun"]).apparent().frame_latlon(ecliptic_frame)
    return [float(x) % 360.0 for x in lon.degrees]


def body_longitudes(target: str, utcs: list[datetime]) -> list[float]:
    """批量算某天体视黄经（target 为 PLANETS 里的星历名）：区间扫描行运 / 站点用，一次向量化。"""
    from skyfield.framelib import ecliptic_frame

    if not utcs:
        return []
    ts, eph = _load()
    t = ts.from_datetimes(utcs)
    _, lon, _ = eph["earth"].at(t).observe(eph[target]).apparent().frame_latlon(ecliptic_frame)
    return [float(x) % 360.0 for x in lon.degrees]


def body_longitude(target: str, utc: datetime) -> float:
    return _apparent_lonlat(_t(utc), target)[0]
