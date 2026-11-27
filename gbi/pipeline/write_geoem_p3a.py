"""P3a baseline geo_em: P1 geo_em (WorldCover LANDUSEF, GAIA FRC_URB2D) + Sep/Oct GREENFRAC (Gutman and Ignatov 1998,
fixed anchors config.GI_NDVI, decision 2026-10-22) + Sep/Oct LAI12M (MODIS MCD15A3H 2023, case year; decision 2026-11-16).
Land use and urban fraction are NOT touched. Run: python -I write_geoem_p3a.py"""
import sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, netCDF4 as nc
import config as C

SRC = Path.home() / "WRF/runs/p1_wc/geo_em.d02.nc"
OUT = Path.home() / "WRF/runs/p3a_base_geo_em.d02.nc"
KEEP = ("LANDUSEF", "LU_INDEX", "LANDMASK", "FRC_URB2D")


def main():
    shutil.copy(SRC, OUT)
    c, ml = np.load(C.CELLS), np.load(C.MODIS_CACHE)
    n0, ninf = C.GI_NDVI                                               # not c["N0"]/c["NINF"]: those are the old scene percentiles
    with nc.Dataset(OUT, "a") as f:
        land = f["LANDMASK"][0] == 1
        use = land & (c["n_land"] > 0)
        fg = np.clip((c["ndvi_cell"] - n0) / (ninf - n0), 0, 1)
        gf, lai = f["GREENFRAC"][0], f["LAI12M"][0]
        for name, (mi, _, _) in C.MONTHS.items():
            gf[mi][use] = fg[use]
            got = land & np.isfinite(ml[name]); lai[mi][got] = ml[name][got]   # gap cells keep the table LAI
            print(f"{name}: GREENFRAC set in {use.sum()} of {land.sum()} land cells (mean {fg[use].mean():.3f}), "
                  f"LAI12M in {got.sum()} (no MODIS: {(land & ~got).sum()})")
        f["GREENFRAC"][0], f["LAI12M"][0] = gf, lai
        f.setncattr("history", "P3a baseline: P1 WorldCover land use + GAIA FRC_URB2D + Sentinel-2 GREENFRAC (Gutman-Ignatov 0.05/0.70) "
                    "+ MODIS 2023 LAI; ~/WRF/pipeline/write_geoem_p3a.py")
    with nc.Dataset(SRC) as a, nc.Dataset(OUT) as b:
        for v in KEEP:
            assert np.array_equal(a[v][:], b[v][:]), v
        g = b["GREENFRAC"][0]; assert 0 <= g.min() and g.max() <= 1
    print("asserts OK (land use + FRC_URB2D unchanged) ->", OUT)


if __name__ == "__main__":
    main()
