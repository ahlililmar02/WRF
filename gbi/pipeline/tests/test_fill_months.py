import sys; sys.path.insert(0, "/home/8/uw07888/WRF/pipeline")
import numpy as np
from write_geoem_clim import fill_months
a = np.full((12, 1, 3), np.nan)
a[:, 0, 0] = np.arange(12) / 20                      # complete: unchanged
a[0, 0, 1], a[2, 0, 1] = 0.2, 0.4                     # two valid months
b = fill_months(a)
assert np.allclose(b[:, 0, 0], np.arange(12) / 20)
assert np.isclose(b[1, 0, 1], 0.3) and np.isclose(b[3, 0, 1], 0.38) and np.isclose(b[11, 0, 1], 0.22)   # wraps Dec -> Jan
assert np.isnan(b[:, 0, 2]).all()                     # no data at all stays NaN
assert np.isnan(a[1, 0, 1])                           # input not modified
print("test_fill_months OK")
