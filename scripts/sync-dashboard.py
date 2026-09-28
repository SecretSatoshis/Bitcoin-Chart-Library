"""Vendor the canonical Chart Library renderer into the Report dashboard. No market data."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chart_build import prepare_assets, WEB
from chart_data import _color
from chart_templates.events import EVENTS

output=Path(sys.argv[1]).resolve()
output.mkdir(parents=True,exist_ok=True)
assets=prepare_assets(output)
page=(WEB/'chart.html').read_text().replace('<body>','<body class="embedded compact-legend">')
page=page.replace('<script defer src="@@RENDERER@@"></script>','<script defer src="embed-host.js"></script>')
values={**assets,'HEAD':'<meta name="viewport" content="width=device-width, initial-scale=1"><title>Bitcoin Price Outlook</title>',
        'NAV':'','FOOTER':'','CATEGORY':'PRICE OUTLOOK','TITLE':'Bitcoin Price Outlook','DESCRIPTION':'',
        'DATE':'','AXIS':'RIGHT: Bitcoin Price (USD)','SOURCE':'Bitview','NOTE':'Daily observations.', 'PAYLOAD':'null'}
for key,value in values.items():page=page.replace('@@'+key+'@@',value)
if '@@' in page:raise ValueError('Unresolved embed template placeholder')
(output/'frame.html').write_text('\n'.join(line.rstrip() for line in page.splitlines())+'\n')
bridge="""// Initialize only from the same-origin dashboard that owns this iframe.
let initialized=false;
addEventListener('message',event=>{
 if(initialized||event.source!==parent||event.origin!==location.origin||event.data?.type!=='ss-chart-init')return;
 const payload=event.data.payload;
 if(payload?.schemaVersion!==2||payload.id!=='dashboard-price-outlook')return;
 initialized=true;document.getElementById('chart-data').textContent=JSON.stringify(payload);
 const script=document.createElement('script');script.src=RENDERER;document.body.append(script);
});
""".replace('RENDERER',json.dumps(assets['RENDERER']))
(output/'embed-host.js').write_text(bridge)
metrics=['price_close','realized_price','sth_realized_price','realizedcap_multiple_3','90_day_ma_price_close','364_day_ma_price_close','200_week_ma_price_close']
components=output.parent.parent/'components'
components.mkdir(exist_ok=True)
# The dashboard component imports this map; it is the only copy the dashboard keeps.
(components/'chart-colors.json').write_text(json.dumps({m:_color(m) for m in metrics},indent=2)+'\n')
(output/'metric-colors.json').unlink(missing_ok=True)
(components/'chart-events.json').write_text(json.dumps(EVENTS,indent=2)+'\n')
(output/'source-manifest.json').write_text(json.dumps({'source':'Bitcoin-Chart-Library','files':{name:hashlib.sha256((WEB/name).read_bytes()).hexdigest() for name in ('renderer.js','chart.html','chart.css','site.css')},'assets':assets},indent=2)+'\n')
# Keep only the current content-versioned runtime and theme after a successful sync.
current = {Path(value).name for value in assets.values()}
for pattern in ('renderer.*.js', 'chart.*.css', 'lightweight-charts.*.js'):
    for path in (output/'assets').glob(pattern):
        if path.name not in current:
            path.unlink()
print('Shared chart renderer synced to',output)
