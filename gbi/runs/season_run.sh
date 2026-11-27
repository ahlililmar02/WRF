#!/bin/bash
# Dry/wet season runs (design 2026-11-19). usage: season_run.sh NAME GEO_D02 START HOURS TILEOPT ERA5DIR
#   START YYYY-MM-DD_HH (UTC); TILEOPT 1 = P4 blue tile on, 0 = off; ERA5DIR holds ERA5:* intermediate files (ungrib_era5.sh).
#   Built from p4_run.sh: P3a namelist + lake on d02 + sst_update=1 (wrflowinp) + hourly history on both domains, blue-tile exe.
#   Optional env NLSED = extra sed script applied to namelist.input. d01 = default geo_em as in all runs.
set -e
[ $# -eq 6 ] || { echo "usage: $0 NAME GEO_D02 START HOURS TILEOPT ERA5DIR"; exit 2; }
source ~/WRF/wrf_env.sh >/dev/null 2>&1
export OMPI_MCA_coll='^hcoll' OPENBLAS_NUM_THREADS=1
N=$1; GEO=$2; S=$3; H=$4; OPT=$5; E5=$6; R=~/WRF/runs; D=$R/$N
mkdir -p $D/metgrid && cd $D
for f in ~/WRF/WRFV4.8.0/run/*; do b=$(basename $f); [ "$b" = namelist.input ] || ln -sf $f $b; done
cp ${GEO1:-$R/default/geo_em.d01.nc} geo_em.d01.nc; cp $GEO geo_em.d02.nc
T0="${S:0:10} ${S:11:2}:00 UTC"
START=$(date -u -d "$T0" +%Y-%m-%d_%H:00:00); END=$(date -u -d "$T0 + $H hours" +%Y-%m-%d_%H:00:00)
sed -e "s/start_date *= *'[^']*', *'[^']*'/start_date = '$START', '$START'/" \
    -e "s/end_date *= *'[^']*', *'[^']*'/end_date   = '$END', '$END'/" $R/sentinel/namelist.wps > namelist.wps
ln -sf ~/WRF/WPS-4.7.0/metgrid/METGRID.TBL.ARW metgrid/METGRID.TBL; ln -sf ~/WRF/WPS-4.7.0/metgrid.exe metgrid.exe
for f in $E5/ERA5:*; do ln -sf $f .; done
./metgrid.exe > metgrid.log 2>&1; tail -n 1 metgrid.log
set_t() { # $1 = start|end, $2 = YYYY-MM-DD_HH:00:00
  echo "-e s/$1_year=[0-9]*,[0-9]*/$1_year=${2:0:4},${2:0:4}/ -e s/$1_month=[0-9]*,[0-9]*/$1_month=${2:5:2},${2:5:2}/
        -e s/$1_day=[0-9]*,[0-9]*/$1_day=${2:8:2},${2:8:2}/ -e s/$1_hour=[0-9]*,[0-9]*/$1_hour=${2:11:2},${2:11:2}/"; }
LAKE=" sf_lake_physics=0,1, use_lakedepth=0,1, lakedepth_default=10.,10., lake_tile_opt=0,$OPT, sst_update=1,"
AUX=" auxinput4_inname=\"wrflowinp_d<domain>\", auxinput4_interval=60,60, io_form_auxinput4=2,"
sed $(set_t start $START) $(set_t end $END) -e "s/run_hours=[0-9]*/run_hours=$H/" \
    -e "s/history_interval=[0-9]*,[0-9]*/history_interval=60,60/" -e "s/frames_per_outfile=[0-9]*,[0-9]*/frames_per_outfile=24,24/" \
    -e "s/^ sf_urban_physics=1,1, rdlai2d=.true.,/ sf_urban_physics=1,1, rdlai2d=.true.,\n$LAKE/" \
    -e "s/^ io_form_history=2, io_form_restart=2, io_form_input=2, io_form_boundary=2,/&\n$AUX/" \
    $R/p3a_base/namelist.input > namelist.input
grep -q sst_update namelist.input && grep -q auxinput4_inname namelist.input || { echo "namelist insertion failed"; exit 1; }
[ -n "$NLSED" ] && sed -i -e "$NLSED" namelist.input
mpirun -np 4 ./real.exe > real.out 2>&1; tail -n 1 rsl.out.0000
[ -f wrflowinp_d01 ] && [ -f wrflowinp_d02 ] || { echo "no wrflowinp (sst_update) - stop"; exit 1; }
SECONDS=0
mpirun -np 16 ./wrf.exe > wrf.out 2>&1 || true
echo "wall_s=$SECONDS" > timing.txt
tail -n 1 rsl.out.0000 | grep -q 'SUCCESS COMPLETE WRF' || { echo "wrf.exe FAILED, see $D/rsl.error.*"; exit 1; }
echo "$N SUCCESS COMPLETE WRF ($(cat timing.txt))"
