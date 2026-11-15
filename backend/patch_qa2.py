import pathlib
c=pathlib.Path('web/src/style.css');s=c.read_text(encoding='utf-8');s=s.replace('.hero-copy p br,.plunge p br,.plunge h2 br{display:none}','.hero-copy p br,.plunge p br{display:none}');c.write_text(s,encoding='utf-8')
t=pathlib.Path('web/tests/visual-check.mjs');v=t.read_text(encoding='utf-8')
reps=[("await page.locator('#date-slider').fill('6');await page.waitForTimeout(1400);\nif(await page.locator('#total').textContent()!=='18.158')throw Error('Incorrect final total');\nif(!((await page.locator('#delta').textContent()).includes('+359')))throw Error('Incorrect delta');",
"await page.waitForTimeout(1400);\nif(!(await page.locator('#date-slider').isDisabled()))throw Error('Single-date slider should be disabled');\nif(await page.locator('#total').textContent()!=='34.248')throw Error('Incorrect total');\nif(!((await page.locator('#delta').textContent()).includes('Satu akuisisi')))throw Error('Incorrect delta');"),
("includes('3.450')","includes('7.219')"),
("'density-2026-10-26.png','density-2026-10-26.tif'","'density-2026-11-06.png','density-2026-11-06.tif'"),
("await reduced.locator('#date-slider').fill('6');if(await reduced.locator('#total').textContent()!=='18.158')throw Error('Reduced motion slider failed');","await reduced.waitForTimeout(500);if(await reduced.locator('#total').textContent()!=='34.248')throw Error('Reduced motion total failed');")]
for a,b in reps:
  print('OK' if a in v else 'MISSING', a[:50]); v=v.replace(a,b)
t.write_text(v,encoding='utf-8')
