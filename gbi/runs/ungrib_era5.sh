#!/bin/bash
# ERA5 GRIB -> WPS intermediate files for one time window.
# usage: ungrib_era5.sh GRIBDIR OUTDIR START END   (START/END YYYY-MM-DD_HH:00:00)
# Writes OUTDIR/ERA5:YYYY-MM-DD_HH; uses only the GRIB files of the days in the window.
set -e
G=$1; O=$2; S=$3; E=$4
[ -n "$E" ] || { echo "usage: $0 GRIBDIR OUTDIR START END"; exit 2; }
source ~/WRF/wrf_env.sh >/dev/null 2>&1
W=~/WRF/WPS-4.7.0
mkdir -p $O && cd $O
ln -sf $W/ungrib/Variable_Tables/Vtable.ECMWF Vtable; ln -sf $W/ungrib.exe ungrib.exe
sed -e "s/start_date *= *'[^']*', *'[^']*'/start_date = '$S', '$S'/" \
    -e "s/end_date *= *'[^']*', *'[^']*'/end_date   = '$E', '$E'/" ~/WRF/runs/sentinel/namelist.wps > namelist.wps
files=(); d=${S:0:10}
while [[ ! "$d" > "${E:0:10}" ]]; do
  for k in sfc pl; do f=$G/era5_${k}_${d//-/}.grib; [ -f $f ] || { echo "missing $f"; exit 1; }; files+=($f); done
  d=$(date -u -d "$d + 1 day" +%Y-%m-%d)
done
rm -f GRIBFILE.*; $W/link_grib.csh "${files[@]}"
./ungrib.exe > ungrib.out 2>&1 || true
cp ungrib.log ungrib_${S:0:13}.log; rm -f GRIBFILE.*
grep -q 'Successful completion of program ungrib.exe' ungrib.log || { echo "ungrib failed, see $O/ungrib.log"; exit 1; }
echo "ungrib OK $S .. $E: $(ls ERA5:${S:0:7}* | wc -l) files for ${S:0:7} in $O"
