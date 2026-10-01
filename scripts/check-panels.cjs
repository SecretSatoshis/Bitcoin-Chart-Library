// Stacked-panel check on the Metcalfe chart: alignment, controls, candles, mobile, catalog and PNG.
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const {resolve,extname,sep}=require('node:path');
const {pathToFileURL}=require('node:url');
const http=require('node:http');
(async()=>{
 const root=resolve('Charts'),artifacts=resolve('outputs/metcalfe-panels');
 await fs.mkdir(artifacts,{recursive:true});
 const server=http.createServer(async(req,res)=>{
  try{
   const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
   const path=resolve(root,'.'+pathname+(pathname.endsWith('/')?'index.html':''));
   if(!path.startsWith(root+sep))throw Error('outside chart pack');
   res.setHeader('Content-Type',({'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.png':'image/png'})[extname(path)]||'application/octet-stream');
   res.end(await fs.readFile(path));
  }catch{res.statusCode=404;res.end('not found');}
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const base=`http://127.0.0.1:${server.address().port}/`,browser=await chromium.launch();
 const errors=[];
 try{
  const page=await browser.newPage({viewport:{width:1440,height:800}});
  page.on('pageerror',e=>errors.push(e.message));
  async function screenshot(name){
   // Flush headless Chromium's canvas surfaces before full-page capture.
   // Otherwise it can composite an old bitmap even with the current chart state.
   await page.waitForTimeout(200);
   for(const frame of page.frames())await frame.evaluate(async()=>{
    await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
    for(const canvas of document.querySelectorAll('canvas'))canvas.toDataURL();
   });
   await page.waitForTimeout(50);
   await page.screenshot({path:resolve(artifacts,name+'.png'),fullPage:name!=='desktop'});
  }
  await page.goto(base+'Bitcoin_Metcalfe_Model.html');
  await page.evaluate(()=>SecretSatoshisChart.ready);
  async function panelState(target=page){return target.evaluate(()=>{
   const c=SecretSatoshisChart,range=c.view.range(),x=range.to;
   return {count:c.view.charts.length,range,ranges:c.view.charts.map(p=>p.timeScale().getVisibleRange()),
    widths:c.view.charts.map(p=>p.priceScale('right').width()),
    coordinates:c.view.charts.map(p=>p.timeScale().timeToCoordinate(x)),
    dates:c.view.charts.map(p=>p.timeScale().options().visible),
    heights:c.view.nodes.map(p=>p.getBoundingClientRect().height),
    labels:c.view.events.map(e=>e.labels),modes:c.state.modes,
    visible:[...c.state.visible]};
  });}
  let state=await panelState();
  assert.equal(state.count,2);assert.deepEqual(state.dates,[false,true]);
  assert.deepEqual(state.labels,[true,false]);assert.deepEqual(state.modes,{right:'log',left:'linear'});
  assert.ok(Math.abs(state.heights[0]/state.heights[1]-65/35)<.02);
  assert.ok(Math.abs(state.coordinates[0]-state.coordinates[1])<1);
  assert.equal(await page.locator('.legend-group').count(),2);
  assert.match(await page.locator('#scales').innerText(),/Price/);assert.match(await page.locator('#scales').innerText(),/Multiple/);
  await page.locator('.chart-card').evaluate(n=>n.scrollIntoView({block:'start'}));
  assert.ok(await page.locator('.plot-wrap').evaluate(n=>n.getBoundingClientRect().height<=innerHeight-80));
  // Fractional bars and panning past history must remain exactly synchronized.
  async function assertLocked(){
   await page.waitForTimeout(100);
   const ranges=await page.evaluate(()=>SecretSatoshisChart.view.charts.map(c=>c.timeScale().getVisibleLogicalRange()));
   assert.ok(Math.abs(ranges[0].from-ranges[1].from)<1e-6);
   assert.ok(Math.abs(ranges[0].to-ranges[1].to)<1e-6);
  }
  for(const panel of [0,1]){
   await page.evaluate(panel=>{const c=SecretSatoshisChart,scale=c.view.charts[panel].timeScale(),r=scale.getVisibleLogicalRange();scale.setVisibleLogicalRange({from:r.from+.3,to:r.to+.3});},panel);
   await assertLocked();
   const box=await page.locator('.chart-pane').nth(panel).boundingBox();
   await page.mouse.move(box.x+box.width*.5,box.y+box.height*.5);
   await page.mouse.wheel(150,0);await assertLocked();
   await page.mouse.wheel(0,-120);await assertLocked();
   await page.mouse.down();await page.mouse.move(box.x+box.width*.5+90,box.y+box.height*.5,{steps:8});await page.mouse.up();await assertLocked();
  }
  await page.evaluate(()=>{const c=SecretSatoshisChart,last=c.payload.x.length-1;c.view.charts[1].timeScale().setVisibleLogicalRange({from:last-100.4,to:last+25.6});});
  await assertLocked();await page.locator('#reset').click();await assertLocked();
  const resetRange=(await panelState()).range;
  assert.deepEqual(resetRange,await page.evaluate(()=>SecretSatoshisChart.state.requestedRange));
  for(const size of [{width:1280,height:720},{width:1440,height:800}]){
   await page.setViewportSize(size);await page.waitForTimeout(150);await assertLocked();
   assert.deepEqual((await panelState()).range,resetRange);
   await page.locator('.chart-card').evaluate(n=>n.scrollIntoView({block:'start'}));
   assert.ok(await page.locator('.plot-wrap').evaluate(n=>n.getBoundingClientRect().height<=innerHeight-80));
   assert.ok(await page.locator('.chart-pane').first().evaluate(n=>n.querySelector('canvas').getBoundingClientRect().right<=n.getBoundingClientRect().right));
  }
  await screenshot('desktop');
  // Zooming either panel must move the shared calendar; hover must update both.
  await page.locator('#chart').dispatchEvent('pointerdown');
  await page.evaluate(()=>{const c=SecretSatoshisChart;c.view.charts[1].timeScale().setVisibleRange({from:'2025-01-01',to:'2026-01-01'});});
  await page.waitForTimeout(100);state=await panelState();assert.deepEqual(state.ranges[0],state.ranges[1]);
  const point=await page.evaluate(()=>{const c=SecretSatoshisChart,r=c.view.nodes[0].getBoundingClientRect();return {x:r.x+c.view.charts[0].timeScale().timeToCoordinate('2025-08-01'),y:r.y+120};});
  await page.mouse.move(point.x,point.y);assert.equal(await page.locator('#reading-date').textContent(),'2025-08-01');
  await page.locator('#scale-left').selectOption('log');
  await page.locator('#series-metcalfe_value').click();
  const before=await panelState();
  for(const interval of ['daily','weekly','monthly']){
   await page.evaluate(interval=>SecretSatoshisChart.setPresentation('candles',interval),interval);
   const result=await panelState();assert.equal(result.count,2);assert.deepEqual(result.modes,before.modes);assert.deepEqual(result.visible,before.visible);
   assert.deepEqual(result.ranges[0],result.ranges[1]);assert.ok(Math.abs(result.coordinates[0]-result.coordinates[1])<1);
  }
  await page.evaluate(()=>SecretSatoshisChart.setPresentation('line'));
  assert.deepEqual((await panelState()).range,before.range);
  await page.locator('#reset').click();await page.locator('#events').click();
  assert.deepEqual(await page.evaluate(()=>SecretSatoshisChart.view.events.map(e=>e.visible)),[false,false]);
  await page.locator('#reset').click();
  await page.locator('#remove-all').click();assert.deepEqual((await panelState()).visible,['price_close']);
  await page.locator('#show-all').click();assert.equal((await panelState()).visible.length,3);
  const range=(await panelState()).range;
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(150);
  state=await panelState();assert.equal(state.count,2);assert.deepEqual(state.range,range);
  assert.ok(Math.abs(state.heights[0]/state.heights[1]-65/35)<.02);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),390);
  await screenshot('mobile');
  await page.setViewportSize({width:1440,height:1200});await page.waitForTimeout(150);
  for(const [name,interval] of [['line',null],['weekly','weekly']]){
   if(interval)await page.evaluate(interval=>SecretSatoshisChart.setPresentation('candles',interval),interval);
   const data=await page.evaluate(()=>SecretSatoshisChart.exportImage(false));
   const bytes=Buffer.from(data.split(',')[1],'base64');assert.equal(bytes.readUInt32BE(16),2400);assert.equal(bytes.readUInt32BE(20),1350);
   await fs.writeFile(resolve(artifacts,name+'-export.png'),bytes);
  }
  await page.goto(base+'?chart=Bitcoin_Metcalfe_Model');
  await page.waitForSelector('#chartFrame[src]');
  const embedded=page.frames().find(f=>f.url().includes('Bitcoin_Metcalfe_Model.html'));
  await embedded.waitForFunction(()=>window.SecretSatoshisChart);await embedded.evaluate(()=>SecretSatoshisChart.ready);
  assert.equal((await panelState(embedded)).count,2);
  await screenshot('catalog');
  await page.goto(pathToFileURL(resolve(root,'Bitcoin_Metcalfe_Model.html')).href);await page.evaluate(()=>SecretSatoshisChart.ready);
  assert.equal((await panelState()).count,2);
  // Existing templates still overlay on desktop and split equally on phones.
  await page.goto(base+'Bitcoin_Price.html');await page.evaluate(()=>SecretSatoshisChart.ready);
  assert.equal(await page.evaluate(()=>SecretSatoshisChart.view.charts.length),1);
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(150);
  assert.equal(await page.evaluate(()=>SecretSatoshisChart.view.charts.length),2);
  assert.deepEqual(errors,[]);
  console.log('PASS Metcalfe panels: alignment, controls, candles, mobile, catalog, file opening and PNG; single-panel chart unchanged.');
 }finally{await browser.close();server.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
