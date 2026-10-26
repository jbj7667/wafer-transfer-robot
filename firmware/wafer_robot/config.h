// config.h — 핀 배치와 튜닝 상수. 실측값은 [측정] 표시, 측정 후 갱신한다.
#pragma once
#include <Arduino.h>

// ---------------- 핀 (Arduino Mega 2560) ----------------
// 주행: L298 — PWM은 Timer5 OC5C(D44)/OC5B(D45)를 레지스터로 직접 구동
constexpr uint8_t PIN_ENA = 44;   // 좌 모터 PWM (OC5C)
constexpr uint8_t PIN_ENB = 45;   // 우 모터 PWM (OC5B)
constexpr uint8_t PIN_IN1 = 30, PIN_IN2 = 31;   // 좌 방향
constexpr uint8_t PIN_IN3 = 32, PIN_IN4 = 33;   // 우 방향

// 승강 스테퍼: DRV8834 — STEP/DIR은 포트 직접 접근(ISR 속도)
constexpr uint8_t PIN_STEP = 36;  // PC1
constexpr uint8_t PIN_DIR = 37;   // PC0
constexpr uint8_t PIN_SLEEP = 38; // PD7, HIGH = 동작

// 라인센서 L/C/R: D22/D24/D26 = PA0/PA2/PA4 (흑 = LOW)
constexpr uint8_t PIN_LINE_L = 22, PIN_LINE_C = 24, PIN_LINE_R = 26;

// 초음파: TRIG 일반 핀, ECHO는 외부 인터럽트(INT5)
constexpr uint8_t PIN_TRIG = 23;
constexpr uint8_t PIN_ECHO = 3;

constexpr uint8_t PIN_IR_WAFER = A0;   // GP2Y0A41SK, 위쪽을 향함
constexpr uint8_t PIN_VBAT_CTRL = A2;  // 분압 20k/10k
constexpr uint8_t PIN_VBAT_MOTOR = A3; // 분압 20k/10k

constexpr uint8_t PIN_LIMIT_LOW = 2;   // 승강 하단(원점), 내부 풀업, 눌림 = LOW
constexpr uint8_t PIN_LIMIT_HIGH = 18; // 승강 상단(과주행 보호)
constexpr uint8_t PIN_START_BTN = 19;  // 출발 푸시 스위치
constexpr uint8_t PIN_LED = 40;        // 외관 상태 LED (추가기능 5)
constexpr uint8_t PIN_NECK_SW = 25;    // 포크 U 바닥 저작동력 레버 스위치(넥 접촉), PA3, 내부 풀업, 눌림 = LOW
// BLE HM-10: Serial3 (TX3=D14 -> RXD, RX3=D15 <- TXD)

// ---------------- 주행 ----------------
constexpr uint8_t SPEED_CRUISE = 170;   // PWM 0..255, 직선 추종
constexpr uint8_t SPEED_SLOW = 110;     // 교차·정지선 접근
constexpr uint8_t SPEED_CREEP = 85;     // 베이스 접근
constexpr uint8_t SPEED_PIVOT = 120;    // 제자리 회전
constexpr int16_t KP = 38;              // 오차 1단계당 PWM 차
constexpr int16_t KD = 60;
constexpr float MM_PER_MS_SLOW = 0.12f; // [측정] SPEED_SLOW 에서 mm/ms
constexpr float MM_PER_MS_CREEP = 0.08f;// [측정]
// 기구 기준 치수 (mechanism.md §3, 바퀴축 기준 진행 방향 +)
constexpr uint16_t SENSOR_AHEAD_MM = 25;       // 바퀴축 ~ 라인센서 중심
constexpr uint16_t FORK_POCKET_AHEAD_MM = 60;  // 라인센서 ~ 포켓 중심 (참고용, 코드에서는 사용하지 않음)
constexpr uint16_t EVENT_MIN_MS = 25;   // 3채널 모두 흑이 이 시간 이상이면 이벤트
constexpr uint16_t LINE_LOST_MS = 600;  // 3채널 모두 백이 지속되면 이탈 -> 선 탐색(SEARCH) 시작
// 선 이탈 복구(SEARCH): 정지 후 마지막으로 본 쪽으로 SEARCH_MAX_MS, 안 보이면 반대쪽으로 2배까지 저속 회전
constexpr uint16_t SEARCH_MAX_MS = 700;   // [측정] 한쪽 탐색 최대 시간
constexpr uint8_t SPEED_SEARCH = 90;      // 탐색 회전 PWM (SPEED_PIVOT보다 느리게)
constexpr uint16_t SEARCH_BRAKE_MS = 80;  // 탐색 시작·방향 전환 전 정지 대기
constexpr uint16_t CROSS_PASS_MM = 40;  // 교차점 직진 통과 거리
constexpr uint16_t RETREAT_MM = 100;    // 집기/놓기 후 회전 전 후퇴 거리 (포크 끝 반경 150 < 85+100-25)

// 제자리 회전. 시간은 모두 각가속도 램프 구간을 포함한다.
constexpr uint16_t PIVOT_RAMP_MS = 300;       // PWM 0 -> SPEED_PIVOT 램프 (CD 미끄러짐 방지, 300ms 이상)
constexpr uint16_t PIVOT_MIN_MS_90 = 400;     // 회전 시작 직후 현재 선을 무시하는 시간 [측정]
constexpr uint16_t PIVOT_MIN_MS_180 = 800;    // [측정]
constexpr uint16_t PIVOT_MIN_MS_PARTIAL = 380;// 상단 행 부분 회전(약 55도) 최소 시간 [측정]

// 능동 제동: 양쪽 IN 모두 HIGH + PWM 255 를 이 시간 유지한 뒤 프리런
constexpr uint16_t BRAKE_MS = 40;

// ---------------- 넥 접촉 크리프 / 초음파 ----------------
constexpr uint16_t CREEP_TIMEOUT_MS = 1500;   // 이 시간 안에 넥 스위치가 안 눌리면 고장
constexpr uint16_t CREEP_SONAR_MIN_MM = 20;   // 초음파는 차체 앞면에서 30mm 뒤로 매립 → 정상 접촉 시 약 35mm. 이보다 가까우면 고장 [측정]
constexpr uint8_t NECK_DEBOUNCE_MS = 8;       // 넥 스위치 연속 눌림 확정 시간
constexpr uint16_t SONAR_SLOW_MM = 150;       // 기둥 접근 감속 시작 거리 [측정]

// ---------------- 승강 ----------------
// 높이 기준 = 포크 윗면 지면고(mm). 원점(하단 리밋)의 높이는 기구 확정 후 측정.
constexpr float LIFT_HOME_MM = 155.0f;      // [측정] 하단 리밋이 눌릴 때 포크 윗면 높이
constexpr float LIFT_STEPS_PER_MM = 25.0f;  // T8 리드 8mm/rev, 풀스텝 200 step/rev = 25 step/mm
constexpr float LIFT_MAX_MM = 215.0f;       // 행정 상한 (원점 + 60mm)
constexpr uint16_t LIFT_RATE_MAX = 1000;    // step/s (7.2V 현실 속도, 40mm/s)
constexpr uint16_t LIFT_RATE_MIN = 300;     // 기동·정지 최저 속도
constexpr uint16_t LIFT_ACCEL = 5000;       // step/s^2 (300->1000 step/s 약 0.14s)
constexpr uint16_t HOME_RATE_FAST = 800;    // 원점 탐색 하강 (LIFT_RATE_MAX 이하)
constexpr uint16_t HOME_RATE_SLOW = LIFT_RATE_MIN; // 정밀 재접근 (LIFT_RATE_MIN 이상이어야 함)
constexpr float HOME_BACKOFF_MM = 2.0f;

constexpr float POST_TOP_MM[3] = {200.0f, 200.0f, 175.0f}; // 행 0=하단, 1=중단, 2=상단 기둥 윗면 높이
constexpr float UNDER_WAFER_MM = 10.0f;  // 집기 전: 기둥 윗면보다 이만큼 아래
constexpr float CARRY_MM = 12.0f;        // 운반: 기둥 윗면보다 이만큼 위
constexpr float CLEAR_MM = 5.0f;         // 기둥 근처 회전·접근 전 높이: 기둥 윗면 + 5
constexpr float LIFT_PARK_MM = 160.0f;   // 홈 복귀·원점 직후 대기 높이

// ---------------- 웨이퍼 감지(IR, 위쪽) ----------------
constexpr uint16_t IR_WAFER_ADC_MIN = 300; // 이보다 크면(가까우면) CD 있음 [측정]

// ---------------- 전압 ----------------
constexpr float VBAT_SCALE = 5.0f / 1023.0f * 3.0f; // 분압 1/3
constexpr float VBAT_CAL_CTRL = 1.000f, VBAT_CAL_MOTOR = 1.000f; // [측정] 멀티미터 대비 보정
constexpr float VBAT_MOTOR_LOW = 6.6f;    // NiMH 6셀 경고 기준

// ---------------- 자가 점검(SELFTEST) ----------------
constexpr uint16_t SELFTEST_LINE_MS = 200;  // 이 시간 동안 3채널 모두 백이면 LINE 경고(진행은 계속)

// ---------------- 시간 ----------------
constexpr uint16_t LED_HALF_PERIOD_MS = 125; // 125ms 켬/끔 = 초당 4회 점멸
constexpr uint16_t TELEMETRY_MS = 500;
// 주행 제한시간: 예선 120s / 본선 150s. 본선 값을 쓰며, 한도에 닿으면 펌웨어는 그냥 정지(고장 상태)한다.
constexpr uint32_t RUN_TIME_LIMIT_MS = 150000UL;
