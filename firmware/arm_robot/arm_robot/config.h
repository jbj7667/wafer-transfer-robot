// config.h — 팔 방식(θ-R-Z) 벤치 시제품 핀·치수·튜닝. 실측값은 [측정], 가정은 [가정] 표시.
// 근거: public/docs/design/arm_option.md (§1 기구학, §2 벨트, §5 제어, §6 전원)
#pragma once
#include <Arduino.h>

// ---------------- 축 번호 ----------------
constexpr uint8_t AX_TH = 0;  // 회전대 (방위각, 0..360, 로봇 정면 0, 왼쪽 +)
constexpr uint8_t AX_R = 1;   // 어깨 링크 각 φ (손목 반경 R_w = 2·L·cosφ)
constexpr uint8_t AX_Z = 2;   // 승강 (하단 리밋 = 0 mm)

// ---------------- 핀 (Arduino Mega 2560) ----------------
// wafer_robot 사용 핀: D2,D3,D18,D19,D22-D26,D30-D33,D36-D38,D40,D44,D45,A0,A2,A3 / Serial3(BLE).
// 아래 핀은 위와 겹치지 않는다. Z 는 wafer_robot 와 같은 36/37/38 (대회 펌웨어에 병합할 때 그대로).
constexpr uint8_t PIN_TH_STEP = 46, PIN_TH_DIR = 47, PIN_TH_SLEEP = 48;  // PL3, PL2, PL1
constexpr uint8_t PIN_R_STEP = 49, PIN_R_DIR = 50, PIN_R_SLEEP = 51;     // PL0, PB3, PB2
constexpr uint8_t PIN_Z_STEP = 36, PIN_Z_DIR = 37, PIN_Z_SLEEP = 38;     // PC1, PC0, PD7
// 리밋 스위치 (내부 풀업, 눌림 = LOW)
constexpr uint8_t PIN_TH_HOME = 4;   // 회전대 캠이 θ_stow 에서 누름
constexpr uint8_t PIN_R_HOME = 5;    // 링크1 접힘 끝(φ=105°)
constexpr uint8_t PIN_Z_LOW = 2;     // 승강 하단 (wafer_robot 과 동일)
// 참고: D46 은 Timer5 OC5A 이나 wafer_robot 은 OC5C/OC5B(D44/D45)만 쓰며 COM5A 를 켜지 않는다.

// ---------------- 방향 (+스텝 = 좌표 증가) ----------------
// [확인필요] 실제 결선·모터 방향에 따라 true/false 조정
constexpr bool DIR_INV_TH = false, DIR_INV_R = false, DIR_INV_Z = false;
// 리밋 쪽 방향 (+1/-1, 좌표 증가 방향 기준)
constexpr int8_t HOME_DIR_TH = +1;   // θ_stow 를 +방향에서 접근 [가정]
constexpr int8_t HOME_DIR_R = +1;    // φ 증가 = 접힘
constexpr int8_t HOME_DIR_Z = -1;    // 아래로

// ---------------- 단위 환산 ----------------
constexpr float MOTOR_FULL_STEPS = 200.0f;   // 1.8°
// 마이크로스텝: DRV8834 M0/M1 은 하드웨어 결선. 아래 값은 결선과 일치시켜야 한다 [확인필요]
constexpr float MICROSTEP_TH = 8.0f, MICROSTEP_R = 8.0f, MICROSTEP_Z = 1.0f;
constexpr float RATIO_TH = 3.0f;   // 20T:60T GT2
constexpr float RATIO_R = 3.0f;    // R 구동 벨트 3:1 (링크 간 2:1 연동은 수동이라 φ 기준에서 흡수됨)
constexpr float STEPS_PER_DEG_TH = MOTOR_FULL_STEPS * MICROSTEP_TH * RATIO_TH / 360.0f;  // 13.33
constexpr float STEPS_PER_DEG_R = MOTOR_FULL_STEPS * MICROSTEP_R * RATIO_R / 360.0f;     // 13.33 (φ 1° 당)
constexpr float STEPS_PER_MM_Z = 25.0f * MICROSTEP_Z;  // T8 리드 8 mm, 풀스텝 25 step/mm
constexpr float STEPS_PER_UNIT[3] = {STEPS_PER_DEG_TH, STEPS_PER_DEG_R, STEPS_PER_MM_Z};

// 홈에서의 좌표 (스위치가 눌린 위치)
constexpr float HOME_COORD_TH = 216.0f;  // 접힘 방위 θ_stow ≈ 216° (L=180, arm_option §1.4)
constexpr float HOME_COORD_R = 105.0f;   // φ_fold
constexpr float HOME_COORD_Z = 0.0f;
constexpr float HOME_COORD[3] = {HOME_COORD_TH, HOME_COORD_R, HOME_COORD_Z};

// ---------------- 링크 기구학 (arm_option §1) ----------------
constexpr float ARM_L = 180.0f;          // 링크 길이 (두 링크 같음)
constexpr float FORK_OFFSET = 64.0f;     // 손목 ~ CD 중심 [가정]
constexpr float PHI_MIN_DEG = 22.7f;     // 특이점 가드: R_w 332(정지오차 10 포함)에 대한 φ (kin_out K3)
constexpr float PHI_FOLD_DEG = 105.0f;
constexpr float CARRY_R_CD = 200.0f;     // 운반 반경 R_C (arm_option §4.2)

// ---------------- 소프트 한계 ----------------
constexpr float TH_MIN_DEG = 60.0f, TH_MAX_DEG = 300.0f;  // 전방 섹터(마스트) 금지
constexpr float R_PHI_MIN_DEG = PHI_MIN_DEG + 1.0f;       // 펴는 쪽
constexpr float R_PHI_MAX_DEG = PHI_FOLD_DEG - 1.0f;      // 접힘 쪽 (홈 스위치 위에 올라타지 않음)
constexpr float Z_MIN_MM = 1.0f, Z_MAX_MM = 60.0f;

// ---------------- 속도·가속 (step/s, step/s^2) ----------------
// 합계 스텝률 예산: 6205 sps (arm_option §5.1) — 아래 최고속 합 4250 은 그 안.
constexpr uint16_t VMAX[3] = {2000, 1500, 750};     // TH 150°/s, R, Z 30 mm/s
constexpr uint16_t VMIN[3] = {100, 100, 250};       // 기동 속도
constexpr uint16_t ACCEL[3] = {6000, 5000, 5000};   // TH 450°/s^2, R 약 2 m/s^2 상당, Z 0.2 m/s^2
constexpr float PICK_Z_SPEED_SCALE = 1.0f;          // (예약)

// ---------------- 홈잉 (arm_option §5.3) ----------------
struct HomeCfg {
  uint16_t fast, slow;     // step/s
  float backoff;           // 단위(deg/mm): 스위치 해제 후 추가 후퇴
  float maxSearch;         // 단위: 한 방향 탐색 최대 거리
  float park;              // 단위: 영점 확정 후 스위치에서 떨어지는 거리 (0 = 그대로)
  bool reverseSearch;      // 못 찾으면 반대 방향 탐색
};
constexpr HomeCfg HOME_CFG[3] = {
    {400, 100, 4.0f, 120.0f, 0.0f, true},   // TH: 최대 120° (arm_option §5.3)
    {400, 100, 3.0f, 90.0f, 1.0f, false},   // R : φ 105 -> 23.7 범위
    {500, 250, 2.0f, 70.0f, 2.0f, false},   // Z : 행정 60 + 여유
};
constexpr uint32_t HOME_AXIS_TIMEOUT_MS = 20000UL;  // 축당 상한 (초과 = FAULT)

// ---------------- 접근 (한 방향 규칙, arm_option §2.5) ----------------
constexpr float TH_APPROACH_DEG = 2.0f;  // 항상 큰 쪽에서 작아지는 방향으로 마지막 접근
constexpr float R_APPROACH_DEG = 2.0f;   // 항상 펴는 방향(φ 감소)으로 마지막 접근
constexpr uint16_t SETTLE_MS = 150;      // 단계 정착
constexpr uint16_t REP_DWELL_MS = 1500;  // rep: 도착 후 대기(손으로 표시할 시간)

// ---------------- 베이스 픽 높이 (wafer_robot 과 동일 기준) ----------------
constexpr float LIFT_HOME_MM = 155.0f;                      // Z=0 에서 포크 윗면 높이
constexpr float POST_TOP_MM[3] = {200.0f, 200.0f, 175.0f};  // 행 0=하단, 1=중단, 2=상단
constexpr float UNDER_WAFER_MM = 10.0f;                     // 기둥 윗면보다 아래

// ---------------- 콘솔 ----------------
constexpr uint32_t SERIAL_BAUD = 115200UL;
constexpr uint8_t LINE_MAX = 48;
