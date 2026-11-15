import pathlib
i=pathlib.Path('web/index.html');t=i.read_text(encoding='utf-8')
if 'favicon' not in t: t=t.replace('<title>','<link rel="icon" type="image/svg+xml" href="./favicon.svg"/><title>');i.write_text(t,encoding='utf-8')
b=pathlib.Path('backend/jalawatch.py');s=b.read_text(encoding='utf-8')
old="        v = density/max(float(density.max()),1e-9)\n"
new="        pos = density[density>0]; vmax = float(np.percentile(pos,99)) if pos.size else 1.0\n        v = np.clip(density/max(vmax,1e-9),0,1)**0.6  # QA fix: stretch so non-peak areas stay visible\n"
print('density patched' if old in s else 'density line not found'); s=s.replace(old,new); b.write_text(s,encoding='utf-8')
