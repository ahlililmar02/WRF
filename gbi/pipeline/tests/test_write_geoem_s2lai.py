import sys; sys.path.insert(0, "/home/8/uw07888/WRF/pipeline")
import numpy as np, write_geoem_s2lai as W
a = np.ones((12, 2, 2))
used = W.put_lai(a, (6, 7), np.array([[0.3, np.nan], [0.2, 0.1]]), np.array([[1, 1], [1, 0]]))
want = np.array([[0.3, 1.0], [0.2, 1.0]])
for m in range(12):
    assert np.array_equal(a[m], want if m in (6, 7) else np.ones((2, 2))), m
assert used.sum() == 2 and used.tolist() == [[True, False], [True, False]], used
try:
    W.put_lai(a, (6, 7), np.ones((3, 3)), np.ones((2, 2)))
    raise SystemExit("no ValueError")
except ValueError:
    pass
land = np.array([[1, 1], [1, 0]])
W.check_land(land, land.astype(bool))
try:
    W.check_land(land, np.array([[1, 1], [0, 1]], bool))
    raise SystemExit("no ValueError")
except ValueError:
    pass
print("OK")
