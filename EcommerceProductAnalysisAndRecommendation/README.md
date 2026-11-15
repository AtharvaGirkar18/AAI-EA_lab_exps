# Agentic Commerce Lab · Experiment 05

A local, self-contained Agentic AI lab project for the **E-commerce Product Analysis & Recommendation Pipeline** experiment. It decomposes multi-item shopping requests, searches and filters products by category, compares candidates, optimizes complete carts under a shared budget, ranks recommendations, and records validation and human approval. The UI also demonstrates parallel and sequential search, workflow traces, authorization checks, and experiment measurements.

The Planner Agent can use the local Ollama model **qwen2.5:7b-instruct** to decompose natural-language requirements. Ollama is optional: if it is unavailable or times out, the rule-based planner keeps the workflow usable. Automated batch suites use deterministic planning so test results do not depend on model startup or inference speed. Successful model plans are cached for the current server process.

## Run locally

Requires Python 3.10 or newer. No package installation or API key is needed.

```powershell
python server.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Pages

- **Overview** — enter natural-language shopping requirements, choose sequential or parallel searches, review ranked cart recommendations, validation checks, agent trace, and record human approval.
- **Agent workflow** — inspect the complete per-agent execution trace, structured messages, and run metrics.
- **Batch tests** — run the experiment checks in order: functional, failure, security, performance. Each suite displays its checks and fills an observation sheet.
- **MCP tools** — discover registered tools and try role-based authorization checks.

## MCP-style interface

This experiment asks for a **basic MCP-style** tool integration and explicitly distinguishes it from the complete MCP protocol. The app includes a simplified JSON-RPC endpoint at `POST /mcp` supporting `initialize`, `tools/list`, and `tools/call`, plus tool registration and role-based authorization. It is an educational implementation, not a full MCP server. Example tool discovery:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list"}
```

Example tool call:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_products","role":"search","arguments":{"category":"laptop"}}}
```

The JSON-RPC endpoint is `http://127.0.0.1:8000/mcp`. Registered tools: `search_products` (search), `filter_products` (filter), `compare_products` (comparison), and `validate_recommendation` (validator). `supervisor` is the coordinating role.

## API

- `GET /api/health` — service status
- `GET /api/products` — sample catalog
- `GET /api/tools` — tool registry
- `POST /api/workflow` — execute a workflow (`query`, `mode`; optional `deterministic: true` for model-independent runs)
- `POST /api/approval` — record an `approved` or `rejected` human decision

The catalog in `products.json` contains 100 product listings across laptops, headphones, mice, monitors, smartphones, and keyboards. Product prices were gathered from Croma listing pages and stored as a dated snapshot; retailer prices and availability can change. The `source_url` and `price_checked_at` fields are included with each row. Product ratings are demo benchmark values for the ranking experiment and are not represented as verified review scores. `GET /api/dataset-summary` reports the actual row count, field names, category counts, price ranges, and average demo ratings. Ranking scores and cost units are teaching/demo metrics, not live marketplace information or monetary cost. Parallel search uses three independent catalog partitions and synchronizes results before filtering. Set OLLAMA_URL or OLLAMA_MODEL before starting the server to change the local endpoint or model name.

The catalog was compiled from these online listings: [Croma laptops](https://www.croma.com/clp/laptops-for-home-use), [headphones](https://www.croma.com/l/wireless-headphones-for-all-devices-0afz00a.html), [mice](https://www.croma.com/computers-tablets/computer-and-laptop-accessories/mice/c/580), [monitors](https://www.croma.com/clp/monitors-between-20-to-24.9-inches), [smartphones under ₹20,000](https://www.croma.com/clp/5g-phones-under-20000), [smartphones ₹20,000–₹30,000](https://www.croma.com/clp/best-mobile-phones-between-20000-to-30000), and [keyboards](https://www.croma.com/clp/keyboards-for-desktops).
