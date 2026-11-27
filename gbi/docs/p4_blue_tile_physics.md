# P4 blue tile: what changed in WRF physics

WRF: `~/WRF/WRFV4.8.0`, branch `blue-tile`, commit `55cda1d` (base: stock v4.8.0 `b6a604c`).
Plan: `docs/superpowers/plans/2026-11-16-p4-blue-tile.md`. Tests and results: `WORKLOG.md` (2026-11-16/17).

## 1. The problem

Every WRF cell has one land-use class (`LU_INDEX`) and one surface scheme.
A **land** cell (`XLAND = 1`) runs only the land model (Noah + SLUCM), even when
`LANDUSEF(water)` says part of the cell is water. That water is ignored.

P2 test: adding a water fraction of 0.3 to 50 land cells gave **bit-identical** output.
So stock WRF has no blue fraction inside land cells.

## 2. The change in one picture

```
 stock WRF                              blue tile (lake_tile_opt = 1)
 ----------                             -----------------------------
 land cell, fw = LANDUSEF(water)        land cell with fw > 0
                                        (same atmosphere forcing for both)
   +-----------------+                    +-----------------+   +-----------------+
   |  Noah + SLUCM   |                    |  Noah + SLUCM   |   | CLM4.5 lake col |
   |  (whole cell)   |                    |  (land part)    |   | (water part)    |
   +--------+--------+                    +--------+--------+   +--------+--------+
            |                                      | (1 - fw)            | fw
            v                                      +---------+-----------+
     fluxes, TSK                                             v
     (fw ignored)                            cell value = (1-fw)*land + fw*lake
```

Water cells (`XLAND = 2`) and the stock lake cells (`LU_INDEX = 21`) are unchanged.

## 3. Method and sources

| Choice | What we do | Source |
|---|---|---|
| Sub-grid water in a land cell | all of it is treated as lake (not sea) | Choulga et al. 2019, HESS, sec. 2 (ECMWF/IFS rule) |
| Minimum water fraction | none: any fw > 0 gets a lake tile (D7) | Choulga et al. 2019: IFS runs FLake in every grid box |
| Lake depth | GLDB via `use_lakedepth`; Jakarta has no GLDB data -> default 10 m everywhere (D5) | Choulga et al. 2019 (GLDB, 10 m default) |
| Lake model | the existing WRF CLM4.5 lake (`sf_lake_physics = 1`), no new physics | Gu et al. 2015; WRF `module_sf_lake.F` |
| Combining land and water | area-weighted tile aggregation of fluxes | standard tile approach in SURFEX, CLM, IFS (H-TESSEL + FLake) |
| Skin temperature | blended to conserve upward longwave, not averaged linearly | follows from sigma*eps*T^4 being the quantity that is area-additive |
| Lake initial temperature | stock WRF: TSK at the surface, linear to 277 K at 50 m (D6 option a) | stock `lakeini`; ERA5 FLake init is deferred |

No new physical parameterisation was written. The change only (1) runs an existing lake
column in more cells and (2) area-weights the two existing answers.

## 4. Equations (per cell, per time step)

`fw = LANDUSEF(i, iswater, j)`, the WorldCover water fraction from P1.

Water-part forcing (the lake column gets water properties, not the land values):

```
alb_w  = 0.6 * ice + 0.08 * (1 - ice)        (ice = lake ice fraction, top layer)
SW_net = SWDOWN * (1 - alb_w)
LW_dn  = GLW * e_w,   e_w = 0.97             (lake emissivity used in ShalLakeFluxes)
```

Blending (land values come from Noah/SLUCM, lake values from the lake column):

```
HFX    = (1-fw) HFX_land    + fw HFX_lake
LH     = (1-fw) LH_land     + fw LH_lake
QFX    = (1-fw) QFX_land    + fw LH_lake / L     (L = Lv, or Ls if lake surface is frozen)
GRDFLX = (1-fw) GRDFLX_land + fw G_lake          (G_lake = heat into the water column)
T2, Q2 = (1-fw) land        + fw lake 2 m values;  TH2 from T2
ALBEDO = (1-fw) alb_land    + fw alb_w
EMISS  = (1-fw) e_land      + fw e_w

TSK    = [ ((1-fw) e_land TSK_land^4 + fw e_w T_lake^4) / EMISS ]^(1/4)
```

The TSK formula makes `EMISS * sigma * TSK^4` equal the area-weighted upward longwave of the
two parts, so radiation sees the correct emitted energy.

## 5. Order inside one time step

```
 radiation, surface layer  <-- use blended TSK, EMISS, ALBEDO from last step
          |
 surface_driver:
   restore TSK = TSK_LAND, EMISS = EMISS_LAND     (tile cells only)
          |                                        Noah must see its OWN land skin,
          v                                        not the land+water blend
   Noah + SLUCM  --> land HFX, LH, GRDFLX, TSK
          |
          v
   Lake():  tile gate: lake_tile_opt=1 and lakemask/=1 and XLAND<1.5 and fw>0
            save TSK_LAND, EMISS_LAND (+ HFX/LH/GRD_LND diagnostics)
            run lake column with water forcing  (+ HFX/LH/GRD/TSK_LKT diagnostics)
            blend (section 4)
          |
          v
 PBL, dynamics  <-- see the blended fluxes
```

The tile gate is recomputed every step from fields that are in the restart file, because
`lakeini` returns early on restart. `TSK_LAND` and `EMISS_LAND` are restart fields, so restarts
are bit-identical to continuous runs (test T7).

## 6. Code changes (6 files, +141 lines)

| File | Change |
|---|---|
| `Registry/registry.lake` | namelist `lake_tile_opt` (default 0 = stock); restart state `TSK_LAND`, `EMISS_LAND`; history diagnostics `HFX_LKT`, `LH_LKT`, `GRD_LKT`, `TSK_LKT`, `HFX_LND`, `LH_LND`, `GRD_LND` |
| `share/module_check_a_mundo.F` | `lake_tile_opt = 1` requires `sf_lake_physics = 1` and `sf_surface_mosaic = 0` |
| `phys/module_physics_init.F` | pass `landusef`, `nlcat`, `lake_tile_opt` to `lakeini` |
| `phys/module_sf_lake.F` | `lakeini`: also marks land cells with fw > 0 as lake columns (`lakemask` stays 0). `Lake()`: tile gate, water forcing, blending, diagnostics; `HFX..Q2`, `TSK`, `EMISS` changed from `INTENT(OUT/IN)` to `INOUT` |
| `phys/module_surface_driver.F` | new arguments; restore land TSK/EMISS before `CALL lsm` |
| `dyn_em/module_first_rk_step_part1.F` | pass the new grid fields |

## 7. How to use it

```
&physics
 sf_lake_physics   = 0, 1,      ! lake model on d02 only (d01 geo_em has no LAKE_DEPTH)
 use_lakedepth     = 0, 1,
 lakedepth_default = 10, 10,
 lake_tile_opt     = 0, 1,      ! 0 = stock, 1 = blue tile
/
```

Needs a geo_em with `LANDUSEF` and `LAKE_DEPTH` (P1/P3a: `runs/p3a_base_geo_em.d02.nc`).
Build notes: after any `registry.*` edit run `touch Registry/Registry`; a new namelist variable
needs `./clean` and a full compile.

## 8. Verification (all pass)

| Test | Check | Result |
|---|---|---|
| T1 | clean build | OK, 617 s |
| T2 | new exe with opt=0 vs stock exe, 6 h | bit-identical (d01, d02) |
| T3 | opt=1 vs opt=0 with no water fraction | bit-identical |
| T4 | stock lake cells under opt=1 | HFX, LH, GRDFLX, TSK unchanged (diff 0) |
| T5 | one cell, fw = 0.3: cell vs (0.7 land + 0.3 lake) | max error 4e-6 W m-2, TSK 2e-5 K |
| T6 | Noah land TSK not contaminated by the blend | max 0.08 K over 6 h (atmospheric feedback only) |
| T7 | 24 h vs 12 h + restart | bit-identical |
| T8 | 5x5 block, fw 0 / 0.10 / 0.25 / 0.40 | monotonic, about linear in fw |

## 9. Result, full Jakarta case (Task 7)

Run 2023-10-06_12 to 10-10_18 UTC, tile on (`runs/p4_base`) minus tile off (`runs/p4_base_off`),
land cells, after 12 h spin-up. Map: `runs/p4_base/task7_effect.png`.

| fw class | cells | day dH | day dLE | day dT2 | night dLE | night dT2 |
|---|---|---|---|---|---|---|
| 0 | 1174 | +1.0 | +0.8 | -0.04 | +0.0 | +0.02 |
| 1-5 % | 276 | -7.5 | +1.6 | -0.10 | +2.7 | +0.06 |
| 5-10 % | 90 | -22.5 | +2.0 | -0.22 | +7.6 | +0.11 |
| 10-20 % | 53 | -50.7 | +9.9 | -0.34 | +14.2 | +0.20 |
| 20-50 % | 53 | -123.7 | +34.0 | -0.59 | +32.1 | +0.53 |

Fluxes are in W m-2 and T2 in K. Water stores heat during the day (dG > 0) and releases it at
night, which gives cooling by day and warming at night (cf. Gunawardena et al. 2017). The effect
is local: it shows on the coast (fishponds, mangrove) and along rivers and canals.

## 10. Known limits

- **Lake depth 10 m everywhere.** Fishponds and canals are 1-2 m deep. Shallow water has less
  heat storage, so the day/night split could change noticeably.
- **Cold lake start (D6).** The stock profile is likely too cold for tropical water, so LE is
  probably too low. Planned fix: start the lake from the ERA5 FLake state.
- **One atmosphere for both parts.** Both tiles feel the same lowest-level wind, temperature and
  humidity. Each computes its own fluxes (the lake column uses its own roughness and stability).
  The atmosphere above sees only the blend. This is the usual tile assumption.
- **Not validated.** The magnitudes have not been compared with observations. Only one 4-day case so far.
- **Day warm patch in the south-west** (cells with fw = 0). Probably a cloud/convection
  difference between the runs; not checked.
