"""Render a Markdown report to a styled, self-contained HTML page.

Usage: python report/build_status.py <in.md> <out.html> [title]
"""

import sys

import markdown

src, out = sys.argv[1:3]
title = sys.argv[3] if len(sys.argv) > 3 else "Safety Gates Status Report"
body = markdown.markdown(open(src).read(), extensions=["tables"])
# wide tables scroll inside their own container, never the page
body = body.replace("<table>", '<div class="tablewrap"><table>').replace("</table>", "</table></div>")

page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400&display=swap" rel="stylesheet">
<style>
:root {{
  /* same family as the results page: steel-blue accent on cool neutrals, a plain memo layout */
  --bg: #f6f7f9; --surface: #ffffff; --ink: #1c2230; --muted: #5c6678; --line: #d9dee7; --accent: #2f5d8a;
  --display: "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif;
  --body: "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif;
  --mono: "IBM Plex Mono", Consolas, Menlo, monospace;
  color-scheme: light;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #141922; --surface: #1c2330; --ink: #e6eaf1; --muted: #9aa5b8; --line: #2e3745; --accent: #7fb0e0;
    color-scheme: dark;
  }}
}}
:root[data-theme="dark"] {{
  --bg: #141922; --surface: #1c2330; --ink: #e6eaf1; --muted: #9aa5b8; --line: #2e3745; --accent: #7fb0e0;
  color-scheme: dark;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; }}
body {{ background: var(--bg); color: var(--ink); font-family: var(--body); font-size: 16px; line-height: 1.55; padding: 0 16px 64px; }}
main {{ max-width: 820px; margin: 0 auto; }}
h1, h2, h3 {{ font-family: var(--display); text-wrap: balance; line-height: 1.2; }}
h1 {{ font-size: 1.9rem; font-weight: 600; margin: 40px 0 4px; }}
h1 + p {{ color: var(--muted); margin-top: 0; }}
h1 + h3 {{ color: var(--muted); font-weight: 500; font-size: 1.05rem; margin: 0 0 6px; }}
h2 {{ font-size: 1.35rem; font-weight: 600; margin: 44px 0 10px; padding-top: 22px; border-top: 1px solid var(--line); }}
h3 {{ font-size: 1.05rem; font-weight: 600; margin: 26px 0 6px; color: var(--accent); }}
p, li {{ max-width: 68ch; }}
ul, ol {{ padding-left: 22px; }}
li {{ margin: 4px 0; }}
code {{ font-family: var(--mono); font-size: 0.86em; background: var(--surface); border: 1px solid var(--line); padding: 0 4px; border-radius: 3px; }}
.tablewrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; margin: 12px 0; background: var(--surface); }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.93rem; }}
th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; font-variant-numeric: tabular-nums; }}
th {{ font-weight: 600; color: var(--muted); font-size: 0.84rem; }}
tr:last-child td {{ border-bottom: none; }}
a {{ color: var(--accent); }}
a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
</style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""
open(out, "w").write(page)
print(len(page), "bytes")
