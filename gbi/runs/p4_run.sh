#!/bin/bash
# P4 test runs. usage: p4_run.sh NAME GEO_D02 EXE(stock|new) HOURS [TILEOPT]
#   EXE=stock uses ~/WRF/bin_stock_b6a604c (no lake_tile_opt in namelist); EXE=new uses WRFV4.8.0 blue-tile build.
#   Physics = P3a baseline namelist (Noah, SLUCM, rdlai2d) + lake model on d02 only (d01 default geo_em has no LAKE_DEPTH): sf_lake_physics=0,1, use_lakedepth=0,1, lakedepth_default=10 (D5).
#   Start 2023-10-06_12 (case start), length HOURS. d01 = default geo_em as in all runs.
set -e
source ~/WRF/wrf_env.sh >/dev/null 2>&1
export OMPI_MCA_coll='^hcoll' OPENBLAS_NUM_THREADS=1
N=$1; GEO=$2; EXE=$3; H=$4; OPT=$5; R=~/WRF/runs; D=$R/$N
mkdir -p $D/metgrid && cd $D
for f in ~/WRF/WRFV4.8.0/run/*; do b=$(basename $f); [ "$b" = namelist.input ] || ln -sf $f $b; done
if [ "$EXE" = stock ]; then ln -sf ~/WRF/bin_stock_b6a604c/wrf.exe wrf.exe; ln -sf ~/WRF/bin_stock_b6a604c/real.exe real.exe; fi
cp ${GEO1:-$R/default/geo_em.d01.nc} geo_em.d01.nc; cp $GEO geo_em.d02.nc
END=$(date -u -d "2023-10-06 12:00 UTC + $H hours" +%Y-%m-%d_%H:00:00)
sed "s/end_date *= *'[^']*', *'[^']*'/end_date   = '$END', '$END'/" $R/sentinel/namelist.wps > namelist.wps
ln -sf ~/WRF/WPS-4.7.0/metgrid/METGRID.TBL.ARW metgrid/METGRID.TBL; ln -sf ~/WRF/WPS-4.7.0/metgrid.exe metgrid.exe
for f in ~/WRF/WPS-4.7.0/ERA5:*; do ln -sf $f .; done
./metgrid.exe > metgrid.log 2>&1; tail -n 1 metgrid.log
EY=${END:0:4}; EM=${END:5:2}; ED=${END:8:2}; EH=${END:11:2}
LAKE=" sf_lake_physics=0,1, use_lakedepth=0,1, lakedepth_default=10.,10.,"
[ -n "$OPT" ] && LAKE="$LAKE lake_tile_opt=0,$OPT,"
sed -e "s/run_hours=[0-9]*/run_hours=$H/" -e "s/end_year=[0-9]*,[0-9]*/end_year=$EY,$EY/" -e "s/end_month=[0-9]*,[0-9]*/end_month=$EM,$EM/" \
    -e "s/end_day=[0-9]*,[0-9]*/end_day=$ED,$ED/" -e "s/end_hour=[0-9]*,[0-9]*/end_hour=$EH,$EH/" \
    -e "s/^ sf_urban_physics=1,1, rdlai2d=.true.,/ sf_urban_physics=1,1, rdlai2d=.true.,\n$LAKE/" $R/p3a_base/namelist.input > namelist.input
grep -q sf_lake_physics namelist.input || { echo "lake insertion failed"; exit 1; }
[ -n "$NLSED" ] && sed -i -e "$NLSED" namelist.input
mpirun -np 4 ./real.exe > real.out 2>&1; tail -n 1 rsl.out.0000
mpirun -np 16 ./wrf.exe > wrf.out 2>&1; tail -n 1 rsl.out.0000
grep -h 'lake grid\|blue-tile' rsl.out.0000 | sort -u
