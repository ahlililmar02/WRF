"""python run.py [stage ...]   stages in order: composite classify aggregate modis write_geoem  (default: all)"""
import importlib, sys
STAGES = ["composite", "classify", "aggregate", "modis", "write_geoem"]
for s in sys.argv[1:] or STAGES:
    print("==", s, flush=True); importlib.import_module(s).main()
