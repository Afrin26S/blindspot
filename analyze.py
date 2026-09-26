#!/usr/bin/env python3
"""
BlindSpot analyzer -- deterministic pass (no AI / no Bobcoins used).

Computes, for a Python repo:
  - cyclomatic complexity per function (via radon)
  - git "churn" (how often each file changed recently)
  - a rough "has this got a test?" signal
  - a combined risk_score per function
  - a basic file tree + likely entry points (for the architecture step)

Writes analysis.json in the current directory. Bob only needs to read this
JSON (small, structured) instead of re-deriving any of these numbers itself
-- that's what keeps Bobcoin usage low.

Requirements:
    pip install radon --break-system-packages

Usage:
    python analyze.py /path/to/repo
"""
import subprocess
import json
import os
import re
import sys
from pathlib import Path


def run(cmd, cwd):
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        return result.stdout
    except FileNotFoundError:
        print(f"Warning: command not found: {cmd[0]}", file=sys.stderr)
        return ""


def get_complexity(repo_path):
    """Use radon to get cyclomatic complexity per function/method, per file."""
    out = run(["radon", "cc", "-j", "-s", "."], repo_path)
    try:
        return json.loads(out) if out.strip() else {}
    except json.JSONDecodeError:
        print("Warning: could not parse radon output. Is radon installed?", file=sys.stderr)
        return {}


def get_churn(repo_path, last_n_commits=200):
    """Count how many times each file was touched in recent git history."""
    out = run(["git", "log", f"-{last_n_commits}", "--name-only", "--pretty=format:"], repo_path)
    churn = {}
    for line in out.splitlines():
        line = line.strip()
        if line and line.endswith(".py"):
            churn[line] = churn.get(line, 0) + 1
    return churn


def find_test_referenced_identifiers(repo_path):
    """
    Rough heuristic: gather every identifier that appears anywhere in a
    file whose name contains 'test'. If a function's name shows up in a
    test file, we treat it as 'probably has some test coverage'.
    This is deliberately simple -- good enough to prioritize risk, not a
    real coverage tool.
    """
    referenced = set()
    for root, _dirs, files in os.walk(repo_path):
        if any(skip in root for skip in (".git", "venv", "__pycache__", "node_modules")):
            continue
        for f in files:
            if "test" in f.lower() and f.endswith(".py"):
                path = Path(root) / f
                try:
                    text = path.read_text(errors="ignore")
                except Exception:
                    continue
                for ident in re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", text):
                    referenced.add(ident)
    return referenced


def find_entry_points(repo_path):
    """Rough heuristic for likely entry points."""
    candidates = []
    names = ("main.py", "app.py", "manage.py", "wsgi.py", "__main__.py", "run.py", "cli.py")
    for name in names:
        for p in Path(repo_path).rglob(name):
            if ".git" not in p.parts and "venv" not in p.parts:
                candidates.append(str(p.relative_to(repo_path)))
    return candidates


def build_file_tree(repo_path, max_depth=4):
    tree = []
    base = Path(repo_path)
    for p in sorted(base.rglob("*.py")):
        parts = p.relative_to(base).parts
        if any(part.startswith(".") or part in ("venv", "node_modules", "__pycache__") for part in parts):
            continue
        if len(parts) <= max_depth:
            tree.append(str(p.relative_to(base)))
    return tree


def normalize(values):
    if not values:
        return {}
    lo, hi = min(values.values()), max(values.values())
    span = (hi - lo) or 1
    return {k: (v - lo) / span for k, v in values.items()}


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze.py /path/to/repo")
        sys.exit(1)

    repo_path = os.path.abspath(sys.argv[1])
    if not os.path.isdir(repo_path):
        print(f"Error: {repo_path} is not a directory")
        sys.exit(1)

    print(f"Analyzing {repo_path} ...")

    complexity_data = get_complexity(repo_path)
    churn = get_churn(repo_path)
    tested_identifiers = find_test_referenced_identifiers(repo_path)
    tree = build_file_tree(repo_path)
    entries = find_entry_points(repo_path)

    functions = []
    for filepath, blocks in complexity_data.items():
        rel = os.path.relpath(filepath, repo_path) if os.path.isabs(filepath) else filepath
        for block in blocks:
            name = block.get("name", "unknown")
            functions.append({
                "file": rel,
                "name": name,
                "complexity": block.get("complexity", 0),
                "line": block.get("lineno", 0),
                "churn": churn.get(rel, 0),
                "has_test_reference": name in tested_identifiers,
            })

    if not functions:
        print("Warning: no functions found. Check the repo path and that it contains .py files.")

    complexities = {f"{f['file']}::{f['name']}": f["complexity"] for f in functions}
    churns = {f"{f['file']}::{f['name']}": f["churn"] for f in functions}
    norm_complexity = normalize(complexities)
    norm_churn = normalize(churns)

    for f in functions:
        key = f"{f['file']}::{f['name']}"
        base_score = 0.6 * norm_complexity.get(key, 0) + 0.4 * norm_churn.get(key, 0)
        risk_score = base_score * (1.5 if not f["has_test_reference"] else 1.0)
        f["risk_score"] = round(risk_score, 4)

    functions.sort(key=lambda x: x["risk_score"], reverse=True)

    result = {
        "repo_path": repo_path,
        "file_tree": tree,
        "entry_points": entries,
        "top_risky_functions": functions[:15],
        "total_functions_analyzed": len(functions),
    }

    out_path = Path("analysis.json")
    out_path.write_text(json.dumps(result, indent=2))

    top = functions[0] if functions else None
    print(f"Wrote {out_path.resolve()}")
    print(f"  {len(functions)} functions analyzed across {len(tree)} files")
    if top:
        print(f"  Riskiest: {top['file']}::{top['name']} (score {top['risk_score']})")


if __name__ == "__main__":
    main()
