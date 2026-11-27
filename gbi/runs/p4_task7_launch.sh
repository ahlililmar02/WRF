#!/bin/bash
# P4 Task 7: tile on (p4_base) and off (p4_base_off), full case, in parallel (2 min stagger), then the analysis.
# Launched in tmux session "p4" so it survives closing the browser/Claude. Log: ~/WRF/runs/p4_task7_launch.log
cd ~/WRF/runs; G=~/WRF/runs/p3a_base_geo_em.d02.nc
echo "$(date '+%F %T') start on $(hostname)"
./p4_run.sh p4_base $G new 102 1 > p4_base.log 2>&1 &
P1=$!; sleep 120
./p4_run.sh p4_base_off $G new 102 0 > p4_base_off.log 2>&1 &
P2=$!; wait $P1; echo "$(date '+%F %T') p4_base: $(tail -n 2 p4_base.log | head -n 1)"
wait $P2; echo "$(date '+%F %T') p4_base_off: $(tail -n 2 p4_base_off.log | head -n 1)"
source ~/WRF/activate_satgeo.sh && python -I ~/WRF/runs/p4_task7.py > p4_task7_result.txt 2>&1
echo "$(date '+%F %T') analysis done -> ~/WRF/runs/p4_task7_result.txt"
echo "- $(date '+%F %T') Task 7 runs finished (tmux p4); results in runs/p4_task7_result.txt, map runs/p4_base/task7_effect.png (not yet reviewed)." >> ~/WRF/WORKLOG.md
