import json, urllib.request
p={'tool':'run_tests','arguments':{'test_path':'test_calculator.py','timeout_seconds':30}}
r=urllib.request.Request('http://127.0.0.1:8000/api/tool',data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
with urllib.request.urlopen(r,timeout=45) as x: print(x.read().decode())
