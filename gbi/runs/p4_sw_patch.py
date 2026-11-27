"""SW-corner check: is the day-time +dH/+dT2 patch in Task 7 (tile on - off) a tile effect or a cloud/rain difference?
Box: land cells 106.52-106.63 E, 6.27-6.43 S (fw ~ 0). d02 has no cumulus scheme (cu_physics=0), so storms are resolved
and small changes can shift them. Test: dH vs dSWDOWN (all-sky), dSWDNBC (clear-sky, should be ~0), column-max CLDFRA, rain,
per day. Same spin-up/day window as p4_task7.py. Out: printed tables + ~/WRF/runs/p4_base/sw_patch.png"""
import glob, numpy as np, netCDF4, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "/home/8/uw07888/WRF/runs/"
V = ("HFX", "T2", "SWDOWN", "SWDNBC")
def load(run):
    d = {v: [] for v in V + ("CLD", "RAIN")}; t = []
    for f in sorted(glob.glob(R + f"{run}/wrfout_d02_*")):
        n = netCDF4.Dataset(f)
        for v in V: d[v].append(n[v][:])
        d["CLD"].append(n["CLDFRA"][:].max(axis=1))             # column-max cloud fraction
        d["RAIN"].append(n["RAINC"][:] + n["RAINNC"][:])        # accumulated since start (mm)
        t.append(n["Times"][:])
    return {v: np.concatenate(d[v]) for v in d}, np.array([b"".join(x).decode() for x in np.concatenate(t)])
on, t = load("p4_base"); off, t2 = load("p4_base_off"); assert (t == t2).all()
k0 = np.searchsorted(t, "2023-10-07_00"); keep = np.arange(len(t)) >= k0
hr = np.array([int(x[11:13]) for x in t]); day = keep & np.isin(hr, range(3, 9))
g = netCDF4.Dataset(R + "p3a_base_geo_em.d02.nc"); fw = g["LANDUSEF"][0][16] + g["LANDUSEF"][0][20]
lm = g["LANDMASK"][0] == 1; lat, lon = g["XLAT_M"][0], g["XLONG_M"][0]
box = lm & (lon >= 106.52) & (lon <= 106.63) & (lat >= -6.43) & (lat <= -6.27)
D = {v: (on[v][day] - off[v][day]).mean(0) for v in V + ("CLD",)}
rain = {r: (x["RAIN"][-1] - x["RAIN"][k0]) for r, x in (("on", on), ("off", off))}
print(f"box: {box.sum()} land cells, mean fw {fw[box].mean():.4f}, max fw {fw[box].max():.3f}")
print("day means in box (on - off): " + ", ".join(f"d{v} {D[v][box].mean():+.2f}" for v in V + ("CLD",)))
print(f"rain in box 10-07_00..end (mm): on {rain['on'][box].mean():.1f}, off {rain['off'][box].mean():.1f}")
print("\nper day, box mean (day 10-15 WIB):")
print(f"{'date':10s} {'dH':>7s} {'dT2':>6s} {'dSWDOWN':>8s} {'dSWclear':>8s} {'dCLD':>6s} {'rain on':>8s} {'rain off':>8s}")
for dt in sorted({x[:10] for x in t[keep]}):
    m = day & np.array([x.startswith(dt) for x in t])
    if not m.any(): continue
    i = np.where(np.array([x.startswith(dt) for x in t]))[0]; i0, i1 = max(i[0], k0), i[-1]
    r = [(x["RAIN"][i1] - x["RAIN"][i0])[box].mean() for x in (on, off)]
    print(f"{dt:10s} " + " ".join(f"{(on[v][m] - off[v][m]).mean(0)[box].mean():+{w}.2f}" for v, w in
          (("HFX", 7), ("T2", 6), ("SWDOWN", 8), ("SWDNBC", 8), ("CLD", 6))) + f" {r[0]:8.1f} {r[1]:8.1f}")
z = lm & (fw == 0)
c = np.corrcoef(D["HFX"][z], D["SWDOWN"][z])[0, 1]
print(f"\nall fw=0 land cells ({z.sum()}): spatial corr(day dH, day dSWDOWN) = {c:+.2f}")
print(f"same in box: {np.corrcoef(D['HFX'][box], D['SWDOWN'][box])[0, 1]:+.2f}")
fig, ax = plt.subplots(1, 4, figsize=(20, 4.8))
for a, (f, lim, lab) in zip(ax, ((D["HFX"], 40, "day dH (W m-2)"), (D["SWDOWN"], 80, "day dSWDOWN (W m-2)"),
                                 (D["CLD"], 0.15, "day d cloud fraction (column max)"), (rain["on"] - rain["off"], 20, "d rain total (mm)"))):
    m = a.pcolormesh(lon, lat, np.where(lm, f, np.nan), cmap="RdBu_r", vmin=-lim, vmax=lim, shading="auto")
    fig.colorbar(m, ax=a, label=lab); a.set_title(lab + ", tile on - off"); a.set_aspect("equal")
    a.contour(lon, lat, box.astype(float), [0.5], colors="k", linewidths=1)
fig.suptitle("SW-corner patch check (black box): tile on - off, 10-07..10-10, after 12 h spin-up")
fig.tight_layout(); fig.savefig(R + "p4_base/sw_patch.png", dpi=100)
print("->", R + "p4_base/sw_patch.png")
