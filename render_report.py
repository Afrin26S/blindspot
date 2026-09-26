#!/usr/bin/env python3
"""
BlindSpot report renderer -- deterministic pass (no AI / no Bobcoins used).

Combines analysis.json (already computed by analyze.py) with the small
markdown files Bob writes (ARCHITECTURE.md, DOC_DRIFT.md) into one
self-contained reports/index.html. No fetch(), no server needed -- it's
all inlined, so you can just double-click the file to open it.

Usage (run from the folder that contains analysis.json):
    python render_report.py
"""
import json
import html
import re
from pathlib import Path


def load_text(path, default=""):
    p = Path(path)
    return p.read_text() if p.exists() else default


def extract_mermaid(markdown_text):
    match = re.search(r"```mermaid\n(.*?)```", markdown_text, re.DOTALL)
    return match.group(1).strip() if match else ""


def markdown_to_html_basic(md_text):
    """Tiny markdown->html converter -- headers, paragraphs, bullet lists.
    Good enough for a generated report; not a general-purpose parser."""
    md_text = re.sub(r"```mermaid.*?```", "", md_text, flags=re.DOTALL)
    lines = md_text.splitlines()
    out = []
    in_list = False
    for line in lines:
        if line.strip().startswith("```"):
            continue
        if line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.strip().startswith(("- ", "* ")):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{html.escape(line.strip()[2:])}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            if line.strip():
                out.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def main():
    analysis = json.loads(load_text("analysis.json", "{}"))
    arch_md = load_text("ARCHITECTURE.md")
    drift_md = load_text("DOC_DRIFT.md")

    mermaid_code = extract_mermaid(arch_md) or "graph TD\n  A[No diagram generated yet]"
    arch_html = markdown_to_html_basic(arch_md) or "<p><em>Run the architecture step in Bob first.</em></p>"
    drift_html = markdown_to_html_basic(drift_md) if drift_md else "<p><em>Not generated in this run (optional step).</em></p>"

    rows = ""
    for f in analysis.get("top_risky_functions", []):
        rows += f"""<tr>
      <td>{html.escape(str(f.get('file','')))}</td>
      <td>{html.escape(str(f.get('name','')))}</td>
      <td>{f.get('complexity','')}</td>
      <td>{f.get('churn','')}</td>
      <td>{'✅' if f.get('has_test_reference') else '❌'}</td>
      <td><strong>{f.get('risk_score','')}</strong></td>
    </tr>"""

    out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BlindSpot Report</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.0/mermaid.min.js"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          max-width: 960px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; line-height: 1.5; }}
  h1 {{ border-bottom: 3px solid #4f46e5; padding-bottom: 8px; }}
  h2 {{ margin-top: 8px; color: #312e81; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; font-size: 14px; }}
  th {{ background: #f4f4f8; }}
  tr:hover {{ background: #fafafa; }}
  section {{ margin-bottom: 48px; }}
  .mermaid {{ text-align: center; margin-top: 16px; }}
  .meta {{ color: #666; font-size: 14px; }}
  code {{ background: #f4f4f8; padding: 2px 6px; border-radius: 4px; }}
</style>
</head>
<body>
  <h1>🔎 BlindSpot Report</h1>
  <p class="meta">Analyzed <strong>{analysis.get('total_functions_analyzed', 0)}</strong> functions in
     <code>{html.escape(str(analysis.get('repo_path', '')))}</code></p>

  <section>
    <h2>Architecture</h2>
    {arch_html}
    <div class="mermaid">
{mermaid_code}
    </div>
  </section>

  <section>
    <h2>Risk Report &mdash; Riskiest Functions</h2>
    <table>
      <tr><th>File</th><th>Function</th><th>Complexity</th><th>Git Churn</th><th>Has Test?</th><th>Risk Score</th></tr>
      {rows}
    </table>
  </section>

  <section>
    <h2>Docs vs Code Drift</h2>
    {drift_html}
  </section>

  <script>mermaid.initialize({{ startOnLoad: true, theme: 'default' }});</script>
</body>
</html>"""

    Path("reports").mkdir(exist_ok=True)
    Path("reports/index.html").write_text(out, encoding="utf-8")
    print("Wrote reports/index.html -- open it directly in your browser.")


if __name__ == "__main__":
    main()
