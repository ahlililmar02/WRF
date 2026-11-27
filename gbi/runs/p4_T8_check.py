"""T8: block (5x5, p4_geo/cells.txt) mean response vs fw0 for fw 0.10/0.25/0.40, 24 h from 2023-10-06_12 UTC.
Day = 10-15 WIB (03-08 UTC), night = 20-04 WIB (13-21 UTC). Monotonic = |delta| grows with fw and keeps its sign."""
import glob, numpy as np, netCDF4
R = "/home/8/uw07888/WRF/runs/"
cells = np.loadtxt(R + "p4_geo/cells.txt", dtype=int); J, I = cells[:, 0], cells[:, 1]
def series(run):
    fs = sorted(glob.glob(R + f"{run}/wrfout_d02_*")); out = {}
    for v in ("HFX", "LH", "T2", "GRDFLX", "TSK"):
        out[v] = np.concatenate([netCDF4.Dataset(f)[v][:][:, J, I].mean(1) for f in fs])
    t = np.concatenate([netCDF4.Dataset(f)["Times"][:] for f in fs]); hrs = np.array([int(b"".join(x)[11:13]) for x in t])
    return out, hrs
base, hrs = series("p4_T8_fw0")
day, night = np.isin(hrs, range(3, 9)), np.isin(hrs, range(13, 22))
print(f"{len(hrs)} hourly times; block {len(J)} cells; base day H {base['HFX'][day].mean():.1f} LE {base['LH'][day].mean():.1f} T2 {base['T2'][day].mean()-273.15:.2f} C")
res = {}
for fw in ("10", "25", "40"):
    s, _ = series(f"p4_T8_block_{fw}")
    res[fw] = {k: ((s[k] - base[k])[day].mean(), (s[k] - base[k])[night].mean()) for k in base}
    print(f"fw 0.{fw}: " + "  ".join(f"d{k} day {res[fw][k][0]:+7.2f} night {res[fw][k][1]:+7.2f}" for k in ("HFX", "LH", "T2", "GRDFLX")))
for k in ("HFX", "LH", "T2", "GRDFLX"):
    for p, name in ((0, "day"), (1, "night")):
        d = [res[f][k][p] for f in ("10", "25", "40")]
        mono = (np.all(np.diff(np.abs(d)) > 0) and (np.all(np.array(d) > 0) or np.all(np.array(d) < 0)))
        print(f"   {k:6s} {name:5s}: {'monotonic' if mono else 'NOT monotonic'}  {[round(x, 3) for x in d]}")
