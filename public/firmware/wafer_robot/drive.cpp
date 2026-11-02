#include "drive.h"
#include "config.h"

// 방향 핀 D30..D33 = PC7..PC4. ISR에서도 부르므로 digitalWrite 대신 포트를 직접 쓴다.
#define IN1_BIT _BV(PC7)
#define IN2_BIT _BV(PC6)
#define IN3_BIT _BV(PC5)
#define IN4_BIT _BV(PC4)

static volatile bool braking = false;
static uint32_t brakeT0 = 0;

void driveInit() {
  pinMode(PIN_ENA, OUTPUT);
  pinMode(PIN_ENB, OUTPUT);
  pinMode(PIN_IN1, OUTPUT);
  pinMode(PIN_IN2, OUTPUT);
  pinMode(PIN_IN3, OUTPUT);
  pinMode(PIN_IN4, OUTPUT);
  // Timer5: Fast PWM 8bit (WGM 0101), 비반전 출력 B/C, 분주 8 -> 16MHz/8/256 = 7.8kHz
  TCCR5A = _BV(COM5B1) | _BV(COM5C1) | _BV(WGM50);
  TCCR5B = _BV(WGM52) | _BV(CS51);
  OCR5B = 0;
  OCR5C = 0;
}

static inline uint8_t clampDuty(int16_t v) {
  if (v < 0) v = -v;
  return v > 255 ? 255 : (uint8_t)v;
}

void driveSet(int16_t left, int16_t right) {
  uint8_t sreg = SREG;
  cli();
  uint8_t c = PORTC & ~(IN1_BIT | IN2_BIT | IN3_BIT | IN4_BIT);
  if (left > 0) c |= IN1_BIT; else if (left < 0) c |= IN2_BIT;
  if (right > 0) c |= IN3_BIT; else if (right < 0) c |= IN4_BIT;
  PORTC = c;  // 양쪽 모두 0이면 IN=LOW,LOW -> 프리런 정지
  OCR5C = clampDuty(left);
  OCR5B = clampDuty(right);
  braking = false;
  SREG = sreg;
}

void driveBrake() {
  uint8_t sreg = SREG;
  cli();
  PORTC |= IN1_BIT | IN2_BIT | IN3_BIT | IN4_BIT;  // 단락 제동 (EN 듀티 = 제동 세기, EN=LOW면 프리런)
  OCR5C = BRAKE_DUTY_START;
  OCR5B = BRAKE_DUTY_START;
  braking = true;
  SREG = sreg;
  brakeT0 = millis();
}

// 제동 세기를 BRAKE_DUTY_START -> 255 로 BRAKE_MS 동안 선형 증가 (급제동 시 앞숙임·센서 헤드 접지 방지).
void driveBrakeUpdate() {
  if (!braking) return;
  uint32_t el = millis() - brakeT0;
  if (el >= BRAKE_MS) {
    driveSet(0, 0);
    return;
  }
  uint8_t duty = (uint8_t)(BRAKE_DUTY_START + (uint32_t)(255 - BRAKE_DUTY_START) * el / BRAKE_MS);
  OCR5C = duty;
  OCR5B = duty;
}
