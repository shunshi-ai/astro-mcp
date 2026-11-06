"""第一把尺子：NASA JPL Horizons（独立实现）。行星视黄经 ≤ 1 角分，落座 100% 一致。

读冻结的 golden_horizons.json，不联网。改测试盘清单后跑 tools/fetch_horizons_golden.py 重新冻结。
"""
import json
from datetime import datetime
from pathlib import Path

import pytest

from astrochart import natal_chart

GOLDEN = json.loads((Path(__file__).parent / "golden_horizons.json").read_text())
TOL_DEG = 1.0 / 60.0


def _delta(a, b):
    d = abs(a - b) % 360.0
    return 360.0 - d if d > 180.0 else d


@pytest.mark.parametrize("case", GOLDEN["charts"], ids=lambda c: c["name"])
def test_planets_match_horizons(case):
    chart = natal_chart(
        local=datetime.fromisoformat(case["local"]),
        lat=case["lat"],
        lon=case["lon"],
    )
    # tzdata 漂移守卫：UTC 换算必须和冻结时一致
    assert chart["time"]["utc"] == case["utc"]
    assert chart["time"]["tz_name"] == case["tz_name"]

    for body, ref in case["planets"].items():
        ours = chart["planets"][body]
        assert _delta(ours["lon"], ref["lon"]) <= TOL_DEG, (body, ours["lon"], ref["lon"])
        assert int(ours["lon"] // 30) == int(ref["lon"] // 30) or _delta(ours["lon"], ref["lon"]) < 1e-3
