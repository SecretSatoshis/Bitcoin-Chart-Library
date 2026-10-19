const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {runInNewContext}=require('node:vm');
const {resolve}=require('node:path');

// Exercise the actual canvas primitive without starting a chart page or fetching data.
const source=readFileSync(resolve(__dirname,'../web/renderer.js'),'utf8');
const start=source.indexOf('  class ReferenceLevels {');
const end=source.indexOf('\n  // Prepared numeric',start);
const ReferenceLevels=runInNewContext(source.slice(start,end)+'\nReferenceLevels',{
  readout:price=>'$'+price,
});
const times=['2025-03-17','2025-03-24','2025-03-31','2025-04-07'];

function draw(levels,{offset=0,width=300,supportResistance=true}={}){
  const lines=[],labels=[];
  const context={
    save(){},restore(){},beginPath(){},rect(){},clip(){},
    setLineDash(value){this.dash=Array.from(value);},
    moveTo(x,y){this.from=[x,y];},lineTo(x,y){this.to=[x,y];},
    stroke(){lines.push({from:this.from,to:this.to,width:this.lineWidth,dash:this.dash});},
    fillText(text,x,y){labels.push({text,x,y,align:this.textAlign});},
  };
  const primitive=new ReferenceLevels(levels,{priceToCoordinate:price=>price},times);
  primitive.setSupportResistance(supportResistance);
  // The vendored chart maps whole indexes; fractional calls return zero.
  primitive.attached({chart:{timeScale:()=>({logicalToCoordinate:index=>Number.isInteger(index)?index*70-offset:0})}});
  primitive.draw({useMediaCoordinateSpace:callback=>callback({context,mediaSize:{width,height:200}})});
  return {lines,labels};
}
const technical={name:'2025 Breakout Pivot',price:100,color:'#9ca3af',type:'resistance',
  startDate:'2025-03-25',lineStyle:'solid',labelAlign:'right'};

test('technical levels interpolate their date within a weekly candle and label the right end',()=>{
  const {lines,labels}=draw([technical]);
  assert.deepEqual(lines,[{from:[80,100],to:[300,100],width:1,dash:[]}]);
  assert.deepEqual(labels,[{text:'2025 Breakout Pivot · $100',x:292,y:94,align:'right'}]);
});
test('annual cases retain dashed full-width lines and left-side labels at the same thickness',()=>{
  const {lines,labels}=draw([{name:'Base Case',price:120,color:'#FFD700'},technical]);
  assert.deepEqual(lines[0],{from:[0,120],to:[300,120],width:1,dash:[4,5]});
  assert.equal(lines[0].width,lines[1].width);
  assert.equal(labels[0].align,'left');
  assert.equal(labels[0].x,8);
});
test('panning beyond an anchor clips the line at the plot edge',()=>{
  assert.equal(draw([technical],{offset:120}).lines[0].from[0],0);
});
test('a line is absent while its anchor lies to the right of the visible plot',()=>{
  assert.equal(draw([technical],{width:60}).lines.length,0);
  assert.equal(draw([{...technical,startDate:'2025-05-01'}]).lines.length,0);
});
test('anchors preceding chart history clip at its first observation',()=>{
  assert.equal(draw([{...technical,startDate:'2024-12-17'}]).lines[0].from[0],0);
});
test('hiding technical levels removes their lines and labels while retaining cases and generic thresholds',()=>{
  const {lines,labels}=draw([
    {name:'Base Case',price:120,color:'#FFD700'},technical,
    {...technical,name:'Support',type:'support',price:80},
    {label:'Model threshold',price:150,color:'#fff'},
  ],{supportResistance:false});
  assert.equal(lines.length,2);
  assert.deepEqual(labels.map(label=>label.text),['Base Case · $120','Model threshold']);
});
test('the toggle requests a redraw and restores technical levels',()=>{
  let updates=0;
  const primitive=new ReferenceLevels([technical],{},times);
  primitive.attached({chart:{},requestUpdate:()=>updates++});
  primitive.setSupportResistance(false);
  assert.equal(primitive.visibleLevels().length,0);
  primitive.setSupportResistance(true);
  assert.equal(primitive.visibleLevels().length,1);
  assert.equal(updates,2);
});
