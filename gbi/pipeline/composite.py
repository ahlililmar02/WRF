"""Stage 1 (Earth Engine): cloud-masked, IQR-trimmed mean composite of Sentinel-2 + broadband albedo -> tiles -> mosaic.tif/json.
The previous median version is ~/sat/archive/composite_median.py."""
import io, json, time, urllib.request, zipfile
from functools import reduce
import ee, rasterio
from pyproj import Transformer
from rasterio.merge import merge
import config as C


def mask_scl(img):
    scl = img.select("SCL")
    return img.updateMask(reduce(lambda a, b: a.Or(b), [scl.eq(k) for k in C.SCL_KEEP]))


def albedo(img):
    """Broadband albedo of ONE scene, as the extra band ALB (reflectance bands stay)."""
    return img.addBands(reduce(lambda a, b: a.add(b), [img.select(k).multiply(1e-4 * w) for k, w in C.ALB_W.items()]).rename("ALB"))


def build(col):
    """IQR-trimmed mean composite of a masked collection. Tukey fences on the per-scene albedo ALB (q1 - k*IQR, q3 + k*IQR) drop whole
    dates (clouds/haze bright, shadow dark), so all bands of a pixel come from the same days. N = valid dates, NK = dates kept."""
    col = col.map(albedo)
    q = col.select("ALB").reduce(ee.Reducer.percentile([25, 75]))
    q1, q3 = q.select("ALB_p25"), q.select("ALB_p75")
    lo, hi = q1.subtract(q3.subtract(q1).multiply(C.IQR_K)), q3.add(q3.subtract(q1).multiply(C.IQR_K))
    kept = col.map(lambda im: im.updateMask(im.select("ALB").gte(lo).And(im.select("ALB").lte(hi))))
    refl = [b for b in C.BANDS if b not in ("N", "NK", "ALB")]
    return (kept.select(refl).mean().round().toInt16()
            .addBands(col.select("B8").count().toInt16().rename("N"))
            .addBands(kept.select("B8").count().toInt16().rename("NK"))
            .addBands(kept.select("ALB").mean().multiply(1e4).round().toInt16())).select(C.BANDS)


def main():
    ee.Initialize()
    tiles = C.MOSAIC.parent / "tiles"; tiles.mkdir(parents=True, exist_ok=True)
    col = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(ee.Geometry.Rectangle(list(C.BBOX)))
    if C.MONTH:                                                            # one calendar month over all CLIM_YEARS
        y0, y1, m = C.CLIM_YEARS[0], C.CLIM_YEARS[-1] + 1, int(C.MONTH)
        col = col.filterDate(f"{y0}-01-01", f"{y1}-01-01").filter(ee.Filter.calendarRange(m, m, "month"))
    else:
        col = col.filterDate(C.START, C.END)
    col = col.map(mask_scl)
    print("scenes:", col.size().getInfo())
    comp = build(col)

    lon0, lat0, lon1, lat1 = C.BBOX
    t = Transformer.from_crs("EPSG:4326", C.CRS, always_xy=True)
    xs, ys = zip(*[t.transform(lo, la) for lo in (lon0, lon1) for la in (lat0, lat1)])
    R, NT = C.RES, C.NT
    x0, y1 = int(min(xs) // R) * R, int(max(ys) // R + 1) * R             # snap to the 20 m grid, top-left origin
    W, H = (int(max(xs) // R + 1) * R - x0) // R, (y1 - int(min(ys) // R) * R) // R
    tw, th = -(-W // NT), -(-H // NT)
    print("grid", W, "x", H, "px; tile", tw, "x", th, "origin", x0, y1)

    files = []
    for j in range(NT):
        for i in range(NT):
            f = tiles / f"s2_{C.START}_{C.END}_{len(C.BANDS)}b_r{j}c{i}.tif"   # band count in the name: tiles of an older band set are never reused
            files.append(f)
            if f.exists():
                continue
            p = {"dimensions": f"{min(tw, W - i * tw)}x{min(th, H - j * th)}", "crs": C.CRS, "format": "GEO_TIFF",
                 "crs_transform": [R, 0, x0 + i * tw * R, 0, -R, y1 - j * th * R]}
            for _ in range(3):
                try:
                    data = urllib.request.urlopen(comp.getDownloadURL(p), timeout=600).read(); break
                except Exception as e:
                    print("retry", j, i, str(e)[:120]); time.sleep(10)
            else:
                raise SystemExit(f"tile {j},{i} failed")
            if data[:2] == b"PK":                                           # multi-band downloads may arrive zipped
                z = zipfile.ZipFile(io.BytesIO(data)); data = z.read(z.namelist()[0])
            f.write_bytes(data); print("saved", f.name, len(data) // 1024, "KB", flush=True)

    src = [rasterio.open(f) for f in files]
    arr, tr = merge(src, nodata=C.NODATA)
    prof = src[0].profile; prof.update(height=arr.shape[1], width=arr.shape[2], transform=tr, count=len(C.BANDS), nodata=C.NODATA)
    with rasterio.open(C.MOSAIC, "w", **prof) as d: d.write(arr)
    json.dump(C.BANDS, open(C.MOSAIC.with_suffix(".json"), "w"))
    print("mosaic", arr.shape, "->", C.MOSAIC)
