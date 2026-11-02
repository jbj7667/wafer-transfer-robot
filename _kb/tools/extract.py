"""DMU_capstone_2-2 원본 자료 -> 텍스트(Markdown) + 인덱스(JSON) 변환기.

사용: python -I extract.py <src_root> <out_root>
"""
import json, os, re, sys, zipfile, zlib, struct, hashlib
from pathlib import Path

src_root = Path(sys.argv[1])
out_root = Path(sys.argv[2])
out_root.mkdir(parents=True, exist_ok=True)


def pptx_text(p, img_dir):
    from pptx import Presentation
    from pptx.util import Emu
    prs = Presentation(str(p))
    lines, nimg = [], 0
    for i, slide in enumerate(prs.slides, 1):
        lines.append(f"\n## Slide {i}")
        for shp in slide.shapes:
            lines.extend(_shape_text(shp))
            if shp.shape_type == 13:  # picture
                nimg += 1
                try:
                    blob = shp.image.blob
                    ext = shp.image.ext
                    img_dir.mkdir(parents=True, exist_ok=True)
                    (img_dir / f"s{i:02d}_{nimg:03d}.{ext}").write_bytes(blob)
                except Exception:
                    pass
        if slide.has_notes_slide:
            n = slide.notes_slide.notes_text_frame.text.strip()
            if n:
                lines.append(f"> 노트: {n}")
    return "\n".join(lines), nimg


def _shape_text(shp):
    out = []
    if shp.has_text_frame if hasattr(shp, "has_text_frame") else False:
        t = shp.text_frame.text.strip()
        if t:
            out.append(t)
    if getattr(shp, "has_table", False) and shp.has_table:
        for row in shp.table.rows:
            out.append("| " + " | ".join(c.text.strip().replace("\n", " ") for c in row.cells) + " |")
    if shp.shape_type == 6:  # group
        for s in shp.shapes:
            out.extend(_shape_text(s))
    return out


def pdf_text(p):
    import fitz
    doc = fitz.open(str(p))
    return "\n".join(f"\n## Page {i}\n" + pg.get_text() for i, pg in enumerate(doc, 1)), 0


def xlsx_text(p):
    import openpyxl
    wb = openpyxl.load_workbook(str(p), data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f"\n## Sheet: {ws.title}")
        for row in ws.iter_rows(values_only=True):
            if any(v is not None for v in row):
                out.append("| " + " | ".join("" if v is None else str(v).replace("\n", " ") for v in row) + " |")
    return "\n".join(out), 0


def hwp_text(p):
    import olefile
    ole = olefile.OleFileIO(str(p))
    # 본문(BodyText/Section*) 레코드에서 PARA_TEXT(tag 67) 추출
    hdr = ole.openstream("FileHeader").read()
    compressed = bool(hdr[36] & 1)
    texts = []
    for entry in sorted(ole.listdir()):
        if entry[0] != "BodyText":
            continue
        data = ole.openstream(entry).read()
        if compressed:
            data = zlib.decompress(data, -15)
        i = 0
        while i < len(data):
            h = struct.unpack_from("<I", data, i)[0]
            tag, size = h & 0x3FF, (h >> 20) & 0xFFF
            i += 4
            if size == 0xFFF:
                size = struct.unpack_from("<I", data, i)[0]
                i += 4
            if tag == 67:
                raw = data[i:i + size]
                s, j = [], 0
                while j + 1 < len(raw):
                    c = struct.unpack_from("<H", raw, j)[0]
                    if c < 32:
                        if c in (0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31):
                            j += 2
                            if c in (10, 13):
                                s.append("\n")
                            continue
                        j += 16  # 확장/인라인 컨트롤 문자(8 WCHAR)
                        if c == 9:
                            s.append("\t")
                        continue
                    s.append(chr(c))
                    j += 2
                t = "".join(s).strip()
                if t:
                    texts.append(t)
            i += size
    return "\n".join(texts), 0


def hwpx_text(p):
    z = zipfile.ZipFile(str(p))
    out = []
    for n in sorted(z.namelist()):
        if re.match(r"Contents/section\d+\.xml", n):
            xml = z.read(n).decode("utf-8", "ignore")
            for para in re.findall(r"<hp:p\b.*?</hp:p>", xml, re.S):
                t = "".join(re.findall(r"<hp:t[^>]*>(.*?)</hp:t>", para, re.S))
                t = re.sub(r"<[^>]+>", "", t).strip()
                if t:
                    out.append(t)
    return "\n".join(out), 0


def zip_listing(p):
    z = zipfile.ZipFile(str(p))
    out = ["## ZIP 목록"]
    for info in z.infolist():
        out.append(f"- {info.filename} ({info.file_size} B)")
        if info.filename.lower().endswith((".ino", ".txt", ".c", ".h", ".cpp", ".md")) and info.file_size < 200_000:
            out.append("```\n" + z.read(info).decode("utf-8", "ignore") + "\n```")
    return "\n".join(out), 0


HANDLERS = {".pptx": pptx_text, ".pdf": pdf_text, ".xlsx": xlsx_text, ".hwp": hwp_text,
            ".hwpx": hwpx_text, ".zip": zip_listing}

index = []
for p in sorted(src_root.rglob("*")):
    if not p.is_file() or ".git" in p.parts:
        continue
    rel = p.relative_to(src_root)
    ext = p.suffix.lower()
    if not ext:  # 확장자 없는 파일: 매직 바이트로 판별
        head = p.read_bytes()[:8]
        ext = ".pptx" if head.startswith(b"PK") else ""
    slug = hashlib.md5(str(rel).encode()).hexdigest()[:8]
    rec = {"path": str(rel).replace("\\", "/"), "ext": ext, "bytes": p.stat().st_size, "id": slug}
    try:
        if ext == ".txt" or ext == ".md":
            text, nimg = p.read_text(encoding="utf-8", errors="ignore"), 0
        elif ext in HANDLERS:
            if ext == ".pptx":
                text, nimg = pptx_text(p, out_root / "images" / slug)
            else:
                text, nimg = HANDLERS[ext](p)
        else:
            text, nimg = "", 0
            rec["note"] = "비텍스트(이미지 등) — 수동 확인"
        text = text.encode("utf-8", "replace").decode("utf-8")
        rec["chars"] = len(text)
        rec["images"] = nimg
        if text:
            (out_root / "text").mkdir(exist_ok=True)
            (out_root / "text" / f"{slug}.md").write_text(f"# {rel}\n\n{text}\n", encoding="utf-8")
            rec["text_file"] = f"text/{slug}.md"
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
    index.append(rec)
    print(rec.get("chars", 0), rec.get("images", 0), rec.get("error", ""), rec["path"])

(out_root / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
