# JalaWatch

Situs desktop ilustratif untuk konsep NASA Space Apps 2026: estimasi keramba Waduk Jatiluhur dari radar NISAR. Satu proyek, dua bagian: frontend statis di `web/` dan batch Python offline di `backend/`. Tidak ada server aplikasi atau basis data.

**Contoh data — estimasi, perlu validasi lapangan.** Batas waduk, pembagian zona, luas zona, batas kapasitas, dan seluruh hasil bawaan merupakan data sintetis/ilustratif. Bukan hasil pengamatan NISAR atau batas resmi PJT II. Jangan gunakan untuk keputusan operasional.

## Menjalankan frontend

Prasyarat: Bun 1.4.4 atau versi yang kompatibel. Data demo sudah disertakan di `web/public/data/`.

```bash
cd web
bun install --frozen-lockfile
bun run dev
# http://localhost:5173
bun run build
bun run preview
```

Target utama 1440 × 900, desktop. Lima bagian setinggi viewport: Hero, Plunge, Dashboard, Fitur, Tentang data. Pengguna bisa memilih tanggal 14–26 Oktober, melihat total 17.799 → 18.158 (+359), memilih Zona saya, membandingkan tren zona/total waduk, memilih zona melewati batas untuk memusatkan peta, menelusuri empat kartu fitur, dan mengunduh hasil olahan.

Peta menggunakan Leaflet dan geometri lokal tanpa ketergantungan tile daring. Ini mempertahankan pemandangan radar dari referensi. Semua font juga disertakan secara lokal; frontend tidak perlu menghubungi Google Fonts. Mode `prefers-reduced-motion` mematikan animasi dekoratif, parallax, interpolasi angka, dan animasi peta, tetapi interaksi tetap bekerja. Carousel mendukung tombol sebelumnya/berikutnya, indikator, klik kartu samping, dan tombol panah saat area carousel mendapat fokus.

## Menjalankan backend

Prasyarat: Python 3.11+ dengan pip; disarankan Python 3.12.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/jalawatch.py --demo
```

Demo deterministik memakai seed 42 dan menjalankan tahapan deteksi pada grid radar sintetis. Bobot jumlah dan luas kemudian disesuaikan secara sintetis untuk mereproduksi angka referensi desain, **bukan ukuran akurasi deteksi**.

Untuk produk asli, unduh sendiri NISAR L2 GCOV dari ASF menggunakan Earthdata Login, simpan `.h5` di `data/raw/`, dan ganti geometri ilustratif dengan batas waduk serta zona resmi. Skrip tidak mengunduh produk dan tidak memerlukan kredensial.

```bash
python backend/jalawatch.py \
  --raw data/raw \
  --reservoir /path/ke/reservoir.geojson \
  --zones /path/ke/zones.geojson \
  --target-db -10 --water-db -16 \
  --filter-size 3 --min-pixels 4 \
  --cage-area 100 --density-sigma 5
```

`reservoir.geojson` menerima Geometry, Feature, atau FeatureCollection dalam EPSG:4326. `zones.geojson` adalah FeatureCollection poligon EPSG:4326; setiap feature mempunyai `id`, `name`, `limit` (jumlah keramba), dan `area_ha` (luas air zona). Zona sebaiknya tidak tumpang tindih dan harus mencakup wilayah analisis. `--output` dapat mengganti direktori keluaran, secara default `web/public/data/`.

### Urutan pipeline FigJam

1. h5py membaca grid kovarians linear HHHH/HVHV dan metadata geocoding.
2. Potong array dan masker sesuai poligon waduk.
3. Konversi kovarians positif ke dB memakai `10 * log10`.
4. Filter speckle median dengan jendela ganjil yang dapat diatur.
5. Masker air berdasarkan HV gelap; lubang internal diisi agar kandidat keramba terang tidak terbuang.
6. Ambang target HH terang pada masker air.
7. Connected components dengan konektivitas delapan membentuk blok kandidat; blok terlalu kecil dibuang.
8. Estimasi jumlah dari luas blok / luas keramba asumsi, lalu agregasi jumlah dan luas per zona.
9. Grid kepadatan berbobot jumlah kandidat dengan penghalusan Gaussian.

Pembacaan GCOV mencari dataset berakhiran `/HHHH`, lalu `/HVHV`, `xCoordinates`, `yCoordinates`, `xCoordinateSpacing`, `yCoordinateSpacing`, dan `projection` pada grup yang sama. Grid harus terproyeksi dalam meter dan north-up. Tanggal berasal dari `zeroDopplerStartTime` atau pola YYYYMMDD pada nama file. Satu produk per tanggal; tanggal duplikat ditolak agar produk mosaik tidak dihitung dua kali. Skrip membaca grid ke memori, sehingga RAM perlu sesuai ukuran produk.

Ambang dB, ukuran filter, ukuran minimum blok, luas keramba asumsi (m²), dan sigma kepadatan (piksel) perlu dikalibrasi terhadap data setempat. Jumlah suatu blok diatribusikan ke zona yang meliputi centroid-nya. Masker HV dan connected components adalah baseline deteksi; ukuran/arah keramba, angin, pantulan ganda, daratan sempit, dan resolusi sensor dapat memengaruhi hasil. Tidak ada klaim akurasi dari data demo.

### Keluaran

| File | Isi |
| --- | --- |
| `counts.csv` | Tanggal, zona, jumlah estimasi, luas blok m², batas contoh, kepadatan keramba/ha, status, dan catatan validasi |
| `cages.geojson` | Kandidat titik centroid dan poligon blok, bertanggal; filter `properties.kind` menjadi `point` atau `block` untuk menghindari menghitung representasi ganda |
| `density-YYYY-MM-DD.png` | Visualisasi RGBA kepadatan; PNG menyimpan label/catatan pada metadata, tidak menyimpan georeferensi |
| `density-YYYY-MM-DD.tif` | Grid float32 bergeoreferensi, berbobot estimasi keramba per sel; NoData −9999 di luar air |
| `summary.json` | Ringkasan tanggal dan zona yang dimuat frontend |
| `zones.geojson`, `reservoir.geojson` | Geometri lokal yang dimuat Leaflet |

Semua hasil membawa label **Contoh data** dan/atau catatan **estimasi, perlu validasi lapangan**. Setelah menjalankan backend, frontend memuat hasil baru tanpa perubahan kode; build ulang untuk publikasi. Batas status: Aman ≤80% batas, Waspada >80% hingga batas, Melebihi batas >100%. Nilai batas bawaan hanyalah contoh.

Hipotesis: air tenang tampak gelap pada radar, sedangkan keramba dapat tampak sebagai titik terang. Prosedur validasi mencakup pemeriksaan visual terhadap citra Google Earth dengan waktu akuisisi yang sesuai dan validasi lapangan. Proyek ini belum melakukan validasi tersebut.

## Pustaka yang digunakan

- **Bun + Vite**: pengelolaan paket, server pengembangan, build statis.
- **JavaScript dan SVG**: UI serta ilustrasi waduk, keramba, satelit, kapal, jaring, ikan, gelembung; tanpa framework UI.
- **GSAP + ScrollTrigger**: parallax, transisi garis air, count-up, dan carousel pegas. Animasi dekoratif ringan menggunakan CSS.
- **Leaflet**: peta vektor lokal, zona, blok kandidat, titik berkedip, zoom, dan interaksi zona.
- **Chart.js**: tren jumlah zona/total waduk, format angka Indonesia.
- **Unbounded, Plus Jakarta Sans, IBM Plex Mono** dari Google Fonts, disertakan lokal dengan lisensi OFL di `web/src/fonts/`.
- **h5py, NumPy, SciPy**: input HDF5, pengolahan radar, filter, connected components, kepadatan.
- **Shapely, pyproj, Rasterio**: geometri, proyeksi, rasterisasi, ekstraksi poligon, GeoTIFF.
- **Pillow**: ekspor PNG.
- **Playwright**: pemeriksaan browser dan tangkapan layar.

Palet utama mengikuti brief: `#2B46AE → #1B164A`, CTA `#FF5277 → #FF7A59`. Warna status yang tidak ditetapkan hex-nya di brief: hijau `#67D9AB`, kuning `#F3D56C`, merah `#FF5277`. Referensi asli ada di `jalawatch-handoff/`.

## Pemeriksaan

```bash
python -m unittest discover -s backend -p 'test_*.py'
# Jalankan bun run dev di terminal lain, lalu:
cd web
node tests/visual-check.mjs
```

Pemeriksaan browser menggunakan Chromium di `/usr/bin/chromium` secara default (atur `CHROMIUM_PATH` bila berbeda), viewport 1440 × 900, memotret kelima bagian, memeriksa overflow, slider, delta, zona, carousel, unduhan, error JavaScript, dan reduced motion. Hasil berada di `artifacts/`. Tes backend menulis fixture HDF5 independen, menjalankan jalur input non-demo, lalu mencocokkan jumlah CSV/GeoJSON dan georeferensi GeoTIFF. Tidak tersedia produk NISAR asli untuk validasi end-to-end terhadap satelit.

## Deploy GitHub Pages

1. Unggah proyek ini sebagai satu repo GitHub, dengan `web/`, `backend/`, dan `.github/` pada root.
2. Pastikan hasil batch di `web/public/data/` sudah di-commit. File `.h5`, `.venv`, `node_modules`, dan hasil build tidak perlu di-commit.
3. Di Settings → Pages, pilih **GitHub Actions** sebagai sumber.
4. Push ke `main`, atau jalankan workflow **Deploy JalaWatch to GitHub Pages** secara manual.

Workflow menginstal Bun 1.4.4, menjalankan `bun install --frozen-lockfile` dan `bun run build`, mengatur `BASE_PATH` sesuai nama repository, lalu memublikasikan `web/dist/`. Untuk domain kustom/root site, sesuaikan `BASE_PATH` menjadi `/` dan konfigurasi domain di GitHub Pages. Tidak ada rahasia atau Earthdata Login di CI.

## Deploy Vercel

Impor repo di Vercel dengan **Root Directory di root repo**, gunakan preset Other. `vercel.json` mengatur install/build Bun dan output `web/dist`. Alternatif CLI dari root: `vercel`, lalu `vercel --prod` ketika siap memublikasikan. Backend dijalankan lokal sebelum deploy, bukan sebagai fungsi serverless. Hasil demo sudah tersedia sehingga build awal dapat langsung berjalan.

## Kredit

Konsep NASA Space Apps 2026. NISAR: NASA / ISRO. Distribusi produk radar: Alaska Satellite Facility (ASF). JalaWatch bukan produk resmi atau bentuk dukungan dari organisasi tersebut. Desain mengacu pada brief, FigJam, dan still Jitter yang diberikan.
