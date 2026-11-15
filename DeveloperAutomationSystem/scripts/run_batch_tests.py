import json, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8000'
OUT = ROOT / 'artifacts' / 'batch_test_observed_results.json'
QUERIES = json.loads((ROOT / 'batch_queries.json').read_text(encoding='utf-8'))

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))

def post(path, payload, timeout=120):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(BASE + path, data=data, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode('utf-8')
    if path == '/api/workflow':
        events = [json.loads(line) for line in body.splitlines() if line.strip()]
        report = next((e['report'] for e in reversed(events) if e.get('type') == 'complete'), None)
        planner = next((e.get('tasks', []) for e in events if e.get('phase') == 'planner' and e.get('status') == 'done'), [])
        return {'report': report, 'planner_tasks': planner, 'events': [{'type':e.get('type'),'phase':e.get('phase'),'status':e.get('status'),'detail':e.get('detail')} for e in events if e.get('type') == 'step']}
    return json.loads(body)

results = {'checked_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'health': get('/api/health'), 'llm': get('/api/llm'), 'queries': {}, 'examples': {}, 'benchmarks': {}}
examples = {
 'Q1': ('Analyze calculator.py with Python AST and search the project for all function definitions. Validate the analysis and search results; do not run tests.', 'sequential'),
 'Q2': ('In parallel, list all files in the sample developer project and read README.md. Validate that both tool results were returned.', 'parallel'),
}
for key, (query, mode) in examples.items():
    print(f'RUN {key} {mode}', flush=True)
    results['examples'][key] = {'query':query, 'mode':mode, **post('/api/workflow', {'query':query,'mode':mode})}
    rep = results['examples'][key].get('report') or {}
    print(f"DONE {key} trace={rep.get('trace_id')} valid={rep.get('validated')} tools={[x.get('tool')+':'+x.get('status') for x in rep.get('records',[])]}", flush=True)

for q in QUERIES:
    qid = q['id']
    print(f'RUN {qid}', flush=True)
    try:
        if qid in ('P01','P02'):
            data = post('/api/performance', {})
            results['benchmarks'][qid] = data
            results['queries'][qid] = {'query':q['query'], 'suite':q['suite'], 'benchmark':data}
            print(f"DONE {qid} trace={data.get('trace_id')} calls={len(data.get('records',[]))} avg_seq={data.get('average_sequential_ms')} avg_par={data.get('average_parallel_ms')}", flush=True)
        else:
            mode = 'parallel' if qid == 'F09' else 'sequential'
            result = post('/api/workflow', {'query':q['query'], 'mode':mode})
            results['queries'][qid] = {'query':q['query'], 'suite':q['suite'], 'mode':mode, **result}
            rep = result.get('report') or {}
            print(f"DONE {qid} trace={rep.get('trace_id')} valid={rep.get('validated')} tools={[x.get('tool')+':'+x.get('status') for x in rep.get('records',[])]}", flush=True)
    except Exception as e:
        results['queries'][qid] = {'query':q['query'], 'suite':q['suite'], 'error':repr(e)}
        print(f'ERROR {qid} {e!r}', flush=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print('SAVED', OUT, flush=True)
