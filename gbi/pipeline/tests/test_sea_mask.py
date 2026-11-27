import sys; sys.path.insert(0, "/home/8/uw07888/WRF/pipeline")
import numpy as np, wc_fetch as F
# GSHHS land = cols 0..5, sea = cols 6..11; band = 2 px. Open-sea seed = water > 2 px offshore (cols 8..11).
land = np.zeros((10, 12), bool); land[:, :6] = True
wc = np.full((10, 12), 40, "u1"); wc[:, 6:] = 80
wc[0:5, 4:6] = 80          # eroded strip inside GSHHS land, touching sea -> sea
wc[5, 0:6] = 80            # river: last 2 px (band) -> sea, deeper part -> inland
wc[7:9, 4] = 80            # enclosed pond inside band, not touching sea -> inland
sea = F.sea_mask(wc, land, band_px=2)
assert sea[:, 8:][wc[:, 8:] == 80].all()                                   # open sea
assert sea[0:5, 4:6].all(), "eroded strip must be sea"
assert sea[5, 4:6].all() and not sea[5, 0:4].any(), sea[5].tolist()        # river cut at band edge (Lamarche 2017 3.5)
assert not sea[7:9, 4].any(), "enclosed pond must stay inland"
assert not sea[wc != 80].any()                                             # only water can be sea
# diagonal-only contact does not connect (4-connectivity)
wc2 = np.full((5, 8), 40, "u1"); wc2[:, 3:] = 80; wc2[1, 2] = 80; wc2[2, 1] = 80; land2 = np.zeros((5, 8), bool); land2[:, :3] = True
s2 = F.sea_mask(wc2, land2, band_px=2)
assert s2[1, 2] and not s2[2, 1], s2.tolist()
# no open sea in the domain -> everything inland
assert not F.sea_mask(np.full((4, 4), 80, "u1"), np.ones((4, 4), bool), band_px=1).any()
print("test_sea_mask OK")
