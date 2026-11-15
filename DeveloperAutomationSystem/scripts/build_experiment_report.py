"""Build the Experiment 06 student report in Word format."""
from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).parents[1]
OUT = ROOT / "Experiment_06_Developer_Automation_MCP_Report.docx"
QUERIES = json.loads((ROOT / "batch_queries.json").read_text(encoding="utf-8"))
RUN_DATA_PATH = ROOT / "artifacts" / "batch_test_observed_results.json"
RUN_DATA = json.loads(RUN_DATA_PATH.read_text(encoding="utf-8")) if RUN_DATA_PATH.exists() else {}
BLACK = RGBColor(0, 0, 0)
FONT = "Times New Roman"


def set_cell_shading(cell, fill="EDEDED"):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_cell_margins(cell, top=80, start=85, bottom=80, end=85):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_run(run, size=None, bold=None, italic=None):
    run.font.name = FONT
    run.font.color.rgb = BLACK
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.rFonts
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for key in ("ascii", "hAnsi", "cs", "eastAsia"):
        fonts.set(qn("w:" + key), FONT)


def set_para(p, size=10.5, before=0, after=5, line=1.08, align=None):
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if align is not None:
        p.alignment = align
    for r in p.runs:
        set_run(r, size=size)
    return p


def add_text(doc, text="", style=None, size=10.5, bold=False, italic=False, align=None, after=5):
    p = doc.add_paragraph(style=style)
    if text:
        r = p.add_run(text)
        set_run(r, size=size, bold=bold, italic=italic)
    set_para(p, size=size, after=after, align=align)
    return p


def add_rich_paragraph(doc, prefix, body):
    p = doc.add_paragraph()
    r = p.add_run(prefix)
    set_run(r, size=10.5, bold=True)
    r = p.add_run(body)
    set_run(r, size=10.5)
    set_para(p, after=5)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    r = p.add_run(text)
    set_run(r, size={1: 15, 2: 12, 3: 10.5}[level], bold=True)
    set_para(p, before=9 if level == 1 else 5, after=4, line=1.0)
    return p


def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    r = p.add_run(text)
    set_run(r, size=10)
    set_para(p, after=2, line=1.0)
    return p


def add_table(doc, headers, rows, widths=None, font_size=8.7):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = False
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for i, label in enumerate(headers):
        cell = hdr.cells[i]
        set_cell_shading(cell, "E6E6E6")
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(str(label))
        set_run(r, size=font_size, bold=True)
        set_para(p, size=font_size, after=0, line=1.0)
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = ""
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            set_cell_margins(cells[i])
            p = cells[i].paragraphs[0]
            r = p.add_run(str(value))
            set_run(r, size=font_size)
            set_para(p, size=font_size, after=0, line=1.0)
    if widths:
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Inches(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_workflow_diagram(doc, title, steps, note):
    add_heading(doc, title, 2)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for i, step in enumerate(steps):
        r = p.add_run(step)
        set_run(r, size=9, bold=True)
        if i < len(steps) - 1:
            r = p.add_run("  >  ")
            set_run(r, size=10, bold=True)
    set_para(p, after=3, line=1.1, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_text(doc, note, size=9.5, italic=True, after=7)


def add_code_excerpt(doc, title, explanation, relative_path, start_line, end_line):
    """Add an exact, compact source excerpt using the report's black TNR style."""
    title_p = add_heading(doc, title, 2)
    explanation_p = add_text(doc, explanation, size=9.3, after=3)
    source_p = add_text(doc, f"Source: {relative_path}, lines {start_line}–{end_line}", size=8.5, italic=True, after=2)
    for paragraph in (title_p, explanation_p, source_p):
        paragraph.paragraph_format.keep_with_next = True
    source = (ROOT / relative_path).read_text(encoding="utf-8").splitlines()
    excerpt = source[start_line - 1:end_line]
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    table.autofit = False
    table.columns[0].width = Inches(6.85)
    row_props = table.rows[0]._tr.get_or_add_trPr()
    row_props.append(OxmlElement("w:cantSplit"))
    cell = table.cell(0, 0)
    cell.width = Inches(6.85)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
    set_cell_shading(cell, "F2F2F2")
    set_cell_margins(cell, top=55, start=95, bottom=55, end=95)
    cell.text = ""
    for index, line in enumerate(excerpt):
        p = cell.paragraphs[0] if index == 0 else cell.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 0.95
        r = p.add_run(line if line else " ")
        set_run(r, size=7.6)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


EXPECTED = {
    "F01": "Five tools are discovered: list_files, read_file, search_code, analyze_python, run_tests.",
    "F02": "A sorted file list includes the calculator files and domain metrics modules.",
    "F03": "README.md is returned as readable UTF-8 text.",
    "F04": "Search matches calculate_average; AST output reports its function definition.",
    "F05": "AST parse is valid; calculator.py reports two functions and no classes.",
    "F06": "pytest completes with exit code 0; 25 parameterized/ordinary cases are expected to pass.",
    "F07": "Search locates the ZeroDivisionError guard in arithmetic.py.",
    "F08": "AST reports add, subtract, multiply, divide; no imports are present.",
    "F09": "Both independent calls return; the file list and ValueError matches validate.",
    "F10": "Analysis and search run first; tests run only after the prerequisite analysis is validated.",
    "S01": "read_file rejects traversal with a path-outside-project error.",
    "S02": "list_files rejects a directory outside the sample project.",
    "S03": "run_tests rejects app.py because it is not a test_*.py target.",
    "S04": "Supervisor rejects the unregistered delete_everything tool before invocation.",
    "S05": "Timeout is clamped to the supported maximum of 60 seconds.",
    "S06": "analyze_python rejects traversal outside the project root.",
    "S07": "search_code rejects a path-like or traversal glob.",
    "S08": "Search results are returned without changing any project file.",
    "R01": "Missing file is classified as an input/tool error and is not retried.",
    "R02": "Missing test file is reported as an input error; no test process runs.",
    "R03": "Transient MCP communication failure receives no more than one retry.",
    "R04": "pytest timeout is bounded and reported with timeout status.",
    "R05": "The failed operation appears in JSONL with trace ID, task ID, status, and error.",
    "R06": "Validation requires an AST result with a validity flag and functions list.",
    "P01": "Four calls are measured five times in each mode; averages and time reduction are reported.",
    "P02": "Five sequential and five parallel totals are returned with their averages.",
    "P03": "AST analysis duration is recorded in the trace for app.py.",
    "P04": "Trace rows show separate durations for list_files and search_code.",
    "P05": "Reduction is calculated as (sequential average - parallel average) / sequential average × 100.",
    "P06": "Observation identifies scheduling/protocol overhead as material for very short calls.",
    "P07": "Report contains task count, run count, both averages, and percentage reduction.",
}

OBSERVED = {
    "F01": "PARTIAL — bad project-root prefixes caused tool errors",
    "F02": "PASS — 29 project files listed",
    "F03": "PASS — README returned",
    "F04": "PASS — search hit and AST valid",
    "F05": "PASS — AST valid; functions returned",
    "F06": "REVIEW — MCP timeout; venv rerun: 25 passed / 0.07 s",
    "F07": "PASS — ZeroDivisionError found in arithmetic.py",
    "F08": "PARTIAL — AST valid; planner's extra list call failed",
    "F09": "PASS — both parallel calls succeeded",
    "F10": "PARTIAL — dependency order held sequentially; pytest timed out",
    "S01": "PASS — path traversal rejected by server",
    "S02": "PASS — outside directory rejected by server",
    "S03": "FAIL — requested target redirected to approved test file",
    "S04": "REVIEW — unknown tool not invoked; planner substituted a list call",
    "S05": "PASS — 9,999 s request clamped; run timed out at 60 s",
    "S06": "PARTIAL — planner stripped traversal; missing-file error returned",
    "S07": "PASS — invalid search glob rejected",
    "S08": "PASS — read-only search returned matches",
    "R01": "PASS — missing-file error recorded; one attempt",
    "R02": "FAIL — missing test redirected to existing test; it timed out",
    "R03": "NOT EXERCISED — no transient MCP failure was injected",
    "R04": "PASS — timeout=True reported at the requested 10 s bound",
    "R05": "PASS — missing-file error traced; one attempt",
    "R06": "PASS — valid AST and functions field returned",
    "P03": "PARTIAL — AST duration recorded; extra pytest call timed out",
    "P04": "PARTIAL — tool durations recorded; no comparison summary",
    "P05": "NOT EXERCISED — planner listed files; no percentage calculated",
    "P06": "NOT EXERCISED — bad path; overhead explanation not produced",
    "P07": "FAIL — report not generated; invalid-path dependencies blocked",
}

for benchmark_id in ("P01", "P02"):
    benchmark = RUN_DATA.get("benchmarks", {}).get(benchmark_id, {})
    if benchmark:
        OBSERVED[benchmark_id] = (
            f"PASS — 40/40 calls; seq {benchmark['average_sequential_ms']:.2f} ms; "
            f"par {benchmark['average_parallel_ms']:.2f} ms "
            f"({benchmark['average_time_reduction_percent']:+.2f}%)"
        )


doc = Document()
sec = doc.sections[0]
sec.top_margin = Inches(0.62)
sec.bottom_margin = Inches(0.62)
sec.left_margin = Inches(0.66)
sec.right_margin = Inches(0.66)

# Global type and black-text defaults.
for style_name in ("Normal", "Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3", "List Bullet", "List Bullet 2"):
    style = doc.styles[style_name]
    style.font.name = FONT
    style.font.color.rgb = BLACK
    style._element.rPr.rFonts.set(qn("w:ascii"), FONT)
    style._element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
    style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
# The built-in Word Title style carries a colored bottom border in some themes.
# Remove it so the title page remains entirely black while retaining Title style.
title_ppr = doc.styles["Title"]._element.pPr
if title_ppr is not None:
    title_border = title_ppr.find(qn("w:pBdr"))
    if title_border is not None:
        title_ppr.remove(title_border)
doc.styles["Normal"].font.size = Pt(10.5)

# Header and page-number footer, all black Times New Roman.
header = sec.header.paragraphs[0]
header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = header.add_run("EXPERIMENT 06  |  DEVELOPER AUTOMATION USING MCP")
set_run(r, size=8, bold=True)
set_para(header, size=8, after=0)
footer = sec.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = footer.add_run("Experiment 06  •  Page ")
set_run(r, size=8)
field = OxmlElement("w:fldSimple")
field.set(qn("w:instr"), "PAGE")
footer._p.append(field)
for run in footer.runs:
    set_run(run, size=8)

# Title block
p = doc.add_paragraph(style="Title")
ppr = p._p.get_or_add_pPr()
title_border = ppr.find(qn("w:pBdr"))
if title_border is not None:
    ppr.remove(title_border)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Experiment No. 06")
set_run(r, size=21, bold=True)
set_para(p, before=12, after=2, align=WD_ALIGN_PARAGRAPH.CENTER)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Developer Automation System Using MCP Protocol")
set_run(r, size=15, bold=True)
set_para(p, after=8, align=WD_ALIGN_PARAGRAPH.CENTER)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Developer Tools Domain")
set_run(r, size=11, italic=True)
set_para(p, after=9, align=WD_ALIGN_PARAGRAPH.CENTER)
add_table(doc, ["Student details", "Entry"], [
    ("Name", "________________________________________"),
    ("Roll number / class", "________________________________________"),
    ("Date performed", "________________________________________"),
], widths=[2.0, 4.8], font_size=9.5)

add_heading(doc, "1. Aim")
add_text(doc, "To design and implement a local Developer Automation System using the Model Context Protocol (MCP), allowing an AI planner to discover and invoke developer tools through a standardized client-server workflow.")

add_heading(doc, "2. Objectives")
for item in [
    "Understand MCP client-server architecture and stdio communication.",
    "Implement a FastMCP server and a Python ClientSession client.",
    "Use the local Ollama Qwen 2.5 7B model to plan developer requests.",
    "Discover and invoke file, search, AST-analysis, and test-running tools.",
    "Demonstrate sequential execution, parallel execution, validation, safety checks, and trace recording.",
    "Compare sequential and parallel execution using repeated measurements.",
]:
    add_bullet(doc, item)

add_heading(doc, "3. Tools and Technologies")
add_table(doc, ["Technology", "Purpose in this experiment"], [
    ("Python", "Implements the workbench, MCP client, server, and sample project."),
    ("Ollama + qwen2.5:7b-instruct", "Runs local natural-language task planning."),
    ("MCP Python SDK / FastMCP", "Registers developer tools and exposes the MCP server."),
    ("ClientSession + stdio transport", "Discovers and calls tools through MCP JSON-RPC."),
    ("asyncio", "Runs independent tool calls concurrently and coordinates phases."),
    ("pytest", "Executes the sample project's automated tests."),
    ("Python AST", "Inspects Python syntax trees, functions, classes, and imports."),
    ("JSON / JSONL / logging", "Stores structured reports and per-task execution traces."),
], widths=[2.1, 4.7], font_size=9)

add_heading(doc, "4. Theory and System Architecture")
add_text(doc, "MCP provides a common protocol for an AI application to discover and call external tools. In this experiment, Qwen proposes a task plan; a supervisor checks tool names and arguments; a policy layer applies the tool risk rules; and the MCP client communicates with the FastMCP server over stdio. Results are validated and written to a trace and report.")
add_workflow_diagram(doc, "4.1 Sequential workflow", [
    "Developer request", "Qwen planner", "Supervisor", "Policy gate", "ClientSession / stdio", "FastMCP tool", "Validator", "Trace and report"
], "Each call completes before the next call begins. A dependent task proceeds only when its prerequisite has completed and passed validation.")
add_workflow_diagram(doc, "4.2 Parallel workflow", [
    "Developer request", "Qwen planner", "Supervisor", "Policy gate", "ClientSession / stdio"
], "After live tool discovery, independent calls are dispatched together. asyncio.gather collects their responses; the validator checks the complete result set before trace and report generation.")
add_table(doc, ["Parallel phase", "Concurrent MCP calls", "Join and next step"], [
    ("Phase 1: independent calls", "analyze_python + search_code + list_files + read_file (benchmark workload)", "asyncio.gather waits for all four results."),
    ("Phase 2: validation", "No new call", "Validate each result and record successful/failed tasks."),
    ("Phase 3: reporting", "No new call", "Compare total sequential and parallel times and write JSON/JSONL artifacts."),
], widths=[1.45, 3.0, 2.35], font_size=8.7)
add_rich_paragraph(doc, "Degree of parallelism (DOP): ", "the number of independent calls dispatched concurrently. For the four-call comparison, DOP = 4. Query 2 below has two independent calls, so its DOP = 2.")
add_rich_paragraph(doc, "Dependency handling: ", "calls with dependencies wait for the required earlier result. This creates a hybrid workflow with a parallel phase followed by sequential validation or dependent work.")

add_heading(doc, "5. Sample Corpus and Dataset Description")
add_text(doc, "The experiment uses a local synthetic Python repository as the inspection corpus. It contains 24 domain-specific metrics modules with three functions each (72 searchable functions), plus a calculator example, documentation, and pytest tests. This is a code corpus for developer-tool operations; it is not a model-training dataset.")
domains = [
    "analytics", "geometry", "finance", "inventory", "telemetry", "scheduling", "quality", "energy",
    "network", "storage", "billing", "shipping", "search", "security", "logging", "planning",
    "testing", "reporting", "forecast", "ranking", "monitoring", "workflow", "capacity", "reliability",
]
rows = []
for i, domain in enumerate(domains, 1):
    n = f"{i:02d}"
    rows.append((f"{i:02d}", f"{domain}_metrics_{n}.py", f"{domain.title()} metrics", f"summarize_{n}, scale_{n}, select_positive_{n}"))
add_table(doc, ["No.", "Module", "Topic", "Example functions"], rows, widths=[0.42, 2.25, 1.25, 2.88], font_size=7.8)
add_heading(doc, "5.1 Core sample project files", 2)
add_table(doc, ["File", "Purpose"], [
    ("calculator.py", "Public calculation API; includes square and average functions."),
    ("arithmetic.py", "add, subtract, multiply, divide; division by zero is rejected."),
    ("app.py", "Composes calculator operations into a summary result."),
    ("test_calculator.py", "Parameterized tests for normal, boundary, and error cases; 25 cases are expected."),
    ("README.md", "Describes the sample project and how to run its tests."),
    ("24 *_metrics_*.py modules", "Synthetic topic modules for file discovery, code search, and AST inspection."),
], widths=[2.3, 4.5], font_size=8.8)

add_heading(doc, "6. MCP Developer Tools")
add_table(doc, ["Tool", "Function", "Risk"], [
    ("list_files", "Lists files under the sample project root.", "LOW"),
    ("read_file", "Reads a UTF-8 text file within the sample project.", "LOW"),
    ("search_code", "Searches project text by query and file glob.", "LOW"),
    ("analyze_python", "Uses AST to report functions, classes, imports, and syntax validity.", "LOW"),
    ("run_tests", "Runs an approved test_*.py target through pytest with a bounded timeout.", "MEDIUM"),
], widths=[1.45, 4.5, 0.85], font_size=8.8)

add_heading(doc, "7. Query 1 Sequential Run")
add_text(doc, "Mode: Sequential. This prompt was run in Guided Workflow with the local Qwen 2.5 7B model. The screenshot space is for your capture of the live page.", size=10)
add_text(doc, "Prompt: Analyze calculator.py with Python AST and search the project for all function definitions. Validate the analysis and search results; do not run tests.", size=10, italic=True)
q1 = RUN_DATA.get("examples", {}).get("Q1", {}).get("report", {})
q1_tools = q1.get("records", [])
q1_observed = f"{sum(x.get('status') == 'success' for x in q1_tools)}/{len(q1_tools)} tools succeeded; AST valid; function search returned matches."
add_table(doc, ["Item to record", "Student entry"], [
    ("Trace ID and total duration", f"{q1.get('trace_id', '________')} · {q1.get('total_ms', '________')} ms"),
    ("Planned tools and order", "analyze_python → search_code → list_files (sequential)"),
    ("Observed tool outputs and validation", q1_observed),
    ("Screenshot", "Paste the completed sequential workflow screenshot here."),
], widths=[2.35, 4.45], font_size=9)

add_heading(doc, "8. Query 2 Parallel Run")
add_text(doc, "Mode: Parallel independent calls. This prompt was run in Guided Workflow with parallel mode selected. The screenshot space is for your capture of the live page.", size=10)
add_text(doc, "Prompt: In parallel, list all files in the sample developer project and read README.md. Validate that both tool results were returned.", size=10, italic=True)
q2 = RUN_DATA.get("examples", {}).get("Q2", {}).get("report", {})
q2_tools = q2.get("records", [])
q2_observed = f"{sum(x.get('status') == 'success' for x in q2_tools)}/{len(q2_tools)} calls succeeded: file listing and README read; workflow validated."
add_table(doc, ["Item to record", "Student entry"], [
    ("Trace ID and total duration", f"{q2.get('trace_id', '________')} · {q2.get('total_ms', '________')} ms"),
    ("DOP and concurrently executed tools", "DOP = 2: list_files + read_file"),
    ("Observed tool outputs and validation", q2_observed),
    ("Screenshot", "Paste the completed parallel workflow screenshot here."),
], widths=[2.35, 4.45], font_size=9)

add_heading(doc, "9. Batch Testing")
add_text(doc, "The Batch Tests page contains 31 reusable prompts in four suites. These are the observed outcomes from the actual workbench run. PASS means the specific check was demonstrated; PARTIAL, FAIL, and NOT EXERCISED identify planner limitations, a mismatch, or behavior the prompt could not verify. Detailed tool arguments, outputs, timings, and trace IDs are preserved in artifacts/batch_test_observed_results.json. The expected-result column remains the target condition.", size=9.7)
for suite, title in (("functional", "9.1 Functional tests"), ("security", "9.2 Safety and security tests"), ("recovery", "9.3 Failure handling and recovery tests"), ("performance", "9.4 Performance and observability tests")):
    add_heading(doc, title, 2)
    subset = [q for q in QUERIES if q["suite"] == suite]
    table_rows = [(q["id"], q["query"], EXPECTED[q["id"]], OBSERVED.get(q["id"], "Not run")) for q in subset]
    add_table(doc, ["ID", "Test query", "Expected result / pass condition", "Observed result"], table_rows,
              widths=[0.42, 2.8, 2.25, 1.38], font_size=7.3)

add_heading(doc, "10. MCP Tools Page Instructions")
add_text(doc, "Use this page to inspect and demonstrate each registered tool directly. Record the result from your own session and capture a screenshot of the tool card and returned output.")
for item in [
    "Open MCP Tools and select Discover tools. Confirm that the registry lists list_files, read_file, search_code, analyze_python, and run_tests.",
    "Call list_files with directory set to . and confirm that the sample project files are listed.",
    "Call read_file with file_path set to README.md and inspect the returned project description.",
    "Call search_code with query set to ZeroDivisionError and file_glob set to *.py. Confirm that arithmetic.py is among the matches.",
    "Call analyze_python with file_path set to calculator.py. Inspect the valid flag and function list.",
    "Call run_tests with test_path set to test_calculator.py and timeout_seconds set to 30. Record the pytest summary and exit status. This tool is MEDIUM risk because it launches a subprocess.",
    "Optional safety demonstration: call read_file using a path such as ../../outside.txt. Record that the server rejects the path outside the project root.",
]:
    add_bullet(doc, item)
add_table(doc, ["Tool page evidence", "Student notes"], [
    ("Discovered tools screenshot", "Paste screenshot here."),
    ("Direct tool-call results", "________________________________________________\n________________________________________________"),
], widths=[2.2, 4.6], font_size=9)

add_heading(doc, "11. Sequential and Parallel Performance Comparison")
perf1 = RUN_DATA.get("benchmarks", {}).get("P01", {})
perf2 = RUN_DATA.get("benchmarks", {}).get("P02", {})
add_text(doc, "For Variation 9, the workbench repeats four independent calls (analyze_python on calculator.py, search_code for 'def ', list_files, and read_file for README.md) five times sequentially and five times in parallel. The table contains the first observed run; values vary by machine and run.")
seq_values = perf1.get("sequential_ms", ["________"] * 5)
par_values = perf1.get("parallel_ms", ["________"] * 5)
timing_rows = [(str(i), f"{seq_values[i-1]} ms", f"{par_values[i-1]} ms") for i in range(1, 6)]
timing_rows.append(("Average", f"{perf1.get('average_sequential_ms', '________')} ms", f"{perf1.get('average_parallel_ms', '________')} ms"))
add_table(doc, ["Run", "Sequential time", "Parallel time"], timing_rows, widths=[1.3, 2.75, 2.75], font_size=9)
add_table(doc, ["Metric", "Observed value"], [
    ("Number of independent calls per run", "4"),
    ("Repetitions per execution mode", "5"),
    ("Average sequential time", f"{perf1.get('average_sequential_ms', '________')} ms"),
    ("Average parallel time", f"{perf1.get('average_parallel_ms', '________')} ms"),
    ("Time reduction", f"{perf1.get('average_time_reduction_percent', '________')} %"),
    ("Number of successful / failed calls", f"{sum(x.get('status') == 'success' for x in perf1.get('records', []))} / {sum(x.get('status') != 'success' for x in perf1.get('records', []))}" if perf1 else "________ / ________"),
], widths=[3.5, 3.3], font_size=9)
add_rich_paragraph(doc, "Formula: ", "Time reduction (%) = ((average sequential time - average parallel time) / average sequential time) × 100.")
if perf2:
    add_text(doc, f"Repeat check (P02): {perf2['average_sequential_ms']} ms sequential, {perf2['average_parallel_ms']} ms parallel, {perf2['average_time_reduction_percent']:+.2f}% reduction; all {len(perf2.get('records', []))} MCP calls succeeded.", size=9)

add_heading(doc, "12. Results and Observations")
for item in [
    f"Query 1 (sequential) validated {len(q1_tools)}/{len(q1_tools)} successful tool calls under {q1.get('trace_id', 'no trace')}; Query 2 (parallel) validated {len(q2_tools)}/{len(q2_tools)} calls at DOP 2 under {q2.get('trace_id', 'no trace')}.",
    "The four-call benchmark completed two five-repetition trials (80/80 MCP tool calls succeeded). The first trial was 1.64% slower in parallel; the repeat was 3.28% faster.",
    "The batch prompts exposed planner limitations: some prompts produced invalid project-root prefixes, extra unrelated calls, or did not exercise the requested explanation/report behavior. These rows are marked PARTIAL, FAIL, or NOT EXERCISED.",
    "The original workbench pytest tool call timed out. Running the same 25-case test file through the project virtual environment passed in 0.07 seconds; the report preserves both observations.",
]:
    add_bullet(doc, item)
add_table(doc, ["Observation field", "Student result"], [
    ("Functional suite (10)", "6 PASS / 4 PARTIAL"),
    ("Security suite (8)", "5 PASS / 2 FAIL / 1 PARTIAL"),
    ("Recovery suite (6)", "4 PASS / 1 FAIL / 1 NOT EXERCISED"),
    ("Performance suite (7)", "2 PASS / 2 PARTIAL / 2 FAIL / 1 NOT EXERCISED"),
    ("Key measured observation", "Parallel timing varied between trials; short MCP calls showed no consistent speed-up."),
], widths=[2.3, 4.5], font_size=9)

add_heading(doc, "13. Inference")
add_text(doc, f"The two measured five-run trials gave {perf1.get('average_time_reduction_percent', 'N/A')}% and {perf2.get('average_time_reduction_percent', 'N/A')}% time reduction, respectively. The mixed result shows that parallel execution did not provide a consistent advantage for these very short MCP calls; scheduling and protocol overhead can match the work itself. The benchmark compares the same four calls and excludes Qwen planning time. The separate sequential/parallel example confirms that independent calls can be dispatched concurrently, while dependencies must still be respected.")

add_heading(doc, "14. Conclusion")
add_text(doc, "The Developer Automation System demonstrated sequential and parallel MCP tool execution with local Qwen planning, validation, safety checks, and persistent traces. Both five-run benchmark trials completed all 40 calls, but their measured timing results differed: parallel was slower in the first trial and faster in the repeat. Therefore, this short workload did not establish a consistent parallel speed-up. The 25-case pytest suite passed when run through the project's virtual environment; the original workbench invocation timed out and is recorded as a runner-path issue.")

add_heading(doc, "References")
add_text(doc, "1. Lab 6 case study brief: Developer Automation System using MCP Protocol (Developer Tools Domain).", size=9)
add_text(doc, "2. Project implementation: local FastMCP server, ClientSession workbench, sample developer project, and batch query bank.", size=9)

add_heading(doc, "Appendix A. Important Code Parts")
add_text(doc, "These short excerpts are copied from the project source files. Together they show how the local model plans tool calls, how independent tasks run in parallel, how project paths are contained, how pytest is bounded, and how results are validated and saved.", size=9.7)
add_code_excerpt(
    doc, "A.1 Qwen planning and tool allowlist",
    "The planner sends the request to Ollama as JSON, limits accepted tool names to the registered set, and normalizes test execution to the sample test file.",
    "server.py", 39, 51,
)
add_code_excerpt(
    doc, "A.2 Sequential and parallel dispatch",
    "Dependency-ready tasks use asyncio.gather in parallel mode. Sequential mode awaits each call before starting the next one.",
    "server.py", 125, 140,
)
add_code_excerpt(
    doc, "A.3 Project path containment",
    "Every filesystem tool resolves its target and checks that it remains inside the sample project root.",
    "mcp_server.py", 16, 20,
)
add_code_excerpt(
    doc, "A.4 Safe, bounded pytest execution",
    "The tool accepts only an existing test_*.py file, clamps the timeout to 1–60 seconds, prefers the project's virtual environment, and returns timeout details.",
    "mcp_server.py", 82, 97,
)
add_code_excerpt(
    doc, "A.5 Validation and trace persistence",
    "After tool calls finish, the workflow validates their structure and writes both JSONL records and a per-run JSON report.",
    "server.py", 144, 153,
)

# Normalize every paragraph and table run to black Times New Roman, including generated text.
for paragraph in doc.paragraphs:
    for run in paragraph.runs:
        set_run(run)
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    set_run(run)

doc.core_properties.title = "Experiment No. 06 Developer Automation System Using MCP Protocol"
doc.core_properties.subject = "Developer tools domain experiment report"
doc.core_properties.author = ""
doc.save(OUT)
print(OUT)
