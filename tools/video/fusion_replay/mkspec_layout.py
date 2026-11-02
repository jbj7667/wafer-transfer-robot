import csv, json
B = r"C:\Users\gy050\Videos\wafer_robot\out\build_frames"
rows = [(int(r[0]), r[2]) for r in csv.reader(open(B + r"\frames_layout.csv", encoding="utf-8"))]
items = [[B + r"\layout\f_%05d.png" % k, 0.4, c] for k, c in rows]
json.dump({"out": r"C:\Users\gy050\Videos\wafer_robot\out\build_layout_v1_1.mp4", "items": items, "hold": 3.0},
          open(B + r"\spec_layout.json", "w", encoding="utf-8"))
print(len(items))
