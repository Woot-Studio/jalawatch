# JalaWatch — Frontend Handoff (Desktop)

Build a static desktop frontend (HTML/CSS/JS, no framework needed) for **JalaWatch**, a NASA Space Apps 2026 concept. It estimates floating fish cage (keramba) counts at Waduk Jatiluhur, Purwakarta, using NISAR L2 GCOV radar data (HH/HV) from ASF. Copy is in Indonesian. Desktop only; mobile comes later.

## Sources
- Motion/visual design (Jitter): https://jitter.video/file/?id=uXS330DNUTmPyc7Ivk6rIT26
- MP4 export of all 5 artboards: https://jitter.video/exports/?file=uXS330DNUTmPyc7Ivk6rIT26&profile=mp4&size=1x&overrides=W3siYXJ0Ym9hcmRJZCI6ImJMWm1RZHlsMUNmUmJ5YWlnZWhydCJ9LHsiYXJ0Ym9hcmRJZCI6ImVSeE8waW81a2ZFOGRRb1VvbG9iaiJ9LHsiYXJ0Ym9hcmRJZCI6Im1KSnFnYXpyV0VvWWl1VDBHUDdUUCJ9LHsiYXJ0Ym9hcmRJZCI6IkZ3dzNudVZTZUNDMEZSa1lYM1ExMSJ9LHsiYXJ0Ym9hcmRJZCI6InhXQVlHd2cza2E5dmZ3cDVjejFFbyJ9XQ%3D%3D
- FigJam board (product spec, users, pipeline): https://www.figma.com/board/ypjp6NpLjqz9qlaFamQj1D/JalaWatch-%E2%80%94-Diagrams
- `figjam-jalawatch-diagrams.txt` is a text dump of the board and `figjam-board.png` is a screenshot of it. `screens/` holds stills from the Jitter file.

## Style
Illustrative underwater storytelling site. Full-viewport vertical sections, parallax layers, gentle bobbing and bubbles, and a plunge transition where the waterline wipes up as you scroll. It should not look like a generic dark admin console.
- Deep gradient: #2B46AE → #1B164A. Coral CTA gradient: #FF5277 → #FF7A59.
- Status colors: green, yellow, and red (over the limit).
- Fonts (all Google Fonts): Unbounded for the wordmark and display, Plus Jakarta Sans for UI and body, IBM Plex Mono for numbers and data labels.
- Glass cards only where they sit over the scene. Pill CTAs. No eyebrow labels, emoji bullets, or filler icons.

## Sections (in scroll order)
1. **Hero** — Daytime Jatiluhur with cages, a boat, and a satellite beam. The wordmark has a rotating sonar mark. Headline "Pantau keramba Jatiluhur / dari orbit" with the second line in coral. A "Lihat dashboard" pill, plus a "Gulir untuk menyelam" scroll cue.
2. **Plunge** — The waterline wipes up and reveals nets, bubbles, and fish. Headline "Radar menembus awan / dan kabut."
3. **Dashboard** — Leaflet map of the reservoir with zones, a sonar sweep, and cages drawn as blinking dots. The estimated total counts up (17.799). Moving the date slider from 14 to 26 Okt changes the total to 18.158 and shows a "+359 sejak 14 Okt" badge, and over-limit zones pulse red. Also a Chart.js trend chart, an export button, and a zone status list.
4. **Fitur carousel** — Spring carousel of 4 cards: 01 Jumlah keramba, 02 Peta kepadatan, 03 Bandingkan tanggal, 04 Ekspor laporan. The center card is about 1.2× scale; side cards are 0.8× at 60% opacity.
5. **Tentang data** — A signal travels through the 9-step pipeline: read with h5py, crop, convert to dB, speckle filter, water mask, bright-target threshold, clustering, count per zone, density grid. Includes a radar tile illustration, a caveat with a "Perlu validasi" chip, downloads (CSV, GeoJSON, PNG/GeoTIFF), and NASA/ISRO/ASF credits.

## Data
Every number is example data. Label it "Contoh data" and "estimasi, perlu validasi lapangan". Load it from a local JSON or CSV so real pipeline output can replace it later.

## Done when
- All 5 sections work at 1440px wide.
- Scroll-driven animations match the Jitter timing closely, and `prefers-reduced-motion` is respected.
- Map, slider, chart, and export all work with the example data.

## Also build (full scope, per the FigJam board)
1. **Backend: `jalawatch.py`.** An offline Python batch script with no server and no database. It reads NISAR L2 GCOV `.h5` files from `data/raw` (downloaded from ASF with an Earthdata Login) and follows the FigJam pipeline in this order:
   - read the HHHH/HVHV grids with h5py
   - crop to the reservoir polygon (`reservoir.geojson`)
   - convert to dB
   - apply a speckle filter
   - apply a water mask
   - apply a bright-target threshold
   - cluster the bright targets into cage blocks (connected components)
   - estimate the count and area per zone
   - build a density grid

   It writes three outputs into the frontend's `public/data/`:
   - CSV of estimated counts per date and zone
   - GeoJSON of the detected cage points and blocks
   - PNG or GeoTIFF density maps

   Make the thresholds configurable. Add a `--demo` flag that generates synthetic outputs so the frontend runs without any real `.h5` file. Include a `requirements.txt` and use a uv- or pip-based setup.
2. **"Zona saya" (cage farmer).** The user picks their own zone and sees that zone's estimated density, its status, and its trend.
3. **"Unduh data olahan" (researcher).** Download buttons for the CSV, GeoJSON, and PNG outputs, with a short description of each file's format.
4. **Validation note.** The "Tentang data" section explains that every estimate is checked visually against Google Earth imagery. It also states the hypothesis: calm water appears dark in radar and cages may appear as bright points, so the estimates still need field validation.
5. **Deploy.** Add a GitHub Actions workflow that builds with Bun and deploys to GitHub Pages. Also make the project deployable to Vercel.
6. **Zones over the limit (reservoir authority).** A list or table of zones whose estimate is over the limit, linked to the map.

Keep the visual style of the earlier sections for all of these.
