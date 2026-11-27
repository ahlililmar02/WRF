"""Compare all common variables of the wrfout files both runs have. usage: python -I p4_compare.py RUN_A RUN_B [dom]
Prints differing variables (max |diff|, cells) and variables present in only one run."""
import sys, glob, numpy as np, netCDF4
R = "/home/8/uw07888/WRF/runs/"
a_run, b_run = sys.argv[1], sys.argv[2]
for dom in sys.argv[3:] or ["d01", "d02"]:
    na = {f.split("/")[-1] for f in glob.glob(f"{R}{a_run}/wrfout_{dom}_*")}; nb = {f.split("/")[-1] for f in glob.glob(f"{R}{b_run}/wrfout_{dom}_*")}
    common = sorted(na & nb); assert common, (dom, sorted(na), sorted(nb))          # restart runs cover only part of the straight run
    if na ^ nb: print(f"{dom}: {len(common)} common files; only in {a_run}: {len(na - nb)}, only in {b_run}: {len(nb - na)}")
    fa = [f"{R}{a_run}/{n}" for n in common]; fb = [f"{R}{b_run}/{n}" for n in common]
    for x, y in zip(fa, fb):
        a, b = netCDF4.Dataset(x), netCDF4.Dataset(y)
        common = [v for v in a.variables if v in b.variables and a[v].dtype.kind not in "SU"]
        diff = [(v, float(np.abs(a[v][:].astype("f8") - b[v][:].astype("f8")).max()), int((a[v][:] != b[v][:]).sum()))
                for v in common if not np.array_equal(a[v][:], b[v][:])]
        print(f"{dom} {x.split('/')[-1]} ({len(a.dimensions['Time'])} times, {len(common)} common vars): "
              f"{'BIT-IDENTICAL' if not diff else 'DIFFER ' + str(diff[:12])}")
        only = sorted(set(b.variables) - set(a.variables)) + ["-" + v for v in sorted(set(a.variables) - set(b.variables))]
        if only: print("   only in one run:", only)
