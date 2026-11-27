import os, subprocess, sys
P = "/home/8/uw07888/WRF/pipeline"
def cfg(env):
    code = f"import sys; sys.path.insert(0, '{P}'); import config as C; print(C.MOSAIC, C.CLASSES, C.CELLS, C.MONTH, list(C.CLIM_YEARS))"
    e = {k: v for k, v in os.environ.items() if k != "PIPE_MONTH"}; e.update(env)
    return subprocess.run([sys.executable, "-I", "-c", code], env=e, capture_output=True, text=True, check=True).stdout.split()
m = cfg({"PIPE_MONTH": "01"})
assert m[:3] == [f"/home/8/uw07888/WRF/pipeline/out/clim5y/m01/{n}" for n in ("mosaic.tif", "classes.tif", "cells.npz")], m
assert m[3] == "01" and " ".join(m[4:]) == "[2021, 2022, 2023, 2024, 2025]", m
c = cfg({})
assert c[:4] == ["/home/8/uw07888/WRF/pipeline/out/mosaic.tif", "/home/8/uw07888/WRF/pipeline/out/classes.tif", "/home/8/uw07888/WRF/pipeline/out/cells.npz", "None"], c
print("test_clim_config OK")
