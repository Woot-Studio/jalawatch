import json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from pyproj import Transformer
d = np.load("artifacts/window.npz"); hh, x, y, epsg = d["hh"], d["x"], d["y"], int(d["epsg"])
db = np.nan_to_num(10*np.log10(np.where(hh > 0, hh, np.nan)), nan=0)
t = Transformer.from_crs(4326, epsg, always_xy=True).transform
fig, ax = plt.subplots(figsize=(10, 9))
ax.imshow(db, cmap="gray", vmin=-18, vmax=0, extent=[x[0], x[-1], y[-1], y[0]])
res = json.load(open("backend/reservoir_nisar.geojson"))["geometry"]
polys = res["coordinates"] if res["type"] == "MultiPolygon" else [res["coordinates"]]
for pg in polys:
    xs, ys = zip(*[t(*c) for c in pg[0]]); ax.plot(xs, ys, c="cyan", lw=0.7)
for f in json.load(open("web/public/data/cages.geojson"))["features"]:
    g = f["geometry"]
    if g["type"] == "Point":
        px, py = t(*g["coordinates"]); ax.plot(px, py, "r.", ms=2)
ax.set_xlim(x[300], x[1900]); ax.set_ylim(y[2100], y[450]); ax.set_title("JalaWatch NISAR 2026-11-06: reservoir (cyan), detected cage blocks (red)")
plt.savefig("artifacts/real_detection_2026-11-06.png", dpi=110, bbox_inches="tight")
