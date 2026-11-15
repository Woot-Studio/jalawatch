# JalaWatch

**Watching Jatiluhur's floating fish cages from orbit.** A NASA Space Apps Challenge 2026 project.

JalaWatch estimates the number and density of floating net cages (*keramba jaring apung*) in Jatiluhur Reservoir, Purwakarta, West Java, Indonesia, using NASA-ISRO **NISAR** L-band radar. Radar sees through the clouds and haze that often hide the reservoir from optical satellites.

- **Live site:** https://jalawatch-tqkk-xi.vercel.app/
- **Current result:** one real NISAR acquisition (6 Nov 2026), **34,248 estimated cages** in **739 detected cage blocks**.

> **Automated estimate, needs field validation.** Zones and capacity limits are illustrative, not official PJT II values. Each dot on the map is a candidate cage block, not a single cage. Do not use these numbers for operational or policy decisions.

The project has two parts and no application server or database:

- `backend/`: offline Python batch scripts that turn NISAR HDF5 products into GeoJSON, CSV, PNG and GeoTIFF.
- `web/`: a static Vite site (Leaflet map, Chart.js trend, GSAP scroll animation) that loads those files from `web/public/data/`.

## Data

| | |
| --- | --- |
| Mission | NASA-ISRO Synthetic Aperture Radar (NISAR) |
| Product | Level-2 Geocoded Polarimetric Covariance (L2 GCOV) |
| Access | Alaska Satellite Facility (ASF) / NASA Earthdata (Earthdata Login required) |
| Granule | `NISAR_L2_PR_GCOV_035_018_D_092_4005_DHDH_A_20261106T111143_20261106T111222_P05036_N_F_J_001.h5` |
| Acquisition | 6 Nov 2026 |
| Bands used | L-band HH (`HHHH`) and HV (`HVHV`) covariance terms |
| Grid | 10 m pixels, UTM zone 48S (EPSG:32748) |

The `.h5` file is not committed (it is large). Download it yourself from ASF and put it in `data/raw/`.

## How it works

### 1. Reservoir mask from radar (`backend/quicklook.py`, `backend/make_reservoir.py`)

`quicklook.py <granule.h5>` cuts a window around Jatiluhur (lon 107.24–107.44, lat −6.68 to −6.45) from the GCOV grid, prints HH/HV dB percentiles, saves quick-look PNGs and writes `artifacts/window.npz`.

`make_reservoir.py` then derives the reservoir outline from the radar itself:

1. HH to dB, 9×9 median filter.
2. Water = HH < −13 dB (calm water is dark in radar).
3. Keep large water bodies, close and fill holes (so bright cages inside the water are kept), take the largest connected component.
4. Morphological opening removes the thin river channel; a 60 m erosion trims the shoreline edge.
5. Result: about 53 km² of reservoir, written to `backend/reservoir_nisar.geojson`.
6. The outline is split into five equal longitude bands, written to `backend/zones_nisar.geojson` as Zone 1 (West) to Zone 5 (East). **These zones and their capacity limits are illustrative only.**

### 2. Cage detection (`backend/jalawatch.py`)

1. Read the `HHHH` / `HVHV` grids and geocoding metadata with h5py; the date comes from `zeroDopplerStartTime`.
2. Clip to the reservoir polygon.
3. Convert linear covariance to dB (`10 * log10`).
4. Median speckle filter (`--filter-size`).
5. Water mask from HV (`--water-db`); internal holes are filled so bright cage candidates survive. With `--water-db 0` the mask is effectively the radar-derived reservoir polygon.
6. Bright targets: HH > `--target-db` inside the water mask.
7. Eight-connected components form candidate cage blocks; blocks smaller than `--min-pixels` are dropped.
8. Cage count per block = block area / `--cage-area` (assumed 100 m² per cage), summed per zone by block centroid. Zone status: Safe ≤ 80% of the limit, Watch > 80%, Over limit > 100%.
9. Count-weighted density grid with Gaussian smoothing (`--density-sigma`, in pixels), saved as GeoTIFF and PNG.

### Reproducing the published result

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# put the granule in data/raw/, then:
python backend/quicklook.py data/raw/NISAR_L2_PR_GCOV_035_018_D_092_4005_DHDH_A_20261106T111143_20261106T111222_P05036_N_F_J_001.h5
python backend/make_reservoir.py
python backend/jalawatch.py \
  --raw data/raw \
  --reservoir backend/reservoir_nisar.geojson \
  --zones backend/zones_nisar.geojson \
  --target-db -8 --water-db 0 \
  --filter-size 3 --min-pixels 4
```

`--cage-area` (default 100 m²) and `--density-sigma` (default 30 px) were left at their defaults; the parameters used are also stored in `web/public/data/summary.json`. Output goes to `web/public/data/` by default (`--output` to change). `backend/overlay.py` draws the detected blocks over the HH image for a visual check (`artifacts/real_detection_2026-11-06.png`).

### Demo mode

```bash
python backend/jalawatch.py --demo --output /tmp/jalawatch-demo
```

`--demo` runs the same detection steps on a seeded synthetic radar grid (seed 42) with the illustrative geometry in `backend/reservoir.geojson` and `backend/zones.geojson`, over seven fake dates. Its counts are tuned to match the original design mock-up and say nothing about detection accuracy. The earlier demo output is kept in `web/public/data-demo-backup/` for reference; the live site uses the real NISAR output.

### Output files (`web/public/data/`)

| File | Contents |
| --- | --- |
| `summary.json` | Per-date and per-zone totals and the run parameters, loaded by the site |
| `counts.csv` | Date, zone, estimated count, block area (m²), illustrative limit, density (cages/ha), status, label and note |
| `cages.geojson` | Candidate blocks as centroid points and polygons; filter `properties.kind` (`point` or `block`) to avoid double counting |
| `density-YYYY-MM-DD.tif` | Georeferenced float32 grid, estimated cages per cell, NoData −9999 outside water |
| `density-YYYY-MM-DD.png` | RGBA visualization of the density grid (not georeferenced) |
| `zones.geojson`, `reservoir.geojson` | Geometry drawn by the map |

## Website

Requires Node.js 18+.

```bash
cd web
npm install
npm run dev      # http://localhost:5173
npm run build    # static site in web/dist/
npm run preview
```

Five full-height sections: Hero, Plunge, Dashboard, Features and About the data. The map uses Leaflet with local vector geometry only (no online tiles), and all fonts are bundled locally. `prefers-reduced-motion` turns off decorative animation while keeping every interaction.

## Deployment

The site is deployed on **Vercel** from the repository root using `vercel.json` (`cd web && npm install`, `npm run build`, output `web/dist`). Every push to `main` redeploys https://jalawatch-tqkk-xi.vercel.app/. The backend runs locally before deploying; it is not a serverless function. A GitHub Pages workflow (`.github/workflows/deploy.yml`) is also included.

## Checks

```bash
python -m unittest discover -s backend -p 'test_*.py'
cd web && npm run build && npm run preview -- --port 4173 &
JALAWATCH_URL=http://localhost:4173/ CHROMIUM_PATH=/path/to/chromium node web/tests/visual-check.mjs
```

The backend test writes a small synthetic HDF5 file, runs the non-demo input path and checks that CSV, GeoJSON and GeoTIFF outputs agree. The browser check uses Playwright at 1440 × 900 and checks layout overflow, the dashboard total, zone selection, the carousel, downloads, JavaScript errors and reduced motion. Screenshots go to `artifacts/`.

## Limitations

- **Single date so far.** Only the 6 Nov 2026 acquisition has been processed, so there is no trend or change detection yet.
- **100 m² per cage is an assumption.** Counts are block area divided by an assumed cage size; real cage sizes vary.
- **Illustrative zones and limits.** The five longitude-band zones and their capacity limits are examples, not official PJT II zoning or carrying-capacity values, so the "Over limit" status is illustrative too.
- **Not field validated.** Results have not been checked against field surveys. Wind, double bounce near the shore, boats and other structures can all look bright in radar.
- **Excluded area.** A bright, gridded area on the west arm of the reservoir was excluded pending verification of what it is.

## Next steps

- Build a time series from NISAR's 12-day repeat cycle to track cages being added or removed.
- Validate against high-resolution imagery and field counts, and calibrate the thresholds and cage size.
- Use official zones and limits from the reservoir authority if available.
- Extend to the other Citarum cascade reservoirs, Cirata and Saguling.

## Use of AI

AI tools helped build this project: **OpenAI Codex CLI** and the **Grok Bot** AI assistant helped write code, the user interface and documentation. The team reviewed the results and made the analysis decisions.

## Credits

NASA Space Apps Challenge 2026 project. NISAR data: NASA / ISRO, distributed by the Alaska Satellite Facility (ASF). JalaWatch is not an official product of, or endorsed by, these organizations.

Libraries: Leaflet, Chart.js, GSAP, Vite, h5py, NumPy, SciPy, rasterio, Shapely, pyproj and Pillow; Playwright for browser checks. Fonts: Unbounded, Plus Jakarta Sans and IBM Plex Mono (SIL Open Font License, bundled in `web/src/fonts/`).
