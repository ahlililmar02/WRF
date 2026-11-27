import sys; sys.path.insert(0, "/home/8/uw07888/WRF/pipeline")
import numpy as np
from write_geoem_frcwc import counts
cls = np.array([50, 50, 10, 80,  50, 0, 80, 80,  80, 80], np.uint8)
idx = np.array([0, 0, 0, 0,  1, 1, 1, 1,  2, 2])
b, l = counts(cls, idx, 4)
assert b.tolist() == [2, 1, 0, 0] and l.tolist() == [3, 1, 0, 0], (b, l)   # 0 = no data and 80 = water are not land
frc = np.where(l > 0, b / np.maximum(l, 1), 0.)
assert np.allclose(frc, [2/3, 1, 0, 0]), frc
print("test_write_geoem_frcwc OK")
