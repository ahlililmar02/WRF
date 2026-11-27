# P4 blue tile: every code change, stock vs ours, line by line

Written 2026-11-27. WRF v4.8.0 in `~/WRF/WRFV4.8.0`.
**Stock** = commit `b6a604c` (pristine tarball). **P4** = commit `55cda1d` (branch `blue-tile`).
Line numbers: "stock L" = line in `b6a604c`, "P4 L" = line in `55cda1d`.
On branch `mosaic-frc` (P4 + mosaic fix) `module_sf_lake.F` has the same numbers; the other files shift by a few lines.
Every P4 line ends with or sits under a comment `! blue-tile (P4)`.
Physics overview and results: `docs/p4_blue_tile_physics.md`.

Check it yourself:
```
cd ~/WRF/WRFV4.8.0
git diff b6a604c 55cda1d --stat                       # 6 files, +141 / -14
git diff b6a604c 55cda1d -- phys/module_sf_lake.F     # one file
git show b6a604c:phys/module_sf_lake.F | sed -n 280,310p   # stock text at given lines
```

## Map of all changes (in the order WRF meets them)

| # | File | Stock L -> P4 L | Kind | What |
|---|---|---|---|---|
| A1 | `Registry/registry.lake` | 26 -> 27-37 | new fields | `TSK_LAND`, `EMISS_LAND` (restart) + 7 diagnostics |
| A2 | `Registry/registry.lake` | 34 -> 46 | new switch | `lake_tile_opt` |
| B | `share/module_check_a_mundo.F` | 519 -> 520-533 | safety | stop on bad option combinations |
| C1 | `phys/module_physics_init.F` | 3882 -> 3882-3883 | plumbing | pass `landusef, nlcat, lake_tile_opt` to `lakeini` |
| C2 | `phys/module_sf_lake.F` | 4899 -> 4952-4953 | plumbing | `lakeini` argument list |
| C3 | `phys/module_sf_lake.F` | 4908 -> 4963-4965 | plumbing | `lakeini` declarations |
| C4 | `phys/module_sf_lake.F` | 5072 -> 5130-5145 | **physics** | **land cells with water get a lake column** |
| D1 | `dyn_em/module_first_rk_step_part1.F` | 710 -> 711-715 | plumbing | pass new grid fields to the surface driver |
| D2 | `phys/module_surface_driver.F` | 113 -> 114-115 | plumbing | argument list |
| D3 | `phys/module_surface_driver.F` | 1474 -> 1477-1479 | plumbing | declarations |
| E | `phys/module_surface_driver.F` | 2907 -> 2913-2925 | **physics** | **put back land TSK/EMISS before Noah** |
| D4 | `phys/module_surface_driver.F` | 4538 -> 4556-4560 | plumbing | pass new fields to `Lake()` |
| F1 | `phys/module_sf_lake.F` | 141 -> 141-145 | plumbing | `Lake()` argument list |
| F2 | `phys/module_sf_lake.F` | 169 -> 173 | interface | `EMISS` IN -> INOUT |
| F3 | `phys/module_sf_lake.F` | 190-197 -> 194-201 | interface | 8 outputs OUT -> INOUT |
| F4 | `phys/module_sf_lake.F` | 217 -> 222-231 | plumbing | `Lake()` declarations, `e_w` |
| F5 | `phys/module_sf_lake.F` | 301 -> 316-319 | physics | default: not a tile, `fw = 1` |
| F6 | `phys/module_sf_lake.F` | 303 -> 321-329 | **physics** | **tile gate + water forcing** |
| H1 | `phys/module_sf_lake.F` | 372 -> 399-402 | diagnostics | lake-part outputs |
| H2 | `phys/module_sf_lake.F` | 372 -> 403-424 | **physics** | **blend land and water by fw** |
| H3 | `phys/module_sf_lake.F` | 388 -> 441 | structure | close the IF of H2 |

Physics lines: C4, E, F5, F6, H2. Everything else carries data to them.

---

## A. Registry (`Registry/registry.lake`)

The Registry is the list from which WRF generates its variables, namelist options and I/O.

### A1. stock L26 -> P4 L27-37 (11 lines added)

Stock: nothing (the line before is the stock lake field `tksatu3d`).

P4:
```
# blue-tile (P4): lake column blended by water fraction in land cells (lake_tile_opt=1)
state real TSK_LAND   ij misc 1 - rh "TSK_LAND"   "land-part skin temperature of lake-tile cells" "K"
state real EMISS_LAND ij misc 1 - rh "EMISS_LAND" "land-part emissivity of lake-tile cells"       ""
state real HFX_LKT    ij misc 1 - h  "HFX_LKT"    "lake-part sensible heat flux, lake cells and tile cells" "W m-2"
state real LH_LKT     ij misc 1 - h  "LH_LKT"     "lake-part latent heat flux, lake cells and tile cells"   "W m-2"
state real GRD_LKT    ij misc 1 - h  "GRD_LKT"    "lake-part ground (storage) heat flux"                    "W m-2"
state real TSK_LKT    ij misc 1 - h  "TSK_LKT"    "lake-part surface temperature (t_grnd)"                  "K"
state real HFX_LND    ij misc 1 - h  "HFX_LND"    "land-part sensible heat flux, tile cells"                "W m-2"
state real LH_LND     ij misc 1 - h  "LH_LND"     "land-part latent heat flux, tile cells"                  "W m-2"
state real GRD_LND    ij misc 1 - h  "GRD_LND"    "land-part ground heat flux, tile cells"                  "W m-2"
```

Meaning:
- `state real X ij`: a new 2-D field (one value per cell) that lives for the whole run.
- `rh`: written to the **r**estart and **h**istory (wrfout) files; `h`: history only.
- `TSK_LAND`, `EMISS_LAND`: WRF has one TSK/EMISS per cell. In a tile cell TSK becomes the land+water blend, so the land
  part's own values must be kept somewhere for Noah's next step (see E). They are restart fields so a restarted run
  continues exactly (test T7 bit-identical).
- `*_LKT`, `*_LND`: diagnostics only, the lake part and land part before blending, to check the blend.

### A2. stock L34 -> P4 L46 (1 line added)

P4:
```
rconfig integer lake_tile_opt namelist,physics max_domains 0 rh "lake_tile_opt" "0 stock; 1 lake column blended by water fraction in land cells (P4 blue tile)"
```

Meaning: new namelist option in `&physics`, one value per domain (`max_domains`), **default 0 = stock**.
`lake_tile_opt = 0, 1` means off on d01, on on d02. With 0 every P4 branch is skipped (test T2: bit-identical to stock).

---

## B. Safety check (`share/module_check_a_mundo.F`)

### stock L519 -> P4 L520-533 (14 lines added)

Stock: nothing (the block before checks another option).

P4:
```fortran
!-----------------------------------------------------------------------
! blue-tile (P4): lake_tile_opt = 1 needs the lake model and no Noah mosaic
!-----------------------------------------------------------------------
      DO i = 1, model_config_rec % max_dom
         IF ( .NOT. model_config_rec % grid_allowed(i) ) CYCLE
         IF ( model_config_rec % lake_tile_opt(i) .EQ. 1 .AND. &
              ( model_config_rec % sf_lake_physics(i) .NE. 1 .OR. &
                model_config_rec % sf_surface_mosaic .NE. 0 ) ) THEN
            wrf_err_message = '--- ERROR: lake_tile_opt = 1 needs sf_lake_physics = 1 and sf_surface_mosaic = 0'
            CALL wrf_debug ( 0, TRIM( wrf_err_message ) )
            count_fatal_error = count_fatal_error + 1
         END IF
      ENDDO
```

Meaning:
- Runs once when wrf.exe reads the namelist. `i` = domain number.
- P4 on in a domain without the lake model there -> stop (no lake column to blend).
- P4 with the Noah mosaic -> stop. Written when we believed the mosaic ran water as a tile; that was wrong (11-24).
  **This is the line to relax for the P4 + mosaic plan.**

---

## C. Start-up: which cells get a lake column (`lakeini`)

### C1. `phys/module_physics_init.F` stock L3882 -> P4 L3882-3883

Stock:
```fortran
                           ims,ime, jms,jme)
```
P4:
```fortran
                           ims,ime, jms,jme,                                                 &
                           landusef, nlcat, config_flags%lake_tile_opt)   ! blue-tile (P4)
```
Meaning: the call to `lakeini` now also hands over the land-use fractions (`landusef`), the number of classes (`nlcat`)
and the switch. Stock `lakeini` never sees `LANDUSEF`.

### C2. `phys/module_sf_lake.F` stock L4899 -> P4 L4952-4953

Stock:
```fortran
                    ims,ime, jms,jme)
```
P4:
```fortran
                    ims,ime, jms,jme,                                                  &
                    landusef, nlcat, lake_tile_opt)                    ! blue-tile (P4)
```
Meaning: the receiving side of C1 (the `SUBROUTINE lakeini(...)` header, which starts at L4939).

### C3. `phys/module_sf_lake.F` stock L4908 -> P4 L4963-4965 (3 lines added)

P4:
```fortran
  INTEGER , INTENT (IN) :: nlcat, lake_tile_opt                          ! blue-tile (P4)
  REAL, DIMENSION( ims:ime, nlcat, jms:jme ), INTENT(IN) :: landusef      ! blue-tile (P4)
  INTEGER :: numb_tile                                                    ! blue-tile (P4)
```
Meaning: declare the new inputs (read-only, `INTENT(IN)`) and a counter. `landusef(i, k, j)` = share of class k in cell (i, j).

### C4. `phys/module_sf_lake.F` stock L5072 -> P4 L5130-5145 (16 lines added) - PHYSICS

Stock (L5071-5072, kept): after deciding the stock lake cells, it prints their number and goes on to build columns.
```fortran
    write(message,*) "the total number of lake grid is :", numb_lak
    CALL wrf_message(message)
```
At this point stock has `lake(i,j) = .true.` only where `lakemask = 1` (cells whose dominant class is lake, 21).

P4 (inserted right after):
```fortran
! blue-tile (P4): land cells with a water fraction also get a lake column (lakemask stays 0).
! All sub-grid water of a land-dominated cell is lake water (Choulga et al. 2019 HESS, sec 2);
! no minimum fraction (IFS runs FLake in every grid box, same paper).
   numb_tile = 0
   IF ( lake_tile_opt == 1 ) THEN
       do i=its,ite
         do j=jts,jte
           if ( .not. lake(i,j) .and. xland(i,j) < 1.5 .and. landusef(i,iswater,j) > 0. ) then
              lake(i,j) = .true.
              numb_tile = numb_tile + 1
           end if
         end do
       end do
       write(message,*) "blue-tile: number of land cells with a lake tile :", numb_tile
       CALL wrf_message(message)
   ENDIF
```

Meaning, line by line:

| Line | Meaning |
|---|---|
| `IF ( lake_tile_opt == 1 )` | only with P4 on |
| `.not. lake(i,j)` | not already a whole-lake cell (no double column) |
| `xland(i,j) < 1.5` | a land cell (`XLAND` 1 = land, 2 = water) |
| `landusef(i,iswater,j) > 0.` | the cell has some water. `iswater` = 17; real.exe already folded class 21 into 17, so this is ALL water in the cell = `fw`. No minimum (decision D7) |
| `lake(i,j) = .true.` | build a lake column here. `lake` is local to `lakeini`; `lakemask`, `XLAND`, `IVGTYP` are NOT changed, so the cell stays a land cell (Noah still runs) |
| `write(message...)` | count goes to `rsl.out` (prints 2012 for Jakarta d02: called twice and includes edge points; real count 989) |

After this block the **stock** code (L ~5150-5360) builds a column in every `lake(i,j)` cell, now including tile cells:
depth from `LAKE_DEPTH` (10 m in Jakarta), 10 water + 10 soil layers, start temperature TSK at the top falling linearly
to 277 K at 50 m. This is where the water fraction first enters the physics: the cell now carries a water column.

---

## D. Plumbing to the surface driver (no physics)

### D1. `dyn_em/module_first_rk_step_part1.F` stock L710 -> P4 L711-715 (5 lines added)

Stock (L710, kept): the last lake argument in the call to `surface_driver`.
```fortran
     &        ,LakeModel=grid%sf_lake_physics,  lake_min_elev=grid%lake_min_elev    & !lake
```
P4 (added after it):
```fortran
     &        ,lake_tile_opt=grid%lake_tile_opt                                    & ! blue-tile (P4)
     &        ,tsk_land=grid%tsk_land,          emiss_land=grid%emiss_land          & ! blue-tile (P4)
     &        ,hfx_lkt=grid%hfx_lkt,  lh_lkt=grid%lh_lkt,  grd_lkt=grid%grd_lkt      & ! blue-tile (P4)
     &        ,tsk_lkt=grid%tsk_lkt,  hfx_lnd=grid%hfx_lnd, lh_lnd=grid%lh_lnd       & ! blue-tile (P4)
     &        ,grd_lnd=grid%grd_lnd                                                 & ! blue-tile (P4)
```
Meaning: every time step, hand the Registry fields (A1, A2) from the model's memory (`grid%...`) to the surface driver.

### D2. `phys/module_surface_driver.F` stock L113 -> P4 L114-115 and D3. stock L1474 -> P4 L1477-1479

P4:
```fortran
     &          ,lake_tile_opt, tsk_land, emiss_land                    & ! blue-tile (P4)
     &          ,hfx_lkt, lh_lkt, grd_lkt, tsk_lkt, hfx_lnd, lh_lnd, grd_lnd & ! blue-tile (P4)
...
    INTEGER, INTENT(IN) :: lake_tile_opt                                   ! blue-tile (P4)
    REAL, DIMENSION(ims:ime,jms:jme), INTENT(INOUT) :: tsk_land, emiss_land, hfx_lkt, lh_lkt, &
                                                        grd_lkt, tsk_lkt, hfx_lnd, lh_lnd, grd_lnd
```
Meaning: the surface driver receives and declares them. `INOUT` because `Lake()` writes them and E reads them.

### D4. `phys/module_surface_driver.F` stock L4538 -> P4 L4556-4560

Stock (end of the `CALL Lake(...)` argument list):
```fortran
                     qfx          ,t2             ,th2          ,q2 )
```
P4:
```fortran
                     qfx          ,t2             ,th2          ,q2              ,&
                     landusef     ,nlcat          ,lake_tile_opt                 ,&  ! blue-tile (P4)
                     tsk_land     ,emiss_land                                    ,&
                     hfx_lkt      ,lh_lkt         ,grd_lkt      ,tsk_lkt         ,&
                     hfx_lnd      ,lh_lnd         ,grd_lnd )
```
Meaning: `Lake()` (every step) now also gets the fractions, the switch and the new fields. Stock `Lake()` never sees `LANDUSEF`.

---

## E. Every step, before Noah (`phys/module_surface_driver.F`) - PHYSICS

### stock L2907 -> P4 L2913-2925 (13 lines added)

Stock: after the optional Noah perturbation block, directly `CALL lsm(dz8w, qv_curr, p8w, t_phy, tsk, ...)` (Noah).

P4 (inserted just before `CALL lsm`):
```fortran
! blue-tile (P4): give Noah its own land-part TSK/EMISS back in lake-tile cells, so the blended
! (land + water) skin values that radiation and the surface layer used do not leak into Noah's land state.
               IF ( lake_tile_opt == 1 .AND. LakeModel == 1 ) THEN
                 DO j = j_start(ij), j_end(ij)
                 DO i = i_start(ij), i_end(ij)
                   IF ( tsk_land(i,j) > 0. ) THEN
                     tsk(i,j)   = tsk_land(i,j)
                     emiss(i,j) = emiss_land(i,j)
                   ENDIF
                 ENDDO
                 ENDDO
               ENDIF
```

Meaning:
- At this point `TSK`/`EMISS` hold last step's **blend** (set in H2), which radiation and the surface layer needed.
- Noah treats `TSK` as its own state (it solves the new TSK from the old one). Giving it the blend would let the water
  temperature leak into the land soil and skin. So Noah gets the land part's own values back.
- `tsk_land > 0` = only tile cells (it is 0 everywhere else, never set).
- Sits in the `sf_surface_mosaic == 0` branch only (the mosaic keeps its own per-tile TSK).

---

## F. Every step, inside `Lake()`: set-up of the water part (`phys/module_sf_lake.F`)

### F1. stock L141 -> P4 L141-145 (argument list)

Stock:
```fortran
                     qfx          ,t2             ,th2          ,q2 )
```
P4:
```fortran
                     qfx          ,t2             ,th2          ,q2              ,&
                     landusef     ,nlcat          ,lake_tile_opt                 ,&  ! blue-tile (P4)
                     tsk_land     ,emiss_land                                    ,&
                     hfx_lkt      ,lh_lkt         ,grd_lkt      ,tsk_lkt         ,&
                     hfx_lnd      ,lh_lnd         ,grd_lnd )
```
Meaning: receiving side of D4.

### F2. stock L169 -> P4 L173

Stock:
```fortran
    REAL, DIMENSION( ims:ime, jms:jme ) ,INTENT(IN)  :: emiss
```
P4:
```fortran
    REAL, DIMENSION( ims:ime, jms:jme ) ,INTENT(INOUT)  :: emiss   ! blue-tile: INOUT (blended in tile cells)
```
Meaning: stock only reads emissivity; P4 also writes it (the blended cell emissivity, H2).

### F3. stock L190-197 -> P4 L194-201

Stock:
```fortran
    REAL, DIMENSION( ims:ime, jms:jme ) ,INTENT(OUT) :: HFX
    ... same for LH, GRDFLX, TSK, QFX, T2, TH2, Q2
```
P4:
```fortran
    REAL, DIMENSION( ims:ime, jms:jme ) ,INTENT(INOUT) :: HFX
    ... same for LH, GRDFLX, TSK, QFX, T2, TH2, Q2
```
Meaning: `OUT` = "the routine only writes this, the old value does not matter". True for stock, because a lake cell is
100 % lake and overwrites everything. In a tile cell P4 must **read** Noah's land value first, then blend, so `INOUT`.

### F4. stock L217 -> P4 L222-231 (10 lines added)

P4:
```fortran
! blue-tile (P4): lake column blended by water fraction in land cells
    INTEGER, INTENT(IN) :: nlcat, lake_tile_opt
    REAL, DIMENSION( ims:ime, nlcat, jms:jme ), INTENT(IN) :: landusef
    REAL, DIMENSION( ims:ime, jms:jme ), INTENT(INOUT) :: tsk_land, emiss_land,           &
                                                          hfx_lkt, lh_lkt, grd_lkt, tsk_lkt, &
                                                          hfx_lnd, lh_lnd, grd_lnd
    LOGICAL  :: tile
    REAL     :: fw, e_l, alb_w, qfx_w
    REAL, PARAMETER :: e_w = 0.97          ! lake surface emissivity, emg in ShalLakeFluxes
```
Meaning: declarations. `tile` = "this cell is a tile cell"; `fw` water fraction; `e_l` land emissivity; `alb_w` water
albedo; `qfx_w` water evaporation; `e_w = 0.97` = the emissivity the lake model itself uses (`emg` in `ShalLakeFluxes`).

### F5. stock L301 -> P4 L316-319 (4 lines added) - PHYSICS (defaults)

Stock (L289-293, kept): the cell forcing is computed for any cell.
```fortran
           LWDN    = GLW(I,J)*EMISSI                    ! (L289) downward longwave times cell emissivity
           SOLDN   = SWDOWN(I,J)
           SOLNET  = SOLDN*(1.-ALBEDO(I,J))             ! net solar with the CELL albedo
```
P4 (added):
```fortran
! blue-tile (P4): a land cell with water fraction fw > 0 also runs the lake column (Choulga et al. 2019:
! all sub-grid water of a land-dominated cell is lake). Its water part is forced with WATER albedo and emissivity.
        tile = .false.
        fw   = 1.
```
Meaning: by default a cell is not a tile and `fw = 1` (a whole-lake cell = 100 % water), so stock lake cells behave as before.

### F6. stock L303 -> P4 L321-329 - PHYSICS (tile gate + water forcing)

Stock:
```fortran
        if (lakemask(i,j).eq.1) THEN          ! run the lake column only in whole-lake cells
```
P4:
```fortran
        if ( lake_tile_opt == 1 .and. lakemask(i,j) .ne. 1 .and. xland(i,j) < 1.5 .and. &
             landusef(i,iswater,j) > 0. ) then
           tile   = .true.
           fw     = landusef(i,iswater,j)
           alb_w  = 0.6 * lake_icefrac3d(i,1,j) + 0.08 * (1.0 - lake_icefrac3d(i,1,j))
           LWDN   = GLW(I,J)*e_w
           SOLNET = SOLDN*(1.-alb_w)
        endif
        if (lakemask(i,j).eq.1 .or. tile) THEN
```

Meaning, line by line:

| Line | Meaning |
|---|---|
| gate `lake_tile_opt == 1 .and. lakemask /= 1 .and. xland < 1.5 .and. fw > 0` | same rule as C4, recomputed every step from fields in the restart file (`lakeini` is skipped on restart) |
| `fw = landusef(i,iswater,j)` | the water fraction, used as the blend weight in H2 |
| `alb_w = 0.6 ice + 0.08 (1 - ice)` | water albedo (same formula the stock code uses for lake cells, L381) |
| `LWDN = GLW * e_w` | stock used the CELL emissivity (land, or last blend); the water part gets water emissivity |
| `SOLNET = SOLDN (1 - alb_w)` | stock used the CELL albedo (e.g. 0.2 for urban); water reflects only 8 %, so it absorbs more sun |
| `if (lakemask == 1 .or. tile)` | run the column in whole-lake cells (stock) **and** in tile cells (P4) |

---

## G. The lake column itself

No change. The stock CLM4.5 lake code runs with the forcing above and the same lowest-level air as the land part, and
returns `eflx_sh_tot` (H), `eflx_lh_tot` (LE), `eflx_gnet` (heat into the water), `t_grnd` (water surface T),
`t_ref2m`, `q_ref2m`.

---

## H. Every step, inside `Lake()`: blend (`phys/module_sf_lake.F`)

### H1. stock L372 -> P4 L399-402 (4 lines added) - diagnostics

P4:
```fortran
           do c = 1,column
            hfx_lkt(i,j) = eflx_sh_tot(c);  lh_lkt(i,j) = eflx_lh_tot(c)          ! blue-tile diagnostics
            grd_lkt(i,j) = eflx_gnet(c);    tsk_lkt(i,j) = t_grnd(c)
           enddo
```
Meaning: store the lake-part answer before any blending (wrfout `HFX_LKT`, `LH_LKT`, `GRD_LKT`, `TSK_LKT`).

### H2. stock L372 -> P4 L403-424 (22 lines added) - PHYSICS (the blend)

Stock (L373-387, kept as the ELSE branch): whole-lake cell, the lake answer **replaces** the cell.
```fortran
           do c = 1,column
            HFX(I,J)          = eflx_sh_tot(c)
            LH(I,J)           = eflx_lh_tot(c)
            GRDFLX(I,J)       = eflx_gnet(c)
            TSK(I,J)          = t_grnd(c)
            T2(I,J)           = t_ref2m(c)
            TH2(I,J)          = T2(I,J)*(1.E5/PSFC)**RCP
            Q2(I,J)           = q_ref2m(c)
            albedo(i,j)       = ( 0.6 * lake_icefrac(c,1) ) + ( (1.0-lake_icefrac(c,1)) * 0.08)
            qfx(i,j)          = eflx_lh_tot(c)/hvap   (or /hsub if frozen)
           enddo
```
P4 (new IF branch in front of it):
```fortran
           IF ( tile ) THEN                                  ! blue-tile: area-weighted tile aggregation
           do c = 1,column
            tsk_land(i,j)   = tsk(i,j);     emiss_land(i,j) = emiss(i,j)          ! land state, restored before Noah
            hfx_lnd(i,j)    = hfx(i,j);     lh_lnd(i,j) = lh(i,j);  grd_lnd(i,j) = grdflx(i,j)
            if( t_grnd(c) >= tfrz ) then
                qfx_w = eflx_lh_tot(c)/hvap
            else
                qfx_w = eflx_lh_tot(c)/hsub
            endif
            e_l           = emiss(i,j)
            HFX(I,J)      = (1.-fw)*HFX(I,J)    + fw*eflx_sh_tot(c)
            LH(I,J)       = (1.-fw)*LH(I,J)     + fw*eflx_lh_tot(c)
            GRDFLX(I,J)   = (1.-fw)*GRDFLX(I,J) + fw*eflx_gnet(c)
            QFX(I,J)      = (1.-fw)*QFX(I,J)    + fw*qfx_w
            T2(I,J)       = (1.-fw)*T2(I,J)     + fw*t_ref2m(c)
            Q2(I,J)       = (1.-fw)*Q2(I,J)     + fw*q_ref2m(c)
            TH2(I,J)      = T2(I,J)*(1.E5/PSFC)**RCP
            albedo(i,j)   = (1.-fw)*albedo(i,j) + fw*alb_w
            emiss(i,j)    = (1.-fw)*e_l         + fw*e_w
            TSK(I,J)      = ( ((1.-fw)*e_l*tsk_land(i,j)**4 + fw*e_w*t_grnd(c)**4) / emiss(i,j) )**0.25   ! conserves upward LW
           enddo
           ELSE
```

Meaning, line by line (at this point `HFX`, `LH`, ... still hold Noah's land answer of this step):

| Line | Meaning |
|---|---|
| `tsk_land = tsk; emiss_land = emiss` | save the land part's TSK/EMISS before they are overwritten; E gives them back to Noah next step |
| `hfx_lnd = hfx ...` | diagnostics: land part before blending (wrfout `HFX_LND`, `LH_LND`, `GRD_LND`) |
| `qfx_w = LE_lake / hvap` (or `hsub` if frozen) | water evaporation in kg m-2 s-1 from the lake latent heat |
| `e_l = emiss` | land emissivity, needed for the TSK line |
| `HFX = (1-fw) HFX + fw H_lake` | area-weighted sensible heat. Same form for `LH`, `QFX` |
| `GRDFLX = (1-fw) GRDFLX + fw G_lake` | **KNOWN BUG, open:** Noah's GRDFLX and the lake's `eflx_gnet` use different signs (and the lake one holds only part of the solar), so the blend mixes conventions -> P4 GRDFLX not usable |
| `T2, Q2 = (1-fw) land + fw lake` | 2 m values blended; `TH2` recomputed from `T2` |
| `albedo = (1-fw) alb + fw alb_w` | cell albedo seen by radiation next step |
| `emiss = (1-fw) e_l + fw e_w` | cell emissivity seen by radiation |
| `TSK = [((1-fw) e_l T_l^4 + fw e_w T_w^4) / emiss]^(1/4)` | not a linear mean: chosen so `emiss * sigma * TSK^4` = the area-weighted upward longwave of the two parts |
| `ELSE` | whole-lake cells keep the stock replacement (above) |

Not blended (open item): `UST` (u*) and `ZNT` (roughness). The lake code writes neither, so the cell keeps the land values.

### H3. stock L388 -> P4 L441 (1 line added)

P4:
```fortran
           ENDIF                                             ! blue-tile
```
Meaning: closes the `IF ( tile ) ... ELSE` of H2.

---

## Summary: where the water fraction acts

```
 C4  start-up      fw > 0          -> the land cell gets a lake column            (lakeini, P4 L5130-5145)
 F6  every step    fw > 0          -> run that column with water albedo/emissivity (Lake, P4 L321-329)
 H2  every step    fw as weight    -> cell = (1-fw) land + fw lake                  (Lake, P4 L403-424)
 E   every step    (support)       -> Noah gets its own land TSK/EMISS back         (surface_driver, P4 L2913-2925)
```
Stock behaviour is unchanged when `lake_tile_opt = 0` (test T2) and in cells with `fw = 0` (test T3).

## Open items in this code

1. `GRDFLX` blend sign (H2, P4 L415 on branch `mosaic-frc`, `module_sf_lake.F`).
2. `UST`/`ZNT` not blended (H2).
3. Check B forbids the mosaic; relax for P4 + mosaic.
4. Lake depth 10 m everywhere and cold start profile (stock set-up after C4).
