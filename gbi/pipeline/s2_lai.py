"""Sentinel-2 effective LAI (s2biophys; Specker et al., preprint rs-6343364/v3) per d02 cell for one calendar month, 2021-2025.
Earth Engine: S2_SR_HARMONIZED surface reflectance (gee-biophys 2.1.3 defaults to L1C top-of-atmosphere, WORKLOG 11-25),
CLOUDY_PIXEL_PERCENTAGE <= 50, Cloud Score+ >= 0.70. Per image the mean of the 5 networks (forward pass re-written from
gee-biophys 2.1.3, MIT licence; weights in data/s2biophys_w.json), then the mean over images, clamped 0-8, WorldCover water
masked. 20 m tiles -> mean of the valid pixels in each 1 km cell (whole cell, not scaled to its natural part).
Run: python -I s2_lai.py MONTH [SCENE_MAX, default 50; other values add _ccN to file names]  ->  out/s2_lai/mMM.npz: sr = LAI, cov = valid share of the cell's pixels, cnt = mean images per valid pixel.
Moved from the throwaway July test ~/scratch/lai_test_2026-11-25/run.py + stats.py (2026-11-26)."""
import sys, io, json, math, time, zipfile, urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, netCDF4 as nc, rasterio
from rasterio.merge import merge
from pyproj import Transformer
import config as C, lib

OUT = C.S2_LAI
W = json.load(open(Path(__file__).parent / "data/s2biophys_w.json"))
B = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
NT, R = 10, 20                                             # 10 x 10 download tiles of 20 m pixels


def lai_image(ee, M, cc=50):
    """ee.Image with bands SR (LAI x 1000, -9999 = no data) and CNT (valid images per pixel) for calendar month M."""
    box = ee.Geometry.Rectangle(list(C.BBOX))
    y0, y1 = C.CLIM_YEARS[0], C.CLIM_YEARS[-1] + 1
    cs = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")

    def angles(im):
        n = lambda k: im.getNumber(k)
        mean = lambda key: ee.Array([n(key + b) for b in B]).reduce(ee.Reducer.mean(), [0]).get([0])
        a = ee.Image([ee.Image(n("MEAN_SOLAR_ZENITH_ANGLE")).toFloat(), ee.Image(mean("MEAN_INCIDENCE_ZENITH_ANGLE_")).toFloat(),
                      ee.Image(mean("MEAN_INCIDENCE_AZIMUTH_ANGLE_").subtract(n("MEAN_SOLAR_AZIMUTH_ANGLE")).abs()).toFloat()])
        return im.addBands(a.rename(["tts", "tto", "psi"]))

    def member(x, w):
        span = {b: w["mm"][b]["max"] - w["mm"][b]["min"] for b in B}
        lo = [w["mm"][b]["min"] - .01 * span[b] for b in B]; hi = [w["mm"][b]["max"] + .01 * span[b] for b in B]
        r = x.select(B); r = r.updateMask(r.gte(ee.Image.constant(lo)).And(r.lte(ee.Image.constant(hi))))
        if w["nirv"]:
            r = r.divide(r.normalizedDifference(["B8", "B4"]).multiply(r.select("B8")))
        assert w["feat"] == B
        r = r.subtract(ee.Image.constant(w["mean"])).divide(ee.Image.constant(w["scale"]))
        a = r.addBands(x.select(["tts", "tto", "psi"]).multiply(math.pi / 180).cos()).toArray().toArray(1).arrayTranspose()
        for k, (c, b) in enumerate(zip(w["layers"], w["bias"])):
            a = a.matrixMultiply(ee.Image(ee.Array(c))).add(ee.Image(ee.Array(b).reshape([1, -1])))
            if k < len(w["layers"]) - 1:
                a = a.tanh()
        y = a.arrayProject([0]).arrayFlatten([["y"]])
        if w["target"] == "log1p":
            return y.exp().subtract(1)
        if w["target"] == "standard":
            return y.multiply(w["tscale"]).add(w["tmean"])
        assert w["target"] in (None, "None"), w["target"]
        return y

    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterDate(f"{y0}-01-01", f"{y1}-01-01")
           .filter(ee.Filter.calendarRange(M, M, "month")).filterBounds(box).filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", cc))
           .linkCollection(cs, ["cs"])
           .map(lambda im: im.select(B).divide(10000).updateMask(im.select("cs").gte(0.70)).copyProperties(im, im.propertyNames()))
           .map(lambda im: angles(ee.Image(im))))
    lai = col.map(lambda im: ee.ImageCollection([member(ee.Image(im), w) for w in W]).mean().rename("y"))
    land = ee.ImageCollection("ESA/WorldCover/v200").first().neq(80)
    sr = lai.mean().clamp(0, 8).updateMask(land).multiply(1000).unmask(-9999).round().toInt16().rename("SR")
    print(f"m{M:02d}: {col.size().getInfo()} images", flush=True)
    return ee.Image.cat([sr, lai.count().unmask(0).toInt16().rename("CNT")])


def download(M, cc=50):
    """20 m GeoTIFF tiles of lai_image over C.BBOX in C.CRS -> list of paths (existing tiles are kept, so a rerun resumes)."""
    import ee
    ee.Initialize()
    img = lai_image(ee, M, cc); tag = f"m{M:02d}" + ("" if cc == 50 else f"_cc{cc}")
    t = Transformer.from_crs("EPSG:4326", C.CRS, always_xy=True); lo0, la0, lo1, la1 = C.BBOX
    xs, ys = zip(*[t.transform(a, b) for a in (lo0, lo1) for b in (la0, la1)])
    x0, y1 = int(min(xs) // R) * R, int(max(ys) // R + 1) * R
    wd, h = (int(max(xs) // R + 1) * R - x0) // R, (y1 - int(min(ys) // R) * R) // R
    tw, th = -(-wd // NT), -(-h // NT)
    (OUT / "tiles").mkdir(parents=True, exist_ok=True)

    def get(ji):
        j, i = ji; f = OUT / "tiles" / f"{tag}_r{j}c{i}.tif"
        if f.exists():
            return f
        p = {"dimensions": f"{min(tw, wd - i * tw)}x{min(th, h - j * th)}", "crs": C.CRS, "format": "GEO_TIFF",
             "crs_transform": [R, 0, x0 + i * tw * R, 0, -R, y1 - j * th * R]}
        for k in range(4):
            try:
                d = urllib.request.urlopen(img.getDownloadURL(p), timeout=900).read()
                if d[:2] == b"PK":
                    z = zipfile.ZipFile(io.BytesIO(d)); d = z.read(z.namelist()[0])
                f.with_suffix(".part").write_bytes(d); f.with_suffix(".part").rename(f)
                return f
            except Exception as e:
                print("retry", j, i, str(e)[:160], flush=True); time.sleep(15)
        raise RuntimeError(f"tile {j},{i} failed 4 times")

    with ThreadPoolExecutor(6) as ex:
        return list(ex.map(get, [(j, i) for j in range(NT) for i in range(NT)]))


def to_cells(files):
    """Merge tiles and average the valid 20 m pixels per d02 cell -> dict sr, cov, cnt (54 x 54, NaN = no valid pixel)."""
    src = [rasterio.open(f) for f in files]
    A, T = merge(src)
    sr, cnt = A[0].astype("f4"), A[1].astype("f4")
    sr[sr == -9999] = np.nan; sr /= 1000
    grid = lib.Grid(nc.Dataset(C.GEO_SRC))
    n, nv, s, c = (np.zeros((grid.ny, grid.nx)) for _ in range(4))
    for sl, flat, inside in grid.chunks(T, sr.shape):
        q = inside & np.isfinite(sr[sl])
        n += grid.sums(flat[inside]); nv += grid.sums(flat[q]); s += grid.sums(flat[q], sr[sl][q]); c += grid.sums(flat[q], cnt[sl][q])
    with np.errstate(invalid="ignore", divide="ignore"):
        out = {"sr": np.where(nv > 0, s / nv, np.nan), "cov": np.where(n > 0, nv / n, np.nan), "cnt": np.where(nv > 0, c / nv, np.nan)}
    assert np.nanmin(out["sr"]) >= 0 and np.nanmax(out["sr"]) <= 8 and np.nanmax(out["cov"]) <= 1
    return out


def main():
    M = int(sys.argv[1]); assert 1 <= M <= 12
    cc = int(sys.argv[2]) if len(sys.argv) > 2 else 50; name = f"m{M:02d}" + ("" if cc == 50 else f"_cc{cc}")
    out = to_cells(download(M, cc))
    np.savez(OUT / f"{name}.npz", **out)
    print(f"{name}: cells with LAI {np.isfinite(out['sr']).sum()}, mean LAI {np.nanmean(out['sr']):.3f}, "
          f"median images per pixel {np.nanmedian(out['cnt']):.1f} -> {OUT / (name + '.npz')}", flush=True)


if __name__ == "__main__":
    main()
