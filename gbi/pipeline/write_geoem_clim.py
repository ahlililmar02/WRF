"""Dry/wet design (2026-11-19): geo_em whose 12 GREENFRAC and LAI12M months ALL come from 2021-2025 monthly averages
(Sentinel-2 composites per calendar month -> Gutman and Ignatov 1998 with fixed anchors config.GI_NDVI; LAI12M = Sentinel-2
effective LAI, s2biophys, s2_lai.py, out/s2_lai/m01..m12.npz; replaced MODIS MCD15A3H on 2026-11-26, MODIS has no value in 612 land cells). One source for all 12 months removes the SHDMIN/SHDMAX artefact of mixed months (WORKLOG 11-18).
Months without data in a cell are filled from the neighbouring months of the same source (fill_months). Cells with no data in
any month keep all 12 default months. Land use, urban fraction and lake depth are NOT touched. Run: python -I write_geoem_clim.py"""
import sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, netCDF4 as nc
import config as C

SRC = Path.home() / "WRF/runs/p1_wc/geo_em.d02.nc"
OUT = Path.home() / "WRF/runs/clim5y_geo_em.d02.nc"
KEEP = ("LANDUSEF", "LU_INDEX", "LANDMASK", "FRC_URB2D", "LAKE_DEPTH")


def fill_months(a):
    """(12, ny, nx) with NaN gaps -> copy with gaps linearly interpolated over the circular month axis per cell; all-NaN cells stay NaN."""
    b = a.copy()
    for j, i in zip(*np.where(np.isnan(a).any(0) & np.isfinite(a).any(0))):
        v = np.isfinite(a[:, j, i]); m = np.flatnonzero(v)
        b[:, j, i] = np.interp(np.arange(12), m, a[m, j, i], period=12)
    return b


def put(field, new, land, name):
    """Write the months of `new` (12, ny, nx; NaN = no data) into `field` in land cells with all 12 months finite after filling."""
    filled = fill_months(new)
    use = land & np.isfinite(filled).all(0)
    for m in range(12):
        own = use & np.isfinite(new[m])
        print(f"{name} m{m + 1:02d}: own data {own.sum()}, filled {(use & ~own).sum()}, default (no data any month) {(land & ~use).sum()}")
        field[m][use] = filled[m][use]
    return use


def main():
    shutil.copy(SRC, OUT)
    n0, ninf = C.GI_NDVI
    gfn, lain = [], []
    for m in range(1, 13):
        c = np.load(C.clim_dir(m) / "cells.npz")
        gfn.append(np.where(c["n_land"] > 0, np.clip((c["ndvi_cell"] - n0) / (ninf - n0), 0, 1), np.nan))
        lain.append(np.load(C.S2_LAI / f"m{m:02d}.npz")["sr"])
    gfn, lain = np.array(gfn), np.array(lain)
    with nc.Dataset(OUT, "a") as f:
        land = f["LANDMASK"][0] == 1
        gf, lai = f["GREENFRAC"][0], f["LAI12M"][0]
        g0, l0 = gf.copy(), lai.copy()
        ug, ul = put(gf, gfn, land, "GREENFRAC"), put(lai, lain, land, "LAI12M")
        f["GREENFRAC"][0], f["LAI12M"][0] = gf, lai
        f.setncattr("history", "clim5y: P1 WorldCover land use + GAIA FRC_URB2D + Sentinel-2 2021-2025 monthly GREENFRAC (Gutman-Ignatov "
                    "0.05/0.70) + Sentinel-2 2021-2025 monthly effective LAI (s2biophys), gaps filled from neighbour months; ~/WRF/pipeline/write_geoem_clim.py")
    with nc.Dataset(SRC) as a, nc.Dataset(OUT) as b:
        for v in KEEP:
            assert np.array_equal(a[v][:], b[v][:]), v
        g, l = b["GREENFRAC"][0], b["LAI12M"][0]
        assert np.isfinite(g).all() and 0 <= g.min() and g.max() <= 1
        for name, new, old, use in (("GREENFRAC", g, g0, ug), ("LAI12M", l, l0, ul)):
            assert not (new[:, ~use] != old[:, ~use]).any(), name + ": changed outside the cells with 12 own-source months"
    print(f"asserts OK (land use, FRC_URB2D, LAKE_DEPTH unchanged; GREENFRAC in [0,1]; 12-or-0 months per cell) -> {OUT}")
    print("land-mean GREENFRAC per month:", " ".join(f"{g[m][land].mean():.3f}" for m in range(12)))


if __name__ == "__main__":
    main()
