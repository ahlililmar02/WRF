import sys; sys.path.insert(0, "/home/8/uw07888/WRF/runs")
from pilot_check import shd_stats
R = "/home/8/uw07888/WRF/runs/"
d = shd_stats(R + "default/wrfinput_d02")
assert d["n"] == 1301 and round(d["at_min"], 1) == 9.4 and round(d["at_max"], 1) == 0.9 and round(d["mean_f"], 2) == 0.07, d
p = shd_stats(R + "p4_base_off/wrfinput_d02")
assert p["n"] == 522 and round(p["at_min"], 1) == 31.6 and round(p["at_max"], 1) == 27.2 and round(p["mean_f"], 2) == 0.47, p
print("test_pilot_check OK")
from pilot_check import sea_sst
s = sea_sst(R + "pilot_smoke")                         # 1 h smoke run of season_run.sh (2025-01-15), kept as fixture
assert s["times"] == 2 and s["n_sea"] == 753 and s["n_missing"] == 585, s   # 585 water cells get SST 0 from metgrid (finding 11-19)
assert 295 < s["first_min"] <= s["first_max"] < 310, s                     # valid sea cells only
print("test_pilot_check sea_sst OK")
