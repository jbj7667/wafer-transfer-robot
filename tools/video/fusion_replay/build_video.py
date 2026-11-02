"""Frames (print_v1/f_*.png + frames.csv) -> build_print_v1.mp4 with captions. Run: python -I build_video.py"""
import subprocess, os, csv
OUT = r"C:\Users\gy050\Videos\wafer_robot\out"
B = OUT + r"\build_frames"
WORK = B + r"\vwork"; os.makedirs(WORK, exist_ok=True)
FONT = "C\:/Windows/Fonts/malgun.ttf"
SHOW = ("P13_fork", "P12_carriage")
rows = list(csv.reader(open(B + r"\frames.csv", encoding="utf-8")))
rows = [(int(r[0]), r[2]) for r in rows]
t = 0.0; segs = []; lst = []
for k, comp in rows:
    d = 0.125 if comp in SHOW else 0.05
    lst.append((k, d))
    if segs and segs[-1][2] == comp: segs[-1][1] = t + d
    else: segs.append([t, t + d, comp])
    t += d
TOTAL = t + 3.0
segs[-1][1] = TOTAL
with open(WORK + r"\list.txt", "w") as f:
    for k, d in lst:
        f.write("file '%s/f_%05d.png'\nduration %.3f\n" % ((B + r"\print_v1").replace("\\", "/"), k, d))
    f.write("file '%s/f_%05d.png'\nduration 3.0\nfile '%s/f_%05d.png'\n" % ((B + r"\print_v1").replace("\\", "/"), lst[-1][0], (B + r"\print_v1").replace("\\", "/"), lst[-1][0]))
def tf(name, text):
    open(WORK + "\\" + name, "w", encoding="utf-8", newline="").write(text); return "vwork/" + name
BOX = "fontcolor=white:fontsize=44:box=1:boxcolor=black@0.6:boxborderw=18"
fl = []
for i, (a, b, comp) in enumerate(segs):
    fl.append("drawtext=fontfile='%s':textfile=%s:%s:x=48:y=h-text_h-70:enable='between(t,%.3f,%.3f)'"
              % (FONT, tf("c%d.txt" % i, "부품: " + comp.strip()), BOX, a, b))
fl.append("drawtext=fontfile='%s':textfile=%s:%s:x=(w-text_w)/2:y=60:enable='lt(t,3)'"
          % (FONT, tf("title.txt", "출력용 모델이 만들어지는 과정 (Fusion 작업 이력 재생)"), BOX))
vf = "scale=1920:1080,fps=30,format=yuv420p," + ",".join(fl)
import sys
crf = sys.argv[1] if len(sys.argv) > 1 else "20"
cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "vwork/list.txt", "-vf", vf,
       "-c:v", "libx264", "-crf", crf, "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30", "-an",
       "-movflags", "+faststart", OUT + r"\build_print_v1.mp4"]
subprocess.run(cmd, cwd=B, check=True)
print("total %.1fs" % TOTAL)
