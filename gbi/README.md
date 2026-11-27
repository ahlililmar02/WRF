# gbi/: Jakarta green/blue/built project files

The WRF Fortran changes (P4 pond tile, `lake_tile_opt`) sit in the WRF tree of this branch.
This folder holds the project scripts that make the inputs, run the cases and compare them.
It is a copy of the private project repo (WRF-GBI). The run log and data are not included.

| Folder | What is in it |
|---|---|
| `pipeline/` | satellite -> WRF input: ESA WorldCover land use (`wc_fetch.py`, `wc_to_wps.py`, `wc_modis.py`), Sentinel-2 green fraction and LAI, geo_em writers (`write_geoem_*.py`), settings in `config.py`, tests in `tests/` |
| `runs/*.sh` | run scripts: `p4_run.sh` (one P4 case), `p4_task7_launch.sh` (P4 on + off), `season_run.sh`, `setup_run.sh` |
| `runs/*.py` | analysis: `p4_task7.py` (P4 on minus off), `p4_vs_default.py`, checks |
| `runs/<case>/namelist.*` | the exact namelists of each past run |
| `docs/` | `p4_blue_tile_physics.md` (method, equations, tests), `p4_code_changes_line_by_line.md` |
| `wrf_env.sh` | modules for TSUBAME 4.0 (GCC + OpenMPI + NetCDF) |

The scripts use our TSUBAME paths (`~/WRF/...`). Change them before running.
To reproduce P4, see issue #1. The input files are on TSUBAME in `/gs/bs/tga-guc-lab/users/uw07888/p4_inputs/`.

**d01 land use:** `pipeline/config.py` with `P1_DOM=d01` makes a WorldCover d01 (default MODIS before 2026-11-27).
The run scripts use it when `GEO1=<path to geo_em.d01.nc>` is set.
