// Focused local/CI check for the optional Bitcoin candle presentation.
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const {resolve}=require('node:path');
const fs=require('node:fs/promises');
(async()=>{const browser=await chromium.launch();try{
 const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('https://**/*',r=>r.abort());
 await page.goto(pathToFileURL(resolve('Charts/Bitcoin_Hashrate_Price.html')).href);
 await page.evaluate(()=>SecretSatoshisChart.ready);
 if(!await page.evaluate(()=>Boolean(SecretSatoshisChart.payload.candleViews))){console.log('No candle dataset in this release; line-only compatibility preserved.');return;}
 await page.locator('#bitcoin-style').selectOption('candles');
 for(const interval of ['daily','weekly','monthly']){
  await page.locator('#candle-interval').selectOption(interval);
  await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  const result=await page.evaluate(()=>{const a=SecretSatoshisChart,p=a.payload;return {kind:a.state.presentation,interval:p.interval,points:a.view.entries.find(e=>e.definition.id==='price_close').parts[0].api.data().length,expected:p.candles.length};});
  assert.equal(result.kind,'candles');assert.equal(result.interval,interval);assert.equal(result.points,result.expected);
 }
 await page.locator('#remove-all').click();assert.deepEqual(await page.evaluate(()=>[...SecretSatoshisChart.state.visible]),['price_close']);
 await page.locator('#show-all').click();
 await fs.mkdir('outputs/candles',{recursive:true});
 const png=await page.evaluate(()=>SecretSatoshisChart.exportImage(false));const bytes=Buffer.from(png.split(',')[1],'base64');
 assert.equal(bytes.readUInt32BE(16),2400);assert.equal(bytes.readUInt32BE(20),1350);
 await fs.writeFile('outputs/candles/monthly-export.png',bytes);
 await page.screenshot({path:'outputs/candles/desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.waitForTimeout(250);
 assert.equal(await page.evaluate(()=>SecretSatoshisChart.view.charts.length),2);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),390);
 await page.screenshot({path:'outputs/candles/mobile.png',fullPage:true});
 await page.locator('#bitcoin-style').selectOption('line');
 assert.equal(await page.evaluate(()=>SecretSatoshisChart.payload.candles===undefined),true);
 await page.goto(pathToFileURL(resolve('Charts/Bitcoin_YTD_Return_Comparison_full.html')).href);await page.evaluate(()=>SecretSatoshisChart.ready);
 assert.equal(await page.locator('#bitcoin-controls').isVisible(),false);
 assert.deepEqual(errors,[]);console.log('PASS candle intervals, visibility, PNG, mobile panels, return to line, excluded return chart.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
