const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {readFile,writeFile,mkdir}=require('node:fs/promises');
const {resolve,join,extname,sep}=require('node:path');
const {pathToFileURL}=require('node:url');
const http=require('node:http');
const root=resolve(process.argv[2]||'Charts'),artifacts=resolve('outputs/browser-checks');
(async()=>{
 await mkdir(artifacts,{recursive:true});
 const server=http.createServer(async(req,res)=>{try{const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);const path=resolve(root,'.'+pathname+(pathname.endsWith('/')?'index.html':''));if(!path.startsWith(root+sep))throw Error('outside root');res.setHeader('Content-Type',({'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.png':'image/png'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));}catch{res.statusCode=404;res.end('missing');}});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}/`;
 const browser=await chromium.launch({headless:true});const errors=[],external=[],timings=[];
 try{
 const context=await browser.newContext({viewport:{width:1440,height:1100},deviceScaleFactor:1});
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(r.url().startsWith('http')&&!r.url().startsWith(base))external.push(r.url());});
 const catalog=JSON.parse(await readFile(join(root,'catalog.json'),'utf8'));
 const examples=new Set(['Bitcoin_On_Chain','Bitcoin_Hashrate_Price','Bitcoin_YTD_Return_Comparison_full','Bitcoin_Equities','Bitcoin_Cycle_Low','MTD_Return_By_Year_Percentage','Bitcoin_YTD_Return_By_Year_Indexed']);
 for(const protocol of (process.env.CHART_TEST_FOCUSED?[]:['http','file'])){
  for(const entry of catalog.charts){
   console.log(`${protocol}: ${entry.filename}`);
   const start=performance.now();await page.goto(protocol==='http'?base+entry.url:pathToFileURL(join(root,entry.url)).href);
   await page.evaluate(()=>SecretSatoshisChart.ready);
   timings.push({chart:entry.filename,protocol,milliseconds:Math.round(performance.now()-start)});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),1440,entry.filename+' overflow');
   assert.equal(await page.evaluate(()=>{const a=SecretSatoshisChart;return a.view.entries.every(e=>{
    const s=e.definition,expected=s.values.flatMap((value,i)=>Number.isFinite(value)&&(a.state.modes[s.axis]!=='log'||value>0)?[{time:a.payload.x[s.start+i],value}]:[]);
    const actual=e.parts.flatMap(p=>p.api.data());return JSON.stringify(actual.map(p=>({time:p.time,value:p.value})))===JSON.stringify(expected);
   });}),true,entry.filename+' plotted parity');
   assert.equal(await page.evaluate(()=>document.fonts.check('700 32px Syne')),true);
   if(protocol==='http'&&examples.has(entry.filename)){
    await page.screenshot({path:join(artifacts,entry.filename+'.png'),fullPage:true});
    // The shared export is exercised for each family and the maximum series count.
    const png=await page.evaluate(()=>SecretSatoshisChart.exportImage(false));
    const data=Buffer.from(png.split(',')[1],'base64');assert.equal(data.readUInt32BE(16),2400);assert.equal(data.readUInt32BE(20),1350);
    await writeFile(join(artifacts,entry.filename+'-export.png'),data);
   }
  }
  console.log(`PASS all ${catalog.charts.length} charts via ${protocol}: exact plotted data, fonts, no overflow`);
 }
 // Responsive layouts, independent axes, range preservation and controls.
 for(const entry of catalog.charts.filter(e=>examples.has(e.filename))){
  await page.goto(base+entry.url);await page.evaluate(()=>SecretSatoshisChart.ready);
  const before=await page.evaluate(()=>SecretSatoshisChart.view.range());
  await page.locator('.solo').first().click();assert.equal(await page.evaluate(()=>SecretSatoshisChart.state.visible.size),1);
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(200);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),390);
  assert.equal(await page.evaluate(()=>SecretSatoshisChart.state.visible.size),1);
  assert.deepEqual(await page.evaluate(()=>SecretSatoshisChart.view.range()),before);
  assert.equal(await page.evaluate(()=>SecretSatoshisChart.view.charts.length),await page.evaluate(()=>Object.keys(SecretSatoshisChart.payload.axes).length));
  await page.locator('#reset').click();await page.waitForTimeout(100);
  if(await page.locator('#scale-left').count()){
   await page.locator('#scale-left').selectOption('log');assert.equal(await page.evaluate(()=>SecretSatoshisChart.state.modes.left),'log');
   assert.equal(await page.evaluate(()=>SecretSatoshisChart.view.charts[1].priceScale('right').options().mode),1);
   await page.locator('#reset').click();
  }
  await page.screenshot({path:join(artifacts,entry.filename+'-mobile.png'),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});await page.waitForTimeout(150);
 }
 // Embedded catalog preserves deep links, search and local-file operation.
 for(const baseURL of [base,pathToFileURL(join(root,'index.html')).href]){
  await page.goto(baseURL+'?chart=Bitcoin_Hashrate_Price');
  await page.waitForFunction(()=>document.querySelector('#chartFrame').src.includes('embed=1'));
  await page.waitForFunction(()=>document.querySelector('#chartFrame').contentWindow);
  await page.frameLocator('#chartFrame').locator('#chart-data').waitFor({state:'attached'});
  const frame=page.frames().find(f=>f.url().includes('Bitcoin_Hashrate_Price.html'));
  await frame.waitForFunction(()=>window.SecretSatoshisChart);await frame.evaluate(()=>SecretSatoshisChart.ready);
  assert.equal(await frame.locator('.site-nav').isVisible(),false);
  await page.locator('#chartSearch').fill('on-chain');
  assert.ok(await page.locator('.chart-card').count()>0);
  await page.locator('#closeViewer').click();assert.equal(await page.locator('#viewer').isVisible(),false);
  await page.locator('#chartSearch').fill('');assert.equal(await page.locator('.chart-card').count(),catalog.chart_count);
  // An unrelated window cannot resize the chart iframe.
  const height=await page.locator('#chartFrame').evaluate(e=>e.style.height);
  await page.evaluate(()=>window.postMessage({type:'ss-chart-size',id:'Bitcoin_Hashrate_Price',height:2999},'*'));
  assert.equal(await page.locator('#chartFrame').evaluate(e=>e.style.height),height);
 }
 // Day zero is a real cycle reading, and controls use numeric ranges.
 await page.goto(base+'Bitcoin_Cycle_Low.html');await page.evaluate(()=>SecretSatoshisChart.ready);
 await page.locator('[data-range="365D"]').click();
 await page.waitForFunction(()=>SecretSatoshisChart.view.range().to===365);
 assert.deepEqual(await page.evaluate(()=>SecretSatoshisChart.view.range()),{from:0,to:365});
 const point=await page.evaluate(()=>{const r=document.querySelector('.chart-pane').getBoundingClientRect();return {x:r.x+SecretSatoshisChart.view.charts[0].timeScale().timeToCoordinate(100),y:r.y+150};});
 await page.mouse.move(point.x,point.y);await page.waitForTimeout(100);assert.equal(await page.locator('#reading-date').textContent(),'Day 100');
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 await writeFile(join(artifacts,'timings.json'),JSON.stringify(timings,null,2));
 console.log('PASS controls, mobile panels, catalog HTTP/file embeds, exports; no browser exceptions or remote requests');
 }finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
