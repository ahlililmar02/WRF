#!/bin/bash
# Dry/wet pilot: 4 one-day runs + restart check. usage: pilot_launch.sh A|B GEO_D02   (log: runs/pilot<P>_launch.log)
# Restart check (A only): jan_on writes wrfrst at 12 h; copy as in p4_T7.sh, restart 12 h, compare with p4_compare.py.
P=$1; G=$2; E=~/WRF/WPS-4.7.0/era5_2025; cd ~/WRF/runs
run() { ./season_run.sh pilot${P}_$1 $G $2 24 $3 $E 2>&1 | tail -n 1; }
if [ $P = A ]; then
  NLSED='s/restart_interval=[0-9]*/restart_interval=720/;s/frames_per_outfile=[0-9]*,[0-9]*/frames_per_outfile=1,1/' run jan_on 2025-01-15_00 1
else run jan_on 2025-01-15_00 1; fi
run jan_off 2025-01-15_00 0
if [ $P = A ]; then
  D=pilotA_jan_on_rst; rm -rf $D; mkdir $D; cd $D
  for f in ../pilotA_jan_on/*; do b=$(basename $f); case $b in wrfout*|rsl.*|wrf.out|met_em*|metgrid|wrfrst*|timing.txt) ;; *) cp -P $f .;; esac; done
  cp ../pilotA_jan_on/wrfrst_d0?_2025-01-15_12:00:00 .
  sed -i -e 's/restart=.false./restart=.true./' -e 's/run_hours=24/run_hours=12/' -e 's/start_hour=00,00/start_hour=12,12/' namelist.input
  source ~/WRF/wrf_env.sh >/dev/null 2>&1; export OMPI_MCA_coll='^hcoll'
  mpirun -np 16 ./wrf.exe > wrf.out 2>&1; echo "$D: $(tail -n 1 rsl.out.0000)"; cd ..
  source ~/WRF/activate_satgeo.sh >/dev/null 2>&1; python -I p4_compare.py pilotA_jan_on pilotA_jan_on_rst > pilotA_restart_compare.txt 2>&1
  grep -c BIT-IDENTICAL pilotA_restart_compare.txt; grep -c DIFFER pilotA_restart_compare.txt
fi
until [ $(ls $E/ERA5:2025-07-1* 2>/dev/null | wc -l) -ge 25 ]; do sleep 60; done
run jul_on 2025-07-15_00 1
run jul_off 2025-07-15_00 0
echo PILOT_${P}_DONE
