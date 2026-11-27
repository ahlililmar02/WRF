"""P4 Task 7: city-wide blue-tile effect, p4_base (lake_tile_opt=1) minus p4_base_off (opt=0), d02, full case.
Spin-up: first 12 h dropped. Day = 10-15 WIB (03-08 UTC), night = 20-04 WIB (13-21 UTC).
Out: table by fw class + maps -> ~/WRF/runs/p4_base/task7_effect.png, task7_effect.npz"""
import glob, numpy as np, netCDF4, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "/home/8/uw07888/WRF/runs/"
def load(run):
    fs = sorted(glob.glob(R + f"{run}/wrfout_d02_*")); d = {}
    for v in ("HFX", "LH", "GRDFLX", "T2", "TSK"):
        d[v] = np.concatenate([netCDF4.Dataset(f)[v][:] for f in fs])
    t = np.concatenate([netCDF4.Dataset(f)["Times"][:] for f in fs])
    return d, np.array([b"".join(x).decode() for x in t])
on, t = load("p4_base"); off, t2 = load("p4_base_off"); assert (t == t2).all()
keep = np.arange(len(t)) >= np.searchsorted(t, "2023-10-07_00")
hr = np.array([int(x[11:13]) for x in t])
day, night = keep & np.isin(hr, range(3, 9)), keep & np.isin(hr, range(13, 22))
g = netCDF4.Dataset(R + "p3a_base_geo_em.d02.nc"); fw = g["LANDUSEF"][0][16] + g["LANDUSEF"][0][20]
lm = g["LANDMASK"][0] == 1; lat, lon = g["XLAT_M"][0], g["XLONG_M"][0]
D = {v: {p: (on[v][m] - off[v][m]).mean(0) for p, m in (("day", day), ("night", night))} for v in on}
print(f"{len(t)} outputs, analysed {keep.sum()} (after 12 h spin-up); day {day.sum()}, night {night.sum()}")
bins = [(0, 0, "fw = 0"), (1e-9, 0.01, "0-1 %"), (0.01, 0.05, "1-5 %"), (0.05, 0.1, "5-10 %"), (0.1, 0.2, "10-20 %"), (0.2, 0.5, "20-50 %")]
print(f"{'land cells':12s} {'n':>5s} | {'dH day':>7s} {'dLE day':>7s} {'dG day':>7s} {'dT2 day':>7s} | {'dH ngt':>7s} {'dLE ngt':>7s} {'dG ngt':>7s} {'dT2 ngt':>7s}")
for lo, hi, name in bins:
    m = lm & ((fw == 0) if hi == 0 else ((fw > lo) & (fw <= hi)))
    row = [D[v][p][m].mean() for p in ("day", "night") for v in ("HFX", "LH", "GRDFLX", "T2")]
    print(f"{name:12s} {m.sum():5d} | " + " ".join(f"{x:+7.2f}" for x in row[:4]) + " | " + " ".join(f"{x:+7.2f}" for x in row[4:]))
fig, ax = plt.subplots(2, 3, figsize=(15, 9))
for r, p in enumerate(("day", "night")):
    for c, (v, lim, lab) in enumerate((("HFX", 40, "dH (W m-2)"), ("LH", 15, "dLE (W m-2)"), ("T2", 0.4, "dT2 (K)"))):
        a = ax[r, c]; m = a.pcolormesh(lon, lat, np.where(lm, D[v][p], np.nan), cmap="RdBu_r", vmin=-lim, vmax=lim, shading="auto")
        fig.colorbar(m, ax=a, label=lab); a.set_title(f"{p}: {lab}, tile on - off"); a.set_aspect("equal")
fig.suptitle("P4 blue tile: effect of the WorldCover water fraction in land cells (10-07..10-10, after 12 h spin-up)")
fig.tight_layout(); fig.savefig(R + "p4_base/task7_effect.png", dpi=100)
np.savez(R + "p4_base/task7_effect.npz", fw=fw, landmask=lm, **{f"{v}_{p}": D[v][p] for v in D for p in D[v]})
print("->", R + "p4_base/task7_effect.png")
