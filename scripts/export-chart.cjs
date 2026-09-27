// Reuse the exact same compositor as the chart's Export PNG button.
const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const {resolve,dirname}=require('node:path');
const {mkdir,writeFile}=require('node:fs/promises');
async function exportChart(input,output,options={}){
 const browser=await chromium.launch({headless:true,...(process.env.CHROME_EXECUTABLE?{executablePath:process.env.CHROME_EXECUTABLE}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  await page.route('http://**/*',route=>route.abort());await page.route('https://**/*',route=>route.abort());
  await page.goto(pathToFileURL(resolve(input)).href);
  await page.waitForFunction(()=>window.SecretSatoshisChart,{timeout:30000});
  const data=await page.evaluate(async options=>{
   const chart=await SecretSatoshisChart.ready;
   if(options.reportDate&&chart.payload.reportDate!==options.reportDate)throw new Error('Chart cutoff mismatch');
   if(options.presentation)chart.setPresentation(options.presentation,options.interval||'daily');
   if(options.range)chart.selectRange(options.range);
   return chart.exportImage(false);
  },options);
  await mkdir(dirname(resolve(output)),{recursive:true});
  await writeFile(resolve(output),Buffer.from(data.split(',')[1],'base64'));
  return resolve(output);
 }finally{await browser.close();}
}
module.exports={exportChart};
if(require.main===module){const [input,output]=process.argv.slice(2);if(!output){console.error('Usage: node scripts/export-chart.cjs INPUT_HTML OUTPUT_PNG');process.exitCode=1;}else exportChart(input,output).then(console.log).catch(e=>{console.error(e);process.exitCode=1;});}
