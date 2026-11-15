import re, pathlib
w = pathlib.Path("web")
m = w / "src/main.js"; s = m.read_text(encoding="utf-8"); orig = s
L = "Data asli NISAR · 6 Nov 2026"
reps = [
 ("<span>Contoh data · ${note}</span>", f"<span>{L} · ${{note}}</span>"),
 ("<p>Contoh data · ${note}</p></div><a class=\"pill small\" id=\"export\"", f"<p>{L} · ${{note}}</p></div><a class=\"pill small\" id=\"export\""),
 ("<p class=\"feature-note\">Contoh data · ${note}</p>", f"<p class=\"feature-note\">{L} · ${{note}}</p>"),
 ("<h3>Unduh data olahan</h3><p>Contoh data · ${note}</p>", f"<h3>Unduh data olahan</h3><p>{L} · ${{note}}</p>"),
 ("<span class=\"example\">Contoh data</span>", "<span class=\"example\">NISAR 6 Nov</span>"),
 ("Data sintetis · bukan dasar penetapan kebijakan", "Estimasi otomatis dari radar · bukan dasar penetapan kebijakan"),
 ("alt=\"Contoh peta kepadatan sintetis Waduk Jatiluhur\"", "alt=\"Peta kepadatan estimasi keramba Waduk Jatiluhur dari NISAR 6 Nov 2026\""),
 ("<div class=\"radar-orbit\"></div><span>Contoh data</span>", "<div class=\"radar-orbit\"></div><span>NISAR · 6 Nov 2026</span>"),
 ("Data contoh ini belum divalidasi.", "Hasil 6 Nov 2026 ini belum divalidasi lapangan."),
 ("'Batas & zona ilustratif · Contoh data'", "'Batas waduk: masker radar NISAR · Zona & batas kapasitas ilustratif'"),
 ("<p>Batas ilustratif · pilih zona", "<p>Batas kapasitas ilustratif · pilih zona"),
 ("'14 Okt → 26 Okt'", "'Aktif begitu ada ≥2 akuisisi'"),
 ("<div class=\"mini-count\">17.799<small>", "<div class=\"mini-count\">34.248<small>"),
 ("'Tanggal pembanding'", "(snapshots.length<2?'Satu akuisisi · 6 Nov 2026':'Tanggal pembanding')"),
 ("<span>· ${mine.count-original.count>=0?'+':''}${fmt(mine.count-original.count)} sejak ${shortDate(first.date)}</span>", "${snapshots.length<2?'<span>· luas blok '+fmt(Math.round(mine.area_m2/1e4*10)/10)+' ha</span>':`<span>· ${mine.count-original.count>=0?'+':''}${fmt(mine.count-original.count)} sejak ${shortDate(first.date)}</span>`}"),
 ("document.querySelector('#date-slider').max=snapshots.length-1;", "document.querySelector('#date-slider').max=snapshots.length-1;if(snapshots.length<2)document.querySelector('#date-slider').disabled=true;"),
 ("pointRadius=snapshots.map((_,i)=>i===current?4:1.5)", "pointRadius=snapshots.map((_,i)=>i===current?5:1.5)"),
 ("'Data belum tersedia. Jalankan backend/jalawatch.py --demo, lalu muat ulang halaman.'", "'Data belum tersedia. Jalankan backend/jalawatch.py pada file NISAR di data/raw (atau --demo), lalu muat ulang halaman.'"),
]
for a, b in reps:
    n = s.count(a)
    print(("OK " if n else "MISSING ") + a[:60])
    s = s.replace(a, b)
m.write_text(s, encoding="utf-8")
i = w / "index.html"; t = i.read_text(encoding="utf-8")
t = t.replace("Contoh data, perlu validasi lapangan.", "Data NISAR 6 Nov 2026, estimasi perlu validasi lapangan."); i.write_text(t, encoding="utf-8")
b = pathlib.Path("backend/jalawatch.py"); bs = b.read_text(encoding="utf-8")
if "REAL_LABEL" not in bs:
    bs = bs.replace("    args=p.parse_args()", "    args=p.parse_args()\n    global LABEL, NOTE\n    if not args.demo:\n        LABEL, NOTE = 'Data asli NISAR', 'estimasi otomatis, perlu validasi lapangan'  # REAL_LABEL", 1)
    print("backend patched" if "REAL_LABEL" in bs else "backend parse_args line not found")
    b.write_text(bs, encoding="utf-8")
