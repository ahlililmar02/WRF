"""P1 Task 3: WorldCover window -> MODIS-21 classes -> one WPS geogrid binary tile + index in C.WPS_DS.

Format: WPS user guide ch. 3, "Writing Static Data to the Geogrid Binary Format" (1-byte categorical, bottom_top rows,
known_lat/lon = centre of pixel (1,1) = south-west pixel). Run: python -I wc_to_wps.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, rasterio
import config as C, wc_modis

N = 12000                                            # pixels per degree (WorldCover native)


def write_tile(cls, west, south, out_dir):
    """cls: uint8 MODIS ids, rows north->south; west/south: outer edges (deg) of the raster."""
    ny, nx = cls.shape
    assert cls.dtype == np.uint8 and max(nx, ny) <= 99999, (cls.dtype, cls.shape)   # 5-digit WPS file names
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    cls[::-1].tofile(out_dir / f"00001-{nx:05d}.00001-{ny:05d}")
    (out_dir / "index").write_text(f"""type=categorical
category_min=1
category_max=21
projection=regular_ll
dx={1 / N:.15e}
dy={1 / N:.15e}
known_x=1.0
known_y=1.0
known_lat={south + 0.5 / N:.12f}
known_lon={west + 0.5 / N:.12f}
wordsize=1
tile_x={nx}
tile_y={ny}
tile_z=1
tile_bdr=0
row_order=bottom_top
units="category"
description="ESA WorldCover v200 2021 -> MODIS 21 (Parde 2026 + D1/D2/D3)"
mminlu="MODIFIED_IGBP_MODIS_NOAH"
iswater=17
islake=21
isice=15
isurban=13
""")


def read_tile(out_dir):
    """-> (uint8 array rows north->south, index dict of strings). Single-tile datasets only."""
    out_dir = Path(out_dir)
    idx = dict(l.split("=", 1) for l in (out_dir / "index").read_text().split("\n") if "=" in l)
    idx = {k.strip(): v.strip() for k, v in idx.items()}
    nx, ny = int(idx["tile_x"]), int(idx["tile_y"])
    a = np.fromfile(out_dir / f"00001-{nx:05d}.00001-{ny:05d}", np.uint8)
    assert a.size == nx * ny, (a.size, nx, ny)
    return a.reshape(ny, nx)[::-1], idx


def sample(a, idx, lat, lon):
    """Class at (lat, lon) from read_tile output."""
    col = round((lon - float(idx["known_lon"])) / float(idx["dx"]))
    row_from_south = round((lat - float(idx["known_lat"])) / float(idx["dy"]))
    assert 0 <= col < a.shape[1] and 0 <= row_from_south < a.shape[0], f"({lat}, {lon}) outside the tile"
    return int(a[a.shape[0] - 1 - row_from_south, col])


def main():
    with rasterio.open(C.P1_DIR / "wc_native.tif") as r:
        wc, T = r.read(1), r.transform
        west, south = T.c, T.f + T.e * r.height
    inland = rasterio.open(C.P1_DIR / "inland.tif").read(1) == 1
    cls = wc_modis.crosswalk(wc, inland, tree_class=C.TREE_CLASS)
    write_tile(cls, west, south, C.WPS_DS)
    v, n = np.unique(cls, return_counts=True)
    print("MODIS class counts:", {int(a): int(b) for a, b in zip(v, n)})
    a, idx = read_tile(C.WPS_DS)
    assert (a == cls).all()
    for (lat, lon), ok in zip(C.P1_PROBES, (lambda c: c == 17, lambda c: c not in (17, 21))):   # Review Focus 4
        c = sample(a, idx, lat, lon)
        print(f"probe ({lat}, {lon}) -> {c}")
        assert ok(c), f"probe ({lat}, {lon}) gave {c}: tile flipped or misplaced?"
    print("wrote", C.WPS_DS)


if __name__ == "__main__":
    main()
