"""FastMCP server exposing safe developer tools over stdio."""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).parent / "sample_developer_project"
mcp = FastMCP("Developer Automation Server")


def safe_project_path(file_path: str = ".") -> Path:
    candidate = (ROOT / file_path).resolve()
    if candidate != ROOT.resolve() and ROOT.resolve() not in candidate.parents:
        raise ValueError("Path outside project")
    return candidate


@mcp.tool()
def list_files(directory: str = ".") -> dict:
    """List project files relative to the sample project root."""
    path = safe_project_path(directory)
    if not path.is_dir():
        raise ValueError("Directory not found")
    return {"files": sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in path.rglob("*") if p.is_file())[:500]}


@mcp.tool()
def read_file(file_path: str) -> dict:
    """Read a UTF-8 text file inside the sample project."""
    path = safe_project_path(file_path)
    if not path.is_file():
        raise ValueError("File not found")
    if path.stat().st_size > 200_000:
        raise ValueError("File exceeds 200 KB limit")
    return {"file_path": file_path, "content": path.read_text(encoding="utf-8")}


@mcp.tool()
def search_code(query: str, file_glob: str = "*.py") -> dict:
    """Search text in project files matching a simple glob."""
    if not query or len(query) > 300:
        raise ValueError("Query must contain 1–300 characters")
    if "/" in file_glob or "\\" in file_glob or ".." in file_glob:
        raise ValueError("Invalid file glob")
    matches = []
    for path in ROOT.rglob(file_glob):
        if path.is_file():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if query.casefold() in line.casefold():
                    matches.append({"file": str(path.relative_to(ROOT)).replace("\\", "/"), "line": number, "text": line.strip()[:240]})
                    if len(matches) >= 200:
                        return {"matches": matches, "truncated": True}
    return {"matches": matches, "truncated": False}


@mcp.tool()
def analyze_python(file_path: str) -> dict:
    """Parse Python with AST and report functions, classes, imports, and syntax errors."""
    path = safe_project_path(file_path)
    if not path.is_file() or path.suffix != ".py":
        raise ValueError("Expected an existing Python file")
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as error:
        return {"file_path": file_path, "valid": False, "syntax_error": str(error), "functions": [], "classes": [], "imports": []}
    return {
        "file_path": file_path, "valid": True,
        "functions": [{"name": node.name, "line": node.lineno, "args": [arg.arg for arg in node.args.args]} for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))],
        "classes": [{"name": node.name, "line": node.lineno} for node in ast.walk(tree) if isinstance(node, ast.ClassDef)],
        "imports": sorted({alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}),
        "line_count": len(source.splitlines()),
    }


@mcp.tool()
def run_tests(test_path: str = "test_calculator.py", timeout_seconds: int = 30) -> dict:
    """Run pytest for a test file in the sample project with a strict timeout."""
    path = safe_project_path(test_path)
    if path.suffix != ".py" or not path.is_file() or not path.name.startswith("test_"):
        raise ValueError("Only existing test_*.py files can be run")
    timeout = max(1, min(int(timeout_seconds), 60))
    # Prefer the project's venv so pytest and its installed plugins match the
    # dependencies used to run this experiment. Fall back to the current
    # interpreter when the project has not been set up with a local venv.
    venv_python = ROOT.parent / ".venv" / "Scripts" / "python.exe"
    python = str(venv_python) if venv_python.is_file() else sys.executable
    try:
        proc = subprocess.run([python, "-m", "pytest", "-q", str(path)], cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        return {"return_code": proc.returncode, "passed": proc.returncode == 0, "stdout": proc.stdout[-12000:], "stderr": proc.stderr[-4000:]}
    except subprocess.TimeoutExpired as error:
        return {"return_code": None, "passed": False, "timeout": True, "stdout": (error.stdout or "")[-4000:], "stderr": "pytest timed out"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
