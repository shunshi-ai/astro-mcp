"""区间扫描：逆行站点 / 换座 / 行运时间线。

对照值：2026 水逆三段、土星 / 海王星进出白羊 —— 各大星历网站公布的日期（UTC 日期，±1 天容差留给时区）。
"""
from datetime import datetime, timedelta, timezone

import pytest
from astrochart import ephemeris, natal_chart
from astrochart.timeline import ingresses, stations, transit_timeline

U = timezone.utc
JIXI = dict(local=datetime(1990, 3, 24, 9, 50), lat=45.29322, lon=130.96217)


def _near(dt: datetime, y, m, d, days=1):
    return abs(dt - datetime(y, m, d, 12, tzinfo=U)) <= timedelta(days=days, hours=12)


def test_2026水逆三段():
    st = stations(datetime(2026, 1, 1, tzinfo=U), datetime(2026, 12, 31, tzinfo=U), bodies=("mercury",))
    got = [(s["kind"], s["at"]) for s in st]
    want = [("retrograde", (2026, 2, 26)), ("direct", (2026, 3, 20)),
            ("retrograde", (2026, 6, 29)), ("direct", (2026, 7, 23)),
            ("retrograde", (2026, 10, 24)), ("direct", (2026, 11, 13))]
    assert len(got) == len(want)
    for (k, t), (wk, wd) in zip(got, want):
        assert k == wk and _near(t, *wd)


def test_土星海王星进出白羊():
    ing = ingresses(datetime(2025, 1, 1, tzinfo=U), datetime(2026, 12, 31, tzinfo=U), bodies=("saturn", "neptune"))
    got = [(x["body"], x["sign"], x["retrograde"], x["at"]) for x in ing]
    want = [("neptune", "aries", False, (2025, 3, 30)), ("saturn", "aries", False, (2025, 5, 25)),
            ("saturn", "pisces", True, (2025, 9, 1)), ("neptune", "pisces", True, (2025, 10, 22)),
            ("neptune", "aries", False, (2026, 1, 26)), ("saturn", "aries", False, (2026, 2, 14))]
    assert len(got) == len(want)
    for (b, s, r, t), (wb, ws, wr, wd) in zip(got, want):
        assert (b, s, r) == (wb, ws, wr) and _near(t, *wd)


def test_精确日独立回验_偏差小于一分():
    c = natal_chart(**JIXI)
    angle = {"conjunction": 0, "sextile": 60, "square": 90, "trine": 120, "opposition": 180}
    tl = transit_timeline(c, datetime(2027, 1, 1, tzinfo=U), datetime(2027, 12, 31, tzinfo=U))
    assert tl
    checked = 0
    for e in tl:
        nlon = c["angles"][e["natal"]]["lon"] if e["natal"] in ("asc", "mc") else c["planets"][e["natal"]]["lon"]
        for t in e["exact"]:
            tlon = ephemeris.planet_positions(t)[e["transit"]]["lon"]
            sep = abs((tlon - nlon + 180) % 360 - 180)
            assert abs(sep - angle[e["aspect"]]) < 1 / 60
            checked += 1
        assert e["start"] <= e["end"]
    assert checked >= 10


def test_逆行多次精确():
    c = natal_chart(**JIXI)
    tl = transit_timeline(c, datetime(2027, 1, 1, tzinfo=U), datetime(2027, 12, 31, tzinfo=U))
    assert any(e["passes"] >= 2 for e in tl)


def test_无时辰不打月亮不打轴点():
    c = natal_chart(local=datetime(1990, 1, 10, 12, 0), lat=None, lon=None, hour_unknown=True,
                    place_known=False, tz_name="Asia/Shanghai")
    tl = transit_timeline(c, datetime(2026, 1, 1, tzinfo=U), datetime(2028, 12, 31, tzinfo=U))
    assert tl and not {e["natal"] for e in tl} & {"moon", "asc", "mc"}


def test_区间校验():
    with pytest.raises(ValueError):
        stations(datetime(2026, 1, 1, tzinfo=U), datetime(2030, 1, 1, tzinfo=U))
    with pytest.raises(ValueError):
        stations(datetime(2026, 1, 1), datetime(2026, 2, 1))
    with pytest.raises(ValueError):
        stations(datetime(2026, 2, 1, tzinfo=U), datetime(2026, 1, 1, tzinfo=U))
