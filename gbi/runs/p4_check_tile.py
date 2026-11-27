"""P4 T4/T5/T6b checks on wrfout_d02. usage: python -I p4_check_tile.py
T4: stock lake cells (LAKEMASK=1) in p4_T4_base: HFX==HFX_LKT, LH==LH_LKT, GRDFLX==GRD_LKT, TSK==TSK_LKT.
T5: test cell (24,33) fw=0.3 in p4_T5_cell: X == 0.7*X_LND + 0.3*X_LKT (HFX, LH, GRDFLX); EMISS == 0.7*EMISS_LAND + 0.3*0.97;
    TSK == ((0.7*e_l*TSK_LAND^4 + 0.3*0.97*TSK_LKT^4)/EMISS)^0.25.  Tolerance: float32 rounding.
T6b: TSK_LAND at the test cell vs TSK of the fw=0 run (p4_T3_on) at the same cell and time (land state not leaking)."""
import glob, numpy as np, netCDF4
R = "/home/8/uw07888/WRF/runs/"
op = lambda r: netCDF4.Dataset(sorted(glob.glob(R + r + "/wrfout_d02_*"))[0])
b = op("p4_T4_base"); lm = b["LAKEMASK"][0] == 1
print(f"T4: {lm.sum()} lakemask cells")
for x, y in (("HFX", "HFX_LKT"), ("LH", "LH_LKT"), ("GRDFLX", "GRD_LKT"), ("TSK", "TSK_LKT")):
    d = np.abs(b[x][1:][:, lm] - b[y][1:][:, lm]).max()
    print(f"   {x} vs {y}: max |diff| over times 1.. = {d:.3g}  {'OK' if d == 0 else 'FAIL'}")
c = op("p4_T5_cell"); j, i = 24, 33; fw = 0.3
print(f"T5: test cell ({j},{i}) LANDUSEF(17) in geo_em = {netCDF4.Dataset(R + 'p4_geo/geo_em_cell.d02.nc')['LANDUSEF'][0][16][j, i]:.3f}, LAKEMASK {c['LAKEMASK'][0][j, i]}, times {c['HFX'].shape[0]}")
for x, l, w in (("HFX", "HFX_LND", "HFX_LKT"), ("LH", "LH_LND", "LH_LKT"), ("GRDFLX", "GRD_LND", "GRD_LKT")):
    X, L, W = (c[v][1:, j, i].astype("f8") for v in (x, l, w))
    d = np.abs(X - ((1 - fw) * L + fw * W)).max()
    print(f"   {x}: max |cell - (0.7 land + 0.3 lake)| = {d:.2e} W m-2  {'OK' if d < 1e-3 else 'FAIL'};  "
          f"mean land {L.mean():7.1f}  lake {W.mean():7.1f}  cell {X.mean():7.1f}")
E, EL = c["EMISS"][1:, j, i].astype("f8"), c["EMISS_LAND"][1:, j, i].astype("f8")
print(f"   EMISS: max |diff| = {np.abs(E - ((1 - fw) * EL + fw * 0.97)).max():.2e}")
T, TL, TW = (c[v][1:, j, i].astype("f8") for v in ("TSK", "TSK_LAND", "TSK_LKT"))
Tc = (((1 - fw) * EL * TL ** 4 + fw * 0.97 * TW ** 4) / E) ** 0.25
print(f"   TSK (LW-conserving): max |diff| = {np.abs(T - Tc).max():.2e} K; mean TSK land {TL.mean():.2f} lake {TW.mean():.2f} cell {T.mean():.2f}")
z = op("p4_T3_on")
t0 = z["TSK"][1:, j, i].astype("f8")
print(f"T6b: TSK_LAND(tile run) - TSK(fw=0 run) at test cell: time 1 (10 min) {TL[0] - t0[0]:+.3f} K, max over 6 h {np.abs(TL - t0).max():.3f} K")
