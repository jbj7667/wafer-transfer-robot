"""PDF 크기 줄이기: 사용한 글자만 남기도록 글꼴 서브셋 + 객체 정리.
사용: python -I shrink_pdf.py <pdf> [<pdf> ...]   (원본을 덮어쓴다)
"""
import os
import sys
import pymupdf

for path in sys.argv[1:]:
    before = os.path.getsize(path)
    doc = pymupdf.open(path)
    doc.subset_fonts()
    tmp = path + ".tmp"
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    os.replace(tmp, path)
    print(f"{os.path.basename(path)}: {before / 1024:.0f} KB -> {os.path.getsize(path) / 1024:.0f} KB")
