"""P4 test geo_em variants from the P3a baseline geo_em (plan 2026-11-16 Task 4).
fw0: every land cell's water (17+21) moved to its dominant class -> fw = 0 on land.
cell: fw0 + one inland urban cell with fw = 0.3.  block_XX: fw0 + 5x5 inland block with fw = 0.10 / 0.25 / 0.40
(0.5 would flip LANDMASK/LU_INDEX to water). Water is added as class 17, others scaled by (1 - fw).
Asserts: only LANDUSEF differs from the parent; sums to 1; LU_INDEX and LANDMASK unchanged.
Run: python -I p4_make_geo.py -> ~/WRF/runs/p4_geo/*.nc + cells.txt"""
import shutil, numpy as np, netCDF4
from pathlib import Path
SRC = Path("/home/8/uw07888/WRF/runs/p3a_base_geo_em.d02.nc"); OUT = Path("/home/8/uw07888/WRF/runs/p4_geo"); OUT.mkdir(exist_ok=True)
with netCDF4.Dataset(SRC) as f:
    lu0 = f["LANDUSEF"][0].astype("f8"); dom = f["LU_INDEX"][0].astype(int) - 1; lm = f["LANDMASK"][0] == 1
ny, nx = dom.shape
fw0 = lu0.copy()
J, I = np.nonzero(lm)
w = fw0[16, J, I] + fw0[20, J, I]
fw0[dom[J, I], J, I] += w; fw0[16, J, I] = 0; fw0[20, J, I] = 0

def add_water(base, cells, fw):
    out = base.copy()
    for j, i in cells:
        out[:, j, i] *= (1 - fw); out[16, j, i] += fw
    return out

dshare = np.take_along_axis(fw0, dom[None], 0)[0]
ok = lm & (dom == 12) & (dshare >= 0.7)                    # urban-dominant (13), strong dominance
cand = [(j, i) for j in range(8, ny - 8) for i in range(8, nx - 8) if ok[j:j + 5, i:i + 5].all()]
assert cand, "no 5x5 block"
bj, bi = cand[len(cand) // 2]
block = [(j, i) for j in range(bj, bj + 5) for i in range(bi, bi + 5)]
cell = [(bj + 2, bi + 2)]                                   # centre of the block
variants = {"fw0": fw0, "cell": add_water(fw0, cell, 0.3)}
for fw in (0.10, 0.25, 0.40):
    variants[f"block_{int(fw * 100):02d}"] = add_water(fw0, block, fw)
for name, lu in variants.items():
    p = OUT / f"geo_em_{name}.d02.nc"; shutil.copy(SRC, p)
    with netCDF4.Dataset(p, "a") as f:
        f["LANDUSEF"][0] = lu.astype("f4")
    with netCDF4.Dataset(SRC) as a, netCDF4.Dataset(p) as b:
        for v in a.variables:
            if v != "LANDUSEF" and a[v].dtype.kind not in "SU":
                assert np.array_equal(a[v][:], b[v][:]), (name, v)
        L = b["LANDUSEF"][0].astype("f8")
        assert abs(L.sum(0) - 1).max() < 1e-5, name
        Lland = L.copy(); Lland[[16, 20]] = -1             # geogrid: land cells take the dominant LAND class
        assert (Lland.argmax(0)[lm] == dom[lm]).all(), name   # LU_INDEX stays consistent
        assert ((L[16] + L[20] < 0.5) == lm).all(), name
        print(f"{name:9s} land-cell fw: mean {(L[16] + L[20])[lm].mean():.4f}, cells fw>0: {int(((L[16] + L[20]) > 0)[lm].sum())}")
np.savetxt(OUT / "cells.txt", np.array(block), fmt="%d", header=f"0-based j i of the 5x5 block; test cell = {cell[0]}")
print("block origin (j,i) =", (bj, bi), "test cell =", cell[0])
