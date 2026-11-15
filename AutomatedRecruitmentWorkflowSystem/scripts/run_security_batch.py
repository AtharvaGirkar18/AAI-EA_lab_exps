"""Run only the prompt-injection suite and refresh those rows in lab evidence."""
import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server

httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{httpd.server_address[1]}"
cases = json.loads((ROOT / "batch_queries.json").read_text(encoding="utf-8"))
ids = [case["id"] for case in cases if case["action"] == "security"]
payload = json.dumps({"ids": ids}).encode()
request = urllib.request.Request(base + "/api/batch/run", data=payload, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(request, timeout=300) as response:
    results = json.loads(response.read())["results"]

evidence_path = ROOT / "artifacts" / "lab_evidence.json"
evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
evidence["batch_cases"] = cases
evidence["batch_results"] = [row for row in evidence["batch_results"] if not row["id"].startswith("M")] + results
evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ids": ids, "passed": sum(bool(row["passed"]) for row in results), "results": results}, ensure_ascii=False, indent=2))
if len(results) != len(ids) or any(not row["passed"] for row in results):
    raise SystemExit(1)
