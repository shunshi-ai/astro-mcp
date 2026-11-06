from astrochart import sign_of


def test_rounds_to_nearest_minute_like_ceice():
    assert sign_of(3 + 9.88 / 60)["min"] == 10    # 测测：太阳 3°9.88′ 显示 3°10′
    assert sign_of(95.0 + 8.23 / 60)["min"] == 8


def test_rolls_into_next_sign_at_boundary():
    s = sign_of(89.995)                            # 29°59.7′ → 巨蟹 0°00′
    assert (s["sign"], s["deg"], s["min"]) == ("cancer", 0, 0)
    s = sign_of(359.999)
    assert (s["sign"], s["deg"], s["min"]) == ("aries", 0, 0)


def test_last_minute_of_sign_stays():
    s = sign_of(89.99)                             # 29°59.4′
    assert (s["sign"], s["deg"], s["min"]) == ("gemini", 29, 59)
