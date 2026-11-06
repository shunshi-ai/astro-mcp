"""出生地钟表时间 → UTC。

西洋占星用钟表时间换世界时，**不做真太阳时**（经度影响由宫位计算吸收）。
时区一律走 IANA tzdata：韩国 1987–88 夏令时、1954–61 年 UTC+8:30、
中国 1986–91 夏令时、日本 1948–51 夏令时都由 tzdata 自带，不手写偏移表。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class UtcResult:
    utc: datetime
    tz_name: str
    utc_offset_hours: float
    # None=正常；"overlap"=夏令时回拨的重复时刻（取第一次出现）；
    # "gap"=夏令时拨快跳过的不存在时刻（按切换前偏移解释）
    ambiguity: str | None


_TF = None


def _tf():
    global _TF
    if _TF is None:
        from timezonefinder import TimezoneFinder
        _TF = TimezoneFinder()
    return _TF


# 新疆钟表走北京时间,但 tzdata 的 Asia/Urumqi(及旧名 Asia/Kashgar)是 UTC+6 → 乌鲁木齐出生的盘
# UTC 晚 2 小时、上升差约 30°(2026-10-09 审查)。同八字 solar_time.CHINA_TZ 的口径:行政统一时区。
_CN_ADMIN_TZ = {"Asia/Urumqi": "Asia/Shanghai", "Asia/Kashgar": "Asia/Shanghai"}


@lru_cache(maxsize=4096)
def tz_name_at(lat: float, lon: float) -> str:
    name = _tf().timezone_at(lat=lat, lng=lon)
    if not name:
        raise ValueError(f"坐标 ({lat}, {lon}) 查不到时区")
    return _CN_ADMIN_TZ.get(name, name)


def local_to_utc(local: datetime, tz_name: str) -> UtcResult:
    """naive 本地钟表时间 → aware UTC。"""
    if local.tzinfo is not None:
        raise ValueError("local 必须是 naive datetime（出生地钟表时间）")
    zi = ZoneInfo(tz_name)
    first = local.replace(tzinfo=zi, fold=0)
    second = local.replace(tzinfo=zi, fold=1)
    off0, off1 = first.utcoffset(), second.utcoffset()

    ambiguity = None
    if off0 != off1:
        # 往返一次：能原样回来的才是真实存在的时刻
        back = first.astimezone(timezone.utc).astimezone(zi).replace(tzinfo=None)
        ambiguity = "overlap" if back == local else "gap"

    utc = first.astimezone(timezone.utc)
    return UtcResult(
        utc=utc,
        tz_name=tz_name,
        utc_offset_hours=off0.total_seconds() / 3600.0,
        ambiguity=ambiguity,
    )
