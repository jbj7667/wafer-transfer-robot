"""Rough cut builder (러프컷). Run: python -I build_rough.py
Outputs only under C:\\Users\\gy050\\Videos\\wafer_robot\\out\\ . Privacy: taskbar cropped; ranges with
LMS pages (names/profile), account settings, login pages are excluded (see SAFE lists)."""
import subprocess, os, glob, sys

WT = r"C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2"
VID = r"C:\Users\gy050\Videos\wafer_robot"
OUT = VID + r"\out"
WORK = OUT + r"\work_rough"
os.makedirs(WORK, exist_ok=True)
FONT = "C\\:/Windows/Fonts/malgun.ttf"
ENC = ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30", "-an"]

def run(args):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, cwd=WORK)
    if r.returncode:
        sys.exit("ffmpeg failed: " + " ".join(args))

def textfile(name, text):
    with open(os.path.join(WORK, name), "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return name

def cap_filter(text, tag):
    tf = textfile("cap_%s.txt" % tag, text)
    return ("drawtext=fontfile='%s':textfile=%s:fontcolor=white:fontsize=44:"
            "box=1:boxcolor=black@0.6:boxborderw=18:x=48:y=h-text_h-100" % (FONT, tf))

CROP = "crop=1920:1032:0:0,pad=1920:1080:0:0:black"
clips = []   # (file, duration, caption or None)

def probe(f):
    o = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", os.path.join(WORK, f)], text=True)
    return float(o.strip())

def add(f, cap):
    clips.append((f, probe(f), cap))

# 1 title
t1 = textfile("t_title.txt", "웨이퍼 이송로봇 제작 기록")
t2 = textfile("t_sub.txt", "정비제 · 2026 동양로봇경진대회 · 동양미래대학교 로봇자동화공학부")
run(["-f", "lavfi", "-i", "color=c=0x12161c:s=1920x1080:r=30:d=4", "-vf",
     "drawtext=fontfile='%s':textfile=%s:fontcolor=white:fontsize=96:x=(w-text_w)/2:y=h/2-110,"
     "drawtext=fontfile='%s':textfile=%s:fontcolor=0xcfd6df:fontsize=40:x=(w-text_w)/2:y=h/2+40" % (FONT, t1, FONT, t2)]
    + ENC + ["c01_title.mp4"])
add("c01_title.mp4", None)

# stills
import fitz
pdf = fitz.open(WT + r"\public\practice\field_overview.pdf")
pdf[0].get_pixmap(dpi=200).save(os.path.join(WORK, "field_overview.png"))
pdf.close()

def still(fn, src, dur, cap, tag):
    n = int(dur * 30)
    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x12161c,"
          "scale=3840:2160,zoompan=z='min(1+0.0007*on,1.12)':d=%d:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30,"
          % n + cap_filter(cap, tag))
    run(["-loop", "1", "-i", src, "-vf", vf, "-t", str(dur)] + ENC + [fn])
    add(fn, cap)

def seg(fn, src, ranges, cap, tag, mask=""):
    """concat several [a,b] ranges of a screen recording, taskbar cropped; mask = extra privacy drawbox filters"""
    parts, labels = [], []
    for i, (a, b) in enumerate(ranges):
        parts.append("[0:v]trim=%s:%s,setpts=PTS-STARTPTS,%s[v%d]" % (a, b, CROP, i))
        labels.append("[v%d]" % i)
    fc = ";".join(parts) + ";" + "".join(labels) + "concat=n=%d:v=1:a=0,fps=30,%s%s[o]" % (len(ranges), mask, cap_filter(cap, tag))
    run(["-i", src, "-filter_complex", fc, "-map", "[o]"] + ENC + [fn])
    add(fn, cap)

S1 = OUT + r"\hyperlapse_session1.mp4"
S2 = OUT + r"\hyperlapse_session2.mp4"
C2 = "AI 도구와 규정 분석: 경기장·제약 조건 정리"
C3 = "4개 관점 × 25안 = 100안 → 단일 승강축 포크 방식 선정"

# 2 rules analysis (safe ranges of session1 only)
still("c02a_field.mp4", WORK + r"\field_overview.png", 5, C2, "2a")
# left explorer nav (OneDrive account label, phone name) is masked
seg("c02b_s1.mp4", S1, [(0, 7.6), (10.2, 11.8)], C2, "2b",
    mask="drawbox=x=0:y=140:w=352:h=892:color=black:t=fill,")
# 3 idea arena -> mechanism (arena agents are visible in session2 terminal)
# first range: LMS page peeks out at right edge / bottom of the Fusion window -> masked
seg("c03_s2arena.mp4", S2, [(30.2, 38.6), (44.2, 46.4)], C3, "3",
    mask="drawbox=x=1682:y=110:w=238:h=922:color=black:t=fill:enable='lt(t,8.4)',"
         "drawbox=x=960:y=905:w=960:h=127:color=black:t=fill:enable='lt(t,8.4)',")
# 4 Fusion modelling
seg("c04a_s2fusion.mp4", S2, [(1.2, 7.4), (48.7, 55.2)], "Fusion 모델링: 부품 배치와 간섭 검사", "4a")
P = WT + r"\public\cad"
still("c04b_iso.mp4", P + r"\model\view_iso.png", 5, "모델 간섭 검사로 설계 오류 7건 수정", "4b")
still("c04c_print.mp4", P + r"\print\view_print_iso.png", 5, "출력용 부품 25종 (소나 제외, 상부 블록 개정)", "4c")
# 5 arm option
still("c05a.mp4", P + r"\arm\L180_folded_iso.png", 5, "팔(θ-R-Z) 방식: 접힘 검사 조건부 통과", "5a")
still("c05b.mp4", P + r"\arm\L180_reach_b5_iso.png", 5, "여섯 베이스 도달 검사", "5b")
still("c05c.mp4", P + r"\arm_bench\bench_reach_iso.png", 5, "벤치 시제품 설계 → 11/01 판정", "5c")

# 6 timelapse of today's screenshots
frames = sorted(glob.glob(VID + r"\frames\20261027\*.jpg"))
with open(os.path.join(WORK, "frames.txt"), "w", encoding="utf-8") as f:
    for p in frames:
        f.write("file '%s'\nduration %.6f\n" % (p.replace("\\", "/"), 1 / 15))
    f.write("file '%s'\n" % frames[-1].replace("\\", "/"))
C6 = "2026-10-27 작업 화면 (변화 구간만 3초 간격 캡처)"
run(["-f", "concat", "-safe", "0", "-i", "frames.txt", "-vf",
     "scale=1920:1080,%s,fps=30,drawbox=x=662:y=412:w=190:h=34:color=black:t=fill,%s" % (CROP, cap_filter(C6, "6"))] + ENC + ["c06_timelapse.mp4"])
add("c06_timelapse.mp4", C6)

# 7 end card
e1 = textfile("t_end1.txt", "다음: 출력·조립 → 시험 → 모의대회(11/10, 11/17) → 대회(11/24)")
e2 = textfile("t_end2.txt", "github.com/jbj7667/wafer-transfer-robot")
run(["-f", "lavfi", "-i", "color=c=0x12161c:s=1920x1080:r=30:d=5", "-vf",
     "drawtext=fontfile='%s':textfile=%s:fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h/2-70,"
     "drawtext=fontfile='%s':textfile=%s:fontcolor=0x9ecbff:fontsize=44:x=(w-text_w)/2:y=h/2+50" % (FONT, e1, FONT, e2)]
    + ENC + ["c07_end.mp4"])
add("c07_end.mp4", None)

# concat
with open(os.path.join(WORK, "list.txt"), "w", encoding="utf-8") as f:
    for c in clips:
        f.write("file '%s'\n" % c[0])
final = OUT + r"\rough_20261027.mp4"
run(["-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "-movflags", "+faststart", final])

# SRT (caption per clip; consecutive clips with the same caption are merged)
def ts(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return "%02d:%02d:%06.3f" % (h, m, s)
t = 0.0
rows = []
for f, d, cap in clips:
    if cap:
        if rows and rows[-1][2] == cap and abs(rows[-1][1] - t) < 1e-6:
            rows[-1][1] = t + d
        else:
            rows.append([t, t + d, cap])
    t += d
with open(OUT + r"\subtitles_rough.srt", "w", encoding="utf-8", newline="\n") as f:
    for i, (a, b, c) in enumerate(rows, 1):
        f.write("%d\n%s --> %s\n%s\n\n" % (i, ts(a).replace(".", ","), ts(b).replace(".", ","), c))
for f, d, cap in clips:
    print("%-20s %6.2f s  %s" % (f, d, cap))
print("TOTAL %.2f s" % t)
