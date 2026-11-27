"""geo_em for the one-day Sentinel-2 LAI check: p3a_base geo_em with LAI12M July and August replaced by the Sentinel-2
July mean (pipeline/out/s2_lai/m07_test.npz, key sr; same values as m07.npz). Nothing else changes. Run: python -I write_geoem_s2lai.py"""
import sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, netCDF4 as nc

SRC = Path.home() / "WRF/runs/p3a_base_geo_em.d02.nc"
OUT = Path.home() / "WRF/runs/s2lai_jul_geo_em.d02.nc"
S2 = Path(__file__).parent / "out/s2_lai/m07_test.npz"   # frozen 11-25 test file (m07.npz is now the pipeline output)
MONTHS = (6, 7)   # Jul and Aug (0-based): sst_update drifts the run toward August


def put_lai(lai12m, months, lai_cell, land):
    """Write lai_cell into lai12m[months] where land and finite; returns that mask. Other cells keep the WPS value."""
    if lai_cell.shape != land.shape or lai_cell.shape != lai12m.shape[-2:]:
        raise ValueError((lai_cell.shape, land.shape, lai12m.shape))
    used = (land == 1) & np.isfinite(lai_cell)
    for m in months:
        lai12m[m][used] = lai_cell[used]
    return used


def check_land(land, s2_land):
    """Stop if the Sentinel-2 grid is not the geo_em grid (same shape is not enough)."""
    if land.shape != s2_land.shape or not np.array_equal(land == 1, s2_land.astype(bool)):
        raise ValueError("Sentinel-2 land mask differs from geo_em LANDMASK")


def main():
    s2 = np.load(S2)
    sr = s2["sr"]
    with nc.Dataset(SRC) as f:
        check_land(f["LANDMASK"][0], s2["land"])
    shutil.copy(SRC, OUT)
    with nc.Dataset(OUT, "a") as f:
        land = f["LANDMASK"][0]
        urb = (f["LU_INDEX"][0] == 13) & (land == 1)                   # geo_em LU_INDEX 13, not wrfinput IVGTYP
        lai = f["LAI12M"][0]
        wps = lai[MONTHS[0]].copy()
        used = put_lai(lai, MONTHS, sr, land)
        f["LAI12M"][0] = lai
        f.setncattr("history", "LAI12M Jul+Aug = Sentinel-2 July mean (s2biophys); ~/WRF/pipeline/write_geoem_s2lai.py")
    for name, g in (("urban", urb), ("other", (land == 1) & ~urb)):
        print(f"{name} land cells {g.sum()}: LAI WPS {wps[g].mean():.2f} vs Sentinel-2 {sr[g].mean():.2f}")
    kept = np.argwhere((land == 1) & ~used)
    print(f"replaced {used.sum()} of {int((land == 1).sum())} land cells; kept WPS default in {len(kept)}: {kept.tolist()}")
    with nc.Dataset(SRC) as a, nc.Dataset(OUT) as b:
        for v in a.variables:
            if v != "LAI12M":
                assert np.array_equal(a[v][:], b[v][:]), v
        x, y = a["LAI12M"][:], b["LAI12M"][:]
        assert np.array_equal(np.delete(x, MONTHS, 1), np.delete(y, MONTHS, 1)), "other months changed"
        L = b["LAI12M"][0][list(MONTHS)][:, land == 1]
        assert np.isfinite(L).all() and 0 <= L.min() and L.max() <= 8, (L.min(), L.max())
        assert (y[0, 6][land == 1] != x[0, 6][land == 1]).sum() <= used.sum()
    print("asserts OK (only LAI12M months 7, 8 changed) ->", OUT)


if __name__ == "__main__":
    main()
