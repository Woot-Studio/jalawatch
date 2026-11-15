import {chromium} from '@playwright/test';
const B='http://localhost:4173';const out={errors:[],failed:[],checks:[]};
const browser=await chromium.launch({channel:'msedge',headless:true});
async function run(vp,tag){
 const page=await browser.newPage({viewport:vp});
 page.on('pageerror',e=>out.errors.push(tag+' pageerror: '+e.message));
 page.on('console',m=>{if(m.type()==='error'||m.type()==='warning')out.errors.push(tag+' console '+m.type()+': '+m.text())});
 page.on('response',r=>{if(r.status()>=400)out.failed.push(tag+' '+r.status()+' '+r.url())});
 await page.goto(B);await page.waitForTimeout(1500);
 for(const id of ['hero','plunge','dashboard','fitur','tentang']){
  await page.locator('#'+id).scrollIntoViewIfNeeded();await page.waitForTimeout(1300);
  await page.screenshot({path:`../artifacts/qa-${tag}-${id}.png`});
  out.checks.push(await page.locator('#'+id).evaluate((el,tag)=>({tag,id:el.id,h:el.clientHeight,vh:innerHeight,overflowX:document.documentElement.scrollWidth>innerWidth?document.documentElement.scrollWidth:false,clipped:[...el.querySelectorAll('h1,h2,h3,p,a,button,small,strong,span,img,canvas,select,input')].filter(c=>{if(c.closest('[aria-hidden="true"],.leaflet-pane,.feature-card'))return false;const r=c.getBoundingClientRect(),s=el.getBoundingClientRect();return r.width>0&&(r.bottom>s.bottom+1||r.right>innerWidth+1||r.left<-1)}).map(c=>(c.id||c.className||c.tagName)+':'+(c.textContent||'').trim().slice(0,40))}),tag));
 }
 await page.locator('#dashboard').scrollIntoViewIfNeeded();await page.waitForTimeout(800);
 const opts=await page.locator('#zone-select option').evaluateAll(o=>o.map(x=>x.value));
 for(const z of opts){await page.locator('#zone-select').selectOption(z);await page.waitForTimeout(400);out.checks.push({tag,zone:z,txt:(await page.locator('#my-zone').textContent()).trim()})}
 await page.locator('[data-trend="total"]').click().catch(e=>out.errors.push(tag+' trend total click: '+e.message.split('\n')[0]));await page.waitForTimeout(400);
 out.checks.push({tag,trendTotal:await page.evaluate(()=>{const c=Chart?.getChart?.(document.querySelector('#trend'));return c?c.data.datasets[0].data:'n/a'}).catch(()=>'n/a')});
 const zb=page.locator('#zone-list button');out.checks.push({tag,zoneListButtons:await zb.count()});if(await zb.count())await zb.nth(2).click().catch(e=>out.errors.push(tag+' zonelist click: '+e.message.split('\n')[0]));
 out.checks.push({tag,sliderDisabled:await page.locator('#date-slider').isDisabled(),ticks:await page.locator('.date-ticks').textContent(),attribution:await page.locator('.leaflet-control-attribution').textContent().catch(()=>'none')});
 const links=await page.locator('a[href]').evaluateAll(a=>a.map(x=>({t:x.textContent.trim().slice(0,30),h:x.getAttribute('href'),dl:x.hasAttribute('download')})));
 out.checks.push({tag,links});
 for(const l of links.filter(l=>!l.h.startsWith('#')&&!l.h.startsWith('http'))){const r=await page.request.get(new URL(l.h,B).href);if(!r.ok())out.failed.push(tag+' LINK '+r.status()+' '+l.h)}
 await page.locator('#fitur').scrollIntoViewIfNeeded();for(let i=0;i<4;i++){await page.locator('#next').click().catch(e=>out.errors.push(tag+' next: '+e.message.split('\n')[0]));await page.waitForTimeout(900)}
 out.checks.push({tag,activeCard:(await page.locator('.feature-card.active').textContent()).slice(0,40)});
 await page.close();
}
await run({width:1440,height:900},'desk');await run({width:1280,height:720},'lap');await run({width:390,height:844},'mob');
console.log(JSON.stringify(out,null,1));await browser.close();
