"""ESA WorldCover v200 class -> MODIS-21 (MODIFIED_IGBP_MODIS_NOAH) category, per pixel.

Base table: Parde et al. 2026 (Zenodo 10.5281/zenodo.22702177), verbatim. Deviations (decisions 2026-11-11/12, WORKLOG):
  D1 tree (10) -> tree_class, set per city;  D3 water (80) -> 21 lake if inside GSHHG land polygon, else 17;
  D2 wetland (90) and mangrove (95) stay 11 (vegetated physics; blue only in accounting).
"""
import numpy as np

TABLE = {10: 5, 20: 7, 30: 10, 40: 12, 50: 13, 60: 16, 70: 15, 80: 17, 90: 11, 95: 11, 100: 19, 0: 17}


def crosswalk(wc, inland, tree_class):
    """wc: uint8 WorldCover classes; inland: bool, True inside a coastline land polygon. Returns uint8 MODIS ids 1..21."""
    bad = np.setdiff1d(np.unique(wc), list(TABLE))
    if bad.size:
        raise ValueError(f"unknown WorldCover classes {bad.tolist()}")
    lut = np.zeros(256, np.uint8)
    for k, v in TABLE.items():
        lut[k] = v
    lut[10] = tree_class
    return np.where((wc == 80) & inland, np.uint8(21), lut[wc]).astype(np.uint8)
