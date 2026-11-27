#!/bin/bash
# T7: 24 h straight (restart file at 12 h) vs restart from 12 h for 12 h; hourly history, one frame per file.
set -e
cd ~/WRF/runs; G=~/WRF/runs/p3a_base_geo_em.d02.nc
NLSED='s/restart_interval=[0-9]*/restart_interval=720/;s/history_interval=[0-9]*,[0-9]*/history_interval=60,60/;s/frames_per_outfile=[0-9]*,[0-9]*/frames_per_outfile=1,1/' \
  ./p4_run.sh p4_T7_24h $G new 24 1
rm -rf p4_T7_rst; mkdir p4_T7_rst; cd p4_T7_rst
for f in ../p4_T7_24h/*; do b=$(basename $f); case $b in wrfout*|rsl.*|wrf.out|met_em*|metgrid) ;; *) cp -P $f .;; esac; done
cp ../p4_T7_24h/wrfrst_d0?_2023-10-07_00:00:00 .
sed -i -e 's/restart=.false./restart=.true./' -e 's/run_hours=24/run_hours=12/' -e 's/start_day=06,06/start_day=07,07/' -e 's/start_hour=12,12/start_hour=00,00/' namelist.input
grep -E 'restart=|start_day|start_hour|run_hours' namelist.input | tr -s ' '
source ~/WRF/wrf_env.sh >/dev/null 2>&1; export OMPI_MCA_coll='^hcoll'
mpirun -np 16 ./wrf.exe > wrf.out 2>&1; tail -n 1 rsl.out.0000
