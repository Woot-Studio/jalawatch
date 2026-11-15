"""Checks real HDF5 input path separately from the seeded demo generator."""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import h5py
import numpy as np
import rasterio
from pyproj import Transformer
from shapely.geometry import shape
import jalawatch as jw

class PipelineTest(unittest.TestCase):
    def test_hdf5_detection_and_outputs(self):
        reservoir=jw.load_geometry(jw.ROOT/'backend/reservoir.geojson')
        polygon=jw.transform_geometry(Transformer.from_crs(4326,32748,always_xy=True).transform,reservoir)
        xmin,ymin,xmax,ymax=polygon.bounds
        x=np.linspace(xmin+15,xmax-15,300);y=np.linspace(ymax-15,ymin+15,400)
        hh=np.full((400,300),10**(-23/10),dtype='float32');hv=np.full_like(hh,10**(-29/10))
        for cx,cy in [(80,120),(150,230),(190,300)]:
            if polygon.covers(shape({'type':'Point','coordinates':[x[cx],y[cy]]})):
                hh[cy-3:cy+4,cx-3:cx+4]=10**(-5/10)
        with tempfile.TemporaryDirectory() as tmp:
            raw=Path(tmp)/'raw';raw.mkdir();out=Path(tmp)/'out'
            with h5py.File(raw/'NISAR_20261014.h5','w') as f:
                g=f.create_group('/science/LSAR/GCOV/grids/frequencyA')
                for name,v in [('HHHH',hh),('HVHV',hv),('xCoordinates',x),('yCoordinates',y),('xCoordinateSpacing',x[1]-x[0]),('yCoordinateSpacing',y[1]-y[0]),('projection',32748)]:
                    g.create_dataset(name,data=v)
                f.create_dataset('/science/LSAR/identification/zeroDopplerStartTime',data=b'2026-10-14T00:00:00')
            subprocess.run([sys.executable,str(jw.ROOT/'backend/jalawatch.py'),'--raw',str(raw),'--output',str(out)],check=True,capture_output=True)
            summary=json.loads((out/'summary.json').read_text());snap=summary['snapshots'][0]
            with (out/'counts.csv').open() as csv_file:
                rows=list(csv.DictReader(csv_file))
            self.assertFalse(summary['synthetic']);self.assertGreater(snap['total'],0)
            self.assertEqual(sum(int(r['count']) for r in rows),snap['total'])
            features=json.loads((out/'cages.geojson').read_text())['features']
            points=[f for f in features if f['properties']['kind']=='point']
            self.assertEqual(sum(f['properties']['count'] for f in points),snap['total'])
            self.assertTrue(all(reservoir.covers(shape(f['geometry'])) for f in points))
            with rasterio.open(out/'density-2026-10-14.tif') as src:
                self.assertEqual(src.crs.to_epsg(),32748)
                self.assertGreater(float(src.read(1,masked=True).max()),0)
                self.assertIn('validation',src.tags()['note'])

if __name__=='__main__':unittest.main()
