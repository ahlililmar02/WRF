"""Run A minus run B, d02, one day, no spin-up dropped (made for the S2 LAI test; also the FRC_URB2D/mosaic test).
Input panels: LAI if the runs differ in LAI, else the paved share each run uses (FRC_URB2D test).
Day = 03-08 UTC, night = 13-21 UTC. Out: runs/<A>/compare.txt, compare{tag}_maps.png
Usage: s2lai_compare.py [runA runB [--allow key1,key2]]   (default s2lai_jul pilotA_jul_off; --allow = namelist keys that may differ)"""
import glob, re, sys, numpy as np, netCDF4
R = "/home/8/uw07888/WRF/runs/"
VARS = ("HFX", "LH", "GRDFLX", "T2", "TSK")
OUT = VARS + ("TH1",)   # TH1 = potential temperature at the lowest model level (K); T2 is only a diagnostic
GAP = "/home/8/uw07888/WRF/pipeline/out/s2_lai/m07_test.npz"   # frozen 11-25 file with key gap (m07.npz is pipeline output since 11-26)

def load(run):
    fs = sorted(glob.glob(R + f"{run}/wrfout_d02_*"))
    assert fs, f"{run}: no wrfout_d02 found"
    ds = [netCDF4.Dataset(f) for f in fs]
    miss = [v for v in VARS + ("T", "LAI", "LANDMASK", "Times") if v not in ds[0].variables]
    assert not miss, f"{run}: variables missing {miss}"
    d = {v: np.concatenate([x[v][:] for x in ds]) for v in VARS}
    d["TH1"] = np.concatenate([x["T"][:, 0] + 300. for x in ds])
    t = np.concatenate([x["Times"][:] for x in ds])
    d["LAI"] = ds[0]["LAI"][0]; d["LANDMASK"] = ds[0]["LANDMASK"][0]
    return d, np.array([b"".join(x).decode() for x in t])

def strip_keys(text, keys):
    """Namelist text without the `key=values,` entries of `keys` (values run to the comma before the next name= or line end), spaces normalised."""
    for k in keys:
        text = re.sub(rf"\b{re.escape(k)}\s*=[^=\n]*?,(?=\s*(?:\w+\s*=|$))", "", text, flags=re.M)
    return "\n".join(" ".join(l.split()) for l in text.split("\n"))

def paved_share(frc, urb, luf, mosaic, fix):
    """Paved fraction of each cell the model uses. No mosaic: FRC_URB2D in urban cells (zeroed elsewhere, urban_var_init).
    Stock mosaic: urban tile weight w_u x FRC_URB2D, urban cells only. mosaic_frc_opt=1: min(FRC_URB2D, w_u) in all cells.
    w_u = LANDUSEF urban / land classes (water 17, lake 21 removed); mosaic_cat=8 covers all land classes in d02 (WORKLOG 11-24)."""
    wu = luf[12] / np.maximum(np.delete(luf, (16, 20), axis=0).sum(0), 1e-9)
    if not mosaic:
        return np.where(urb, frc, 0.)
    return np.minimum(frc, wu) if fix else np.where(urb, wu * frc, 0.)

def run_paved(run):
    w = netCDF4.Dataset(R + f"{run}/wrfinput_d02"); nl = open(R + f"{run}/namelist.input").read()
    on = lambda k: re.search(rf"\b{k}\s*=\s*1\b", nl) is not None
    return paved_share(w["FRC_URB2D"][0], w["IVGTYP"][0] == 13, w["LANDUSEF"][0], on("sf_surface_mosaic"), on("mosaic_frc_opt"))

def group_stats(diff, mask):
    x = diff[mask]  # cell standard deviation (population)
    return int(mask.sum()), float(x.mean()), float(x.std())

def compare(a, b, out=True, allow=()):
    A, ta = load(a); B, tb = load(b)
    na, nb = (open(R + f"{r}/namelist.input").read() if glob.glob(R + f"{r}/namelist.input") else None for r in (a, b))
    assert na is not None and nb is not None, "namelist.input missing in a run"
    assert strip_keys(na, allow) == strip_keys(nb, allow), f"namelist.input differs between {a} and {b} beyond {list(allow)}: runs are not comparable"
    assert len(ta) == len(tb) and (ta == tb).all(), f"times differ: {ta[[0,-1]]} vs {tb[[0,-1]]}"
    hr = np.array([int(x[11:13]) for x in ta])
    win = {"day": np.isin(hr, range(3, 9)), "night": np.isin(hr, range(13, 22))}
    iv = netCDF4.Dataset(R + f"{b}/wrfinput_d02")["IVGTYP"][0]
    lm = A["LANDMASK"] == 1
    gap = np.load(GAP)["gap"].astype(bool) & lm
    grp = {"all land": lm, "urban": lm & (iv == 13), "other land": lm & (iv != 13), "MODIS gap": gap}
    if np.array_equal(A["LAI"], B["LAI"]):           # same LAI: not an LAI test -> show the paved share, drop the MODIS gap group
        del grp["MODIS gap"]; inp = ("paved share", run_paved(b), run_paved(a), "fraction")
    else:
        inp = ("LAI", B["LAI"], A["LAI"], "m2 m-2")
    D = {(v, p): (A[v][m] - B[v][m]).mean(0) for v in OUT for p, m in win.items()}
    rows = [(v, p, *group_stats(D[v, p], g)[1:], group_stats(D[v, p], g)[0], gn) for v, p in D for gn, g in grp.items()]
    # row = (var, period, mean, sd, n, group)
    lines = [f"{a} minus {b}, d02, {len(ta)} hourly outputs {ta[0]} .. {ta[-1]}",
             f"namelist keys allowed to differ: {list(allow) or 'none'}; cell groups (urban = IVGTYP 13) from {b} wrfinput",
             f"day = hours 03-08 UTC ({win['day'].sum()} outputs), night = 13-21 UTC ({win['night'].sum()} outputs); no spin-up dropped",
             "ONE-DAY CHECK, one pair, no ensemble. Units: W m-2 (HFX, LH, GRDFLX), K (T2, TSK, TH1 = theta at the lowest model level). mean and sd are over cells of the time-mean difference.", "",
             f"{'group':11s} {'n':>5s} {inp[0]+' '+b:>24s} {inp[0]+' '+a:>24s}"]
    for gn, g in grp.items():
        lines.append(f"{gn:11s} {g.sum():5d} {inp[1][g].mean():24.3f} {inp[2][g].mean():24.3f}")
    for p in win:
        lines += ["", f"{p}: difference {a} - {b}", f"{'variable':9s} {'group':11s} {'n':>5s} {'mean':>9s} {'sd':>8s}"]
        lines += [f"{v:9s} {gn:11s} {n:5d} {m:+9.3f} {s:8.3f}" for v in OUT for gn in grp for (vv, pp, m, s, n, g2) in rows if (vv, pp, g2) == (v, p, gn)]
    tag = "" if b == "pilotA_jul_off" else f"_{b}"   # keep the first result
    txt = "\n".join(lines)
    if out:
        print(txt); open(R + f"{a}/compare{tag}.txt", "w").write(txt + "\n"); maps(a, b, A, B, D, lm, tag, inp)
    return {"rows": rows, "text": txt}

def maps(a, b, A, B, D, lm, tag="", inp=None):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    ink = "#222222"; water = "#dfe7ee"
    div = LinearSegmentedColormap.from_list("bgr", ["#2a5ea8", "#efefef", "#c0392b"])  # blue-gray-red, gray midpoint
    name, xb, xa, unit = inp or ("LAI", B["LAI"], A["LAI"], "m2 m-2")
    seq = LinearSegmentedColormap.from_list(name, ["#eef5ea", "#1f6b35"] if name == "LAI" else ["#f4f4f4", "#3a3a3a"])   # LAI green, paved gray
    for c in (div, seq): c.set_bad(water)  # axis("off") hides the axes patch, so NaN needs its own colour
    lai = [np.where(lm, x, np.nan) for x in (xb, xa)]; top = np.nanmax(lai)
    src = {"pilotA_jul_off": "WPS", "s2lai_jul": "Sentinel-2, no gap", "modislai_jul": "MODIS, gaps = WPS"}
    src.update({"frcwc_jul": "WorldCover FRC, no mosaic", "mos_jul": "mosaic as published", "mosfix_jul": "mosaic + fix"})
    if name == "LAI": src.update({"s2lai_jul": "Sentinel-2, no gap"})
    else: src.update({"s2lai_jul": "GAIA FRC, no mosaic"})
    panels = [(f"{name} {b} ({src.get(b, b)})", lai[0], seq, 0, top, unit), (f"{name} {a} ({src.get(a, a)})", lai[1], seq, 0, top, unit)]
    for t, k, u in (("day dLH", ("LH", "day"), "W m-2"), ("day dHFX", ("HFX", "day"), "W m-2"), ("night dT2", ("T2", "night"), "K")):
        x = np.where(lm, D[k], np.nan); l = np.nanmax(np.abs(x)); panels.append((f"{t} ({a} - {b})", x, div, -l, l, u))
    fig, ax = plt.subplots(2, 3, figsize=(15, 9)); ax = ax.ravel(); ax[5].axis("off")
    for a_, (t, x, cm, lo, hi, u) in zip(ax, panels):
        im = a_.imshow(x, origin="lower", cmap=cm, vmin=lo, vmax=hi)
        a_.set_title(t, color=ink); a_.axis("off")
        fig.colorbar(im, ax=a_, shrink=0.8).set_label(u, color=ink)
    fig.suptitle("One-day check (2025-07-15), one pair, no ensemble; water = gray-blue", color=ink)
    fig.tight_layout(); fig.savefig(R + f"{a}/compare{tag}_maps.png", dpi=100)

if __name__ == "__main__":
    args, allow = sys.argv[1:], ()
    if "--allow" in args:
        i = args.index("--allow"); allow = tuple(args[i + 1].split(",")); args = args[:i] + args[i + 2:]
    compare(*(args[:2] or ("s2lai_jul", "pilotA_jul_off")), allow=allow)
