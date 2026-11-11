/** 检查 UE 专栏在真实构建页面中的入口、配图、资源请求与窄屏布局。 */
const { chromium } = require('C:/Users/BlueDevil/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
(async () => {
 const browser = await chromium.launch({channel:"msedge",headless:true});
 const page = await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
 const origin='http://127.0.0.1:4322';
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const report={pages:[],errors};
 await page.goto(origin+'/qmx-Gameknowledge/',{waitUntil:'networkidle'});
 report.homeCategory=await page.locator('.category-nav a[href="#unreal"]').count();
 if(report.homeCategory!==1)throw Error('UE category missing');
 await page.locator('#unreal').screenshot({path:'artifacts/ue-movement/home-category.png'});
 const links=await page.locator('#unreal a[href*="/knowledge/"]').evaluateAll(es=>[...new Set(es.map(e=>e.getAttribute('href')))]);
 for(const href of links){
  const response=await page.goto(origin+href,{waitUntil:'networkidle'});
  const images=await page.locator('main img').evaluateAll(es=>es.map(e=>({src:e.getAttribute('src'),loaded:e.complete&&e.naturalWidth>0})));
  report.pages.push({href,status:response.status(),images});
  if(response.status()!==200||images.some(i=>!i.loaded))throw Error('Bad page/image: '+href);
 }
 await page.goto(origin+'/qmx-Gameknowledge/knowledge/ue专栏/运动系统/07-gasp-input/',{waitUntil:'networkidle'});
 await page.screenshot({path:'artifacts/ue-movement/article-desktop.png',fullPage:false});
 await page.locator('img[src*="slide-transitions"]').screenshot({path:'artifacts/ue-movement/slide-diagram.png'});
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:'artifacts/ue-movement/article-mobile.png'});
 report.mobile={viewport:390,documentWidth:await page.evaluate(()=>document.documentElement.scrollWidth)};
 const r=await page.request.get(origin+'/qmx-Gameknowledge/assets/ue-movement/blueprint-evidence.json');
 report.evidenceStatus=r.status();if(r.status()!==200)throw Error('Missing evidence');
 fs.writeFileSync('artifacts/ue-movement/browser-check.json',JSON.stringify(report,null,2));
 await browser.close();
 console.log(JSON.stringify({pages:report.pages.length,homeCategory:report.homeCategory,mobile:report.mobile,errors:report.errors}));
 if(errors.length||report.mobile.documentWidth>390)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});

