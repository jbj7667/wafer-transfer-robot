"""out/ 추출 결과를 <kb>/sources 에 원본 경로 구조 그대로 미러링하고 카탈로그를 만든다."""
import json, shutil, sys
from pathlib import Path

out, kb = Path(sys.argv[1]), Path(sys.argv[2])
src_dir = kb / "sources"
fig_dir = kb / "figures"
src_dir.mkdir(parents=True, exist_ok=True)
fig_dir.mkdir(parents=True, exist_ok=True)

idx = json.loads((out / "index.json").read_text(encoding="utf-8"))
catalog = []
for r in idx:
    p = r["path"]
    if p.startswith("contaxt/공지사항"):
        cat = "official_notice"
    elif p.startswith("contaxt/강좌 Q&A"):
        cat = "official_qna"
    elif p.startswith("contaxt/주제 별"):
        cat = "other_team_deck"
    else:
        cat = "misc"
    entry = {"source": "contaxt/../" + p if False else p, "category": cat, "type": r["ext"],
             "bytes": r["bytes"], "chars": r.get("chars", 0), "images": r.get("images", 0)}
    if r.get("text_file"):
        dst = src_dir / (p + ".md")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out / r["text_file"], dst)
        entry["text"] = "sources/" + p + ".md"
        if r.get("images"):
            entry["extracted_images"] = r["images"]
    else:
        entry["note"] = r.get("note", "")
    catalog.append(entry)

# 공식 자료 이미지만 figures 로 (타 팀 덱 이미지는 용량이 커서 제외)
parts = next(r for r in idx if "주요부품사이즈" in r["path"])
shutil.copytree(out / "images" / parts["id"], fig_dir / "parts_size", dirs_exist_ok=True)
for f in Path(".").glob("rule_p*.png"):
    shutil.copyfile(f, fig_dir / f.name.replace("rule_p", "rule_page_"))

(kb / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(catalog), "entries")
