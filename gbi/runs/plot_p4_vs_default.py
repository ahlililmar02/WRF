"""Bar charts for the direct comparison (p4_base - default) next to the tile-only effect (p4_base - p4_base_off),
grouped by water fraction and by land-use change. Reads p4_base/vs_default.npz and p4_base/task7_effect.npz.
Out: ~/WRF/runs/p4_base/vs_default_bars.png"""
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "/home/8/uw07888/WRF/runs/p4_base/"
d, t = np.load(R + "vs_default.npz"), np.load(R + "task7_effect.npz")
lm, fw, lu, lu0 = d["landmask"], d["fw"], d["lu"], d["lu0"]
assert np.allclose(fw, t["fw"])  # same geo_em for both
fwc = [("0", fw == 0), ("0-1", (fw > 0) & (fw <= .01)), ("1-5", (fw > .01) & (fw <= .05)), ("5-10", (fw > .05) & (fw <= .1)),
       ("10-20", (fw > .1) & (fw <= .2)), ("20-50", (fw > .2) & (fw <= .5))]
luc = [("urban\n->urban", (lu0 == 13) & (lu == 13)), ("other\n->urban", (lu0 != 13) & (lu == 13)),
       ("urban\n->other", (lu0 == 13) & (lu != 13)), ("other\n->other", (lu0 != 13) & (lu != 13))]
S = [("p4_base - default (total)", d, "#2a78d6"), ("p4_base - p4_base_off (tile only)", t, "#eb6834")]
VARS = [("HFX", "dH (W m-2)"), ("LH", "dLE (W m-2)"), ("T2", "dT2 (K)")]
for groups, xlab, out in ((fwc, "water fraction fw (%)", "vs_default_bars_fw.png"), (luc, "dominant land use, default -> new", "vs_default_bars_lu.png")):
    fig, ax = plt.subplots(2, 3, figsize=(15, 8), sharex=True)
    x = np.arange(len(groups)); w = 0.38
    for r, p in enumerate(("day", "night")):
        for c, (v, lab) in enumerate(VARS):
            a = ax[r, c]
            for k, (name, src, col) in enumerate(S):
                vals = [src[f"{v}_{p}"][lm & m].mean() for _, m in groups]
                a.bar(x + (k - .5) * w, vals, w - 0.03, color=col, label=name)
            a.axhline(0, color="#52514e", lw=0.8); a.grid(axis="y", color="#e6e5e0", lw=0.6); a.set_axisbelow(True)
            for s in ("top", "right"): a.spines[s].set_visible(False)
            a.set_title(f"{p} ({'10-15' if p == 'day' else '20-04'} WIB): {lab}", fontsize=10); a.set_ylabel(lab)
            if r == 1:
                a.set_xticks(x, [f"{g}\nn={(lm & m).sum()}" for g, m in groups], fontsize=8); a.set_xlabel(xlab)
    ax[0, 0].legend(frameon=False, fontsize=9, loc="best")
    fig.suptitle(f"d02 land cells, means 10-07..10-10 after 12 h spin-up, by {xlab}")
    fig.tight_layout(); fig.savefig(R + out, dpi=110); print("->", R + out)
