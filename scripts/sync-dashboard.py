"""Copy the chart renderer, colours and events into the Report Library dashboard. No market data."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chart_build import prepare_assets, WEB
from chart_style import series_color
from chart_templates.events import EVENTS

output=Path(sys.argv[1]).resolve()
output.mkdir(parents=True,exist_ok=True)
assets=prepare_assets(output)
frames={'frame.html':('dashboard-price-outlook','Bitcoin Price Outlook','Bitcoin Price (USD)'),
        'seasonal-mtd.html':('dashboard-seasonal-mtd','MTD Returns Comparison','Indexed to Month Start ($)'),
        'seasonal-ytd.html':('dashboard-seasonal-ytd','YTD Returns Comparison','Indexed to Year Start ($)')}
# The dashboard column is 1,120px, narrower than a chart page; a shorter plot keeps the
# chart pages' proportions on desktop. Phones keep the shared mobile height.
DASHBOARD_PLOT_STYLE=('<style>@media (min-width:761px){.embedded .plot-wrap{height:520px;min-height:520px}'
                      '.embedded #legend{max-height:296px}}</style>')
for filename,(chart_id,title,axis) in frames.items():
    page=(WEB/'chart.html').read_text().replace('<body>',f'<body class="embedded compact-legend" data-chart-id="{chart_id}">')
    page=page.replace('<script defer src="@@RENDERER@@"></script>','<script defer src="embed-host.js"></script>')
    values={**assets,'HEAD':f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>'+DASHBOARD_PLOT_STYLE,
            'NAV':'','FOOTER':'','CATEGORY':'MARKET INTELLIGENCE','TITLE':title,'DESCRIPTION':'',
            'DATE':'','DATE_LABEL':'DAILY CLOSE THROUGH','AXIS':'RIGHT: '+axis,'SOURCE':'Data Source: BRK','NOTE':'Daily observations.', 'PAYLOAD':'null'}
    for key,value in values.items():page=page.replace('@@'+key+'@@',value)
    if '@@' in page:raise ValueError('Unresolved embed template placeholder')
    (output/filename).write_text('\n'.join(line.rstrip() for line in page.splitlines())+'\n')
bridge="""// Initialize only from the same-origin dashboard that owns this iframe.
let initialized=false;
addEventListener('message',event=>{
 if(initialized||event.source!==parent||event.origin!==location.origin||event.data?.type!=='ss-chart-init')return;
 const payload=event.data.payload;
 if(payload?.schemaVersion!==2||payload.id!==document.body.dataset.chartId)return;
 initialized=true;document.getElementById('chart-data').textContent=JSON.stringify(payload);
 const script=document.createElement('script');script.src=RENDERER;
 const fail=error=>parent.postMessage({type:'ss-chart-error',id:payload.id,message:error.message||String(error)},location.origin);
 script.onerror=()=>fail(new Error('Shared renderer could not load'));
 script.onload=async()=>{try{
   const chart=await window.SecretSatoshisChart.ready;
   parent.postMessage({type:'ss-chart-ready',id:payload.id,reportDate:chart.payload.reportDate},location.origin);
 }catch(error){fail(error);}};
 document.body.append(script);
});
""".replace('RENDERER',json.dumps(assets['RENDERER']))
(output/'embed-host.js').write_text(bridge)
metrics=['price_close','realized_price','sth_realized_price','realizedcap_multiple_3','90_day_ma_price_close','364_day_ma_price_close','200_week_ma_price_close']
components=output.parent.parent/'components'
components.mkdir(exist_ok=True)
# The dashboard's price chart colours and event lines come only from these two files.
(components/'chart-colors.json').write_text(json.dumps({m:series_color(m) for m in metrics},indent=2)+'\n')
(components/'chart-events.json').write_text(json.dumps(EVENTS,indent=2)+'\n')
provenance={name:hashlib.sha256((WEB/name).read_bytes()).hexdigest() for name in ('renderer.js','chart.html','chart.css','site.css','vendor-lock.json','fonts/JetBrainsMono-400.ttf','fonts/JetBrainsMono-600.ttf','fonts/Syne-700.ttf')}
provenance['scripts/sync-dashboard.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
(output/'source-manifest.json').write_text(json.dumps({'source':'Bitcoin-Chart-Library','files':provenance,'assets':assets,
    'frames':list(frames),'vendored_hashes':{p:hashlib.sha256((output/p).read_bytes()).hexdigest() for p in [*assets.values(),*frames,'embed-host.js']}},indent=2)+'\n')
# Keep only the current content-versioned runtime and theme after a successful sync.
current = {Path(value).name for value in assets.values()}
for pattern in ('renderer.*.js', 'chart.*.css', 'lightweight-charts.*.js'):
    for path in (output/'assets').glob(pattern):
        if path.name not in current:
            path.unlink()
print('Shared chart renderer synced to',output)
