"""P1 Task 2: native WorldCover 10 m window over d02 + inland/sea split of its water, on the same grid.

-> out/p1/wc_native.tif (uint8 WorldCover class, 0 = no data) and out/p1/inland.tif (uint8, 1 = not open sea; 0 = sea water).
Sea/inland split follows Lamarche et al. 2017 (RS 9:36, sec 3.5): the coastline comes from the water map itself; GSHHS is only
used, with a +0.033 deg band, to cut rivers from the ocean. Our reading (not spelled out in the paper): sea = WorldCover water
4-connected to open sea (water > band offshore of the GSHHS coast), flooding no deeper than the band into GSHHS land.
Grid: EPSG:4326, pixel 1/12000 deg, aligned to the WorldCover pixel grid. Run: python -I wc_fetch.py
"""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, rasterio, netCDF4
from scipy import ndimage as nd
from rasterio.windows import Window
from rasterio.transform import from_origin
from osgeo import gdal, ogr
import config as C

N = 12000                                            # WorldCover pixels per degree; all grid math in integer pixel units
gdal.UseExceptions()


def bbox():
    """domain (C.P1_DOM) corner extent + margin, snapped outward to the 1/N grid -> integer pixel edges (i0, i1, j0, j1) = (W, E, S, N) * N."""
    with netCDF4.Dataset(C.P1_GEO) as f:
        lat, lon = f["XLAT_C"][0].astype("f8"), f["XLONG_C"][0].astype("f8")
    m = C.P1_MARGIN
    return (math.floor((lon.min() - m) * N), math.ceil((lon.max() + m) * N),
            math.floor((lat.min() - m) * N), math.ceil((lat.max() + m) * N)), lat, lon


def read_wc(i0, i1, j0, j1):
    out = np.zeros((j1 - j0, i1 - i0), np.uint8)
    for t in C.WC_TILES:
        with rasterio.open("/vsicurl/" + C.WC_URL.format(t)) as r:
            T = r.transform
            assert abs(T.a - 1 / N) < 1e-12 and abs(-T.e - 1 / N) < 1e-12, (t, T)
            left, top = round(T.c * N), round(T.f * N)
            assert abs(T.c * N - left) < 1e-6 and abs(T.f * N - top) < 1e-6, ("tile not on 1/N grid", t, T)
            win = Window(i0 - left, top - j1, i1 - i0, j1 - j0)
            a = r.read(1, window=win, boundless=True, fill_value=0)
        out = np.maximum(out, a)                     # tiles do not overlap; outside fill is 0
        print(f"{t}: read window, {np.count_nonzero(a):,} valid pixels")
    return out


def rasterize_land(i0, i1, j0, j1, transform):
    ds = gdal.GetDriverByName("MEM").Create("", i1 - i0, j1 - j0, 1, gdal.GDT_Byte)
    ds.SetGeoTransform(transform.to_gdal())
    ds.SetProjection("EPSG:4326")
    src = ogr.Open(str(C.COAST_SHP))
    lyr = src.GetLayer()
    lyr.SetSpatialFilterRect(i0 / N, j0 / N, i1 / N, j1 / N)
    print(f"GSHHS L1 polygons in bbox: {lyr.GetFeatureCount()}")
    gdal.RasterizeLayer(ds, [1], lyr, burn_values=[1], options=["ALL_TOUCHED=FALSE"])   # pixel-centre rule
    return ds.GetRasterBand(1).ReadAsArray().astype(np.uint8)


def sea_mask(wc, land, band_px):
    """wc: WorldCover classes; land: bool GSHHS L1 land; band_px: Lamarche buffer in pixels. -> bool, True = sea water."""
    water = wc == 80
    seed = water & (nd.distance_transform_edt(~land) > band_px)      # open sea: water beyond the band, offshore
    if not seed.any():
        if (water & ~land).any():
            raise ValueError("water offshore of GSHHS but none beyond the band: widen the bbox to include open sea")
        return np.zeros(wc.shape, bool)                              # no sea in the domain: all water inland
    reach = water & ~(land & (nd.distance_transform_edt(land) > band_px))   # water outside deep GSHHS land
    lab, _ = nd.label(reach)                                         # default structure = 4-connectivity
    ids = np.unique(lab[seed]); ids = ids[ids > 0]
    return np.isin(lab, ids)


def write(path, a, transform, nodata):
    prof = dict(driver="GTiff", dtype="uint8", count=1, width=a.shape[1], height=a.shape[0], crs="EPSG:4326",
                transform=transform, compress="lzw", tiled=True, nodata=nodata)
    with rasterio.open(path, "w", **prof) as w:
        w.write(a, 1)


def main():
    (i0, i1, j0, j1), lat, lon = bbox()
    T = from_origin(i0 / N, j1 / N, 1 / N, 1 / N)
    print(f"bbox lon {i0/N:.5f}..{i1/N:.5f}  lat {j0/N:.5f}..{j1/N:.5f}  shape {(j1-j0, i1-i0)}")
    # Review Focus 1: raster must contain every d02 corner (+ margin by construction)
    assert i0 / N <= lon.min() and i1 / N >= lon.max() and j0 / N <= lat.min() and j1 / N >= lat.max()
    wc = read_wc(i0, i1, j0, j1)
    land = rasterize_land(i0, i1, j0, j1, T)
    # Review Focus 2: no no-data seam where the two tiles meet (lat -6.0), on the land side
    seam = j1 - (-6 * N)                             # first row south of lat -6.0; row seam-1 is first row north
    if 0 < seam < wc.shape[0]:
        rows = wc[seam - 1:seam + 1]
        n0 = int(((rows == 0) & (land[seam - 1:seam + 1] == 1)).sum())
        assert n0 == 0, f"{n0} class-0 land pixels at the -6.0 seam"
        print(f"seam lat -6.0: 0 no-data land pixels in rows {seam-1},{seam}")
    vals, cnt = np.unique(wc, return_counts=True)
    print("class counts:", {int(v): int(c) for v, c in zip(vals, cnt)})
    n0 = int((wc == 0).sum())
    print(f"class 0 (no data): {n0:,} = {n0 / wc.size:.4%}")
    w80 = wc == 80
    sea = sea_mask(wc, land == 1, round(C.COAST_BAND * N))
    inl = w80 & ~sea
    print(f"class 80: {w80.sum():,} px; sea (-> 17): {sea.sum():,}; inland (-> 21): {inl.sum():,} = {inl.sum() / max(w80.sum(), 1):.2%}")
    print(f"  of which inside GSHHS land: sea {(sea & (land == 1)).sum():,}, inland {(inl & (land == 1)).sum():,}; "
          f"outside GSHHS land: inland {(inl & (land == 0)).sum():,}")
    C.P1_DIR.mkdir(parents=True, exist_ok=True)
    write(C.P1_DIR / "wc_native.tif", wc, T, 0)
    write(C.P1_DIR / "inland.tif", (~sea).astype(np.uint8), T, None)
    print("wrote", C.P1_DIR / "wc_native.tif", C.P1_DIR / "inland.tif")


if __name__ == "__main__":
    main()
