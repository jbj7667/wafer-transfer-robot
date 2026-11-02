"""P04 시험판: 하체 모터 고정 구멍 맞춤 확인용 (3 mm 판, STL 직접 생성).

좌표: 원점 = 감속기 몸통 중심, +X = 축 방향, 출력면에서 내려다본 평면도(출력 상면 = 출력면 시점).
구멍 위치는 params.md '실측값'의 (x, y_right)를 쓰며 평면 Y = -y_right (시계방향이 -Y).
"""
import math
from pathlib import Path

import trimesh
from shapely.geometry import Point

THK = 3.0
R_OUT = 18.5          # 판 외경 Ø37 (모터 Ø34~35보다 약간 큼)
SHAFT = (7.5, 0.0)    # 축 위치(몸통 중심에서 편심 7.5)
BOSS_D = 18.0         # 축 둘레 보스 여유 구멍
HOLE_D = 3.4          # M3 여유(탭 Ø3)
PCD_R = 15.21         # PCD 30.4 / 2
ANGLES = (55.0, 175.0, 295.0)   # 축 방향 0°, 시계방향 (사진 추정 ±5°)

shape = Point(0, 0).buffer(R_OUT, resolution=64)
shape = shape.difference(Point(*SHAFT).buffer(BOSS_D / 2, resolution=48))
for a in ANGLES:
    x = PCD_R * math.cos(math.radians(a))
    y_right = PCD_R * math.sin(math.radians(a))
    shape = shape.difference(Point(x, -y_right).buffer(HOLE_D / 2, resolution=24))

mesh = trimesh.creation.extrude_polygon(shape, THK)
assert mesh.is_watertight, "not watertight"
out = Path(__file__).with_name("P04_test_plate.stl")
mesh.export(out)
print(out, "bbox", mesh.bounds.round(2).tolist(), "vol cm3", round(mesh.volume / 1000, 2))
