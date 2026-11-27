import sys, os; sys.path.insert(0, "/home/8/uw07888/WRF/runs")
import numpy as np
from s2lai_compare import group_stats, compare
R = "/home/8/uw07888/WRF/runs/"
# 3. group statistics on a 2 x 2 array: values 1,2,3,5 -> mean 2.75, population sd sqrt(2.1875)
n, m, s = group_stats(np.array([[1., 2.], [3., 5.]]), np.ones((2, 2), bool))
assert n == 4 and abs(m - 2.75) < 1e-12 and abs(s - 2.1875 ** 0.5) < 1e-12, (n, m, s)
assert group_stats(np.array([[1., 2.], [3., 5.]]), np.array([[1, 0], [0, 1]], bool))[0] == 2
# 1. self-comparison: every difference exactly 0
res = compare("pilotA_jul_off", "pilotA_jul_off", out=None)
assert all(r[2] == 0 and r[3] == 0 for r in res["rows"]) and len(res["rows"]) > 0, res["rows"][:3]
# 2. different namelist.input -> refuse
try:
    compare("pilotA_jul_on", "pilotA_jul_off", out=None); raise SystemExit("FAIL: no refusal")
except AssertionError as e:
    assert "namelist" in str(e), e
# missing run
try:
    compare("no_such_run", "pilotA_jul_off", out=None); raise SystemExit("FAIL: no refusal")
except AssertionError as e:
    assert "wrfout_d02" in str(e), e
# 5. strip_keys: allowed namelist keys are ignored, any other difference is kept
from s2lai_compare import strip_keys
base = " sf_urban_physics=1,1, rdlai2d=.true.,\n num_land_cat=21,\n"
mos  = " sf_urban_physics=1,1, rdlai2d=.true., sf_surface_mosaic=1, mosaic_cat=8, mosaic_frc_opt=1,\n num_land_cat=21,\n"
k = ["sf_surface_mosaic", "mosaic_cat", "mosaic_frc_opt"]
assert strip_keys(mos, k) == strip_keys(base, k), (strip_keys(mos, k), strip_keys(base, k))
assert strip_keys(mos.replace("num_land_cat=21", "num_land_cat=20"), k) != strip_keys(base, k)
assert strip_keys(mos, k[:2]) != strip_keys(base, k[:2])          # mosaic_frc_opt not allowed -> differs
# 6. paved_share: paved fraction of the cell the model uses (no mosaic / stock mosaic / mosaic + fix)
from s2lai_compare import paved_share
frc = np.array([[0.6, 0.2]]); urb = np.array([[True, False]])
luf = np.zeros((21, 1, 2)); luf[12] = [[0.6, 0.2]]; luf[1] = [[0.2, 0.7]]; luf[16] = [[0.2, 0.1]]   # urban, tree, sea
wu = np.array([[0.6 / 0.8, 0.2 / 0.9]])                                                            # water removed, renormalised
assert np.allclose(paved_share(frc, urb, luf, mosaic=False, fix=False), [[0.6, 0.0]])
assert np.allclose(paved_share(frc, urb, luf, mosaic=True, fix=False), [[wu[0, 0] * 0.6, 0.0]])
assert np.allclose(paved_share(frc, urb, luf, mosaic=True, fix=True), np.minimum(frc, wu))
# 7. TH1 = potential temperature at the lowest model level is reported next to T2 (T2 is a diagnostic)
r = compare("s2lai_jul", "pilotA_jul_off", out=False)
assert any(row[0] == "TH1" for row in r["rows"]), "TH1 missing"
print("test_s2lai_compare OK")
