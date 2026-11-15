import h5py, numpy as np, sys
from pyproj import Transformer
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
p = sys.argv[1]
with h5py.File(p) as f:
    g = f["/science/LSAR/GCOV/grids/frequencyA"]
    x = g["xCoordinates"][:]; y = g["yCoordinates"][:]
    epsg = int(g["projection"][()])
    t = Transformer.from_crs(4326, epsg, always_xy=True).transform
    xs, ys = zip(*[t(lon, lat) for lon in (107.24, 107.44) for lat in (-6.68, -6.45)])
    c0, c1 = np.searchsorted(x, min(xs)), np.searchsorted(x, max(xs))
    r = np.where((y >= min(ys)) & (y <= max(ys)))[0]; r0, r1 = r.min(), r.max()+1
    hh = g["HHHH"][r0:r1, c0:c1]; hv = g["HVHV"][r0:r1, c0:c1]
    print("epsg", epsg, "spacing", x[1]-x[0], y[1]-y[0], "window", hh.shape)
    print("x0", x[c0], "y0", y[r0])
for name, a in (("HH", hh), ("HV", hv)):
    a = np.where(a > 0, a, np.nan); d = 10*np.log10(a)
    print(name, "pct 1/5/25/50/75/95/99:", np.round(np.nanpercentile(d, [1,5,25,50,75,95,99]), 1))
    plt.figure(figsize=(8, 9)); plt.imshow(d, cmap="gray", vmin=np.nanpercentile(d, 2), vmax=np.nanpercentile(d, 98)); plt.colorbar(); plt.title(name+" dB 2026-11-06")
    plt.savefig(f"artifacts/quicklook_{name}.png", dpi=90); plt.close()
np.savez_compressed("artifacts/window.npz", hh=hh, hv=hv, x=x[c0:c1], y=y[r0:r1], epsg=epsg)
