#!/bin/bash
# Cleanup agreed 2026-11-24. Default = dry run (lists only). Run with "go" to act:  bash cleanup_2026-11-24.sh go
# 1) links the Thompson tables in kept runs to WRFV4.8.0/run (only if byte-identical)
# 2) removes wrfout + tables of 4 runs; namelists, logs, wrfinput and geo_em stay
# green20 is kept. blue20 only with a 2nd argument:  bash cleanup_2026-11-24.sh go blue20
# then blue20 loses all wrfout except the two d02 files validation/lake_test.py needs (2023-10-06_12, 10-07_12).
set -u
cd /home/8/uw07888/WRF/runs || exit 1
REF=/home/8/uw07888/WRF/WRFV4.8.0/run
GO=${1:-dry}; tot=0; n=0; bad=0
DEL="sentinel_gf sentinel_gf_lai default_flags veg_min ${2:-}"; case "${2:-}" in ""|blue20) ;; *) echo "2nd argument must be blue20"; exit 1;; esac
for d in $DEL; do
  [ -f "$d/namelist.input" ] || { echo "SKIP $d (no namelist.input)"; continue; }
  for f in "$d"/wrfout_d0* "$d"/freezeH2O.dat "$d"/qr_acr_qg_V4.dat "$d"/qr_acr_qsV2.dat; do
    [ -f "$f" ] && [ ! -L "$f" ] || continue
    case "$f" in blue20/wrfout_d02_2023-10-0[67]_12:00:00) continue;; esac
    s=$(stat -c %s "$f"); tot=$((tot+s)); echo "remove $((s/1000000)) MB  $f"
    [ "$GO" = go ] && rm -f -- "$f"
  done
done
for f in */freezeH2O.dat */qr_acr_qg_V4.dat */qr_acr_qsV2.dat; do
  [ -f "$f" ] && [ ! -L "$f" ] || continue
  case " $DEL " in *" ${f%%/*} "*) continue;; esac
  b=$(basename "$f")
  if cmp -s "$f" "$REF/$b"; then
    s=$(stat -c %s "$f"); tot=$((tot+s)); n=$((n+1))
    [ "$GO" = go ] && { ln -s "$REF/$b" "$f.new" && mv -f "$f.new" "$f"; }
  else bad=$((bad+1)); echo "NOT identical, left alone: $f"; fi
done
echo "tables linked: $n   not identical: $bad   total freed: $((tot/1000000)) MB   mode: $GO"
