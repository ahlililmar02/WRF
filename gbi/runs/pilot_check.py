"""Dry/wet pilot checks. usage: python -I pilot_check.py RUN [RUN ...]   (run dirs under ~/WRF/runs)
Per run: wall time, wrfout size, wrflowinp_d02 times + sea SST range, SHDMIN/SHDMAX position of VEGFRA (shd_stats)."""
import sys, glob, os, numpy as np, netCDF4 as nc

R = "/home/8/uw07888/WRF/runs/"


def shd_stats(wrfinput):
    """Non-urban land cells (XLAND 1, IVGTYP != 13): % with VEGFRA <= SHDMIN, % with VEGFRA >= SHDMAX, mean interpolation
    fraction clip((VEGFRA-SHDMIN)/(SHDMAX-SHDMIN), 0, 1) as in Noah sflx (module_sf_noahlsm.F:442-475). All in %."""
    with nc.Dataset(wrfinput) as f:
        v, lo, hi = (f[k][0].astype("f8") for k in ("VEGFRA", "SHDMIN", "SHDMAX"))
        m = (f["XLAND"][0] == 1) & (f["IVGTYP"][0] != 13)
    ok = m & (hi > lo)
    fr = np.clip((v - lo) / np.where(hi > lo, hi - lo, 1), 0, 1)
    return {"n": int(m.sum()), "at_min": 100 * (v[m] <= lo[m]).mean(), "at_max": 100 * (v[m] >= hi[m]).mean(), "mean_f": fr[ok].mean()}


def sea_sst(run_dir):
    """wrflowinp_d02 SST over water cells (wrfinput_d02 LANDMASK == 0): times, water cells, cells outside 250-350 K at the first
    time (WRF sst_update ignores those, module_surface_driver.F), min/max of the valid ones at first and last time (K)."""
    with nc.Dataset(run_dir + "/wrfinput_d02") as f:
        sea = f["LANDMASK"][0] == 0
    with nc.Dataset(run_dir + "/wrflowinp_d02") as f:
        sst = f["SST"][:]
    ok = sea & (sst[0] > 250) & (sst[0] < 350)
    a, b = sst[0][ok], sst[-1][ok]
    return {"times": sst.shape[0], "n_sea": int(sea.sum()), "n_missing": int((sea & ~ok).sum()),
            "first_min": float(a.min()), "first_max": float(a.max()), "last_min": float(b.min()), "last_max": float(b.max())}


def main(runs):
    for r in runs:
        d = R + r + "/"
        wall = open(d + "timing.txt").read().strip() if os.path.exists(d + "timing.txt") else "wall_s=?"
        mb = sum(os.path.getsize(x) for x in glob.glob(d + "wrfout_*")) / 1e6
        line = f"{r}: {wall} wrfout {mb:.0f} MB"
        if os.path.exists(d + "wrflowinp_d02"):
            t = sea_sst(d)
            line += " | wrflowinp_d02 %d times, SST missing in %d of %d water cells, valid first %.2f-%.2f last %.2f-%.2f K" % (
                t["times"], t["n_missing"], t["n_sea"], t["first_min"], t["first_max"], t["last_min"], t["last_max"])
        s = shd_stats(d + "wrfinput_d02")
        print(line + " | shd n %d at_min %.1f%% at_max %.1f%% mean_f %.2f" % (s["n"], s["at_min"], s["at_max"], s["mean_f"]))


if __name__ == "__main__":
    main(sys.argv[1:])
