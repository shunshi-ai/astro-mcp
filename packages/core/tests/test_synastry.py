from datetime import datetime

from astrochart import natal_chart
from astrochart.synastry import house_overlay, synastry_aspects


def _fake(planets: dict, hour_unknown=False, angles=None, cusps=None):
    return {
        "input": {"hour_unknown": hour_unknown},
        "planets": {k: {"lon": v} for k, v in planets.items()},
        "angles": angles,
        "houses": {"cusps": [{"lon": c} for c in cusps]} if cusps else None,
    }


def test_cross_aspects_and_orbs():
    a = _fake({"venus": 10.0, "sun": 0.0})
    b = _fake({"mars": 130.0, "moon": 186.5})
    got = {(x["a"], x["b"]): x for x in synastry_aspects(a, b)}
    assert got[("venus", "mars")]["aspect"] == "trine" and got[("venus", "mars")]["orb"] == 0.0
    # 太阳冲月亮 7.5°：超出 6+1 → 不算；改成 6.5° 才算（见下一断言前的调整）
    assert got[("sun", "moon")]["aspect"] == "opposition"
    # 金星与月亮 176.5° 冲 → 3.5° 内
    assert got[("venus", "moon")]["aspect"] == "opposition"


def test_sextile_orb_is_tight():
    a = _fake({"venus": 0.0})
    b = _fake({"mars": 64.5})          # 六合 4.5° > 4°
    assert synastry_aspects(a, b) == []


def test_generational_pairs_skipped():
    a = _fake({"pluto": 100.0, "venus": 100.0})
    b = _fake({"neptune": 100.0})
    pairs = {(x["a"], x["b"]) for x in synastry_aspects(a, b)}
    assert ("pluto", "neptune") not in pairs
    assert ("venus", "neptune") in pairs


def test_hour_unknown_moon_and_houses_dropped():
    a = _fake({"moon": 50.0, "sun": 50.0}, hour_unknown=True)
    b = _fake({"mars": 50.0}, cusps=[i * 30.0 for i in range(12)])
    pairs = {(x["a"], x["b"]) for x in synastry_aspects(a, b)}
    assert ("sun", "mars") in pairs and ("moon", "mars") not in pairs
    assert {o["planet"] for o in house_overlay(a, b)} == {"sun"}
    assert house_overlay(b, a) == []      # 无时辰的一方没有宫位


def test_overlay_onto_self_equals_natal_houses():
    ch = natal_chart(local=datetime(1975, 6, 4, 9, 9), lat=34.0522, lon=-118.2437)
    got = {o["planet"]: o["house"] for o in house_overlay(ch, ch)}
    assert {k: got[k] for k in ch["planets"]} == {k: v["house"] for k, v in ch["planets"].items()}
    assert got["asc"] == 1 and got["mc"] == 10 and got["north_node"] == ch["nodes"]["north_node"]["house"]


def test_angles_take_part_including_with_each_other():
    a = _fake({"sun": 0.0}, angles={"asc": {"lon": 90.0}, "mc": {"lon": 0.0}})
    b = _fake({"venus": 90.0}, angles={"asc": {"lon": 90.5}, "mc": {"lon": 0.5}})
    pairs = {(x["a"], x["b"]) for x in synastry_aspects(a, b)}
    assert ("asc", "venus") in pairs and ("asc", "asc") in pairs and ("mc", "mc") in pairs


def test_north_node_tight_orb_and_no_outer():
    a = _fake({"venus": 100.0, "pluto": 102.0})
    a["nodes"] = {"north_node": {"lon": 200.0}}
    b = _fake({"sun": 202.5, "venus": 204.0, "neptune": 200.0})
    b["nodes"] = {"north_node": {"lon": 101.0}}
    pairs = {(x["a"], x["b"]) for x in synastry_aspects(a, b)}
    assert ("north_node", "sun") in pairs                    # 2.5° ≤ 3
    assert ("north_node", "venus") not in pairs              # 4° > 3（不吃日月加成）
    assert ("north_node", "neptune") not in pairs and ("pluto", "north_node") not in pairs
    assert ("venus", "north_node") in pairs


def test_midpoint_short_arc():
    from astrochart.synastry import midpoint
    assert midpoint(10, 30) == 20
    assert midpoint(350, 10) == 0          # 跨 0° 走短弧
    assert abs(midpoint(100, 300) - 20) < 1e-9   # 200° 弧 → 走另一边的 160°


def test_composite_and_marks():
    from astrochart.synastry import composite_chart, marks_chart, midpoint
    a = natal_chart(local=datetime(1975, 6, 4, 9, 9), lat=34.0522, lon=-118.2437)
    b = natal_chart(local=datetime(1963, 12, 18, 6, 31), lat=35.3273, lon=-96.9253)
    c = composite_chart(a, b)
    assert abs(c["points"]["sun"] - midpoint(a["planets"]["sun"]["lon"], b["planets"]["sun"]["lon"])) < 1e-9
    assert c["cusps"] and len(c["cusps"]) == 12 and set(c["houses"]) == set(c["points"])
    m = marks_chart(c, a)
    assert abs(m["points"]["venus"] - midpoint(c["points"]["venus"], a["planets"]["venus"]["lon"])) < 1e-9
    nohour = natal_chart(local=datetime(1963, 12, 18, 12, 0), lat=35.3273, lon=-96.9253, hour_unknown=True)
    c2 = composite_chart(a, nohour)
    assert "moon" not in c2["points"] and "asc" not in c2["points"] and c2["cusps"] is None
