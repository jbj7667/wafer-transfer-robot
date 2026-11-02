import csv, json, sys
# python -I mkspec_arm.py <OUTdir> <mp4 name>
n, mp4 = sys.argv[1], sys.argv[2]
B = r"C:\Users\gy050\Videos\wafer_robot\out\build_frames"
rows = list(csv.reader(open(B + r"\frames_%s.csv" % n, encoding="utf-8")))
items = [[B + "\\%s\\f_%05d.png" % (n, int(r[0])), float(r[1]), r[2]] for r in rows]
json.dump({"out": r"C:\Users\gy050\Videos\wafer_robot\out\%s" % mp4, "items": items, "hold": 3.0},
          open(B + r"\spec_%s.json" % n, "w", encoding="utf-8"))
print(len(items), sum(i[1] for i in items))
