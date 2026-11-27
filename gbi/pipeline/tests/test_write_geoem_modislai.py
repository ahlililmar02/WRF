import sys; sys.path.insert(0, "/home/8/uw07888/WRF/pipeline")
import numpy as np, write_geoem_modislai as M
# NaN cell keeps the WPS value; mask = finite land cells
a = np.ones((12, 2, 2))
used = M.put_lai(a, (6, 7), np.array([[0.3, np.nan], [0.2, np.nan]]), np.array([[1, 1], [1, 0]]))
assert used.sum() == 2 and a[6, 0, 1] == 1.0 and a[7, 0, 0] == 0.3 and a[0, 0, 0] == 1.0
# real data: MODIS gap mask equals the Sentinel-2 gap mask
mod = np.load(M.LAI_NPZ)[M.KEY]; s2 = np.load(M.S2)
land = s2["land"].astype(bool)
g = land & ~np.isfinite(mod)
assert g.sum() == 612 and (land & np.isfinite(mod)).sum() == 1551 and np.array_equal(g, s2["gap"]), g.sum()
print("OK")
