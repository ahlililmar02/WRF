import sys; sys.path.insert(0, "/home/8/uw07888/WRF/pipeline")
import numpy as np, wc_modis as W
wc = np.array([[10, 20, 30, 40, 50, 60], [70, 80, 80, 90, 95, 100], [0, 50, 80, 10, 60, 0]], "u1")
inland = np.array([[1, 1, 1, 1, 1, 1], [1, 1, 0, 1, 1, 1], [0, 0, 0, 1, 0, 1]], bool)
out = W.crosswalk(wc, inland, tree_class=2)
assert out.tolist() == [[2, 7, 10, 12, 13, 16], [15, 21, 17, 11, 11, 19], [17, 13, 17, 2, 16, 17]], out.tolist()
assert W.crosswalk(wc, inland, tree_class=5)[0, 0] == 5                    # D1 is a parameter
assert out.dtype == np.uint8 and out.min() >= 1 and out.max() <= 21
try: W.crosswalk(np.array([[42]], "u1"), np.ones((1, 1), bool), 2); raise SystemExit("unknown class not rejected")
except ValueError: pass
print("test_wc_modis OK")
