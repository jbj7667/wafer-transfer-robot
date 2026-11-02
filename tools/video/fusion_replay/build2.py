"""python -I build2.py spec.json : spec = {out, items:[[png, dur, caption],...], hold}. Captions burned with drawtext."""
import subprocess, os, sys, json
OUT = r"C:\Users\gy050\Videos\wafer_robot\out"
B = OUT + r"\build_frames"
spec = json.load(open(sys.argv[1], encoding="utf-8"))
name = os.path.splitext(os.path.basename(spec["out"]))[0]
WORK = B + "\\vw_" + name; os.makedirs(WORK, exist_ok=True)
FONT = "C\\:/Windows/Fonts/malgun.ttf"
items = spec["items"]; hold = spec.get("hold", 3.0)
t = 0.0; segs = []
with open(WORK + r"\list.txt", "w") as f:
    for n, (img, d, cap) in enumerate(items):
        f.write("file '%s'\nduration %.3f\n" % (img.replace("\\", "/"), d + (hold if n == len(items) - 1 else 0)))
        if segs and segs[-1][2] == cap: segs[-1][1] = t + d
        else: segs.append([t, t + d, cap])
        t += d
    last = items[-1][0].replace("\\", "/")
    f.write("file '%s'\n" % last)
TOTAL = t + hold
segs[-1][1] = TOTAL
BOX = "fontcolor=white:fontsize=44:box=1:boxcolor=black@0.6:boxborderw=18"
fl = []
for i, (a, b, cap) in enumerate(segs):
    p = WORK + "\\c%d.txt" % i
    open(p, "w", encoding="utf-8", newline="").write("부품: " + cap.strip())
    fl.append("drawtext=fontfile='%s':textfile=%s:%s:x=48:y=h-text_h-70:enable='gte(t,%.3f)*lt(t,%.3f)'"
              % (FONT, "vw_%s/c%d.txt" % (name, i), BOX, a, b))
vf = "scale=1920:1080,fps=30,format=yuv420p," + ",".join(fl)
crf = sys.argv[2] if len(sys.argv) > 2 else "20"
cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "vw_%s/list.txt" % name, "-vf", vf,
       "-c:v", "libx264", "-crf", crf, "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30", "-an", "-t", "%.3f" % TOTAL,
       "-movflags", "+faststart", spec["out"]]
subprocess.run(cmd, cwd=B, check=True)
print("total %.1fs" % TOTAL)
