"""python -I chk2.py clip.mp4 -> build_frames/chk_m.png (2x2 montage of 4 frames) + ffprobe"""
import subprocess, sys, json
O = r"C:\Users\gy050\Videos\wafer_robot\out"
B = O + r"\build_frames"
clip = O + "\\" + sys.argv[1]
pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=width,height,r_frame_rate,pix_fmt,codec_name", "-of", "json", clip], capture_output=True, text=True)
j = json.loads(pr.stdout); d = float(j["format"]["duration"]); print(j["streams"], d, int(j["format"]["size"]) / 1e6, "MB")
fr = [0.2, 0.4, 0.65, 0.97]
for i, f in enumerate(fr):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % (d * f), "-i", clip, "-frames:v", "1", "-vf", "scale=960:540", B + r"\chk_%d.png" % i], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y"] + sum([["-i", B + r"\chk_%d.png" % i] for i in range(4)], []) +
               ["-filter_complex", "[0][1]hstack[a];[2][3]hstack[b];[a][b]vstack", "-frames:v", "1", B + r"\chk_m.png"], check=True)
