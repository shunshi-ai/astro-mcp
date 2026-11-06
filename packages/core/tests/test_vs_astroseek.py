"""第二把尺子：astro-seek（英语版，默认 Placidus / 平均交点 / Default orbs）。

bench 测试盘 2004-05-15 12:00 香港（手动坐标 22°19′N 114°10′E，GMT+8），2026-10-03 抓取。
astro-seek 度分**截断**显示（测测是四舍五入），所以位置按 ±1′ 比；相位比「列 / 不列」集合。
"""
from datetime import datetime
from itertools import combinations

import pytest

from astrochart import SIGNS, natal_chart
from astrochart.aspects import find_aspects

LAT, LON = 22 + 19 / 60, 114 + 10 / 60

SEEK_PLANETS = {
    "sun": ("taurus", 24, 39, 10), "moon": ("aries", 9, 26, 8),
    "mercury": ("aries", 28, 51, 9), "venus": ("gemini", 25, 59, 11),
    "mars": ("cancer", 4, 56, 11), "jupiter": ("virgo", 9, 4, 1),
    "saturn": ("cancer", 10, 13, 11), "uranus": ("pisces", 6, 30, 7),
    "neptune": ("aquarius", 15, 23, 6), "pluto": ("sagittarius", 21, 35, 5),
}
SEEK_CUSPS = [("leo", 21, 4), ("virgo", 17, 44), ("libra", 17, 48),
              ("scorpio", 19, 50), ("sagittarius", 21, 30), ("capricorn", 21, 53)]
SEEK_NODE_MEAN = ("taurus", 10, 32, 9)

# astro-seek「Planet aspects」列出的全部行星对（只含 10 大行星）
SEEK_ASPECTS = {
    ("sun", "neptune", "square"), ("moon", "mars", "square"), ("moon", "saturn", "square"),
    ("mercury", "venus", "sextile"), ("venus", "pluto", "opposition"),
    ("mars", "saturn", "conjunction"), ("mars", "uranus", "trine"),
    ("jupiter", "saturn", "sextile"), ("jupiter", "uranus", "opposition"),
    ("saturn", "uranus", "trine"),
}


def _lon(sign, d, m):
    return SIGNS.index(sign) * 30 + d + m / 60


def _within(lon, want, tol_min=1.0):
    d = abs(lon - want) % 360
    return min(d, 360 - d) * 60 <= tol_min


@pytest.fixture(scope="module")
def chart():
    return natal_chart(local=datetime(2004, 5, 15, 12, 0), lat=LAT, lon=LON, tz_name="Asia/Hong_Kong")


def test_planets_and_houses(chart):
    for body, (sign, d, m, house) in SEEK_PLANETS.items():
        p = chart["planets"][body]
        assert _within(p["lon"], _lon(sign, d, m)), body
        assert p["house"] == house, body
    assert chart["planets"]["pluto"]["retrograde"]


def test_cusps(chart):
    for i, (sign, d, m) in enumerate(SEEK_CUSPS):
        assert _within(chart["houses"]["cusps"][i]["lon"], _lon(sign, d, m)), i + 1


def test_mean_node(chart):
    sign, d, m, house = SEEK_NODE_MEAN
    n = chart["nodes"]["north_node"]
    assert _within(n["lon"], _lon(sign, d, m)) and n["house"] == house


def test_major_aspect_set_matches(chart):
    pts = {b: {"lon": chart["planets"][b]["lon"], "speed": chart["planets"][b]["speed"]}
           for b in SEEK_PLANETS}
    ours = {(a["p1"], a["p2"], a["aspect"]) for a in find_aspects(pts)}
    assert ours == SEEK_ASPECTS
