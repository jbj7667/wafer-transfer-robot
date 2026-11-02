"""Combined cut (no privacy edits). Run: python -I build_combined.py"""
import subprocess, os, glob, sys
WT = r"C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2"
VID = r"C:\Users\gy050\Videos\wafer_robot"
OUT = VID + r"\out"
WORK = OUT + r"\work_combined"
os.makedirs(WORK, exist_ok=True)
FONT = "C\:/Windows/Fonts/malgun.ttf"
ENC = ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30", "-an"]
BG = "0x12161c"

def run(args):
    if subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, cwd=WORK).returncode:
        sys.exit("ffmpeg failed: " + " ".join(args))
def textfile(name, text):
    with open(os.path.join(WORK, name), "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return name
def cap_filter(text, tag):
    return ("drawtext=fontfile='%s':textfile=%s:fontcolor=white:fontsize=44:"
            "box=1:boxcolor=black@0.6:boxborderw=18:x=48:y=h-text_h-100" % (FONT, textfile("cap_%s.txt" % tag, text)))
def label_filter(text, tag):
    return ("drawtext=fontfile='%s':textfile=%s:fontcolor=white:fontsize=36:"
            "box=1:boxcolor=black@0.6:boxborderw=14:x=40:y=40" % (FONT, textfile("lab_%s.txt" % tag, text)))
def probe(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", os.path.join(WORK, f)], text=True).strip())
clips = []
def add(f, cap): clips.append((f, probe(f), cap))

def card(fn, lines, dur, sizes=(96, 40), cap=None):
    fs = []
    for i, (t, s) in enumerate(zip(lines, sizes)):
        tf = textfile(fn + "_%d.txt" % i, t)
        y = "h/2-110" if i == 0 else "h/2+40"
        fs.append("drawtext=fontfile='%s':textfile=%s:fontcolor=%s:fontsize=%d:x=(w-text_w)/2:y=%s"
                  % (FONT, tf, "white" if i == 0 else "0xcfd6df", s, y))
    run(["-f", "lavfi", "-i", "color=c=%s:s=1920x1080:r=30:d=%s" % (BG, dur), "-vf", ",".join(fs)] + ENC + [fn])
    add(fn, cap)
def still(fn, src, dur, cap, tag):
    n = int(dur * 30)
    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=%s,"
          "scale=3840:2160,zoompan=z='min(1+0.0007*on,1.12)':d=%d:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30,"
          % (BG, n) + cap_filter(cap, tag))
    run(["-loop", "1", "-i", src, "-vf", vf, "-t", str(dur)] + ENC + [fn]); add(fn, cap)
def seg(fn, src, a, b, cap, tag):
    trim = "trim=start=%s" % a + (":end=%s" % b if b else "")
    fc = "[0:v]%s,setpts=PTS-STARTPTS,fps=30,scale=1920:1080,%s[o]" % (trim, cap_filter(cap, tag))
    run(["-i", src, "-filter_complex", fc, "-map", "[o]"] + ENC + [fn]); add(fn, cap)
def labeled(fn, src, label, tag):   # clip already has caption burned in
    run(["-i", src, "-vf", "fps=30,scale=1920:1080," + label_filter(label, tag)] + ENC + [fn])
    add(fn, label)

S1 = OUT + "/hyperlapse_session1.mp4"; S2 = OUT + "/hyperlapse_session2.mp4"
P = WT + "/public/cad"
C2 = "AI 도구와 규정 분석: 경기장·제약 조건 정리"
C3 = "4개 관점 × 25안 = 100안 → 단일 승강축 포크 방식 선정"

card("c01_title.mp4", ["웨이퍼 이송로봇 제작 기록", "정비제 · 2026 동양로봇경진대회 · 동양미래대학교 로봇자동화공학부"], 4)
still("c02a_field.mp4", VID + "/out/work_full/field_overview.png", 5, C2, "2a")
seg("c02b_s1.mp4", S1, 0, 30, C2, "2b")
seg("c03_s1b.mp4", S1, 30, 55, C3, "3")
seg("c04a_s2.mp4", S2, 0, None, "Fusion 모델링: 부품 배치와 간섭 검사", "4a")
card("c04b_sec.mp4", ["모델이 만들어지는 과정"], 2, (80,))
labeled("c04c_layout.mp4", OUT + "/build_layout_v1_1.mp4", "1) 배치 모델", "l1")
labeled("c04d_print.mp4", OUT + "/build_print_v1_zoom.mp4", "2) 출력용 모델: 작업 이력 재생 (스케치 → 돌출 157단계)", "l2")
still("c04e_printiso.mp4", P + "/print/view_print_iso.png", 5, "출력용 부품 25종 (소나 제외, 상부 블록 개정)", "4e")
card("c05a_sec.mp4", ["팔(θ-R-Z) 방식 검토"], 2, (80,))
labeled("c05b_arm.mp4", OUT + "/build_arm_L180.mp4", "3) 팔 방식 배치 모델", "l3")
still("c05c.mp4", P + "/arm/L180_folded_iso.png", 5, "접힘 검사: 여유 3.2/4.0/5.0 mm (조건부 통과)", "5c")
still("c05d.mp4", P + "/arm/L180_reach_b5_iso.png", 5, "여섯 베이스 도달·후방 스윙·구역 경계 검사 통과", "5d")
labeled("c05e_bench.mp4", OUT + "/build_arm_bench.mp4", "4) 벤치 시제품 17종 (11/01 반복 정밀도 측정용)", "l4")
still("c05f.mp4", P + "/arm_bench/bench_reach_iso.png", 5, "벤치 시제품 → 11/01 판정", "5f")

frames = sorted(glob.glob(VID + r"\frames\20261027\*.jpg"))
print("frames", len(frames))
with open(os.path.join(WORK, "frames.txt"), "w", encoding="utf-8") as f:
    for p in frames:
        f.write("file '%s'\nduration %.6f\n" % (p.replace("\\", "/"), 1 / 15))
    f.write("file '%s'\n" % frames[-1].replace("\\", "/"))
C6 = "2026-10-27 작업 화면 (변화 구간만 3초 간격 캡처)"
run(["-f", "concat", "-safe", "0", "-i", "frames.txt", "-vf",
     "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,%s" % cap_filter(C6, "6")] + ENC + ["c06_timelapse.mp4"])
add("c06_timelapse.mp4", C6)

e1 = textfile("t_end1.txt", "다음: 출력·조립 → 시험 → 모의대회(11/10, 11/17) → 대회(11/24)")
e2 = textfile("t_end2.txt", "github.com/jbj7667/wafer-transfer-robot")
run(["-f", "lavfi", "-i", "color=c=%s:s=1920x1080:r=30:d=5" % BG, "-vf",
     "drawtext=fontfile='%s':textfile=%s:fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h/2-70,"
     "drawtext=fontfile='%s':textfile=%s:fontcolor=0x9ecbff:fontsize=44:x=(w-text_w)/2:y=h/2+50" % (FONT, e1, FONT, e2)]
    + ENC + ["c07_end.mp4"])
add("c07_end.mp4", None)

with open(os.path.join(WORK, "list.txt"), "w", encoding="utf-8") as f:
    for c in clips: f.write("file '%s'\n" % c[0])
final = OUT + r"\final_combined_20261027.mp4"
run(["-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "-movflags", "+faststart", final])

def ts(t):
    return "%02d:%02d:%06.3f" % (int(t // 3600), int(t % 3600 // 60), t % 60)
t = 0.0; rows = []; lines = []
for f, d, cap in clips:
    lines.append("%7.1f s  %6.1f s  %s  %s" % (t, d, f, cap or ""))
    if cap and not f.startswith("c04c") and not f.startswith("c04d") and not f.startswith("c05b") and not f.startswith("c05e"):
        rows.append([t, t + d, cap])
    elif cap:
        rows.append([t, t + d, cap])   # label text for burned-in-caption clips
    t += d
with open(OUT + r"\subtitles_combined.srt", "w", encoding="utf-8", newline="\n") as f:
    for i, (a, b, c) in enumerate(rows, 1):
        f.write("%d\n%s --> %s\n%s\n\n" % (i, ts(a).replace(".", ","), ts(b).replace(".", ","), c))
with open(OUT + r"\README_combined.txt", "w", encoding="utf-8") as f:
    f.write("final_combined_20261027.mp4 (1920x1080 30fps, no audio, hard cuts), total %.1f s\nstart / duration / clip / caption-or-label\n" % t)
    f.write("\n".join(lines) + "\nShare copy: final_combined_share.mp4 (1600x900)\nBuilt by tools/video/build_combined.py\n")
print("\n".join(lines)); print("TOTAL %.2f s" % t)
