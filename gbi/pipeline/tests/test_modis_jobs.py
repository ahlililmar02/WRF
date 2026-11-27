import sys; sys.path.insert(0, "/home/8/uw07888/WRF/pipeline")
from modis import clim_jobs
j = dict(clim_jobs(range(2021, 2026)))
assert sorted(j) == [f"m{m:02d}_5y" for m in range(1, 13)], sorted(j)
assert j["m01_5y"][0] == ("2021-01-01", "2021-02-01") and len(j["m01_5y"]) == 5
assert j["m12_5y"][-1] == ("2025-12-01", "2026-01-01")      # December ends on 1 January of the next year
print("test_modis_jobs OK")
