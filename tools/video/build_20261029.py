"""2026-10-29 design-day video. Run: python -I tools\video\build_20261029.py
Output: out\final_20261029_design.mp4 (silent, no burned subs) + .srt. Re-runnable."""
import subprocess, os, glob, sys

WT = r"C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2"
VID = r"C:\Users\gy050\Videos\wafer_robot"
OUT = VID + r"\out"
WORK = OUT + r"\work_1029"
R = WT + r"\public\cad\assembly\renders"
os.makedirs(WORK, exist_ok=True)
FONT = r"C\:/Windows/Fonts/malgun.ttf"
ENC = ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30", "-an"]
FIT = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0xf4f1ea"

def run(args):
    if subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, cwd=WORK).returncode:
        sys.exit("ffmpeg failed: " + " ".join(args))

def probe(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", os.path.join(WORK, f)], text=True).strip())

def textfile(name, text):
    with open(os.path.join(WORK, name), "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return name

def fade(d):
    return "fade=t=in:st=0:d=0.4,fade=t=out:st=%.2f:d=0.4" % (d - 0.4)

clips = []  # (file, caption list [(offset, dur, text)])
def add(fn, caps):
    clips.append((fn, probe(fn), caps))

def card(fn, lines, d, bg, fg, subfg):
    t = [textfile("%s_%d.txt" % (fn, i), s) for i, s in enumerate(lines)]
    vf = ("drawtext=fontfile='%s':textfile=%s:fontcolor=%s:fontsize=84:x=(w-text_w)/2:y=h/2-90,"
          "drawtext=fontfile='%s':textfile=%s:fontcolor=%s:fontsize=48:x=(w-text_w)/2:y=h/2+50,%s"
          % (FONT, t[0], fg, FONT, t[1], subfg, fade(d)))
    run(["-f", "lavfi", "-i", "color=c=%s:s=1920x1080:r=30:d=%s" % (bg, d), "-vf", vf] + ENC + [fn])

def still(fn, src, d):
    run(["-loop", "1", "-i", src, "-vf", FIT + ",fps=30," + fade(d), "-t", str(d)] + ENC + [fn])

def timelapse(fn, a, b, d):
    fr = [p for p in sorted(glob.glob(VID + r"\frames\20261029\*.jpg"))
          if a <= os.path.basename(p)[:6] <= b]
    with open(os.path.join(WORK, fn + ".txt"), "w", encoding="utf-8") as f:
        for p in fr:
            f.write("file '%s'\nduration %.6f\n" % (p.replace("\\", "/"), d / len(fr)))
        f.write("file '%s'\n" % fr[-1].replace("\\", "/"))
    run(["-f", "concat", "-safe", "0", "-i", fn + ".txt", "-vf", "crop=800:450:0:0,scale=1920:1080:flags=lanczos," + FIT + ",fps=30," + fade(d), "-t", str(d)] + ENC + [fn])
    return len(fr)

# opening
card("c01_title.mp4", ["웨이퍼 이송 로봇", "2026.10.29 설계 일지"], 5, "0xf4f1ea", "0x1d2733", "0x4a5a6a")
add("c01_title.mp4", [(0.3, 4.4, "웨이퍼 이송 로봇 — 설계 일지 2026.10.29")])

TL = [  # fn, start, end, dur, captions
 ("c02_t1.mp4", "221321", "224000", 22, ["실측값 반영: 모터 Ø35, 축 편심 7.5, 구멍 PCD 30.4", "모터 브래킷 시험판으로 구멍 맞춤"]),
 ("c03_t2.mp4", "224001", "230000", 18, ["Fusion 없이 Python으로 부품 생성", "브래킷 · 바퀴 · 라인센서 · 캐스터 스페이서"]),
 ("c04_t3.mp4", "230001", "232000", 22, ["승강부 전부 출력 설계 (에이전트 병렬)", "리드스크류 · 레일 일체 마스트 · 캐리지·포크"]),
 ("c05_t4.mp4", "232001", "235959", 14, ["레드팀 검토와 조립 점검 3회", "간섭 · 전복 · 조립 순서에서 문제 발견·수정"]),
]
nfr = {}
for fn, a, b, d, caps in TL:
    nfr[fn] = timelapse(fn, a, b, d)
    h = d / 2
    add(fn, [(0.5, h - 0.7, caps[0]), (h, h - 0.5, caps[1])])

# assembly sim
run(["-i", R + r"\build_anim.mp4", "-vf", FIT + ",fps=30," + fade(53), "-t", "53"] + ENC + ["c06_build.mp4"])
add("c06_build.mp4", [])  # captions from build_anim.srt
still("c07_exploded.mp4", R + r"\exploded.png", 4)
add("c07_exploded.mp4", [(0.3, 3.4, "분해도: 승강부까지 전부 출력 부품")])
# lift: gif (loop to 8 s) then two stills
run(["-stream_loop", "-1", "-i", R + r"\lift_anim\lift_anim.gif", "-vf", FIT + ",fps=30," + fade(8), "-t", "8"] + ENC + ["c08_lift.mp4"])
add("c08_lift.mp4", [(0.3, 7.4, "승강 동작: 리드스크류로 포크 상승")])
still("c09_home.mp4", R + r"\lift_home_f155_iso.png", 3)
add("c09_home.mp4", [(0.2, 2.6, "승강 최저 위치")])
still("c10_top.mp4", R + r"\lift_top_f215_iso.png", 3)
add("c10_top.mp4", [(0.2, 2.6, "승강 최고 위치")])
still("c11_iso.mp4", R + r"\view_iso.png", 3)
add("c11_iso.mp4", [(0.2, 2.6, "현재 설계 완성본")])
card("c12_end.mp4", ["다음: 1·2차 출력 → 조립 → 시험", "11/01 판정"], 5, "0xf4f1ea", "0x1d2733", "0x4a5a6a")
add("c12_end.mp4", [(0.3, 4.4, "다음: 1·2차 출력 → 조립 → 시험 (11/01 판정)")])

with open(os.path.join(WORK, "list.txt"), "w", encoding="utf-8") as f:
    for c in clips:
        f.write("file '%s'\n" % c[0])
final = OUT + r"\final_20261029_design.mp4"
run(["-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "-movflags", "+faststart", final])

def ts(t):
    return "%02d:%02d:%06.3f" % (t // 3600, t % 3600 // 60, t % 60)
rows, t = [], 0.0
import re
for fn, d, caps in clips:
    if fn == "c06_build.mp4":
        txt = open(R + r"\build_anim.srt", encoding="utf-8").read()
        for m in re.finditer(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)\n(.+?)\n\n", txt + "\n", re.S):
            g = [int(x) for x in m.groups()[:8]]
            a = g[0]*3600 + g[1]*60 + g[2] + g[3]/1000
            b = g[4]*3600 + g[5]*60 + g[6] + g[7]/1000
            rows.append((t + a, min(t + b, t + d) - 0.05, m.group(9).replace("\n", " ")))
    for off, dd, s in caps:
        rows.append((t + off, t + off + dd, s))
    t += d
with open(OUT + r"\final_20261029_design.srt", "w", encoding="utf-8", newline="\n") as f:
    for i, (a, b, s) in enumerate(rows, 1):
        f.write("%d\n%s --> %s\n%s\n\n" % (i, ts(a).replace(".", ","), ts(b).replace(".", ","), s))
for fn, d, caps in clips:
    print("%-18s %6.2f s" % (fn, d))
print("TOTAL %.2f s  timelapse frames %s" % (t, nfr))
