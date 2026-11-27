"""Direct comparison: p4_base (WorldCover + NDVI GREENFRAC + MODIS LAI + blue tile) minus runs/default (stock geo_em).
Mixes land use, GREENFRAC/LAI and the tile; see p4_task7.py for the tile alone. Same spin-up/day/night as Task 7.
Out: tables by fw class and by land-use change + maps -> ~/WRF/runs/p4_base/vs_default.png"""
import glob, numpy as np, netCDF4, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "/home/8/uw07888/WRF/runs/"
V = ("HFX", "LH", "GRDFLX", "T2", "TSK")
def load(run):
    fs = sorted(glob.glob(R + f"{run}/wrfout_d02_*")); d = {}
    for v in V:
        d[v] = np.concatenate([netCDF4.Dataset(f)[v][:] for f in fs])
    t = np.concatenate([netCDF4.Dataset(f)["Times"][:] for f in fs])
    return d, np.array([b"".join(x).decode() for x in t])
new, t = load("p4_base"); old, t2 = load("default"); assert (t == t2).all()
keep = np.arange(len(t)) >= np.searchsorted(t, "2023-10-07_00")
hr = np.array([int(x[11:13]) for x in t])
day, night = keep & np.isin(hr, range(3, 9)), keep & np.isin(hr, range(13, 22))
g = netCDF4.Dataset(R + "p3a_base_geo_em.d02.nc"); g0 = netCDF4.Dataset(R + "default/geo_em.d02.nc")
fw = g["LANDUSEF"][0][16] + g["LANDUSEF"][0][20]
lu, lu0 = g["LU_INDEX"][0], g0["LU_INDEX"][0]
lm = (g["LANDMASK"][0] == 1) & (g0["LANDMASK"][0] == 1)  # land in both runs
lat, lon = g["XLAT_M"][0], g["XLONG_M"][0]
D = {v: {p: (new[v][m] - old[v][m]).mean(0) for p, m in (("day", day), ("night", night))} for v in V}
print(f"{len(t)} outputs, analysed {keep.sum()} (after 12 h spin-up); day {day.sum()}, night {night.sum()}")
print(f"land in both: {lm.sum()} cells (new land {(g['LANDMASK'][0] == 1).sum()}, default land {(g0['LANDMASK'][0] == 1).sum()})")
hdr = f"{'':16s} {'n':>5s} | {'dH day':>7s} {'dLE day':>7s} {'dG day':>7s} {'dT2 day':>7s} | {'dH ngt':>7s} {'dLE ngt':>7s} {'dG ngt':>7s} {'dT2 ngt':>7s}"
def table(title, groups):
    print("\n" + title); print(hdr)
    for name, m in groups:
        m = lm & m
        row = [D[v][p][m].mean() for p in ("day", "night") for v in ("HFX", "LH", "GRDFLX", "T2")]
        print(f"{name:16s} {m.sum():5d} | " + " ".join(f"{x:+7.2f}" for x in row[:4]) + " | " + " ".join(f"{x:+7.2f}" for x in row[4:]))
table("p4_base - default, by water fraction fw (new land use)", [("all land", lm)] + [
    (name, (fw == 0) if hi == 0 else ((fw > lo) & (fw <= hi)))
    for lo, hi, name in [(0, 0, "fw = 0"), (1e-9, 0.01, "0-1 %"), (0.01, 0.05, "1-5 %"), (0.05, 0.1, "5-10 %"), (0.1, 0.2, "10-20 %"), (0.2, 0.5, "20-50 %")]])
table("p4_base - default, by dominant land use (default -> new; 13 = urban)", [
    ("urban -> urban", (lu0 == 13) & (lu == 13)), ("other -> urban", (lu0 != 13) & (lu == 13)),
    ("urban -> other", (lu0 == 13) & (lu != 13)), ("other -> other", (lu0 != 13) & (lu != 13))])
fig, ax = plt.subplots(2, 3, figsize=(15, 9))
for r, p in enumerate(("day", "night")):
    for c, (v, lim, lab) in enumerate((("HFX", 150, "dH (W m-2)"), ("LH", 150, "dLE (W m-2)"), ("T2", 2.0, "dT2 (K)"))):
        a = ax[r, c]; m = a.pcolormesh(lon, lat, np.where(lm, D[v][p], np.nan), cmap="RdBu_r", vmin=-lim, vmax=lim, shading="auto")
        fig.colorbar(m, ax=a, label=lab); a.set_title(f"{p}: {lab}, p4_base - default"); a.set_aspect("equal")
fig.suptitle("p4_base (WorldCover + NDVI/LAI + blue tile) minus stock default, d02 land cells, 10-07..10-10")
fig.tight_layout(); fig.savefig(R + "p4_base/vs_default.png", dpi=100)
np.savez(R + "p4_base/vs_default.npz", fw=fw, landmask=lm, lu=lu, lu0=lu0, **{f"{v}_{p}": D[v][p] for v in D for p in D[v]})
print("->", R + "p4_base/vs_default.png")
