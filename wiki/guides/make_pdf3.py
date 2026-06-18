"""Render GUIDE3.md (beginner-friendly 2-strategy guide) -> PDF + HTML."""
import datetime
from pathlib import Path
import markdown
from xhtml2pdf import pisa

HERE = Path(__file__).parent
SRC = HERE / "GUIDE3.md"
OUT = HERE / "Weather-and-Sports-Beginner-Guide.pdf"
HTML_OUT = HERE / "Weather-and-Sports-Beginner-Guide.html"

body = markdown.markdown(SRC.read_text(encoding="utf-8"),
                         extensions=["extra", "sane_lists", "toc", "nl2br"])

CSS = """
@page { size: a4 portrait; margin: 1.9cm 1.8cm;
  @frame footer_frame { -pdf-frame-content: footerContent; bottom: 1.0cm; left: 1.8cm; right: 1.8cm; height: 1cm; } }
body { font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #1a1a1a; }
h1 { font-size: 19pt; color: #0b3d63; border-bottom: 2px solid #0b3d63; padding-bottom: 4px; page-break-before: always; }
h2 { font-size: 14pt; color: #14507a; margin-top: 15px; }
h3 { font-size: 12pt; color: #20618f; margin-top: 11px; }
p { margin: 6px 0; }
ul, ol { margin: 5px 0 5px 3px; }
li { margin: 3px 0; }
hr { border: none; border-top: 1px solid #d9d9d9; margin: 13px 0; }
blockquote { background: #eef7ee; border-left: 4px solid #4a9d4a; margin: 9px 0; padding: 8px 12px; color: #1f4f1f; }
strong { color: #111; }
em { color: #333; }
#footerContent { font-size: 8pt; color: #888; text-align: center; }
"""

today = datetime.date.today().strftime("%B %Y")
title = f"""
<div style="page-break-after: always; text-align:center;">
  <div style="margin-top: 4.5cm;"></div>
  <div style="font-size: 26pt; color:#0b3d63; font-weight:bold; line-height:1.25;">Weather &amp; Sports Betting<br/>on Prediction Markets</div>
  <div style="margin-top: 1cm; font-size: 15pt; color:#14507a;">Explained for a Complete Beginner</div>
  <div style="margin-top: 0.5cm; font-size: 12pt; color:#555;">Every word in plain English &mdash; no background needed</div>
  <div style="margin-top: 3cm; font-size: 11pt; color:#777;">{today}</div>
  <div style="margin-top: 2.5cm; font-size: 9pt; color:#a33; max-width: 12cm; margin-left:auto; margin-right:auto;">
    Educational only &mdash; not financial advice. Betting is risky and restricted in many places
    including Australia. Never bet money you can't afford to lose.</div>
</div>"""

html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div id="footerContent">Weather &amp; Sports Beginner Guide &mdash; page <pdf:pagenumber> of <pdf:pagecount></div>
{title}{body}</body></html>"""

HTML_OUT.write_text(html.replace("<pdf:pagenumber>","").replace("<pdf:pagecount>","")
    .replace('<div id="footerContent">Weather &amp; Sports Beginner Guide &mdash; page  of </div>',""), encoding="utf-8")
print(f"OK -> {HTML_OUT} ({HTML_OUT.stat().st_size//1024} KB)")
with open(OUT, "wb") as f:
    res = pisa.CreatePDF(html, dest=f, encoding="utf-8")
print(("ERRORS: "+str(res.err)) if res.err else f"OK -> {OUT} ({OUT.stat().st_size//1024} KB)")
