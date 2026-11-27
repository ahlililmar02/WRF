#!/bin/bash
# usage: setup_run.sh NAME GEO_D02_PATH FLAGS(0|1)   -> builds ~/WRF/runs/NAME, runs metgrid + real.exe (not wrf.exe)
# FLAGS=1 adds usemonalb=.true., rdlai2d=.true. to &physics (Noah then reads geo_em ALBEDO12M / LAI12M instead of land-use table values)
# FLAGS=2 adds rdlai2d=.true. only (geo_em LAI12M, table albedo; P3a baseline, decision 2026-11-16)
set -e
source ~/WRF/wrf_env.sh
export OMPI_MCA_coll='^hcoll' OPENBLAS_NUM_THREADS=1
R=~/WRF/runs; N=$1; GEO=$2; FLAGS=$3; D=$R/$N
mkdir -p $D/metgrid && cd $D
for f in ~/WRF/WRFV4.8.0/run/*; do b=$(basename $f); [ "$b" = namelist.input ] || ln -sf $f $b; done
cp ${GEO1:-$R/default/geo_em.d01.nc} geo_em.d01.nc   # d01 default unless GEO1 is set (GEO1=~/WRF/runs/p1_wc_d01/geo_em.d01.nc = WorldCover d01, 2026-11-27)
[ "$(readlink -f $GEO)" = "$D/geo_em.d02.nc" ] || cp $GEO geo_em.d02.nc
cp $R/sentinel/namelist.wps namelist.wps
ln -sf ~/WRF/WPS-4.7.0/metgrid/METGRID.TBL.ARW metgrid/METGRID.TBL
ln -sf ~/WRF/WPS-4.7.0/metgrid.exe metgrid.exe
for f in ~/WRF/WPS-4.7.0/ERA5:*; do ln -sf $f .; done
cp $R/sentinel/namelist.input namelist.input
if [ "$FLAGS" = 1 ]; then
  sed -i 's/^ sf_urban_physics=1,1,/ sf_urban_physics=1,1, usemonalb=.true., rdlai2d=.true.,/' namelist.input
  grep -q rdlai2d namelist.input || { echo "flag insertion failed"; exit 1; }
elif [ "$FLAGS" = 2 ]; then
  sed -i 's/^ sf_urban_physics=1,1,/ sf_urban_physics=1,1, rdlai2d=.true.,/' namelist.input
  grep -q rdlai2d namelist.input || { echo "flag insertion failed"; exit 1; }
fi
./metgrid.exe > metgrid.log 2>&1; tail -2 metgrid.log
mpirun -np 4 ./real.exe > real.out 2>&1; tail -2 rsl.out.0000
