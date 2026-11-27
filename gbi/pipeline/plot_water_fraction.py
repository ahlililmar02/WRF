"""Water at full WorldCover resolution vs the water fraction WRF gets (LANDUSEF 17+21 on d02).
Out: out/p1/water_fraction.png"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, PowerNorm
from netCDF4 import Dataset
import config as C
from wc_to_wps import read_tile

ZOOM = (106.88, 107.00, -6.16, -6.04)          # NE coast: fishponds + river mouth

a, idx = read_tile(C.WPS_DS)                    # rows north -> south
d = float(idx["dx"])
w, s = float(idx["known_lon"]) - d / 2, float(idx["known_lat"]) - d / 2
ext = (w, w + a.shape[1] * d, s, s + a.shape[0] * d)
pix = np.where(a == 17, 2, np.where(a == 21, 1, 0)).astype(np.uint8)   # 0 other, 1 inland, 2 sea

with Dataset(C.H / "WRF/runs/p1_wc/geo_em.d02.nc") as g:
    lat, lon = g["XLAT_M"][0], g["XLONG_M"][0]
    lu = g["LANDUSEF"][0]
    fw = lu[16] + lu[20]                        # classes 17 + 21 (0-based 16, 20)
    land = g["LANDMASK"][0]
    clat, clon = g["XLAT_C"][0], g["XLONG_C"][0]
assert np.all((fw >= 0) & (fw <= 1.0001))

cmap_pix = ListedColormap(["#e8e4d8", "#4fa3e0", "#0b3d91"])
fig, ax = plt.subplots(2, 2, figsize=(13, 12), constrained_layout=True)
for row, box in enumerate([None, ZOOM]):
    p = ax[row, 0].imshow(pix, extent=ext, cmap=cmap_pix, vmin=-0.5, vmax=2.5, interpolation="nearest")
    m = ax[row, 1].pcolormesh(clon, clat, fw, cmap="Blues", norm=PowerNorm(0.4, 0, 1))   # stretch so 1-10 % river cells show
    ax[row, 1].contour(lon, lat, land, [0.5], colors="red", linewidths=0.8)
    for k in (0, 1):
        if box:
            ax[row, k].set_xlim(box[:2]); ax[row, k].set_ylim(box[2:])
            for x in clon[0]: ax[row, k].axvline(x, color="k", lw=0.3, alpha=0.4)   # 1 km cell edges
            for y in clat[:, 0]: ax[row, k].axhline(y, color="k", lw=0.3, alpha=0.4)
        else:
            ax[row, k].set_xlim(clon.min(), clon.max()); ax[row, k].set_ylim(clat.min(), clat.max())
        ax[row, k].set_aspect("equal")
    z = "zoom NE coast, grey = 1 km WRF cells" if box else "d02"
    ax[row, 0].set_title(f"WorldCover 10 m: light = inland 21, dark = sea 17\n({z})")
    ax[row, 1].set_title(f"WRF input LANDUSEF 17+21 per cell, red = LANDMASK edge\n({z})")
    if not box:
        ax[0, 0].add_patch(plt.Rectangle((ZOOM[0], ZOOM[2]), ZOOM[1] - ZOOM[0], ZOOM[3] - ZOOM[2], fill=False, ec="red"))
fig.colorbar(m, ax=ax[:, 1], shrink=0.5, label="water fraction")
n = ((land == 1) & (fw > 0)).sum()
fig.suptitle(f"Jakarta d02 water: full resolution vs WRF input  ({n} land cells with water > 0, mean fw land = {fw[land == 1].mean():.3f})")
out = C.P1_DIR / "water_fraction.png"
fig.savefig(out, dpi=150)
print(out, n)
