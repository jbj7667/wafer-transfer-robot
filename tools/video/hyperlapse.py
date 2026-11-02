"""화면 녹화 -> 적응형 하이퍼랩스 (무음, 1080p30).

사용: python -I hyperlapse.py 입력.mp4 출력.mp4 [--target 55] [--chunk 30]

알고리즘
 1) ffmpeg로 2fps / 160x90 / gray 원시 프레임을 한 번에 파이프로 읽음.
 2) 30초 청크별 '프레임 간 평균 절대차'를 활동 점수로 계산.
 3) 점수를 로그-백분위(p10~p90)로 정규화 -> 6x(활동 큼) ~ 60x(정적).
 4) 합계가 목표 길이보다 길면 모든 배속에 같은 배율을 곱해 맞춤(상한 MAXSPEED).
 5) 청크별 mpdecimate + setpts 로 렌더 후 concat. 속도는 CSV로 기록.
"""
import argparse, csv, math, os, subprocess, sys, tempfile
import numpy as np

W, H = 160, 90
MIN_SPEED, MAX_SPEED_BASE, CAP = 6.0, 60.0, 300.0


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe_duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", path], text=True)
    return float(out.strip())


def motion_scores(path, chunk):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-an", "-vf", f"fps=2,scale={W}:{H},format=gray",
           "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    fsize = W * H
    frames = []
    while True:
        b = p.stdout.read(fsize)
        if len(b) < fsize:
            break
        frames.append(np.frombuffer(b, np.uint8))
    p.wait()
    diffs = [float(np.mean(np.abs(frames[i].astype(np.int16) - frames[i - 1].astype(np.int16))))
             for i in range(1, len(frames))]
    per = int(chunk * 2)
    scores = []
    for i in range(0, len(diffs), per):
        seg = diffs[i:i + per]
        scores.append(sum(seg) / len(seg) if seg else 0.0)
    return scores


def speeds_from_scores(scores, dur, chunk, target):
    ls = np.log10(np.array(scores) + 0.01)
    lo, hi = np.percentile(ls, 10), np.percentile(ls, 90)
    norm = np.clip((ls - lo) / (hi - lo + 1e-9), 0, 1)  # 1 = 활동 큼
    base = MAX_SPEED_BASE * (MIN_SPEED / MAX_SPEED_BASE) ** norm  # 60 -> 6 로그 보간
    lens = [min(chunk, dur - i * chunk) for i in range(len(scores))]
    total = sum(l / s for l, s in zip(lens, base))
    k = max(1.0, total / target)
    sp = np.minimum(base * k, CAP)
    return list(sp), lens, k


def render(path, out, speeds, lens, chunk):
    tmp = tempfile.mkdtemp(prefix="hl_")
    parts = []
    for i, (s, l) in enumerate(zip(speeds, lens)):
        if l < 1:
            continue
        part = os.path.join(tmp, f"p{i:04d}.mp4")
        vf = (f"mpdecimate,setpts=PTS/{s:.4f},fps=30,"
              "scale=1920:1080:force_original_aspect_ratio=decrease,"
              "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p")
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{i * chunk}", "-t", f"{l}", "-i", path, "-an",
             "-vf", vf, "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", part])
        if os.path.exists(part) and os.path.getsize(part) > 1000:
            parts.append(part)
        print(f"chunk {i + 1}/{len(speeds)} speed {s:.1f}x", flush=True)
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for p in parts:
            f.write("file '" + p.replace("\\", "/") + "'\n")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
         "-an", "-movflags", "+faststart", out])
    for p in parts:
        os.remove(p)
    os.remove(lst)
    os.rmdir(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--target", type=float, default=55.0, help="목표 출력 길이(초)")
    ap.add_argument("--chunk", type=float, default=30.0)
    a = ap.parse_args()
    dur = probe_duration(a.inp)
    scores = motion_scores(a.inp, a.chunk)
    speeds, lens, k = speeds_from_scores(scores, dur, a.chunk, a.target)
    est = sum(l / s for l, s in zip(lens, speeds))
    print(f"입력 {dur:.0f}s, 청크 {len(speeds)}, 보정배율 {k:.2f}, 예상 출력 {est:.1f}s")
    csv_path = os.path.splitext(a.out)[0] + "_speeds.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["chunk", "start_s", "len_s", "motion_score", "speed_x", "out_len_s"])
        for i, (sc, s, l) in enumerate(zip(scores, speeds, lens)):
            w.writerow([i, i * a.chunk, f"{l:.1f}", f"{sc:.3f}", f"{s:.1f}", f"{l / s:.2f}"])
    render(a.inp, a.out, speeds, lens, a.chunk)
    print("완료:", a.out, "|", csv_path)


if __name__ == "__main__":
    sys.exit(main())
