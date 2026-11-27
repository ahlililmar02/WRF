"""ERA5 GRIB for ungrib (Vtable.ECMWF), whole days. usage: python -I era5_get.py OUTDIR YYYY-MM-DD [YYYY-MM-DD ...]
Lists copied from ~/sat/era5_get.py (2023 case). Days whose sfc and pl files both exist are skipped."""
import sys, os, cdsapi

AREA = [-4.5, 105.1, -7.9, 108.5]            # N, W, S, E: outer domain (~150 km) + ~1 deg margin
HOURS = [f"{h:02d}:00" for h in range(24)]
SFC = ["2m_temperature", "2m_dewpoint_temperature", "10m_u_component_of_wind", "10m_v_component_of_wind",
       "surface_pressure", "mean_sea_level_pressure", "skin_temperature", "sea_surface_temperature",
       "sea_ice_cover", "snow_depth", "land_sea_mask", "geopotential",
       "soil_temperature_level_1", "soil_temperature_level_2", "soil_temperature_level_3", "soil_temperature_level_4",
       "volumetric_soil_water_layer_1", "volumetric_soil_water_layer_2", "volumetric_soil_water_layer_3",
       "volumetric_soil_water_layer_4"]
PL = ["geopotential", "temperature", "u_component_of_wind", "v_component_of_wind", "relative_humidity"]
LEV = [str(p) for p in (1000, 975, 950, 925, 900, 875, 850, 825, 800, 775, 750, 700, 650, 600, 550, 500, 450, 400, 350, 300,
                        250, 225, 200, 175, 150, 125, 100, 70, 50, 30, 20, 10, 7, 5, 3, 2, 1)]

out, days = sys.argv[1], sys.argv[2:]
assert days, __doc__
os.makedirs(out, exist_ok=True)
c = cdsapi.Client()
for day in days:
    y, m, d = day.split("-")
    sfc, pl = f"{out}/era5_sfc_{y}{m}{d}.grib", f"{out}/era5_pl_{y}{m}{d}.grib"
    if os.path.exists(sfc) and os.path.exists(pl):
        print("skip", day); continue
    base = {"product_type": "reanalysis", "year": y, "month": m, "day": d, "time": HOURS, "area": AREA, "data_format": "grib"}
    c.retrieve("reanalysis-era5-single-levels", dict(base, variable=SFC), sfc)
    c.retrieve("reanalysis-era5-pressure-levels", dict(base, variable=PL, pressure_level=LEV), pl)
