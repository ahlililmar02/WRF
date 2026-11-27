"""Distributions + statistical comparison: default vs p4_base (total) and p4_base_off vs p4_base (tile only), d02 land cells.
Spatial: per-cell time means (day 10-15 WIB / night 20-04 WIB, after 12 h spin-up) -> histograms, box plots by fw,
  paired Wilcoxon signed-rank + KS over cells (cells are spatially correlated -> p-values too small, descriptive only).
Temporal: land-mean difference series per output time, t-test with effective n = n(1-r1)/(1+r1) (Wilks 2011, Statistical
  Methods in the Atmospheric Sciences, 3rd ed., sec. 5.2.4) - the honest significance test here.
Out: runs/p4_base/stats_dist.png, stats_box_fw.png, stats table on stdout"""
import glob, numpy as np, netCDF4, matplotlib
from scipy import stats
matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "/home/8/uw07888/WRF/runs/"
V = [("HFX", "H (W m-2)"), ("LH", "LE (W m-2)"), ("T2", "T2 (K)")]
def load(run):
    fs = sorted(glob.glob(R + f"{run}/wrfout_d02_*"))
    d = {v: np.concatenate([netCDF4.Dataset(f)[v][:] for f in fs]) for v, _ in V}
    t = np.concatenate([netCDF4.Dataset(f)["Times"][:] for f in fs])
    return d, np.array([b"".join(x).decode() for x in t])
runs = {}
for r in ("default", "p4_base_off", "p4_base"):
    runs[r], t = load(r)
hr = np.array([int(x[11:13]) for x in t]); keep = t >= "2023-10-07_00"
P = {"day": keep & np.isin(hr, range(3, 9)), "night": keep & np.isin(hr, range(13, 22))}
g, g0 = netCDF4.Dataset(R + "p3a_base_geo_em.d02.nc"), netCDF4.Dataset(R + "default/geo_em.d02.nc")
fw = g["LANDUSEF"][0][16] + g["LANDUSEF"][0][20]
lm = (g["LANDMASK"][0] == 1) & (g0["LANDMASK"][0] == 1)
cell = {r: {(v, p): runs[r][v][m].mean(0)[lm] for v, _ in V for p, m in P.items()} for r in runs}  # per-cell means
series = {r: {v: runs[r][v][:, lm].mean(1) for v, _ in V} for r in runs}  # land-mean per output time
fwl = fw[lm]
CMP = [("total", "default", "p4_base"), ("tile only", "p4_base_off", "p4_base")]

def neff_ttest(d):
    r1 = np.corrcoef(d[:-1], d[1:])[0, 1]; n = len(d); ne = max(2.0, n * (1 - r1) / (1 + r1))
    tval = d.mean() / (d.std(ddof=1) / np.sqrt(ne))
    return r1, ne, 2 * stats.t.sf(abs(tval), ne - 1)
print(f"land cells {lm.sum()}, outputs day {P['day'].sum()}, night {P['night'].sum()} (10-min output)")
print(f"{'compare':10s} {'var':4s} {'per':5s} | {'base mean':>9s} {'new mean':>9s} {'base sd':>8s} {'new sd':>8s} | "
      f"{'d mean':>7s} {'d med':>7s} {'d p5':>7s} {'d p95':>7s} {'d>0 %':>6s} {'Cohen':>6s} | {'Wilc p':>8s} {'KS p':>8s} | {'r1':>5s} {'n_eff':>6s} {'t-test p':>8s}")
for name, a, b in CMP:
    for v, _ in V:
        for p, m in P.items():
            x, y = cell[a][(v, p)], cell[b][(v, p)]; d = y - x
            ds = series[b][v][m] - series[a][v][m]
            r1, ne, pt = neff_ttest(ds)
            print(f"{name:10s} {v:4s} {p:5s} | {x.mean():9.2f} {y.mean():9.2f} {x.std():8.2f} {y.std():8.2f} | "
                  f"{d.mean():+7.2f} {np.median(d):+7.2f} {np.percentile(d, 5):+7.2f} {np.percentile(d, 95):+7.2f} {100 * (d > 0).mean():6.1f} "
                  f"{d.mean() / d.std():+6.2f} | {stats.wilcoxon(d).pvalue:8.1e} {stats.ks_2samp(x, y).pvalue:8.1e} | {r1:5.2f} {ne:6.1f} {pt:8.1e}")

# Fig 1: distribution of per-cell means, default vs p4_base_off vs p4_base
cols = {"default": "#2a78d6", "p4_base_off": "#1baf7a", "p4_base": "#eb6834"}
lab = {"default": "default (stock)", "p4_base_off": "new land use, tile off", "p4_base": "new land use, tile on"}
fig, ax = plt.subplots(2, 3, figsize=(15, 8))
for r_, p in enumerate(P):
    for c, (v, vl) in enumerate(V):
        a = ax[r_, c]; allv = np.concatenate([cell[k][(v, p)] for k in runs])
        bins = np.linspace(*np.percentile(allv, [0.5, 99.5]), 50)
        for k in runs:
            a.hist(cell[k][(v, p)], bins, histtype="step", lw=2, color=cols[k], label=lab[k])
            a.axvline(np.median(cell[k][(v, p)]), color=cols[k], lw=1, ls="--")
        a.set_title(f"{p}: per-cell mean {vl}", fontsize=10); a.set_xlabel(vl); a.set_ylabel("cells")
        for s in ("top", "right"): a.spines[s].set_visible(False)
ax[0, 0].legend(frameon=False, fontsize=9); fig.suptitle(f"Distribution over {lm.sum()} d02 land cells (dashed = median), 10-07..10-10")
fig.tight_layout(); fig.savefig(R + "p4_base/stats_dist.png", dpi=110)

# Fig 2: box plots of per-cell differences by fw class, total vs tile only
fwc = [("0", fwl == 0), ("0-1", (fwl > 0) & (fwl <= .01)), ("1-5", (fwl > .01) & (fwl <= .05)), ("5-10", (fwl > .05) & (fwl <= .1)),
       ("10-20", (fwl > .1) & (fwl <= .2)), ("20-50", (fwl > .2) & (fwl <= .5))]
fig, ax = plt.subplots(2, 3, figsize=(15, 8), sharex=True)
x = np.arange(len(fwc))
for r_, p in enumerate(P):
    for c, (v, vl) in enumerate(V):
        a = ax[r_, c]
        for k, (name, ra, rb) in enumerate(CMP):
            d = cell[rb][(v, p)] - cell[ra][(v, p)]; col = ("#2a78d6", "#eb6834")[k]
            bp = a.boxplot([d[m] for _, m in fwc], positions=x + (k - .5) * .38, widths=.32, patch_artist=True, showfliers=False,
                           medianprops=dict(color="#0b0b0b"), whis=(5, 95))
            for b in bp["boxes"]: b.set(facecolor=col, edgecolor=col, alpha=.8)
            a.plot([], [], color=col, lw=6, label=f"{name} ({rb} - {ra})")
        a.axhline(0, color="#52514e", lw=.8); a.grid(axis="y", color="#e6e5e0", lw=.6); a.set_axisbelow(True)
        for s in ("top", "right"): a.spines[s].set_visible(False)
        a.set_title(f"{p}: d{vl}", fontsize=10); a.set_ylabel(f"d{vl}")
        if r_ == 1: a.set_xticks(x, [f"{n}\nn={m.sum()}" for n, m in fwc], fontsize=8); a.set_xlabel("water fraction fw (%)")
ax[0, 0].legend(frameon=False, fontsize=8)
fig.suptitle("Per-cell differences by water fraction: box = 25-75 %, whiskers = 5-95 %, line = median")
fig.tight_layout(); fig.savefig(R + "p4_base/stats_box_fw.png", dpi=110)
print("->", R + "p4_base/stats_dist.png", R + "p4_base/stats_box_fw.png")
