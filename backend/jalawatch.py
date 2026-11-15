#!/usr/bin/env python3
"""JalaWatch: offline NISAR GCOV pipeline. All estimates require field validation."""
import argparse
import csv
import json
from datetime import date
from pathlib import Path
import h5py
import numpy as np
from scipy import ndimage
import rasterio
from rasterio.features import geometry_mask, shapes
from rasterio.transform import from_origin, from_bounds
from shapely.geometry import shape, mapping, box, Point
from shapely import transform as shapely_transform

def transform_geometry(fn, geom):
    return shapely_transform(geom, fn, interleaved=False)
from pyproj import Transformer, CRS
from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'Sample data'
NOTE = 'estimate, needs field validation'

def load_geometry(path):
    obj = json.loads(Path(path).read_text())
    if obj['type'] == 'FeatureCollection':
        from shapely.ops import unary_union
        return unary_union([shape(f['geometry']) for f in obj['features']])
    return shape(obj.get('geometry', obj))

def read_gcov(path):
    # Stage 1: read the two covariance grids and their sibling geocoding metadata.
    with h5py.File(path) as f:
        candidates = []
        f.visititems(lambda name, obj: candidates.append(name) if isinstance(obj, h5py.Dataset) and name.endswith('/HHHH') else None)
        if not candidates:
            raise ValueError(f'{path}: HHHH not found')
        hh_ds = f[candidates[0]]
        group = hh_ds.parent
        hh, hv = hh_ds[:], group['HVHV'][:]
        if hh.shape != hv.shape or hh.ndim != 2:
            raise ValueError('HHHH/HVHV must be 2D grids of the same size')
        x, y = group['xCoordinates'][:], group['yCoordinates'][:]
        dx, dy = float(group['xCoordinateSpacing'][()]), float(group['yCoordinateSpacing'][()])
        crs = CRS.from_epsg(int(group['projection'][()]))
        if dx <= 0 or dy >= 0 or not crs.is_projected or crs.axis_info[0].unit_name != 'metre':
            raise ValueError('Grid must be north-up, projected, and in metres')
        affine = from_origin(float(x[0])-dx/2, float(y[0])-dy/2, dx, -dy)
        hh = np.where(hh == hh_ds.attrs.get('_FillValue', -9999), np.nan, hh)
        hv = np.where(hv == group['HVHV'].attrs.get('_FillValue', -9999), np.nan, hv)
        # Prefer identification metadata over filenames.
        stamp = f.get('/science/LSAR/identification/zeroDopplerStartTime')
        observed = stamp[()].decode()[:10] if stamp is not None else None
    if not observed:
        import re
        match = re.search(r'(20\d{6})', path.name)
        if not match:
            raise ValueError('Acquisition date not found')
        observed = date.fromisoformat(f'{match[1][:4]}-{match[1][4:6]}-{match[1][6:]}').isoformat()
    return hh, hv, affine, crs, observed

def pipeline(hh, hv, affine, crs, reservoir, args):
    project = Transformer.from_crs(4326, crs, always_xy=True).transform
    polygon = transform_geometry(project, reservoir)
    # Stage 2: polygon crop, including physical array window.
    inside = geometry_mask([mapping(polygon)], hh.shape, affine, invert=True)
    rows, cols = np.where(inside)
    if len(rows) == 0:
        raise ValueError('Reservoir polygon does not intersect the grid')
    r0, r1, c0, c1 = rows.min(), rows.max()+1, cols.min(), cols.max()+1
    hh, hv, inside = hh[r0:r1,c0:c1], hv[r0:r1,c0:c1], inside[r0:r1,c0:c1]
    affine = affine * rasterio.Affine.translation(int(c0), int(r0))
    # Stage 3: calibrated linear covariance -> dB; invalid pixels stay invalid.
    valid = inside & np.isfinite(hh) & np.isfinite(hv) & (hh > 0) & (hv > 0)
    hh_db = 10*np.log10(np.where(valid, hh, np.nan))
    hv_db = 10*np.log10(np.where(valid, hv, np.nan))
    # Stage 4: median speckle filter (odd window, configurable).
    smooth = ndimage.median_filter(np.nan_to_num(hh_db, nan=-100), size=args.filter_size)
    hv_smooth = ndimage.median_filter(np.nan_to_num(hv_db, nan=-100), size=args.filter_size)
    # Stage 5: dark HV water, fill small bright holes so cage candidates survive.
    water = ndimage.binary_fill_holes((hv_smooth < args.water_db) & valid) & valid
    # Stage 6: bright HH targets, restricted to water.
    bright = (smooth > args.target_db) & water
    # Stage 7: eight-connected components.
    components, _ = ndimage.label(bright, structure=np.ones((3,3)))
    pixel_area = abs(affine.a*affine.e-affine.b*affine.d)
    if crs.is_geographic:
        raise ValueError('Use a projected grid in metres for area estimates')
    records = []
    back = Transformer.from_crs(crs, 4326, always_xy=True).transform
    component_sizes = np.bincount(components.ravel())
    for geom, label in shapes(components.astype('int32'), mask=bright, transform=affine, connectivity=8):
        pixels = int(component_sizes[int(label)])
        if pixels < args.min_pixels:
            continue
        block = shape(geom)
        area = pixels * pixel_area
        records.append({'geometry':transform_geometry(back, block), 'count':max(1, round(area/args.cage_area)), 'area_m2':area})
    # Stage 8 is performed per zone in publish(); stage 9 uses a count-weighted grid.
    return records, water, affine, crs

def publish(snapshots, reservoir, zones, output, args):
    output.mkdir(parents=True, exist_ok=True)
    zone_features = zones['features']
    zone_geoms = [shape(z['geometry']) for z in zone_features]
    rows, features, history = [], [], []
    for observed, records, water, affine, crs in snapshots:
        counts = [0]*len(zone_geoms)
        areas = [0.0]*len(zone_geoms)
        density = np.zeros(water.shape, dtype='float32')
        project = Transformer.from_crs(4326, crs, always_xy=True).transform
        for i, rec in enumerate(records):
            center = rec['geometry'].centroid
            zone = next((j for j,g in enumerate(zone_geoms) if g.covers(center)), None)
            if zone is None:
                continue
            counts[zone] += rec['count']; areas[zone] += rec['area_m2']
            props = {'date':observed, 'zone':zone_features[zone]['properties']['id'], 'count':rec['count'], 'area_m2':round(rec['area_m2'],2), 'label':LABEL, 'note':NOTE}
            features.extend([{'type':'Feature','geometry':mapping(center),'properties':{**props,'kind':'point'}}, {'type':'Feature','geometry':mapping(rec['geometry']),'properties':{**props,'kind':'block'}}])
            xy = transform_geometry(project,center)
            col,row = (~affine)*(xy.x,xy.y)
            if 0 <= int(row) < density.shape[0] and 0 <= int(col) < density.shape[1]:
                density[int(row),int(col)] += rec['count']
        snapshot = {'date':observed,'total':sum(counts),'zones':[]}
        for j,z in enumerate(zone_features):
            props = z['properties']; limit = props['limit']
            status = 'Over limit' if counts[j] > limit else 'Watch' if counts[j] > limit*.8 else 'Safe'
            item = {'id':props['id'],'name':props['name'],'count':counts[j],'area_m2':round(areas[j],2),'limit':limit,'density':round(counts[j]/props['area_ha'],1),'status':status}
            snapshot['zones'].append(item)
            rows.append({'date':observed,**item,'label':LABEL,'note':NOTE})
        history.append(snapshot)
        # Stage 9: spatial smoothing of weighted candidate counts, cages per cell.
        density = ndimage.gaussian_filter(density, args.density_sigma)*water
        with rasterio.open(output/f'density-{observed}.tif','w',driver='GTiff',height=density.shape[0],width=density.shape[1],count=1,dtype='float32',crs=crs,transform=affine,nodata=-9999,compress='deflate') as dst:
            dst.write(np.where(water,density,-9999),1)
            dst.update_tags(label=LABEL,note=NOTE,units='estimated cages per cell')
        pos = density[density>0]; vmax = float(np.percentile(pos,99)) if pos.size else 1.0
        v = np.clip(density/max(vmax,1e-9),0,1)**0.6  # QA fix: stretch so non-peak areas stay visible
        rgba = np.stack([40+210*v,110+90*(1-v),180-90*v,np.where(water,220,0)],axis=-1).astype('uint8')
        meta = PngImagePlugin.PngInfo(); meta.add_text('label',LABEL); meta.add_text('note',NOTE)
        Image.fromarray(rgba).save(output/f'density-{observed}.png',pnginfo=meta)
    history.sort(key=lambda x:x['date'])
    with (output/'counts.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    write_json(output/'cages.geojson',{'type':'FeatureCollection','label':LABEL,'note':NOTE,'features':features})
    write_json(output/'zones.geojson',zones)
    write_json(output/'reservoir.geojson',{'type':'Feature','properties':{'label':LABEL,'note':NOTE},'geometry':mapping(reservoir)})
    write_json(output/'summary.json',{'label':LABEL,'note':NOTE,'synthetic':args.demo,'snapshots':history,'density':f"density-{history[-1]['date']}", 'parameters':{k:v for k,v in vars(args).items() if isinstance(v,(int,float,bool))}})
    print(f'{LABEL} — {NOTE}\n{len(history)} date(s), {len(features)//2} blocks → {output}')

def write_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,default=str,separators=(',',':')))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--demo',action='store_true',help='run on a seeded synthetic radar grid instead of real NISAR files')
    p.add_argument('--raw',type=Path,default=ROOT/'data/raw',help='folder with NISAR L2 GCOV .h5 files (default: data/raw)')
    p.add_argument('--reservoir',type=Path,default=ROOT/'backend/reservoir.geojson',help='reservoir outline GeoJSON in EPSG:4326')
    p.add_argument('--zones',type=Path,default=ROOT/'backend/zones.geojson',help='zone FeatureCollection in EPSG:4326 with id, name, limit, area_ha')
    p.add_argument('--output',type=Path,default=ROOT/'web/public/data',help='output folder (default: web/public/data)')
    p.add_argument('--target-db',type=float,default=-10,help='bright-target HH threshold in dB')
    p.add_argument('--water-db',type=float,default=-16,help='water mask HV threshold in dB (pixels below are water)')
    p.add_argument('--filter-size',type=int,default=3,help='median speckle filter window, odd number of pixels')
    p.add_argument('--min-pixels',type=int,default=4,help='minimum pixels per candidate cage block')
    p.add_argument('--cage-area',type=float,default=100,help='assumed area of one cage in m2')
    p.add_argument('--density-sigma',type=float,default=30,help='Gaussian smoothing sigma for the density grid, in pixels')
    args=p.parse_args()
    global LABEL, NOTE
    if not args.demo:
        LABEL, NOTE = 'Real NISAR data', 'automated estimate, needs field validation'  # REAL_LABEL
    if args.filter_size < 1 or args.filter_size%2 != 1 or args.cage_area <= 0 or args.min_pixels < 1 or args.density_sigma <= 0:
        p.error('Filter size must be a positive odd number; cage area, minimum pixels and sigma must be positive')
    reservoir=load_geometry(args.reservoir); zones=json.loads(args.zones.read_text())
    snapshots=[]
    if args.demo:
        rng=np.random.default_rng(42)
        crs=CRS.from_epsg(32748)
        projected=transform_geometry(Transformer.from_crs(4326,crs,always_xy=True).transform,reservoir)
        affine=from_bounds(*projected.bounds,420,560)
        hh=np.full((560,420),10**(-23/10)); hv=np.full_like(hh,10**(-29/10))
        mask=geometry_mask([mapping(projected)],hh.shape,affine,invert=True)
        for r,c in rng.integers([6,6],[554,414],size=(400,2)):
            if mask[r,c]: hh[r-2:r+3,c-2:c+3]=10**(-5/10)
        records,water,affine,crs=pipeline(hh,hv,affine,crs,reservoir,args)
        # Synthetic counts deliberately reproduce the design reference, not inferred accuracy.
        zone_geoms=[shape(z['geometry']) for z in zones['features']]
        for day in range(14,27,2):
            total=round(17799+(day-14)*359/12)
            weights=np.array([.29,.23,.19,.17,.12]); targets=np.floor(weights*total).astype(int); targets[0]+=total-targets.sum()
            dated=[]
            for j,g in enumerate(zone_geoms):
                subset=[rec.copy() for rec in records if g.covers(rec['geometry'].centroid)]
                if not subset: raise ValueError('Demo zone has no candidates')
                for i,rec in enumerate(subset):
                    rec['count']=int(targets[j]//len(subset)+(i<targets[j]%len(subset)))
                    rec['area_m2']=rec['count']*args.cage_area
                dated.extend(subset)
            snapshots.append((f'2026-10-{day}',dated,water,affine,crs))
    else:
        paths=sorted(args.raw.glob('*.h5'))
        if not paths: p.error(f'No .h5 files in {args.raw}; use --demo for a synthetic example')
        for path in paths:
            hh,hv,affine,crs,observed=read_gcov(path)
            records,water,affine,crs=pipeline(hh,hv,affine,crs,reservoir,args)
            snapshots.append((observed,records,water,affine,crs))
    if len({s[0] for s in snapshots}) != len(snapshots):
        p.error('Duplicate acquisition dates; merge products into one grid per date first')
    publish(snapshots,reservoir,zones,args.output,args)

if __name__=='__main__': main()
