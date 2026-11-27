"""geo_em for the one-day MODIS-with-gaps check: p3a_base geo_em with LAI12M July and August replaced by the MODIS July 2021-2025 mean
(pipeline/out/modis_lai.npz, key m07_5y) where MODIS has a value; its gap cells (NaN) keep the WPS value. Run: python -I write_geoem_modislai.py"""
import sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, netCDF4 as nc
from write_geoem_s2lai import put_lai, check_land, SRC, MONTHS

OUT = Path.home() / "WRF/runs/modislai_jul_geo_em.d02.nc"
LAI_NPZ = Path(__file__).parent / "out/modis_lai.npz"
KEY = "m07_5y"
S2 = Path(__file__).parent / "out/s2_lai/m07_test.npz"   # only for its land mask (frozen 11-25 test file)


def main():
    lai_cell = np.load(LAI_NPZ)[KEY]
    s2 = np.load(S2)
    with nc.Dataset(SRC) as f:
        check_land(f["LANDMASK"][0], s2["land"])
    shutil.copy(SRC, OUT)
    with nc.Dataset(OUT, "a") as f:
        land = f["LANDMASK"][0]
        lai = f["LAI12M"][0]
        wps = lai[MONTHS[0]].copy()
        used = put_lai(lai, MONTHS, lai_cell, land)
        f["LAI12M"][0] = lai
        f.setncattr("history", "LAI12M Jul+Aug = MODIS July 2021-2025 mean, WPS kept in MODIS gaps; ~/WRF/pipeline/write_geoem_modislai.py")
    kept = (land == 1) & ~used
    print(f"MODIS cells {used.sum()}: LAI WPS {wps[used].mean():.2f} vs MODIS {lai_cell[used].mean():.2f}")
    print(f"kept cells {kept.sum()}: LAI WPS {wps[kept].mean():.2f} (MODIS gap)")
    with nc.Dataset(SRC) as a, nc.Dataset(OUT) as b:
        for v in a.variables:
            if v != "LAI12M":
                assert np.array_equal(a[v][:], b[v][:]), v
        x, y = a["LAI12M"][:], b["LAI12M"][:]
        assert np.array_equal(np.delete(x, MONTHS, 1), np.delete(y, MONTHS, 1)), "other months changed"
        L = y[0][list(MONTHS)][:, land == 1]
        assert np.isfinite(L).all() and 0 <= L.min() and L.max() <= 8, (L.min(), L.max())
        assert (y[0, 6][land == 1] != x[0, 6][land == 1]).sum() <= used.sum()
        assert np.array_equal(y[0, 6][used], lai_cell[used].astype(y.dtype)) and np.array_equal(y[0, 6][kept], x[0, 6][kept])
    print("asserts OK (only LAI12M months 7, 8 changed) ->", OUT)


if __name__ == "__main__":
    main()
