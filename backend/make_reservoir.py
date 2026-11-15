import numpy as np, json
from scipy import ndimage
from rasterio.features import shapes
from rasterio.transform import from_origin
from shapely.geometry import shape, mapping, box
from shapely.ops import unary_union
import shapely
from pyproj import Transformer
d = np.load("artifacts/window.npz"); hh, x, y, epsg = d["hh"], d["x"], d["y"], int(d["epsg"])
hhdb = np.nan_to_num(10*np.log10(np.where(hh > 0, hh, np.nan)), nan=0)
sm = ndimage.median_filter(hhdb, size=9)
water = sm < -13
lab, n = ndimage.label(water); sizes = ndimage.sum(water, lab, range(1, n+1))
big = np.isin(lab, 1 + np.where(sizes > 20000)[0])
res = ndimage.binary_fill_holes(ndimage.binary_closing(big, structure=np.ones((3,3)), iterations=25))
lab2, n2 = ndimage.label(res); s2 = ndimage.sum(res, lab2, range(1, n2+1)); res = lab2 == (1 + int(np.argmax(s2)))
# drop thin river channel (opening) and shoreline edge (erode 6 px = 60 m)
res = ndimage.binary_opening(res, structure=np.ones((3,3)), iterations=8)
lab3, n3 = ndimage.label(res); s3 = ndimage.sum(res, lab3, range(1, n3+1)); res = lab3 == (1 + int(np.argmax(s3)))
res = ndimage.binary_erosion(res, structure=np.ones((3,3)), iterations=6)
print("reservoir km2", round(res.sum()*100/1e6, 1))
aff = from_origin(float(x[0])-5, float(y[0])+5, 10, 10)
poly = unary_union([shape(g) for g, v in shapes(res.astype("uint8"), mask=res, transform=aff) if v == 1]).simplify(20)
back = Transformer.from_crs(epsg, 4326, always_xy=True).transform
p = shapely.ops.transform(back, poly)
json.dump({"type": "Feature", "properties": {"label": "Batas dari data NISAR 2026-11-06", "note": "Diturunkan otomatis dari masker air radar, perlu validasi"}, "geometry": mapping(p)}, open("backend/reservoir_nisar.geojson", "w"))
old = json.load(open("backend/zones.geojson"))["features"]
minx, miny, maxx, maxy = p.bounds; w = (maxx-minx)/5; feats = []
for i in range(5):
    z = p.intersection(box(minx+i*w, miny-0.01, minx+(i+1)*w, maxy+0.01))
    props = dict(old[i]["properties"]) if i < len(old) else {"limit": 3000}
    props.update({"id": f"Z-0{i+1}", "name": f"Zona {i+1} ({['Barat','Barat-Tengah','Tengah','Timur-Tengah','Timur'][i]})", "area_ha": round(shapely.ops.transform(Transformer.from_crs(4326, epsg, always_xy=True).transform, z).area/1e4, 1), "note": "Pembagian zona ilustratif (pita bujur), bukan zona resmi PJT II; batas kapasitas contoh"})
    feats.append({"type": "Feature", "properties": props, "geometry": mapping(z)})
json.dump({"type": "FeatureCollection", "features": feats}, open("backend/zones_nisar.geojson", "w"))
print([ (f["properties"]["id"], f["properties"]["area_ha"], f["properties"].get("limit")) for f in feats])
