"""2026-11-02 week-10 progress video. Run: python -I tools\video\build_20261102.py
Output (OUT dir): final_20261102_progress.mp4 (1080p30 silent, clean) + .srt, progress_embed.mp4 (burned Korean subs, <=25MB).
Structure copied from build_20261029.py (timelapse/card/still, caption list -> SRT, concat -c copy)."""
import subprocess, os, glob, sys, re, shutil
FFDIR = r"C:\Users\gy050\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
os.environ["PATH"] = FFDIR + os.pathsep + os.environ["PATH"]
WT = r"C:\Users\gy050\workspace\DMU_capstone_2-2\.claude\worktrees\plan-stage2"
SHOOT = r"C:\Users\gy050\workspace\DMU_capstone_2-2\촬영"
VID = r"C:\Users\gy050\Videos\wafer_robot"
OUT = r"C:\Users\gy050\Downloads\10주차_진행상황보고\영상"
PHOTO = r"C:\Users\gy050\Downloads\10주차_진행상황보고\사진"
WORK = OUT + r"\work"
R = WT + r"\public\cad\assembly\renders"
os.makedirs(WORK, exist_ok=True)
FONT = r"C\:/Windows/Fonts/malgun.ttf"
ENC = ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30", "-an"]
FIT = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0xf4f1ea"
# blur-background fit (for 1536x1080 avi / 4:3 photos)
BLUR = ("[0:v]split[a][b];[a]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=30:5[bg];"
        "[b]scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")

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

clips = []
def add(fn, caps):
    clips.append((fn, probe(fn), caps))

def card(fn, lines, d, bg, fg, subfg):
    t = [textfile("%s_%d.txt" % (fn, i), s) for i, s in enumerate(lines)]
    vf = ("drawtext=fontfile='%s':textfile=%s:fontcolor=%s:fontsize=72:x=(w-text_w)/2:y=h/2-90,"
          "drawtext=fontfile='%s':textfile=%s:fontcolor=%s:fontsize=48:x=(w-text_w)/2:y=h/2+50,%s"
          % (FONT, t[0], fg, FONT, t[1], subfg, fade(d)))
    run(["-f", "lavfi", "-i", "color=c=%s:s=1920x1080:r=30:d=%s" % (bg, d), "-vf", vf] + ENC + [fn])

def still(fn, src, d):  # png render, letterbox
    run(["-loop", "1", "-i", src, "-vf", FIT + ",fps=30," + fade(d), "-t", str(d)] + ENC + [fn])

def photo(fn, src, d):  # 4:3 photo, blur bg + slow zoom
    n = int(d * 30)
    fc = ("[0:v]split[a][b];[a]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=30:5[bg];"
          "[b]scale=2880:2160,zoompan=z='1+0.08*on/%d':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=%d:s=1440x1080:fps=30[fg];"
          "[bg][fg]overlay=(W-w)/2:(H-h)/2,%s,format=yuv420p" % (n, n, fade(d)))
    run(["-i", src, "-filter_complex", fc, "-t", str(d)] + ENC + [fn])

def vclip(fn, src, ss, d):  # video excerpt -> blur-bg fit
    pre = ["-ss", str(ss), "-t", str(d)] if ss is not None else []
    run(pre + ["-i", src, "-filter_complex", BLUR + ",fps=30," + fade(d) + ",format=yuv420p"] + ENC + [fn])

def timelapse(fn, a, b, d):
    fr = [p for p in sorted(glob.glob(VID + r"\frames\20261029\*.jpg")) if a <= os.path.basename(p)[:6] <= b]
    with open(os.path.join(WORK, fn + ".txt"), "w", encoding="utf-8") as f:
        for p in fr:
            f.write("file '%s'\nduration %.6f\n" % (p.replace("\\", "/"), d / len(fr)))
        f.write("file '%s'\n" % fr[-1].replace("\\", "/"))
    run(["-f", "concat", "-safe", "0", "-i", fn + ".txt", "-vf", "crop=800:450:0:0,scale=1920:1080:flags=lanczos," + FIT + ",fps=30," + fade(d), "-t", str(d)] + ENC + [fn])
    return len(fr)

BG, FG, SUB = "0xf4f1ea", "0x1d2733", "0x4a5a6a"
card("c01_title.mp4", ["웨이퍼 이송 로봇 — 10주차 진행 상황", "로봇자동화공학부 정비제"], 5, BG, FG, SUB)
add("c01_title.mp4", [])  # card has its own text

TL = [
 ("c02_t1.mp4", "221321", "224000", 10, ["실측값 반영: 모터 Ø35, 구멍 PCD 30.4", "모터 브래킷 시험판으로 구멍 맞춤"]),
 ("c03_t2.mp4", "230001", "232000", 10, ["승강부 전부 출력 설계", "리드스크류 · 레일 일체 마스트 · 포크"]),
 ("c04_t3.mp4", "232001", "235959", 10, ["레드팀 검토와 조립 점검", "간섭 · 전복 · 조립 순서 수정"]),
]
nfr = {}
for fn, a, b, d, caps in TL:
    nfr[fn] = timelapse(fn, a, b, d)
    h = d / 2
    add(fn, [(0.5, h - 0.7, caps[0]), (h, h - 0.5, caps[1])])

PH = [("c05_ir1.mp4", "IR센서_앞면.jpg", "IR 센서 실측: 모델 GP2Y0A21 확인"),
      ("c06_ir2.mp4", "IR센서_옆면_각인.jpg", "옆면 각인 SHARP 2Y0A21"),
      ("c07_sw.mp4", "마이크로스위치_캘리퍼.jpg", "마이크로 스위치 실측: 29.41 mm"),
      ("c08_motor.mp4", "모터_시험판_맞춤.jpg", "모터 위에 시험판 맞춤 확인")]
for fn, img, cap in PH:
    photo(fn, PHOTO + "\\" + img, 3.75)
    add(fn, [(0.3, 3.1, cap)])

P1 = SHOOT + r"\20261102_165005.mp4"
vclip("c09_print1.mp4", P1, 6, 12)
add("c09_print1.mp4", [(0.4, 11.0, "출력 진행: 하판·브래킷·바퀴")])
vclip("c10_print2.mp4", P1, 30, 12)
add("c10_print2.mp4", [(0.4, 11.0, "3D 프린터로 부품을 순차 출력 중")])
vclip("c11_wheel.mp4", SHOOT + r"\video_2026-11-02_17-38-27.avi", None, 7.1)
add("c11_wheel.mp4", [(0.3, 6.4, "바퀴 본체 출력 (클로즈업)")])
vclip("c12_base.mp4", SHOOT + r"\video_2026-11-02_18-49-21.avi", None, 2.1)
add("c12_base.mp4", [(0.2, 1.8, "하판 출력")])

# assembly sim (source has English 'Step N/18' burned top-left; Korean subs go bottom)
run(["-i", R + r"\build_anim.mp4", "-vf", FIT + ",fps=30," + fade(56), "-t", "56"] + ENC + ["c13_build.mp4"])
add("c13_build.mp4", [])
run(["-stream_loop", "-1", "-i", R + r"\lift_anim\lift_anim.gif", "-vf", FIT + ",fps=30," + fade(8), "-t", "8"] + ENC + ["c14_lift.mp4"])
add("c14_lift.mp4", [(0.3, 7.4, "승강 동작 시뮬레이션 (실물 시험 전)")])
still("c15_exploded.mp4", R + r"\exploded.png", 4)
add("c15_exploded.mp4", [(0.3, 3.4, "분해도: 승강부까지 전부 출력 부품")])
card("c16_end.mp4", ["다음: 하체 조립 · 주행 시험", "→ 승강부 조립 → 11/10 모의대회 1"], 6, BG, FG, SUB)
add("c16_end.mp4", [])

with open(os.path.join(WORK, "list.txt"), "w", encoding="utf-8") as f:
    for c in clips:
        f.write("file '%s'\n" % c[0])
final = OUT + r"\final_20261102_progress.mp4"
run(["-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "-movflags", "+faststart", final])

def ts(t):
    return "%02d:%02d:%06.3f" % (t // 3600, t % 3600 // 60, t % 60)
rows, t = [], 0.0
for fn, d, caps in clips:
    if fn == "c13_build.mp4":
        txt = open(R + r"\build_anim.srt", encoding="utf-8-sig").read().replace("\r", "")
        for m in re.finditer(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)\n(.+?)\n\n", txt + "\n", re.S):
            g = [int(x) for x in m.groups()[:8]]
            a = g[0]*3600 + g[1]*60 + g[2] + g[3]/1000
            b = g[4]*3600 + g[5]*60 + g[6] + g[7]/1000
            s = m.group(9).replace("\n", " ").split(" / ")[0]
            if a < d:
                rows.append((t + a, min(t + b, t + d) - 0.05, s))
    for off, dd, s in caps:
        rows.append((t + off, t + off + dd, s))
    t += d
srt = OUT + r"\final_20261102_progress.srt"
with open(srt, "w", encoding="utf-8", newline="\n") as f:
    for i, (a, b, s) in enumerate(rows, 1):
        f.write("%d\n%s --> %s\n%s\n\n" % (i, ts(a).replace(".", ","), ts(b).replace(".", ","), s))
shutil.copy(srt, WORK + r"\p.srt")
shutil.copy(final, WORK + r"\p.mp4")
# embed version: burned subs, 1280x720, low bitrate
run(["-i", "p.mp4", "-vf", "subtitles=p.srt:original_size=1920x1080:force_style='FontName=Malgun Gothic,FontSize=26,Bold=1,Outline=3,Shadow=1,MarginV=60',scale=1280:720,format=yuv420p",
     "-c:v", "libx264", "-preset", "slow", "-b:v", "1000k", "-maxrate", "1400k", "-bufsize", "2800k", "-r", "30", "-an",
     "-movflags", "+faststart", OUT + r"\progress_embed.mp4"])
for fn, d, caps in clips:
    print("%-18s %6.2f s" % (fn, d))
print("TOTAL %.2f s  timelapse frames %s" % (t, nfr))
