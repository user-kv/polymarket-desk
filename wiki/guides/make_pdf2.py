"""Render GUIDE2.md (dense 2-strategy playbook) -> PDF + HTML."""
import sys, datetime
from pathlib import Path
import markdown
from xhtml2pdf import pisa

HERE = Path(__file__).parent
SRC = HERE / "GUIDE2.md"
OUT = HERE / "Weather-and-Sports-Value-Betting-Dense-Guide.pdf"
HTML_OUT = HERE / "Weather-and-Sports-Value-Betting-Dense-Guide.html"

body = markdown.markdown(SRC.read_text(encoding="utf-8"),
                         extensions=["extra", "sane_lists", "toc", "nl2br"])

CSS = """
@page { size: a4 portrait; margin: 1.7cm 1.6cm;
  @frame footer_frame { -pdf-frame-content: footerContent; bottom: 0.9cm; left: 1.6cm; right: 1.6cm; height: 1cm; } }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10.5pt; line-height: 1.42; color: #1a1a1a; }
h1 { font-size: 18pt; color: #0b3d63; border-bottom: 2px solid #0b3d63; padding-bottom: 3px; page-break-before: always; }
h2 { font-size: 13pt; color: #14507a; margin-top: 13px; border-bottom: 1px solid #cdddea; padding-bottom: 2px; }
h3 { font-size: 11.5pt; color: #20618f; margin-top: 10px; }
p { margin: 5px 0; }
ul, ol { margin: 4px 0 4px 2px; }
li { margin: 2px 0; }
hr { border: none; border-top: 1px solid #d9d9d9; margin: 10px 0; }
blockquote { background: #eef5fb; border-left: 4px solid #2b7cc0; margin: 8px 0; padding: 6px 10px; color: #143b56; }
code { font-family: Courier, monospace; background: #f2f2f2; font-size: 9.5pt; padding: 1px 2px; }
table { border-collapse: collapse; width: 100%; margin: 7px 0; }
th, td { border: 1px solid #bbb; padding: 3px 5px; font-size: 9pt; text-align: left; vertical-align: top; }
th { background: #e8f0f7; }
strong { color: #111; }
#footerContent { font-size: 8pt; color: #888; text-align: center; }
"""

today = datetime.date.today().strftime("%B %Y")
title = f"""
<div style="page-break-after: always; text-align:center;">
  <div style="margin-top: 4.5cm;"></div>
  <div style="font-size: 27pt; color:#0b3d63; font-weight:bold; line-height:1.2;">The Two-Strategy Playbook</div>
  <div style="margin-top: 0.8cm; font-size: 15pt; color:#14507a;">Weather Trading &nbsp;+&nbsp; Sports Value-Betting</div>
  <div style="margin-top: 0.5cm; font-size: 12pt; color:#555;">Dense Edition &mdash; every line is signal</div>
  <div style="margin-top: 3cm; font-size: 11pt; color:#777;">{today}</div>
  <div style="margin-top: 2.5cm; font-size: 9pt; color:#a33; max-width: 12cm; margin-left:auto; margin-right:auto;">
    Educational only &mdash; not financial advice. Prediction-market trading is risky, zero-sum, and
    legally restricted in many places including Australia. Never trade money you cannot afford to lose.</div>
</div>"""

html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div id="footerContent">Two-Strategy Playbook &mdash; page <pdf:pagenumber> of <pdf:pagecount></div>
{title}{body}</body></html>"""

HTML_OUT.write_text(html.replace("<pdf:pagenumber>","").replace("<pdf:pagecount>","")
    .replace('<div id="footerContent">Two-Strategy Playbook &mdash; page  of </div>',""), encoding="utf-8")
print(f"OK -> {HTML_OUT} ({HTML_OUT.stat().st_size//1024} KB)")
with open(OUT, "wb") as f:
    res = pisa.CreatePDF(html, dest=f, encoding="utf-8")
print(("ERRORS: "+str(res.err)) if res.err else f"OK -> {OUT} ({OUT.stat().st_size//1024} KB)")
