"""Paved share the model uses vs fluxes, d02 land cells, 4 runs of the FRC_URB2D test (24 h from 2025-07-15, S2 July LAI).
Row 1: distributions of paved share and of day-mean HFX, LH. Row 2: day HFX, LH and night T2, TH1 against paved share
(cells as dots, line = mean per 0.1 bin, bins with < 10 cells dropped). Day 03-08 UTC, night 13-21 UTC (as s2lai_compare.py).
Out: runs/frc_flux.png, printed table. One day, one run per setting, no ensemble."""
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from s2lai_compare import R, load, run_paved

ALL = (("s2lai_jul", "GAIA, no mosaic (default)", "tab:gray"), ("frcwc_jul", "WorldCover, no mosaic", "tab:orange"),
        ("mos_jul", "WorldCover, mosaic as published", "tab:blue"), ("mosfix_jul", "WorldCover, mosaic + fix", "tab:red"))
import sys   # optional args: run names to plot (default all 4); output frc_flux[_runA_runB].png
RUNS = tuple(x for x in ALL if x[0] in sys.argv[1:]) or ALL
OUT = R + "frc_flux" + "".join("_" + x[0] for x in RUNS if sys.argv[1:]) + ".png"
d = {}
for r, _, _ in RUNS:
    x, t = load(r); hr = np.array([int(s[11:13]) for s in t])
    day, night = np.isin(hr, range(3, 9)), np.isin(hr, range(13, 22))
    d[r] = {"paved": np.asarray(run_paved(r)), "land": np.asarray(x["LANDMASK"]) == 1,
            "day HFX": x["HFX"][day].mean(0), "day LH": x["LH"][day].mean(0),
            "night T2": x["T2"][night].mean(0), "night TH1": x["TH1"][night].mean(0)}
land = d[RUNS[0][0]]["land"]
assert all((v["land"] == land).all() for v in d.values())
V = ("paved", "day HFX", "day LH", "night T2", "night TH1")
print(f"{'run':12s}" + "".join(f"{v:>11s}" for v in V) + "   (land-cell means)")
for r, _, _ in RUNS:
    print(f"{r:12s}" + "".join(f"{float(d[r][v][land].mean()):11.3f}" for v in V))

fig, ax = plt.subplots(2, 4, figsize=(20, 9))
pb = np.linspace(0, 1, 21)
for r, lab, c in RUNS:
    p = d[r]["paved"][land]
    ax[0, 0].hist(p, pb, histtype="step", lw=2, color=c, label=f"{lab}: mean {p.mean():.2f}, zeros {int((p == 0).sum())}")
    s = np.sort(p); ax[0, 1].plot(s, np.arange(1, s.size + 1) / s.size, color=c, lw=2)
    for a, v in ((ax[0, 2], "day HFX"), (ax[0, 3], "day LH")):
        a.hist(np.asarray(d[r][v][land]), 30, histtype="step", lw=2, color=c)
    for a, v in zip(ax[1], ("day HFX", "day LH", "night T2", "night TH1")):
        y = np.asarray(d[r][v][land]); a.scatter(p, y, s=2, color=c, alpha=.15)
        k = np.minimum((p * 10).astype(int), 9); n = np.bincount(k, minlength=10)
        m = np.bincount(k, y, minlength=10) / np.maximum(n, 1)
        ok = n >= 10; a.plot((np.arange(10) + .5)[ok] / 10, m[ok], "-o", color=c, lw=2, ms=4)
ax[0, 0].legend(fontsize=8, loc="upper center")
ax[0, 0].set(title="paved share the model uses", xlabel="paved share", ylabel="land cells (of %d)" % land.sum())
ax[0, 1].set(title="paved share, CDF", xlabel="paved share", ylabel="cumulative fraction"); ax[0, 1].grid(alpha=.3)
ax[0, 2].set(title="day-mean HFX (03-08 UTC)", xlabel="W m-2", ylabel="land cells")
ax[0, 3].set(title="day-mean LH (03-08 UTC)", xlabel="W m-2", ylabel="land cells")
for a, v, u in zip(ax[1], ("day HFX", "day LH", "night T2", "night TH1"), ("W m-2", "W m-2", "K", "K")):
    a.set(title=f"{v} vs paved share", xlabel="paved share", ylabel=u); a.grid(alpha=.3)
fig.suptitle("FRC_URB2D test, d02 land cells, 2025-07-15, one day, one run per setting, no ensemble "
             "(dots = cells, line = mean per 0.1 bin, n >= 10)")
fig.tight_layout(); fig.savefig(OUT, dpi=110); print("wrote", OUT)
