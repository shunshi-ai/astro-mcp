from astrochart.aspects import find_aspects


def test_basic_aspects_and_orb():
    pts = {
        "sun": {"lon": 10.0, "speed": 1.0},
        "mars": {"lon": 100.5, "speed": 0.5},   # 刑 90.5
        "venus": {"lon": 190.0, "speed": 1.2},  # 与日冲 180
    }
    got = {(a["p1"], a["p2"]): a for a in find_aspects(pts)}
    assert got[("sun", "mars")]["aspect"] == "square"
    assert got[("sun", "mars")]["orb"] == 0.5
    assert got[("sun", "venus")]["aspect"] == "opposition"


def test_applying_vs_separating():
    # 月亮顺行：85° 正在逼近 90° 刑 → 入相；92°、98° 已越过 → 出相
    saturn = {"lon": 0.0, "speed": 0.0}
    approaching = find_aspects({"moon": {"lon": 85.0, "speed": 13.0}, "saturn": saturn})
    past_close = find_aspects({"moon": {"lon": 92.0, "speed": 13.0}, "saturn": saturn})
    past_far = find_aspects({"moon": {"lon": 98.0, "speed": 13.0}, "saturn": saturn})
    assert approaching[0]["aspect"] == "square" and approaching[0]["applying"] is True
    assert past_close[0]["applying"] is False
    assert past_far[0]["applying"] is False


def test_asc_mc_pair_not_an_aspect():
    got = find_aspects({"asc": {"lon": 0.0}, "mc": {"lon": 270.0}})
    assert got == []


def test_out_of_orb_ignored():
    assert find_aspects({"mercury": {"lon": 0.0}, "jupiter": {"lon": 75.0}}) == []
