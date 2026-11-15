import json, urllib.request, urllib.error, threading, time, sys
from time import perf_counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
base='http://127.0.0.1:8001'
def post(path,obj):
    data=json.dumps(obj).encode(); req=urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=300) as r:return r.read().decode()
evidence={}
query='Evaluate candidate C0001. Show the validation result, each weighted score contribution, the overall score, the proposed review status, and the notification draft. Explain that the status is a recommendation for human review, not a final hiring decision.'
try:
    # Start an in-process workbench when no instance is already listening.
    # This keeps the evidence run self-contained and ensures MCP subprocesses use this interpreter.
    try:
        with urllib.request.urlopen(base+'/api/health',timeout=1): pass
    except Exception:
        from http.server import ThreadingHTTPServer
        import server as workbench
        httpd=ThreadingHTTPServer(('127.0.0.1',8001),workbench.Handler)
        threading.Thread(target=httpd.serve_forever,daemon=True).start()
        for _ in range(30):
            try:
                with urllib.request.urlopen(base+'/api/health',timeout=1): break
            except Exception: time.sleep(.2)
    evidence['query2_prompt']=query
    evidence['query2_events']=[json.loads(x) for x in post('/api/workflow',{'query':query}).splitlines() if x.strip()]
    with urllib.request.urlopen(base+'/api/batch',timeout=30) as r: cases=json.load(r)['cases']
    evidence['batch_cases']=cases
    evidence['batch_results']=json.loads(post('/api/batch/run',{'ids':[x['id'] for x in cases]}))['results']
    start=perf_counter()
    process=json.loads(post('/api/batch/run',{'ids':['X01']}))['results'][0]['result']
    elapsed_ms=(perf_counter()-start)*1000
    evidence['full_dataset_timing']={'elapsed_ms':round(elapsed_ms,2),'valid_records':process['valid'],'milliseconds_per_valid_record':round(elapsed_ms/process['valid'],4),'measurement':'End-to-end HTTP + MCP subprocess batch invocation on this machine.'}
except Exception as e:
    evidence['error']=repr(e)
Path('artifacts').mkdir(exist_ok=True)
Path('artifacts/lab_evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
if evidence.get('error'): raise RuntimeError(evidence['error'])
