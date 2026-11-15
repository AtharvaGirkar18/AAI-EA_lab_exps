"""Local web workbench and MCP ClientSession orchestrator."""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).parent.resolve()
PROJECT = ROOT / "sample_developer_project"
ARTIFACTS = ROOT / "artifacts"
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
OLLAMA = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
TOOLS = ["list_files", "read_file", "search_code", "analyze_python", "run_tests"]
RISK = {"list_files": "LOW", "read_file": "LOW", "search_code": "LOW", "analyze_python": "LOW", "run_tests": "MEDIUM"}
ARGUMENTS = {"list_files": {"directory"}, "read_file": {"file_path"}, "search_code": {"query", "file_glob"}, "analyze_python": {"file_path"}, "run_tests": {"test_path", "timeout_seconds"}}
REQUIRED = {"list_files": set(), "read_file": {"file_path"}, "search_code": {"query"}, "analyze_python": {"file_path"}, "run_tests": set()}
QUERIES = json.loads((ROOT / "batch_queries.json").read_text(encoding="utf-8"))


def plan(query: str) -> list[dict]:
    """Use local Qwen for structured planning; retain a safe rule fallback."""
    system = ("You plan tasks for a developer automation lab. Return only JSON: {tasks:[{tool:string,arguments:object,depends_on:array}]}. "
              "Allowed tools: list_files(directory), read_file(file_path), search_code(query,file_glob), analyze_python(file_path), run_tests(test_path,timeout_seconds). "
              "The sample project's only test file is exactly test_calculator.py; always use that exact test_path for run_tests. "
              "Never invent tools. Paths are relative to sample_developer_project. Use only requested read/analysis/test operations. "
              "Independent calls have empty depends_on. run_tests may depend on analysis when requested. If intent is unclear choose list_files.")
    try:
        payload = json.dumps({"model": MODEL, "messages": [{"role": "system", "content": system}, {"role": "user", "content": query}], "stream": False, "format": "json", "options": {"temperature": 0, "num_predict": 350}, "keep_alive": "30m"}).encode()
        req = urllib.request.Request(OLLAMA.rstrip("/") + "/api/chat", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=45) as res:
            obj = json.loads(res.read())
        tasks = json.loads(obj["message"]["content"]).get("tasks", [])
        clean = []
        for task in tasks[:8]:
            name, args = task.get("tool"), task.get("arguments", {})
            if name not in TOOLS or not isinstance(args, dict):
                continue
            if name == "run_tests":
                args = {**args, "test_path": "test_calculator.py"}
            clean.append({"tool": name, "arguments": args, "depends_on": task.get("depends_on", []) if isinstance(task.get("depends_on", []), list) else []})
        if clean:
            return clean
    except Exception:
        pass
    q = query.casefold()
    tasks = []
    if any(s in q for s in ("list", "discover", "files")):
        tasks.append({"tool": "list_files", "arguments": {"directory": "."}, "depends_on": []})
    if "read" in q:
        name = next((x for x in ("README.md", "calculator.py", "arithmetic.py", "app.py", "test_calculator.py") if x.casefold() in q), "README.md")
        tasks.append({"tool": "read_file", "arguments": {"file_path": name}, "depends_on": []})
    if "search" in q or "find" in q:
        term = next((x for x in ("calculate_average", "calculate_square", "ValueError", "ZeroDivisionError", "def ", "import ") if x.casefold() in q), "def ")
        tasks.append({"tool": "search_code", "arguments": {"query": term}, "depends_on": []})
    if "analy" in q or "ast" in q:
        name = next((x for x in ("arithmetic.py", "app.py", "test_calculator.py") if x in q), "calculator.py")
        tasks.append({"tool": "analyze_python", "arguments": {"file_path": name}, "depends_on": []})
    if "test" in q or "pytest" in q:
        tasks.append({"tool": "run_tests", "arguments": {"test_path": "test_calculator.py", "timeout_seconds": 30}, "depends_on": []})
    return tasks or [{"tool": "list_files", "arguments": {"directory": "."}, "depends_on": []}]


def content_value(result):
    blocks = []
    for item in getattr(result, "content", []):
        if getattr(item, "text", None):
            try: blocks.append(json.loads(item.text))
            except ValueError: blocks.append(item.text)
    return blocks[0] if len(blocks) == 1 else blocks


async def execute_workflow(query: str, mode: str, emit=lambda e: None):
    trace_id = "TRACE-" + uuid.uuid4().hex[:8].upper()
    started = time.perf_counter()
    records = []
    async def step(phase, status, detail, **extra):
        emit({"type": "step", "phase": phase, "status": status, "detail": detail, **extra})
    await step("request", "done", "Developer request received and assigned " + trace_id, trace_id=trace_id)
    await step("planner", "active", f"Sending prompt to local Ollama model {MODEL}")
    plan_start = time.perf_counter()
    tasks = await asyncio.to_thread(plan, query)
    planner_ms = round((time.perf_counter() - plan_start) * 1000, 2)
    await step("planner", "done", f"Planner returned {len(tasks)} task(s) in {planner_ms} ms", tasks=tasks)
    unknown = [t["tool"] for t in tasks if t["tool"] not in TOOLS]
    if unknown:
        await step("supervisor", "blocked", "Unknown tool rejected: " + ", ".join(unknown))
        return {"trace_id": trace_id, "error": "Unknown tool", "records": records}
    invalid = [t["tool"] for t in tasks if not isinstance(t.get("arguments"), dict) or not REQUIRED[t["tool"]].issubset(t["arguments"]) or not set(t["arguments"]).issubset(ARGUMENTS[t["tool"]])]
    if invalid:
        await step("supervisor", "blocked", "Invalid or incomplete arguments rejected for: " + ", ".join(invalid))
        return {"trace_id": trace_id, "error": "Invalid tool arguments", "records": records}
    await step("supervisor", "done", f"Approved {len(tasks)} task(s); tool names and argument shapes checked")
    for task in tasks:
        await step("policy", "done", f"{task['tool']} is {RISK[task['tool']]} risk and permitted for this demo")
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")], env=os.environ.copy())
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                discovered = await session.list_tools()
                names = [tool.name for tool in discovered.tools]
                await step("discovery", "done", "ClientSession tools/list discovered: " + ", ".join(names), tools=names)
                approved = [t for t in tasks if t["tool"] in names]
                pending = list(enumerate(approved, 1))
                completed, failed = set(), set()
                while pending:
                    ready = [(i, task) for i, task in pending if all(str(dep) in completed for dep in task.get("depends_on", []))]
                    if not ready:
                        for i, task in pending:
                            item = {"trace_id": trace_id, "task_id": f"TASK-{i:03d}", "tool": task["tool"], "arguments": task["arguments"], "status": "blocked", "result": None, "error": "Unresolved or failed dependency", "duration_ms": 0, "timestamp": datetime.now(timezone.utc).isoformat()}
                            records.append(item); failed.add(task["tool"])
                            await step("execution", "error", f"{item['task_id']} blocked by an unresolved dependency", record=item)
                        break
                    if mode == "parallel" and len(ready) > 1:
                        await step("execution", "active", f"Running {len(ready)} dependency-ready tasks concurrently")
                        results = await asyncio.gather(*(self_call(session, task, trace_id, i) for i, task in ready))
                    else:
                        results = []
                        for i, task in ready:
                            await step("execution", "active", f"Calling {task['tool']} through MCP ClientSession")
                            results.append(await self_call(session, task, trace_id, i))
                    for (i, task), item in zip(ready, results):
                        records.append(item)
                        if item["status"] == "success":
                            completed.update({task["tool"], f"TASK-{i:03d}", str(i)})
                        else:
                            failed.update({task["tool"], f"TASK-{i:03d}", str(i)})
                        await step("execution", item["status"], f"{item['task_id']} {item['tool']} completed in {item['duration_ms']} ms", record=item)
                    pending = [(i, task) for i, task in pending if (i, task) not in ready]
    except Exception as exc:
        await step("execution", "error", "MCP connection failed: " + str(exc))
        records.append({"trace_id": trace_id, "task_id": "TASK-001", "tool": "stdio_client", "status": "error", "error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()})
    await step("validation", "active", "Checking result shape and tool status")
    valid = all(x.get("status") == "success" and x.get("result") is not None for x in records)
    await step("validation", "done" if valid else "warning", f"{sum(x.get('status')=='success' for x in records)}/{len(records)} results passed structural validation")
    ARTIFACTS.mkdir(exist_ok=True)
    with (ARTIFACTS / "mcp_traces.jsonl").open("a", encoding="utf-8") as f:
        for record in records: f.write(json.dumps(record, ensure_ascii=False) + "\n")
    elapsed = round((time.perf_counter()-started)*1000,2)
    report = {"trace_id": trace_id, "query": query, "mode": mode, "model": MODEL, "planner_ms": planner_ms, "total_ms": elapsed, "validated": valid, "records": records}
    (ARTIFACTS / f"{trace_id.lower()}_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    await step("report", "done", f"Trace persisted and report generated in {elapsed} ms", report=report)
    return report


async def self_call(session, task, trace_id, index):
    t0 = time.perf_counter(); error = None; attempts = 0
    while attempts < 2:
        attempts += 1
        try:
            result = await session.call_tool(task["tool"], task["arguments"])
            value = content_value(result)
            if getattr(result, "isError", False): error = str(value)
            status = "error" if error else "success"
            break
        except Exception as exc:
            error = str(exc)
            if attempts < 2:
                await asyncio.sleep(0.1)
            else:
                value, status = {"error": error}, "error"
    return {"trace_id": trace_id, "task_id": f"TASK-{index:03d}", "tool": task["tool"], "arguments": task["arguments"], "status": status, "result": value, "error": error, "attempts": attempts, "duration_ms": round((time.perf_counter()-t0)*1000,2), "timestamp": datetime.now(timezone.utc).isoformat()}


async def performance_benchmark():
    """Compare the same four independent MCP calls sequentially and concurrently."""
    trace_id = "TRACE-" + uuid.uuid4().hex[:8].upper()
    cases = [
        {"tool": "analyze_python", "arguments": {"file_path": "calculator.py"}},
        {"tool": "search_code", "arguments": {"query": "def "}},
        {"tool": "list_files", "arguments": {"directory": "."}},
        {"tool": "read_file", "arguments": {"file_path": "README.md"}},
    ]
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")], env=os.environ.copy())
    sequential, parallel, records = [], [], []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize(); await session.list_tools()
            for iteration in range(1, 6):
                start = time.perf_counter()
                for index, task in enumerate(cases, 1):
                    item = await self_call(session, task, trace_id, index)
                    item["task_id"] = f"RUN-{iteration}-SEQ-TASK-{index:02d}"
                    records.append(item)
                sequential.append(round((time.perf_counter() - start) * 1000, 2))
                start = time.perf_counter()
                batch = await asyncio.gather(*(self_call(session, task, trace_id, index) for index, task in enumerate(cases, 1)))
                for index, item in enumerate(batch, 1): item["task_id"] = f"RUN-{iteration}-PAR-TASK-{index:02d}"
                records.extend(batch)
                parallel.append(round((time.perf_counter() - start) * 1000, 2))
    seq_avg = round(sum(sequential) / len(sequential), 2)
    par_avg = round(sum(parallel) / len(parallel), 2)
    report = {"trace_id": trace_id, "task_count": 4, "run_count": 5, "sequential_ms": sequential, "parallel_ms": parallel,
              "average_sequential_ms": seq_avg, "average_parallel_ms": par_avg,
              "average_time_reduction_percent": round((seq_avg - par_avg) / seq_avg * 100, 2) if seq_avg else 0,
              "average_speedup": round(seq_avg / par_avg, 2) if par_avg else 0,
              "records": records, "timestamp": datetime.now(timezone.utc).isoformat()}
    ARTIFACTS.mkdir(exist_ok=True)
    with (ARTIFACTS / "mcp_traces.jsonl").open("a", encoding="utf-8") as f:
        for record in records: f.write(json.dumps(record, ensure_ascii=False) + "\n")
    (ARTIFACTS / "performance_comparison.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def llm_status():
    try:
        with urllib.request.urlopen(OLLAMA.rstrip("/") + "/api/tags", timeout=2) as res: data = json.loads(res.read())
        models = [m.get("name", "") for m in data.get("models", [])]
        return {"connected": True, "model": MODEL, "available": MODEL in models or any(x.startswith(MODEL.split(":")[0] + ":") for x in models), "models": models}
    except Exception:
        return {"connected": False, "model": MODEL, "available": False, "models": []}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def send_json(self, data, status=200):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path == "/":
            body = (ROOT / "web" / "index.html").read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        elif self.path == "/api/health": self.send_json({"ok": True, "model": MODEL})
        elif self.path == "/api/llm": self.send_json(llm_status())
        elif self.path == "/api/batch": self.send_json({"queries": QUERIES, "suites": ["functional", "security", "recovery", "performance"]})
        elif self.path == "/api/traces":
            path = ARTIFACTS / "mcp_traces.jsonl"; rows = []
            if path.exists():
                for line in path.read_text(encoding="utf-8").splitlines()[-300:]:
                    try: rows.append(json.loads(line))
                    except ValueError: pass
            self.send_json({"records": rows})
        elif self.path == "/api/performance":
            path = ARTIFACTS / "performance_comparison.json"
            self.send_json(json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"report": None})
        else: self.send_json({"error": "Not found"}, 404)
    def do_POST(self):
        try: payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        except Exception: self.send_json({"error": "Invalid JSON"}, 400); return
        if self.path == "/api/workflow":
            query = str(payload.get("query", "")).strip(); mode = "parallel" if payload.get("mode") == "parallel" else "sequential"
            if not query or len(query) > 700: self.send_json({"error": "Enter a request between 1 and 700 characters."}, 400); return
            self.send_response(200); self.send_header("Content-Type", "application/x-ndjson; charset=utf-8"); self.send_header("Cache-Control", "no-cache"); self.send_header("Connection", "close"); self.end_headers()
            def emit(event):
                self.wfile.write((json.dumps(event, ensure_ascii=False) + "\n").encode()); self.wfile.flush()
            try:
                report = asyncio.run(execute_workflow(query, mode, emit)); emit({"type": "complete", "report": report})
            except Exception as exc: emit({"type": "fatal", "error": str(exc)})
        elif self.path == "/api/tool":
            name, args = payload.get("tool"), payload.get("arguments", {})
            if name not in TOOLS or not isinstance(args, dict): self.send_json({"error": "Tool not approved"}, 400); return
            async def call():
                params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")], env=os.environ.copy())
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize(); tools = await session.list_tools()
                        if name not in [x.name for x in tools.tools]: raise ValueError("Tool unavailable")
                        result = await session.call_tool(name, args)
                        return {"result": content_value(result), "isError": result.isError}
            try: self.send_json(asyncio.run(call()))
            except Exception as exc: self.send_json({"error": str(exc)}, 400)
        elif self.path == "/api/performance":
            try: self.send_json(asyncio.run(performance_benchmark()))
            except Exception as exc: self.send_json({"error": str(exc)}, 500)
        else: self.send_json({"error": "Not found"}, 404)


if __name__ == "__main__":
    print(f"Developer Automation Lab at http://127.0.0.1:8000 · Ollama model {MODEL}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", int(os.getenv("PORT", "8000"))), Handler).serve_forever()
