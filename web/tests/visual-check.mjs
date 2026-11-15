import {chromium} from '@playwright/test';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
const artifacts=fileURLToPath(new URL('../../artifacts/',import.meta.url));
fs.mkdirSync(artifacts,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:1});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://localhost:5173');await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(700);
const results=[];
for(const id of ['hero','plunge','dashboard','fitur','tentang']){
 await page.locator('#'+id).scrollIntoViewIfNeeded();await page.waitForTimeout(1300);
 await page.screenshot({path:`${artifacts}/${id}.png`});
 results.push(await page.locator('#'+id).evaluate(el=>({id:el.id,width:el.clientWidth,height:el.clientHeight,overflow:document.documentElement.scrollWidth>innerWidth,clipped:[...el.querySelectorAll('h1,h2,h3,p,footer,.date-control,.download-links')].filter(c=>{if(c.closest('[aria-hidden="true"]'))return false;const r=c.getBoundingClientRect(),s=el.getBoundingClientRect();return r.bottom>s.bottom+1||r.right>s.right+1}).map(c=>c.className||c.tagName)})));
}
await page.locator('#dashboard').scrollIntoViewIfNeeded();
await page.waitForTimeout(1400);
if(!(await page.locator('#date-slider').isDisabled()))throw Error('Single-date slider should be disabled');
if(await page.locator('#total').textContent()!=='34.248')throw Error('Incorrect total');
if(!((await page.locator('#delta').textContent()).includes('Satu akuisisi')))throw Error('Incorrect delta');
await page.locator('#zone-select').selectOption('Z-03');await page.waitForTimeout(500);
if(!((await page.locator('#my-zone').textContent()).includes('7.219')))throw Error('Zone selection failed');
await page.locator('#zone-list button').first().click();
await page.locator('#fitur').scrollIntoViewIfNeeded();await page.locator('#next').click();await page.waitForTimeout(1000);
if(!((await page.locator('.feature-card.active').textContent()).includes('Ekspor laporan')))throw Error('Carousel failed');
for(const file of ['counts.csv','cages.geojson','density-2026-11-06.png','density-2026-11-06.tif']){const r=await page.request.get('http://localhost:5173/data/'+file);if(!r.ok())throw Error('Download missing '+file)}
const reduced=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});await reduced.goto('http://localhost:5173');await reduced.locator('#dashboard').scrollIntoViewIfNeeded();await reduced.waitForTimeout(500);if(await reduced.locator('#total').textContent()!=='34.248')throw Error('Reduced motion total failed');
const moving=await reduced.locator('.sonar-logo').first().evaluate(el=>getComputedStyle(el).animationName);if(moving!=='none')throw Error('Reduced motion animation active');
fs.writeFileSync(`${artifacts}/browser-check.json`,JSON.stringify({results,errors,reducedMotion:true,interactions:true},null,2));
console.log(JSON.stringify({results,errors,reducedMotion:true,interactions:true},null,2));
await browser.close();if(errors.length||results.some(r=>r.overflow||r.clipped.length))process.exit(1);
