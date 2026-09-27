"""Generate the static Secret Satoshis Chart Library without a browser or Plotly."""
import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from chart_build import ROOT, build_pack
from chart_definitions import REPORT_CSV_DIR


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv-dir',default=REPORT_CSV_DIR)
    parser.add_argument('--output',type=Path,default=ROOT/'Charts')
    parser.add_argument('--serve',action='store_true')
    parser.add_argument('--port',type=int,default=8767)
    args=parser.parse_args()
    print(json.dumps(build_pack(args.csv_dir,args.output),indent=2),flush=True)
    if args.serve:
        handler=partial(SimpleHTTPRequestHandler,directory=str(args.output.resolve()))
        with ThreadingHTTPServer(('127.0.0.1',args.port),handler) as server:
            print(f'Preview: http://127.0.0.1:{args.port}/',flush=True)
            try:server.serve_forever()
            except KeyboardInterrupt:pass


if __name__=='__main__':main()
