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
constexpr uint16_t SENSOR_AHEAD_MM = 60;// 라인센서 중심 ~ 바퀴축 거리
constexpr uint16_t EVENT_MIN_MS = 25;   // 3채널 모두 흑이 이 시간 이상이면 이벤트
constexpr uint16_t LINE_LOST_MS = 600;  // 3채널 모두 백이 지속되면 이탈
constexpr uint16_t PIVOT_MIN_MS_90 = 250;  // 회전 시작 직후 현재 선을 무시하는 시간 [측정]
constexpr uint16_t PIVOT_MIN_MS_180 = 600; // [측정]
constexpr uint16_t RETREAT_MM = 80;     // 집기/놓기 후 회전 전 후퇴 거리

// ---------------- 베이스 접근(초음파) ----------------
constexpr uint16_t APPROACH_STOP_MM = 15;  // 차체 앞면 ~ 하단 원기둥 간격 목표
constexpr uint16_t SONAR_OFFSET_MM = 5;    // 초음파 전면 ~ 차체 앞면 [측정]
constexpr uint16_t APPROACH_TIMEOUT_MS = 2500;

// ---------------- 승강 ----------------
// 높이 기준 = 포크 윗면 지면고(mm). 원점(하단 리밋)의 높이와 mm당 스텝은 기구 확정 후 측정.
constexpr float LIFT_HOME_MM = 150.0f;      // [측정]
constexpr float LIFT_STEPS_PER_MM = 25.0f;  // T8 리드(8mm/rev), 200 step/rev = 25 step/mm
constexpr float LIFT_MAX_MM = 222.0f;
constexpr uint16_t LIFT_RATE_MAX = 3000;    // step/s
constexpr uint16_t LIFT_RATE_MIN = 300;
constexpr uint16_t LIFT_ACCEL = 8000;       // step/s^2
constexpr uint16_t HOME_RATE_FAST = 1200, HOME_RATE_SLOW = 250;
constexpr float HOME_BACKOFF_MM = 2.0f;

constexpr float POST_TOP_MM[3] = {200.0f, 200.0f, 175.0f}; // 행 0=하단, 1=중단, 2=상단
constexpr float UNDER_WAFER_MM = 10.0f;  // 집기 전: CD 밑면보다 이만큼 아래
constexpr float CARRY_MM = 12.0f;        // 운반: 기둥 윗면보다 이만큼 위
constexpr float LIFT_PARK_MM = 160.0f;   // 주행 중 대기 높이

// ---------------- 웨이퍼 감지(IR, 위쪽) ----------------
constexpr uint16_t IR_WAFER_ADC_MIN = 300; // 이보다 크면(가까우면) CD 있음 [측정]

// ---------------- 전압 ----------------
constexpr float VBAT_SCALE = 5.0f / 1023.0f * 3.0f; // 분압 1/3
constexpr float VBAT_CAL_CTRL = 1.000f, VBAT_CAL_MOTOR = 1.000f; // [측정] 멀티미터 대비 보정
constexpr float VBAT_MOTOR_LOW = 6.6f;    // NiMH 6셀 경고 기준

// ---------------- 시간 ----------------
constexpr uint16_t LED_HALF_PERIOD_MS = 125; // 125ms 켬/끔 = 초당 4회 점멸
constexpr uint16_t TELEMETRY_MS = 500;
constexpr uint32_t RUN_TIME_LIMIT_MS = 150000UL;
