"""Every setting of the Sentinel-2 -> geo_em pipeline in one place. Run: python run.py [stage ...]"""
import os
from pathlib import Path

H = Path.home()
OUT = H / "WRF/pipeline/out"
GEO_SRC = H / "WRF/runs/default/geo_em.d02.nc"      # untouched original d02; never modified
GEO_OUT = OUT / "geo_em.d02.nc"

# --- composite (Earth Engine) ---
BBOX = (106.45, -6.50, 107.10, -5.88)                # lon0, lat0, lon1, lat1: d02 + ~10 km margin
START, END = "2023-09-01", "2023-10-31"              # END is exclusive in Earth Engine
CRS, RES, NT = "EPSG:32748", 20, 3                   # UTM 48S, 20 m (B11 native), NT x NT download tiles
SCL_KEEP = (4, 5, 6, 7)                              # vegetation, bare, water, unclassified
BANDS = ["B3", "B4", "B8", "B11", "B2", "B12", "N", "NK", "ALB"]   # export order; N = valid dates, NK = dates kept after IQR trim, ALB = broadband albedo x10000
IQR_K = 1.5                                          # Tukey fence factor on the per-scene albedo (1.5 = usual outlier, 3 = far outlier)
ALB_W = {"B2": 0.2266, "B3": 0.1236, "B4": 0.1573, "B8": 0.3417, "B11": 0.1170, "B12": 0.0338}  # Bonafoni and Sekertekin 2020
NODATA = -32768
MOSAIC = OUT / "mosaic.tif"                          # band names live in mosaic.json next to it

# --- monthly 5-year composites (dry/wet design 2026-11-19): PIPE_MONTH=01..12 -> calendar month over CLIM_YEARS; unset = Sep-Oct 2023 case ---
CLIM_YEARS = range(2021, 2026)
MONTH = os.environ.get("PIPE_MONTH")
def clim_dir(m):
    return OUT / "clim5y" / f"m{m:02d}"

# --- classification / aggregation ---
CLASSES = OUT / "classes.tif"                        # bands: fv, fw, fb, ndvi, alb (-9999 = no data)
CELLS = OUT / "cells.npz"
if MONTH:                                            # monthly mode only moves the stage files
    MOSAIC, CLASSES, CELLS = (clim_dir(int(MONTH)) / n for n in ("mosaic.tif", "classes.tif", "cells.npz"))
NDVI_PCT = (5, 98)                                   # NDVIs / NDVIinf anchors for Carlson and Ripley fv (own choice)
GI_NDVI = (0.05, 0.70)                               # NDVI0 / NDVIinf for Gutman and Ignatov GREENFRAC: fixed, user decision 2026-10-22 (bare ~0.05 typical in literature, Zhao et al. 2026; dense ~0.70 = mean NDVI of Dynamic World tree pixels). None -> use GI_PCT
GI_PCT = (5, 95)                                     # old rule (scene percentiles, used for runs up to 2026-10-21); only used if GI_NDVI is None
WC_DIR = H / "sat/wc"                               # ESA WorldCover v200 tiles on the 20 m grid (sat/s2_worldcover.py), used by write_geoem_hybrid.py
MERC = "+proj=merc +lat_ts=0 +lon_0=106.77 +a=6370000 +b=6370000 +units=m +no_defs"   # WPS mercator, sphere R=6370 km

# --- Sentinel-2 LAI (s2_lai.py) -> LAI12M of write_geoem_clim.py (decision 2026-11-25) ---
S2_LAI = OUT / "s2_lai"                              # mMM.npz per calendar month, 2021-2025 (CLIM_YEARS)

# --- MODIS LAI -> LAI12M (P3a) ---
MODIS_CACHE = OUT / "modis_lai.npz"                  # delete to re-query Earth Engine
LAI_CLIM_YEARS = range(2013, 2023)                    # 10 complete years before the case; all daily images of the same month -> keys sep_10y, oct_10y
MONTHS = {"sep": (8, "2023-09-01", "2023-10-01"), "oct": (9, "2023-10-01", "2023-11-01")}   # name: (0-based month, start, end)

# --- P1 route 1: native WorldCover 10 m -> MODIS-21 WPS_GEOG dataset (plan 2026-11-12) ---
# crosswalk = Parde et al. 2026 (Zenodo 10.5281/zenodo.22702177) + D1 tree class per city, D2 wetland/mangrove -> 11, D3 inland water -> 21 (wc_modis.py)
CITY = "jakarta"
TREE_CLASS = 2                                       # D1: Jakarta tree -> evergreen broadleaf
P1_DIR = OUT / "p1"
WC_TILES = ("S06E105", "S09E105")                    # native ESA tiles covering d02 (3x3 deg each, EPSG:4326, 1/12000 deg)
WC_URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{}_Map.tif"
COAST_SHP = H / "data/gshhg/GSHHS_shp/f/GSHHS_f_L1.shp"   # GSHHG 2.3.7 full res, level 1 (user download)
WPS_DS = H / "WRF/WPS_GEOG/wc_modis21_jakarta"
P1_MARGIN = 0.02                                     # deg; WorldCover window must cover d02 corners + this
COAST_BAND = 0.033                                   # deg; Lamarche et al. 2017 sec 3.5 GSHHS buffer (~3.6 km) for the sea/inland split
P1_PROBES = ((-6.00, 106.80), (-6.30, 106.80))         # Review Focus 4: Jakarta Bay sea (must be 17), south Jakarta (must not be 17/21)
# P1_DOM=d01 (env): same P1 steps on the outer-domain window, own output dirs, so the d02 files stay untouched (2026-11-27)
P1_DOM = os.environ.get("P1_DOM", "d02")
P1_GEO = GEO_SRC.with_name(f"geo_em.{P1_DOM}.nc")    # default geo_em whose corners set the WorldCover window
if P1_DOM != "d02":
    P1_DIR, WPS_DS = OUT / f"p1_{P1_DOM}", WPS_DS.with_name(f"{WPS_DS.name}_{P1_DOM}")
    P1_MARGIN = 0.10                                 # 0.02 deg < one 3 km cell: geogrid edge row/col lost land-use data (HGT_M changed there)
