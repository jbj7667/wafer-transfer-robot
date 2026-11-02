import csv, json
B = r"C:\Users\gy050\Videos\wafer_robot\out\build_frames"
rows = [(int(r[0]), r[2]) for r in csv.reader(open(B + r"\frames_print_v1z.csv", encoding="utf-8"))]
items = [[B + r"\print_v1z\f_%05d.png" % k, 0.25 if c in ("P13_fork", "P12_carriage") else 0.12, c] for k, c in rows]
json.dump({"out": r"C:\Users\gy050\Videos\wafer_robot\out\build_print_v1_zoom.mp4", "items": items, "hold": 3.0},
          open(B + r"\spec_print.json", "w", encoding="utf-8"))
print(len(items), sum(i[1] for i in items))
