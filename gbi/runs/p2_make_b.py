"""P2 stock check: geo_em B = p1_wc d02 + 0.3 lake (21) in 50 land cells, other classes x0.7; LU_INDEX/LANDMASK unchanged.
Spec sec 4. Run: python -I p2_make_b.py  -> ~/WRF/runs/p2_B_geo_em.d02.nc (+ p2_B_cells.txt)"""
import shutil, numpy as np, netCDF4
src, dst = "/home/8/uw07888/WRF/runs/p1_wc/geo_em.d02.nc", "/home/8/uw07888/WRF/runs/p2_B_geo_em.d02.nc"
shutil.copy(src, dst)
with netCDF4.Dataset(dst, "a") as f:
    lu = f["LANDUSEF"][0].astype("f8"); dom = f["LU_INDEX"][0].astype(int) - 1; lm = f["LANDMASK"][0] == 1
    new = lu * 0.7; new[20] += 0.3
    srt = np.sort(new, 0)
    keep = (new.argmax(0) == dom) & (srt[-1] - srt[-2] > 0.02)      # dominant class unchanged, with margin
    ok = np.argwhere(lm & keep & (lu[20] < 0.01) & (lu[16] < 0.01))  # land cells, no water now
    rng = np.random.default_rng(20261116); pick = ok[rng.choice(len(ok), 50, replace=False)]
    for j, i in pick:
        lu[:, j, i] = new[:, j, i]
    assert abs(lu.sum(0) - 1).max() < 1e-6
    f["LANDUSEF"][0] = lu.astype("f4")
    np.savetxt(dst.replace("_geo_em.d02.nc", "_cells.txt"), pick, fmt="%d", header="j i (0-based) cells with +0.3 lake")
    print(f"{len(ok)} eligible land cells; 50 picked; dominant classes of picked: {np.bincount(dom[tuple(pick.T)] + 1).nonzero()[0].tolist()}")
