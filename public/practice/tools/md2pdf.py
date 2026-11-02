"""Minimal markdown -> A4 PDF (headings, paragraphs, lists, tables). usage: python -I md2pdf.py in.md out.pdf"""
import sys, re, html
import pymupdf

src, dst = sys.argv[1], sys.argv[2]
FONTDIR = "C:/Windows/Fonts"


def inline(s):
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return s


out, lines, i = [], open(src, encoding="utf8").read().split("\n"), 0
while i < len(lines):
    ln = lines[i]
    if ln.startswith("#"):
        n = len(ln) - len(ln.lstrip("#"))
        out.append(f"<h{n}>{inline(ln[n:].strip())}</h{n}>")
    elif ln.startswith("|"):
        rows = []
        while i < len(lines) and lines[i].startswith("|"):
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                rows.append(cells)
            i += 1
        t = "<table>"
        for k, r in enumerate(rows):
            tag = "th" if k == 0 else "td"
            t += "<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in r) + "</tr>"
        out.append(t + "</table>")
        continue
    elif re.match(r"^(- |\d+\. )", ln):
        ordered = ln[0].isdigit()
        items = []
        while i < len(lines) and re.match(r"^(- |\d+\. )", lines[i]):
            items.append(re.sub(r"^(- |\d+\. )", "", lines[i]))
            i += 1
        tag = "ol" if ordered else "ul"
        out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
        continue
    elif ln.strip():
        out.append(f"<p>{inline(ln)}</p>")
    i += 1

css = """
@font-face { font-family: mg; src: url(malgun.ttf); }
@font-face { font-family: mg; font-weight: bold; src: url(malgunbd.ttf); }
body { font-family: mg; font-size: 9.5pt; line-height: 1.35; }
h1 { font-size: 17pt; } h2 { font-size: 12.5pt; margin-top: 10pt; } h3 { font-size: 11pt; }
table { border-collapse: collapse; margin: 4pt 0; }
th, td { border: 0.5pt solid #555; padding: 2pt 4pt; font-size: 8.5pt; }
th { background-color: #e6e6e6; }
code { font-family: mg; }
li { margin-bottom: 2pt; }
"""
story = pymupdf.Story("<html><body>" + "\n".join(out) + "</body></html>", user_css=css,
                      archive=pymupdf.Archive(FONTDIR))
W, H = 595.28, 841.89
mar = 42
w = pymupdf.DocumentWriter(dst)
more = 1
while more:
    dev = w.begin_page(pymupdf.Rect(0, 0, W, H))
    more, _ = story.place(pymupdf.Rect(mar, mar, W - mar, H - mar))
    story.draw(dev)
    w.end_page()
w.close()
print("ok", dst)
