"""Stage 4 (Earth Engine): MODIS MCD15A3H V061 monthly mean LAI per d02 cell -> modis_lai.npz (cached; delete to re-query)."""
from functools import reduce
import numpy as np, netCDF4 as nc
import config as C, lib


def clim_jobs(years):
    """[(name, [(start, end) per year])] for the 12 calendar months, e.g. m01_5y; end is exclusive (1st of next month)."""
    nxt = lambda y, m: f"{y + m // 12}-{m % 12 + 1:02d}-01"
    return [(f"m{m:02d}_{len(years)}y", [(f"{y}-{m:02d}-01", nxt(y, m)) for y in years]) for m in range(1, 13)]


def main():
    old = dict(np.load(C.MODIS_CACHE)) if C.MODIS_CACHE.exists() else {}
    todo = [k for k in ("sep", "oct", "sep_10y", "oct_10y") if k not in old] + [n for n, _ in clim_jobs(C.CLIM_YEARS) if n not in old]
    if not todo:
        print("using cache", C.MODIS_CACHE); return
    import ee
    ee.Initialize()
    f = nc.Dataset(C.GEO_SRC); ny, nx = f["XLAT_C"].shape[1] - 1, f["XLAT_C"].shape[2] - 1
    fc, col = lib.cell_polygons(f), ee.ImageCollection("MODIS/061/MCD15A3H")

    def good(im):                                         # Lai valid range 0-100, scale 0.1; QC bit 0 = 0 -> main algorithm
        lai = im.select("Lai")
        return lai.updateMask(lai.lte(100).And(im.select("FparLai_QC").bitwiseAnd(1).eq(0))).multiply(0.1).rename("LAI")

    out = dict(old)                                                                       # keeps the 2023 keys already cached
    jobs = [(n, [(a, b)]) for n, (_, a, b) in C.MONTHS.items() if n not in old]
    jobs += [(n + "_10y", [(a.replace("2023", str(y)), b.replace("2023", str(y))) for y in C.LAI_CLIM_YEARS]) for n, (_, a, b) in C.MONTHS.items()
             if n + "_10y" not in old]
    jobs += [(n, w) for n, w in clim_jobs(C.CLIM_YEARS) if n not in old]                 # monthly 5-year means (design 2026-11-19)
    for name, wins in jobs:
        sel = reduce(lambda x, y: x.merge(y), [col.filterDate(a, b) for a, b in wins])
        rows = (sel.map(good).mean()
                .reduceRegions(fc, ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True), scale=500, crs="EPSG:4326")
                .select(["j", "i", "mean", "count"], retainGeometry=False).getInfo()["features"])
        m, n = np.full((ny, nx), np.nan), np.zeros((ny, nx))
        for r in rows:
            p = r["properties"]; n[p["j"], p["i"]] = p.get("count") or 0
            if p.get("mean") is not None: m[p["j"], p["i"]] = p["mean"]
        out[name], out["n_" + name] = m, n
        print(name, "cells with a value:", int(np.isfinite(m).sum()))
    np.savez(C.MODIS_CACHE, **out)
