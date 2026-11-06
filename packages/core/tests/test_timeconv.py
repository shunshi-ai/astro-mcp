"""钟表时间 → UTC：历史夏令时 / 时区变更全部走 tzdata。"""
from datetime import datetime

import pytest

from astrochart.timeconv import local_to_utc

SEOUL, SHANGHAI, TOKYO = "Asia/Seoul", "Asia/Shanghai", "Asia/Tokyo"


@pytest.mark.parametrize("tz,local,offset", [
    (SEOUL, datetime(1988, 7, 15, 14, 30), 10.0),   # 1988 汉城奥运夏令时
    (SEOUL, datetime(1987, 8, 20, 8, 0), 10.0),
    (SEOUL, datetime(1988, 12, 1, 12, 0), 9.0),
    (SEOUL, datetime(1958, 1, 10, 6, 0), 8.5),      # 1954–61 UTC+8:30
    (SEOUL, datetime(1959, 7, 1, 22, 15), 9.5),     # 8:30 期间的夏令时
    (SEOUL, datetime(1949, 7, 10, 10, 0), 10.0),    # 1948–51 夏令时
    (SEOUL, datetime(1962, 1, 1, 12, 0), 9.0),
    (SHANGHAI, datetime(1988, 7, 1, 12, 0), 9.0),   # 中国 1986–91 夏令时
    (SHANGHAI, datetime(1990, 3, 24, 9, 50), 8.0),  # 1990 年 4/15 才开始
    (SHANGHAI, datetime(1986, 5, 4, 10, 0), 9.0),   # 切换当日
    (SHANGHAI, datetime(1992, 7, 1, 12, 0), 8.0),
    (TOKYO, datetime(1949, 7, 1, 12, 0), 10.0),     # 日本 1948–51 夏令时
    (TOKYO, datetime(1952, 7, 1, 12, 0), 9.0),
])
def test_historical_offsets(tz, local, offset):
    r = local_to_utc(local, tz)
    assert r.utc_offset_hours == offset
    assert r.ambiguity is None


def test_gap_time_flagged():
    # 1986-05-04 02:00 → 03:00，02:30 不存在
    r = local_to_utc(datetime(1986, 5, 4, 2, 30), SHANGHAI)
    assert r.ambiguity == "gap"
    assert r.utc_offset_hours == 8.0  # 按切换前偏移解释


def test_overlap_time_flagged():
    # 1988-09-11 02:00 → 01:00，01:30 出现两次，取第一次（夏令时）
    r = local_to_utc(datetime(1988, 9, 11, 1, 30), SHANGHAI)
    assert r.ambiguity == "overlap"
    assert r.utc_offset_hours == 9.0


def test_aware_input_rejected():
    from datetime import timezone
    with pytest.raises(ValueError):
        local_to_utc(datetime(2000, 1, 1, tzinfo=timezone.utc), SEOUL)


@pytest.mark.parametrize("lat,lon", [(43.83, 87.62), (39.47, 75.99)])   # 乌鲁木齐 / 喀什
def test_xinjiang_coords_use_beijing_time(lat, lon):
    """tzdata 的 Asia/Urumqi 是 UTC+6,但新疆钟表走北京时间(同八字 CHINA_TZ 口径)"""
    from astrochart.timeconv import tz_name_at
    assert tz_name_at(lat, lon) == SHANGHAI
    r = local_to_utc(datetime(1990, 6, 15, 10, 30), tz_name_at(lat, lon))
    assert r.utc == datetime(1990, 6, 15, 1, 30, tzinfo=r.utc.tzinfo)   # 1990 夏令时 UTC+9
