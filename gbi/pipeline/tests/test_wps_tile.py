import sys, tempfile; sys.path.insert(0, "/home/8/uw07888/WRF/pipeline")
from pathlib import Path
import numpy as np, wc_to_wps as P
a = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]], "u1")           # rows north -> south
d = Path(tempfile.mkdtemp(dir=Path.home() / "scratch/geo-agent")) / "ds"
P.write_tile(a, 106.0, -6.0, d)
b, idx = P.read_tile(d)
assert (b == a).all() and b.dtype == np.uint8, b
f = d / "00001-00004.00001-00003"
assert f.exists(), list(d.iterdir())
assert list(f.read_bytes()[:4]) == [9, 10, 11, 12]                          # bottom row first (Review Focus 4)
assert f.stat().st_size == 12
assert abs(float(idx["known_lat"]) - (-6.0 + 0.5 / 12000)) < 1e-12, idx["known_lat"]
assert abs(float(idx["known_lon"]) - (106.0 + 0.5 / 12000)) < 1e-12, idx["known_lon"]
assert abs(float(idx["dx"]) - 1 / 12000) < 1e-14 and abs(float(idx["dy"]) - 1 / 12000) < 1e-14, (idx["dx"], idx["dy"])
assert idx["tile_x"] == "4" and idx["tile_y"] == "3", idx
need = {"type": "categorical", "category_min": "1", "category_max": "21", "mminlu": '"MODIFIED_IGBP_MODIS_NOAH"',
        "iswater": "17", "islake": "21", "isice": "15", "isurban": "13", "wordsize": "1", "projection": "regular_ll",
        "known_x": "1.0", "known_y": "1.0", "tile_bdr": "0", "row_order": "bottom_top"}
for k, v in need.items():
    assert idx.get(k) == v, (k, idx.get(k), v)
print("test_wps_tile OK")
