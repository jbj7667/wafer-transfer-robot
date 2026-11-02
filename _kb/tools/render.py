import pymupdf, sys
from pathlib import Path
root = Path(sys.argv[1])
pdf = next(root.rglob("*운영계획*.pdf"))
d = pymupdf.open(str(pdf))
for i in (7, 8, 10, 11):
    d[i - 1].get_pixmap(dpi=120).save(f"rule_p{i}.png")
print(pdf.name)
