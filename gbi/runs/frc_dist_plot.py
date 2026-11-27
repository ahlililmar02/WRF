"""FRC_URB2D distribution, d02 land cells: WRF default (GAIA, kept only in urban-dominant cells IVGTYP 13, zeroed elsewhere
by urban_var_init) vs WorldCover built share (all land cells, as kept by mosaic_frc_opt=1).
Inputs: s2lai_jul/wrfinput_d02 (default), frcwc_jul/wrfinput_d02 (WorldCover). Out: runs/frc_dist.png, printed stats."""
import numpy as np, netCDF4, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "/home/8/uw07888/WRF/runs/"

def get(run):
    w = netCDF4.Dataset(R + f"{run}/wrfinput_d02")
    return (np.asarray(w[v][0]) for v in ("FRC_URB2D", "IVGTYP", "LANDMASK"))

gf, giv, land = get("s2lai_jul"); wf, _, wland = get("frcwc_jul")
assert (land == wland).all()
land = land == 1; urb = giv == 13
default = np.where(urb, gf, 0.)          # what the stock model keeps
wc = wf                                   # all land cells (water cells not plotted)

A, B = default[land], wc[land]
for n, x in (("default (GAIA, urban-dominant only)", A), ("WorldCover (all land)", B)):
    print(f"{n:38s} n={x.size} zero={int((x == 0).sum())} mean={x.mean():.3f} median={np.median(x):.3f} "
          f"mean(>0)={x[x > 0].mean():.3f}")

fig, ax = plt.subplots(2, 2, figsize=(11, 9))
bins = np.linspace(0, 1, 21)
for x, c, lab in ((A, "tab:gray", "default GAIA, urban-dominant only"), (B, "tab:orange", "WorldCover, all land")):
    ax[0, 0].hist(x, bins, histtype="step", lw=2, color=c,
                  label=f"{lab}\nmean {x.mean():.2f}, zeros {int((x == 0).sum())}")
ax[0, 0].set(xlabel="FRC_URB2D", ylabel="land cells (of %d)" % A.size, title="Histogram (bin 0.05)")
ax[0, 0].legend(fontsize=8)
for x, c in ((A, "tab:gray"), (B, "tab:orange")):
    s = np.sort(x); ax[0, 1].plot(s, np.arange(1, s.size + 1) / s.size, color=c, lw=2)
ax[0, 1].set(xlabel="FRC_URB2D", ylabel="cumulative fraction of land cells", title="CDF")
ax[0, 1].grid(alpha=.3)
for a, f, t in ((ax[1, 0], default, "default: GAIA, urban-dominant cells only"), (ax[1, 1], wc, "WorldCover built share, all land")):
    im = a.imshow(np.ma.masked_where(~land, f), origin="lower", cmap="Greys", vmin=0, vmax=1)
    a.contour(urb, [0.5], colors="tab:red", linewidths=.6); a.set_title(t, fontsize=10); a.set_xticks([]); a.set_yticks([])
fig.colorbar(im, ax=ax[1], shrink=.8, label="FRC_URB2D (red line = IVGTYP urban edge)")
fig.suptitle("FRC_URB2D on d02 land cells: stock WRF vs WorldCover (mosaic_frc_opt=1)")
fig.savefig(R + "frc_dist.png", dpi=130, bbox_inches="tight"); print("wrote", R + "frc_dist.png")
