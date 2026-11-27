"""Shared helpers: mosaic reader, WPS-grid binning, Earth Engine cell polygons."""
import json
import numpy as np, rasterio
from pyproj import Transformer
import config as C


def read_mosaic(path=C.MOSAIC):
    """-> ({band name: float32 array}, transform, profile). Band names come from mosaic.json, never from position."""
    names = json.load(open(path.with_suffix(".json")))
    with rasterio.open(path) as r:
        a = r.read().astype("float32")
        assert len(names) == a.shape[0], (names, a.shape)
        return dict(zip(names, a)), r.transform, r.profile


class Grid:
    """d02 cell geometry in WPS mercator; cells are 1 km squares around the XLAT_M/XLONG_M centres."""
    def __init__(self, f):
        lat, lon = f["XLAT_M"][0].astype("f8"), f["XLONG_M"][0].astype("f8")
        self.ny, self.nx = lat.shape
        xc, yc = Transformer.from_crs("EPSG:4326", C.MERC, always_xy=True).transform(lon, lat)
        self.x_lo, self.y_lo = xc[0, 0] - 500, yc[0, 0] - 500

    def chunks(self, T, shape, step=400, crs=C.CRS):
        """Yield (row slice, flat cell index per pixel, inside-grid mask) for row chunks of a raster in `crs` (default UTM)."""
        tu = Transformer.from_crs(crs, C.MERC, always_xy=True)
        cols = np.arange(shape[1])
        for r0 in range(0, shape[0], step):
            rows = np.arange(r0, min(r0 + step, shape[0]))
            X, Y = np.meshgrid(T.c + (cols + .5) * T.a, T.f + (rows + .5) * T.e)
            mx, my = tu.transform(X, Y)
            ci, cj = np.floor((mx - self.x_lo) / 1000).astype(int), np.floor((my - self.y_lo) / 1000).astype(int)
            yield slice(rows[0], rows[-1] + 1), cj * self.nx + ci, (ci >= 0) & (ci < self.nx) & (cj >= 0) & (cj < self.ny)

    def sums(self, idx, w=None):
        return np.bincount(idx, weights=w, minlength=self.ny * self.nx).reshape(self.ny, self.nx)


def cell_polygons(f):
    """Earth Engine FeatureCollection of the d02 cells (corner lat/lon), properties j, i."""
    import ee
    la, lo = f["XLAT_C"][0], f["XLONG_C"][0]
    ny, nx = la.shape[0] - 1, la.shape[1] - 1
    return ee.FeatureCollection([
        ee.Feature(ee.Geometry.Polygon([[[float(lo[a, b]), float(la[a, b])] for a, b in ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i), (j, i))]]), {"j": j, "i": i})
        for j in range(ny) for i in range(nx)])
