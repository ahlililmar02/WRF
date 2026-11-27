"""Stage 2 (local): indices -> per-pixel water / vegetation / built+bare fractions (fw + fv + fb = 1) -> classes.tif."""
import numpy as np, rasterio
import config as C, lib


def nd(x, y):
    return np.where((x + y) != 0, (x - y) / (x + y), np.nan)


def otsu(x, bins=256):                                   # threshold that best splits a bimodal histogram
    h, e = np.histogram(x, bins=bins, range=(-1, 1)); c = (e[:-1] + e[1:]) / 2
    w0 = np.cumsum(h); w1 = w0[-1] - w0; m0 = np.cumsum(h * c) / np.maximum(w0, 1)
    m1 = (np.sum(h * c) - np.cumsum(h * c)) / np.maximum(w1, 1)
    return c[np.argmax(w0 * w1 * (m0 - m1) ** 2)]


def main():
    b, T, prof = lib.read_mosaic()
    bad = b["B3"] == C.NODATA
    g, r, n, s = [b[k] / 10000.0 for k in ("B3", "B4", "B8", "B11")]
    ndvi, mndwi = nd(n, r), nd(g, s)                     # NDVI (B8, B4); MNDWI (B3, B11, Xu 2006)
    for x in (ndvi, mndwi): x[bad] = np.nan
    ok = ~bad & np.isfinite(mndwi) & np.isfinite(ndvi)

    T_W = round(float(otsu(mndwi[ok])), 2)
    water = ok & (mndwi > T_W)
    land = ok & ~water
    ns, ni = np.nanpercentile(ndvi[land], C.NDVI_PCT)    # soil / full-cover NDVI from our own land pixels
    fv = np.where(land, np.clip((ndvi - ns) / (ni - ns), 0, 1) ** 2, 0.0)    # Carlson and Ripley 1997
    fw = water.astype("float32")
    fb = np.where(ok, 1.0 - fv - fw, np.nan)
    assert np.nanmax(np.abs(fv + fw + fb - 1)[ok]) < 1e-5
    print("T_W %.2f | NDVIs %.3f NDVIinf %.3f | valid pixels: veg %.1f%% water %.1f%% built+bare %.1f%%"
          % (T_W, ns, ni, 100 * fv[ok].mean(), 100 * fw[ok].mean(), 100 * fb[ok].mean()))

    alb = np.where(b["ALB"] != C.NODATA, b["ALB"] / 10000.0, -9999) if "ALB" in b else np.full(bad.shape, -9999)
    out = np.stack([np.where(ok, x, -9999) for x in (fv, fw, fb, ndvi)] + [alb]).astype("float32")
    prof.update(count=5, dtype="float32", nodata=-9999)
    with rasterio.open(C.CLASSES, "w", **prof) as d: d.write(out)
