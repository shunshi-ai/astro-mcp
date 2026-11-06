"""星座 / 行星 / 相位常量。

流派默认值（相位容许度、月交点）集中在这里，第 0 步对齐 ko.astro-seek 默认后只改这一处。
"""

SIGNS = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)

# skyfield / DE440s 里的目标名。外行星用系统质心：质心与本体偏差远小于 1 角分。
PLANETS = (
    ("sun", "sun"),
    ("moon", "moon"),
    ("mercury", "mercury"),
    ("venus", "venus"),
    ("mars", "mars barycenter"),
    ("jupiter", "jupiter barycenter"),
    ("saturn", "saturn barycenter"),
    ("uranus", "uranus barycenter"),
    ("neptune", "neptune barycenter"),
    ("pluto", "pluto barycenter"),
)

# 五主相位：名 → 角度。
ASPECTS = (
    ("conjunction", 0.0),
    ("sextile", 60.0),
    ("square", 90.0),
    ("trine", 120.0),
    ("opposition", 180.0),
)

# 容许度（度）。近似对齐 astro-seek「Default orbs」（2026-10-03）：它不公开表、且按行星区分，
# 这组值能完全复现 bench 盘（2004-05-15 12:00 香港）上它列出 / 未列出的 20 个近似相位，
# 见 tests/test_vs_astroseek.py。改动前先跑那份测试。
ASPECT_ORBS = {
    "conjunction": 8.0,
    "opposition": 8.0,
    "square": 7.0,
    "trine": 6.0,
    "sextile": 4.0,
}

# 发光体放宽（取两颗星里较大的那个）：太阳与海王星刑 9°16′ 被列出 → 太阳 ≥ +2.3；
# 月亮与海王星六合 5°57′ 未列 → 月亮 < +1.95。
ORB_BONUS = {"sun": 3.0, "moon": 1.0}

# 全站统一 Placidus（2026-10-03 拍板）：测测 / openfate / astro.com / 英语版 astro-seek 默认。
# 注意 ko.astro-seek 默认整宫制 —— 韩国用户对比时「落第几宫」可能不同，星座与上升不受影响。
DEFAULT_HOUSE_SYSTEM = "placidus"

# 月交点默认平均交点：astro-seek 英 / 韩两版默认都是 mean（true_uzel 未勾）。true 仍随盘输出。
DEFAULT_NODE = "mean"
