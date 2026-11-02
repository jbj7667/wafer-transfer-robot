# public/cad/print — 현행 파일과 구버전 구분 (2026-10-31)

출력용 폴더는 `public/cad/26.10.29_출력`(1차), `26.10.29_출력_2차`다. 이 폴더(`print/`)는 **생성 소스와 모든 버전**이 섞여 있으므로 아래로 구분한다.

## 현행(출력 대상)
P01_deck1_v2, P02_deck2_v2(기둥 일체), P04_motor_brkt_L/R(동일), P04_test_plate, P05_caster_spacer_v2, P06_line_hanger, P06_line_head_t0/t5/t10/t15(모터 회피 홈·최저 Z 3 반영), P08_stepper_brkt/plate, P10_mast_upper_v2, P11_limit_collar_v2, P12_carriage_v2, P13_fork_v2, P14_batt_cradle_v2_L/R, P15_panel_v2, P16_wheel_body_v2, P17_wheel_tire_TPU, P20_leadscrew, P20t_screw_test, P21t_nut_test, P23_mast_L/R, (P24_nut_float — 플로팅 너트 작업 후 추가)

## 구버전 — 출력 금지(소스·참고용으로 남김)
- P03_standoff_x5 (상판 기둥 일체로 대체)
- P05_caster_spacer(높이 39 가정), P01_deck1 / P14_batt_cradle_L/R(구멍 추가 전; `v13_caster.py`·`v14_fixes.py`가 원본으로 읽음 — **삭제 금지**)
- P09_mast_lower_L/R, P09_mast_lower_v2_*, P22_rail (레일 일체 `P23_mast_*`로 대체)
- P10_mast_upper, P11_limit_low, P12_carriage, P13_fork (Fusion 산출 구버전; `P13_fork.stl`은 `lift_fork.py`가 읽는 원본이라 **삭제 금지**)
- P16_wheel_body, P16_wheel_hub (v2로 대체/미사용)
- P07_sonar_mount, optional/P11_limit_high (소나·상한 스위치는 기본 구성에서 제외)

## 생성 스크립트 (재생성: 워크트리 루트에서 `python -X utf8 public/cad/print/<이름>.py`)
v12_parts.py(P04·바퀴·헬퍼), v13_caster.py(P05_v2·P01_v2·P14_v2), v14_fixes.py(P06 모터 회피·바퀴 v2·하판 구멍·헤드 최저 Z), lift_thread.py·lift_screw.py(P20·시험), lift_mast.py(P23·P10·P12·P24), lift_fork.py(P13·P11), lift_deck2.py(P02·P15).
주의: `v14_fixes.py p06`은 현재 파일에 홈을 다시 파는 멱등 연산이지만, 원본(깎이지 않은) P06이 아니라 **이미 수정된 파일**을 읽는다 — git에서 원본을 복원한 뒤 실행하면 항상 같은 결과.
