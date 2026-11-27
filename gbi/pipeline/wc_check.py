"""P1 Task 5: route 2 (bin the WPS tile pixels onto d02 cells ourselves) vs geogrid LANDUSEF, + green/blue/built histogram.

-> out/p1/route2_vs_geogrid.npz, out/p1/gbb_hist.png. Run: python -I wc_check.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, netCDF4, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from rasterio.transform import from_origin
import config as C, lib, wc_to_wps

GEO_P1 = Path.home() / "WRF/runs/p1_wc/geo_em.d02.nc"
GREEN, BLUE, BUILT, OTHER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14], [11, 17, 21], [13], [15, 16, 18, 19, 20]   # D2: 11 counted blue


def bin_classes(cls, T, grid):
    """cls: uint8 MODIS ids (rows north->south) on EPSG:4326 transform T -> (21, ny, nx) fraction per class per cell."""
    n = np.zeros((21, grid.ny * grid.nx))
    for sl, flat, inside in grid.chunks(T, cls.shape, crs="EPSG:4326"):
        c = cls[sl][inside].astype(int); f = flat[inside]
        np.add.at(n, (c - 1, f), 1)
    tot = n.sum(0)
    assert (tot > 0).all(), f"{(tot == 0).sum()} cells got no pixels"
    return (n / tot).reshape(21, grid.ny, grid.nx)


def main():
    cls, idx = wc_to_wps.read_tile(C.WPS_DS)
    dx = float(idx["dx"])
    west, south = float(idx["known_lon"]) - dx / 2, float(idx["known_lat"]) - dx / 2
    T = from_origin(west, south + cls.shape[0] * dx, dx, dx)
    with netCDF4.Dataset(GEO_P1) as f:
        grid = lib.Grid(f)
        geo = f["LANDUSEF"][0].astype("f8"); lm = f["LANDMASK"][0] == 1
    r2 = bin_classes(cls, T, grid)
    d = np.abs(r2 - geo)
    print(" cls  max|d|  mean|d|  cells>0.02")
    for k in range(21):
        if r2[k].max() > 0 or geo[k].max() > 0:
            print(f"{k + 1:4d}  {d[k].max():.4f}  {d[k].mean():.5f}  {(d[k] > 0.02).sum():6d}")
    np.savez(C.P1_DIR / "route2_vs_geogrid.npz", route2=r2, geogrid=geo, landmask=lm)
    assert d.mean(axis=(1, 2)).max() < 0.005 and d.max() < 0.05, "route 2 disagrees with geogrid: see systematic-debugging step"
    print("route-2 check OK")
    g = {n: geo[[k - 1 for k in ks]].sum(0)[lm] for n, ks in (("green", GREEN), ("blue (17+21+11)", BLUE), ("built (13)", BUILT), ("other", OTHER))}
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    for a, n in zip(ax, list(g)[:3]):
        a.hist(g[n], bins=np.linspace(0, 1, 21), color={"green": "#2e8b57"}.get(n, "#3b6fd4" if "blue" in n else "#888888"))
        a.set_title(f"{n}: land-cell mean {g[n].mean():.2f}", fontsize=10); a.set_xlabel("fraction of cell"); a.set_ylabel("land cells")
    fig.suptitle(f"d02 land cells (n={lm.sum()}), geogrid LANDUSEF from WorldCover 2021 (P1 route 1); other mean {g['other'].mean():.3f}", fontsize=10)
    fig.tight_layout(); fig.savefig(C.P1_DIR / "gbb_hist.png", dpi=110)
    print({n: round(float(v.mean()), 3) for n, v in g.items()}, "->", C.P1_DIR / "gbb_hist.png")


if __name__ == "__main__":
    main()
