"""宫位：openfate 对照盘 + 自洽性 + 极地回退。"""
from datetime import datetime

import pytest

from astrochart import natal_chart
from astrochart.houses import asc_mc, compute_houses, house_of, placidus_supported


def _fmt(p):
    return (p["sign"], p["deg"], p["min"])


def _near(p, sign, deg, minute, tol_min=1.0):
    """截图只到角分，且对方城市坐标未知 → 允许 ±1′。"""
    from astrochart import SIGNS
    want = SIGNS.index(sign) * 30 + deg + minute / 60.0
    d = abs(p["lon"] - want) % 360.0
    return min(d, 360.0 - d) * 60.0 <= tol_min


def test_openfate_reference_chart():
    """openfate.ai/zh-hans/astro-chart 截图（2026-10-03）：Placidus，回归黄道。"""
    c = natal_chart(local=datetime(1990, 3, 24, 9, 50), lat=45.29322, lon=130.96217)
    assert c["houses"]["system"] == "placidus"
    assert _near(c["angles"]["asc"], "cancer", 5, 9)
    assert _near(c["angles"]["mc"], "pisces", 8, 6)
    p = c["planets"]
    assert _near(p["jupiter"], "cancer", 2, 0) and p["jupiter"]["house"] == 12
    assert _near(p["uranus"], "capricorn", 9, 24) and p["uranus"]["house"] == 7
    assert _near(p["moon"], "aquarius", 26, 21) and p["moon"]["house"] == 9


# 测测 App「本命盘参数 · 现代参数」截图（2026-10-03），同一张盘、同一组城市预设坐标。
_CEICE = {
    "sun": ("aries", 3, 10, 10, False), "moon": ("aquarius", 26, 21, 9, False),
    "mercury": ("aries", 8, 11, 10, False), "venus": ("aquarius", 16, 52, 9, False),
    "mars": ("aquarius", 9, 13, 8, False), "jupiter": ("cancer", 2, 0, 12, False),
    "saturn": ("capricorn", 23, 56, 8, False), "uranus": ("capricorn", 9, 24, 7, False),
    "neptune": ("capricorn", 14, 25, 7, False), "pluto": ("scorpio", 17, 29, 5, True),
}
_CEICE_ANGLES = {"asc": ("cancer", 5, 8), "dsc": ("capricorn", 5, 8),
                 "ic": ("virgo", 8, 6), "mc": ("pisces", 8, 6)}


def test_ceice_reference_chart_exact():
    """测测 14 项（10 星 + 四轴）落座、度分、宫位、逆行逐一完全一致。"""
    c = natal_chart(local=datetime(1990, 3, 24, 9, 50), lat=45.29322, lon=130.96217)
    for body, (sign, d, m, house, retro) in _CEICE.items():
        p = c["planets"][body]
        assert (p["sign"], p["deg"], p["min"], p["house"], bool(p["retrograde"])) == \
            (sign, d, m, house, retro), body
    for k, want in _CEICE_ANGLES.items():
        assert _fmt(c["angles"][k]) == want, k


@pytest.mark.parametrize("ramc,eps,lat", [
    (0.0, 23.44, 37.5), (45.0, 23.44, 37.5), (137.2, 23.44, -33.9),
    (250.0, 23.44, 51.5), (359.0, 23.44, 64.1), (89.9, 23.44, 0.0),
])
def test_placidus_self_consistency(ramc, eps, lat):
    h = compute_houses(ramc, eps, lat, "placidus")
    cusps = h["cusps"]
    assert cusps[0] == pytest.approx(h["asc"])
    assert cusps[9] == pytest.approx(h["mc"])
    for i in range(6):  # 对宫相差 180°
        assert (cusps[i + 6] - cusps[i]) % 360.0 == pytest.approx(180.0, abs=1e-6)
    # 宫头沿黄经单调递增，绕一圈总和 360°
    spans = [(cusps[(i + 1) % 12] - cusps[i]) % 360.0 for i in range(12)]
    assert all(0 < s < 180 for s in spans)
    assert sum(spans) == pytest.approx(360.0)


def test_equator_asc_mc_independent_formula():
    # 赤道上：ASC 赤经 = RAMC + 90°（第二套推导独立复算）
    import math
    ramc, eps = 30.0, 23.44
    asc, _ = asc_mc(ramc, eps, 0.0)
    ra = math.radians(ramc + 90.0)
    expect = math.degrees(math.atan2(math.sin(ra), math.cos(ra) * math.cos(math.radians(eps)))) % 360
    assert asc == pytest.approx(expect, abs=1e-9)


def test_polar_falls_back_to_porphyry():
    """极圈内同 Swiss Ephemeris / astro.com：退 Porphyry（象限三等分）。"""
    assert not placidus_supported(69.6, 23.44)
    c = natal_chart(local=datetime(1985, 12, 21, 12, 0), lat=69.6492, lon=18.9553)
    assert c["houses"]["requested_system"] == "placidus"
    assert c["houses"]["system"] == "porphyry"
    cusps = [x["lon"] for x in c["houses"]["cusps"]]
    assert cusps[0] == pytest.approx(c["angles"]["asc"]["lon"])
    assert cusps[9] == pytest.approx(c["angles"]["mc"]["lon"])
    q = (cusps[3] - cusps[0]) % 360.0
    assert (cusps[1] - cusps[0]) % 360.0 == pytest.approx(q / 3)


def test_house_of_wraps():
    cusps = [350.0 + 30 * i for i in range(12)]
    cusps = [c % 360 for c in cusps]
    assert house_of(355.0, cusps) == 1
    assert house_of(5.0, cusps) == 1
    assert house_of(20.0, cusps) == 2
    assert house_of(349.0, cusps) == 12


def test_hour_unknown_no_angles_and_moon_range():
    c = natal_chart(local=datetime(2010, 6, 12, 0, 0), lat=37.5665, lon=126.978, hour_unknown=True)
    assert c["angles"] is None and c["houses"] is None
    assert "house" not in c["planets"]["sun"]
    assert set(c["day_sign_ranges"]["moon"]) == {"start_sign", "end_sign", "ambiguous"}
    assert c["input"]["calc_local"].endswith("12:00:00")


def test_unknown_place_no_angles():
    c = natal_chart(local=datetime(1995, 1, 1, 8, 0), lat=37.5665, lon=126.978, place_known=False)
    assert c["angles"] is None and c["houses"] is None
    assert c["time"]["tz_name"] == "Asia/Seoul"


def test_hour_unknown_sun_ingress_day_flagged():
    """太阳换座日：2000-03-20 首尔 16:35 太阳入白羊，按中午排会说白羊，必须标 ambiguous。"""
    c = natal_chart(local=datetime(2000, 3, 20, 0, 0), lat=37.5665, lon=126.978, hour_unknown=True)
    sun = c["day_sign_ranges"]["sun"]
    assert sun == {"start_sign": "pisces", "end_sign": "aries", "ambiguous": True}
    assert c["day_sign_ranges"]["saturn"]["ambiguous"] is False


def test_default_node_is_mean_like_astro_seek():
    c = natal_chart(local=datetime(1990, 3, 24, 9, 50), lat=45.29322, lon=130.96217)
    assert c["node_type"] == "mean"
    assert c["nodes"]["north_node"]["lon"] == c["nodes"]["north_node_mean"]["lon"]
    assert (c["nodes"]["south_node"]["lon"] - c["nodes"]["north_node"]["lon"]) % 360 == pytest.approx(180)


def test_output_is_json_native():
    """numpy 标量混进输出会让 FastAPI 序列化 400（2026-10-04 接口测试抓到）。"""
    import json
    c = natal_chart(local=datetime(1990, 3, 24, 9, 50), lat=45.29322, lon=130.96217)
    json.dumps(c)
    assert type(c["planets"]["pluto"]["retrograde"]) is bool
