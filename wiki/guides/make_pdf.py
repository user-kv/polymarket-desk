"""Convert GUIDE.md -> styled PDF (GUIDE.pdf) using markdown + xhtml2pdf (pure Python)."""
import sys, datetime
from pathlib import Path
import markdown
from xhtml2pdf import pisa

HERE = Path(__file__).parent
SRC = HERE / "GUIDE.md"
OUT = HERE / "Prediction-Markets-Complete-Guide.pdf"

md_text = SRC.read_text(encoding="utf-8")
body = markdown.markdown(md_text, extensions=["extra", "sane_lists", "toc", "nl2br"])

CSS = """
@page {
  size: a4 portrait;
  margin: 2.0cm 1.9cm 2.0cm 1.9cm;
  @frame footer_frame {
    -pdf-frame-content: footerContent;
    bottom: 1.0cm; left: 1.9cm; right: 1.9cm; height: 1cm;
  }
}
body { font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #1a1a1a; }
h1 { font-size: 20pt; color: #0b3d63; border-bottom: 2px solid #0b3d63; padding-bottom: 4px;
     page-break-before: always; margin-top: 6px; }
h2 { font-size: 15pt; color: #14507a; margin-top: 16px; border-bottom: 1px solid #cdddea; padding-bottom: 2px; }
h3 { font-size: 12.5pt; color: #20618f; margin-top: 12px; }
p { margin: 6px 0; }
strong { color: #111; }
ul, ol { margin: 6px 0 6px 4px; }
li { margin: 3px 0; }
hr { border: none; border-top: 1px solid #d9d9d9; margin: 14px 0; }
blockquote {
  background: #eef5fb; border-left: 4px solid #2b7cc0; margin: 10px 0; padding: 8px 12px;
  color: #143b56; font-size: 10.5pt;
}
code { font-family: Courier, monospace; background: #f2f2f2; font-size: 10pt; padding: 1px 3px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; }
th, td { border: 1px solid #bbb; padding: 4px 6px; font-size: 9.5pt; text-align: left; }
th { background: #e8f0f7; }
#footerContent { font-size: 8pt; color: #888; text-align: center; }
a { color: #14507a; text-decoration: none; }
"""

# Title page (first page, before any h1's forced page break)
today = datetime.date.today().strftime("%B %Y")
title_html = f"""
<div style="page-break-after: always; text-align:center;">
  <div style="margin-top: 5cm;"></div>
  <div style="font-size: 30pt; color:#0b3d63; font-weight:bold; line-height:1.2;">
    The Complete Beginner's Guide to<br/>Trading Prediction Markets
  </div>
  <div style="margin-top: 1cm; font-size: 14pt; color:#14507a;">
    Weather &middot; Copy Trading &middot; Building Your Own Bot
  </div>
  <div style="margin-top: 0.6cm; font-size: 12pt; color:#555;">
    Explained from absolute zero &mdash; understand everything before risking a dollar
  </div>
  <div style="margin-top: 3cm; font-size: 11pt; color:#777;">{today}</div>
  <div style="margin-top: 2.5cm; font-size: 9.5pt; color:#a33; max-width: 12cm; margin-left:auto; margin-right:auto;">
    Educational only &mdash; not financial advice. Prediction-market trading is risky, zero-sum,
    and legally restricted in many places including Australia. Never trade money you cannot
    afford to lose.
  </div>
</div>
"""

html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div id="footerContent">Prediction Markets Guide &mdash; page <pdf:pagenumber> of <pdf:pagecount></div>
{title_html}
{body}
</body></html>"""

# Also write a self-contained HTML (renders emoji perfectly; browser Print->PDF as backup)
HTML_OUT = HERE / "Prediction-Markets-Complete-Guide.html"
html_web = html.replace("<pdf:pagenumber>", "").replace("<pdf:pagecount>", "").replace(
    '<div id="footerContent">Prediction Markets Guide &mdash; page  of </div>', "")
HTML_OUT.write_text(html_web, encoding="utf-8")
print(f"OK -> {HTML_OUT} ({HTML_OUT.stat().st_size//1024} KB)")

with open(OUT, "wb") as f:
    result = pisa.CreatePDF(html, dest=f, encoding="utf-8")

if result.err:
    print(f"PDF generation had {result.err} error(s)")
    sys.exit(1)
print(f"OK -> {OUT} ({OUT.stat().st_size//1024} KB)")
