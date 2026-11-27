"""FRC_URB2D from WorldCover (design 2026-11-26, docs/superpowers/specs/2026-11-26-frc-urb2d-mosaic-design.md):
FRC_URB2D = WorldCover 2021 v200 built pixels (class 50) / land pixels (not 0 = no data, not 80 = water) per d02 cell,
from the same ~9.3 m pixels as our LANDUSEF (out/p1/wc_native.tif); 0 in water cells (LANDMASK = 0).
Method as WRF's GAIA FRC_URB2D (Liao et al. 2025 ESSD p. 2538: paved share of each 1 km cell); WorldCover precedent:
Patel and Roth, Zenodo 10.5281/zenodo.7298393. Writes a copy of the July S2 LAI geo_em; nothing else changes.
Run: python -I write_geoem_frcwc.py"""
import sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, netCDF4 as nc, rasterio
import config as C, lib

SRC = Path.home() / "WRF/runs/s2lai_jul_geo_em.d02.nc"
OUT = Path.home() / "WRF/runs/frcwc_jul_geo_em.d02.nc"
WC = C.OUT / "p1/wc_native.tif"


def counts(cls, idx, n):
    """Per flat cell index: (built pixel count, land pixel count); land = not no data (0) and not water (80)."""
    land = (cls != 0) & (cls != 80)
    return (np.bincount(idx[cls == 50], minlength=n), np.bincount(idx[land], minlength=n))


def main():
    with nc.Dataset(SRC) as g:
        grid = lib.Grid(g)
        lm, gaia, lu, luf = g["LANDMASK"][0] == 1, g["FRC_URB2D"][0].astype("f8"), g["LU_INDEX"][0], g["LANDUSEF"][0].astype("f8")
    n = grid.ny * grid.nx
    b, l = np.zeros(n), np.zeros(n)
    with rasterio.open(WC) as r:
        assert r.crs.to_string() == "EPSG:4326", r.crs
        a, T = r.read(1), r.transform
    for sl, flat, inside in grid.chunks(T, a.shape, crs="EPSG:4326"):
        bb, ll = counts(a[sl][inside], flat[inside], n)
        b += bb; l += ll
    b, l = b.reshape(grid.ny, grid.nx), l.reshape(grid.ny, grid.nx)
    frc = np.where(l > 0, b / np.maximum(l, 1), 0.)
    frc[~lm] = 0.
    shutil.copy(SRC, OUT)
    with nc.Dataset(OUT, "a") as f:
        f["FRC_URB2D"][0] = frc
        f.setncattr("history", f.getncattr("history") + " | FRC_URB2D = WorldCover 2021 v200 built / land pixels "
                    "per cell, ~/WRF/pipeline/write_geoem_frcwc.py" if "history" in f.ncattrs() else
                    "FRC_URB2D = WorldCover 2021 v200 built / land pixels per cell, ~/WRF/pipeline/write_geoem_frcwc.py")
    with nc.Dataset(SRC) as s, nc.Dataset(OUT) as o:
        for v in s.variables:
            if v != "FRC_URB2D":
                assert np.array_equal(s[v][:], o[v][:]), v
        x = o["FRC_URB2D"][0]
        assert 0 <= x.min() and x.max() <= 1 and not x[~lm].any()
    wu = luf[12] / np.maximum(np.delete(luf, (16, 20), axis=0).sum(0), 1e-9)       # urban tile weight: water 17 and lake 21 removed
    ud = lm & (lu == 13)
    for name, k in (("all land", lm), ("LU_INDEX urban", ud), ("other land", lm & ~ud)):
        print(f"{name:15s} n={k.sum():4d}  FRC WorldCover {frc[k].mean():.3f}  GAIA {gaia[k].mean():.3f}")
    print(f"land cells with FRC >= 0.5 (real.exe makes them urban): WorldCover {(lm & (frc >= .5)).sum()}, GAIA {(lm & (gaia >= .5)).sum()}")
    cap = lm & (frc > wu + 1e-6)
    print(f"cap cells (FRC > urban tile weight): {cap.sum()} of {lm.sum()}, mean excess {(frc - wu)[cap].mean() if cap.any() else 0:.3f}; "
          f"land cells with FRC > 0 but no urban tile: {(lm & (frc > 0) & (luf[12] == 0)).sum()}")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
