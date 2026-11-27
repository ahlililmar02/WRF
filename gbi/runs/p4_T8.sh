#!/bin/bash
# T8: 5x5 block with fw 0 / 0.10 / 0.25 / 0.40, 24 h each, hourly history.
cd ~/WRF/runs; G=~/WRF/runs/p4_geo
export NLSED='s/history_interval=[0-9]*,[0-9]*/history_interval=60,60/;s/frames_per_outfile=[0-9]*,[0-9]*/frames_per_outfile=24,24/'
for v in fw0 block_10 block_25 block_40; do ./p4_run.sh p4_T8_$v $G/geo_em_$v.d02.nc new 24 1 > p4_T8_$v.log 2>&1; echo "$v: $(tail -n 2 p4_T8_$v.log | head -n 1)"; sleep 15; done
