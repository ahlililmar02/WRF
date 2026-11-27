"""Stage 3 (local): 20 m pixels -> d02 1 km cell means (fractions, land NDVI, land albedo) -> cells.npz."""
import numpy as np, rasterio, netCDF4 as nc
import config as C, lib


def main():
    grid = lib.Grid(nc.Dataset(C.GEO_SRC))
    with rasterio.open(C.CLASSES) as r:
        fv, fw, fb, ndvi, alb = r.read(); T = r.transform
    valid = fv > -9000
    land = (fw == 0) & (ndvi > -9000)                    # Gutman and Ignatov uses land pixels only
    N0, NINF = C.GI_NDVI or np.percentile(ndvi[land], C.GI_PCT)
    cnt, n_land = np.zeros((grid.ny, grid.nx)), np.zeros((grid.ny, grid.nx))
    sw = np.zeros((3, grid.ny, grid.nx)); s_ndvi = np.zeros_like(cnt); n_alb, s_alb = np.zeros_like(cnt), np.zeros_like(cnt)
    for sl, flat, inside in grid.chunks(T, fv.shape):
        m = inside & valid[sl]; idx = flat[m]
        cnt += grid.sums(idx)
        for k, a in enumerate((fv, fw, fb)): sw[k] += grid.sums(idx, a[sl][m])
        m = inside & land[sl]; idx = flat[m]
        n_land += grid.sums(idx); s_ndvi += grid.sums(idx, ndvi[sl][m])
        m = inside & land[sl] & (alb[sl] > -9000); idx = flat[m]
        n_alb += grid.sums(idx); s_alb += grid.sums(idx, alb[sl][m])
    if C.MONTH:                                          # monthly mode: clouds also thin cells -> report, gaps are filled later (write_geoem_clim)
        land_cells = nc.Dataset(C.GEO_SRC)["LANDMASK"][0] == 1
        print("month %s: cells with < 90 %% of median pixel count %d; land cells with n_land == 0: %d"
              % (C.MONTH, (cnt < 0.9 * np.median(cnt)).sum(), (land_cells & (n_land == 0)).sum()))
    else:
        assert cnt.min() > 0.9 * np.median(cnt), "some cells not covered by the satellite mosaic"
    Fv, Fw, Fb = sw / cnt
    print("pixels per cell: min %d median %d max %d | d02 means fv %.3f fw %.3f fb %.3f" % (cnt.min(), np.median(cnt), cnt.max(), Fv.mean(), Fw.mean(), Fb.mean()))
    nz = lambda s, n: np.where(n > 0, s / np.maximum(n, 1), np.nan)
    np.savez(C.CELLS, Fv=Fv, Fw=Fw, Fb=Fb, cnt=cnt, ndvi_cell=nz(s_ndvi, n_land), n_land=n_land, N0=N0, NINF=NINF,
             alb_cell=nz(s_alb, n_alb), n_alb=n_alb)      # alb_cell: extracted for later, not written to geo_em yet
