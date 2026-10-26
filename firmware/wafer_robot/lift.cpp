#include "lift.h"
#include "config.h"

// STEP=PC1(D36), DIR=PC0(D37). 리밋: 하단 D2=PE4, 상단 D18=PD3 (눌림 = LOW)
#define STEP_HIGH() (PORTC |= _BV(PC1))
#define STEP_LOW() (PORTC &= ~_BV(PC1))
#define DIR_UP() (PORTC |= _BV(PC0))
#define DIR_DOWN() (PORTC &= ~_BV(PC0))
#define LIMIT_LOW_HIT() (!(PINE & _BV(PE4)))
#define LIMIT_HIGH_HIT() (!(PIND & _BV(PD3)))

static volatile int32_t posSteps = 0;     // 원점 기준 스텝
static volatile int32_t targetSteps = 0;
static volatile int8_t dir = 0;           // +1 위, -1 아래, 0 정지
static volatile bool running = false;
static volatile bool stopOnLowLimit = false;
static volatile bool hitLow = false, hitHigh = false;
static volatile uint16_t rate = 0;        // 현재 step/s
static volatile uint16_t rateCap = LIFT_RATE_MAX;

enum HomeStage : uint8_t { H_IDLE, H_FAST_DOWN, H_BACKOFF, H_SLOW_DOWN, H_PARK, H_DONE, H_FAIL };
static HomeStage home = H_IDLE;
static uint32_t homeT0 = 0;

static void setRate(uint16_t r) {
  if (r < LIFT_RATE_MIN) r = LIFT_RATE_MIN;
  rate = r;
  OCR3A = (uint16_t)(2000000UL / r) - 1;  // 분주 8 -> 2MHz 기준
}

static void startMove(int32_t target, uint16_t cap, bool untilLowLimit) {
  uint8_t sreg = SREG;
  cli();
  targetSteps = target;
  stopOnLowLimit = untilLowLimit;
  hitLow = hitHigh = false;
  rateCap = cap;
  dir = target > posSteps ? 1 : (target < posSteps ? -1 : 0);
  if (dir > 0) DIR_UP(); else DIR_DOWN();
  running = dir != 0;
  setRate(LIFT_RATE_MIN);
  TCNT3 = 0;
  if (running) TIMSK3 |= _BV(OCIE3A);
  SREG = sreg;
}

ISR(TIMER3_COMPA_vect) {
  if (!running) { TIMSK3 &= ~_BV(OCIE3A); return; }
  if (dir < 0 && LIMIT_LOW_HIT()) {
    hitLow = true;
    running = false;
    return;
  }
  if (dir > 0 && LIMIT_HIGH_HIT()) {
    hitHigh = true;
    running = false;
    return;
  }
  STEP_HIGH();
  __builtin_avr_delay_cycles(32);  // DRV8834 최소 펄스폭 1.9us 이상
  STEP_LOW();
  posSteps += dir;
  if (posSteps == targetSteps) running = false;  // 원점 탐색 중 여기 도달 = 리밋 미검출
}

void liftTick1ms() {
  if (!running) return;
  int32_t remain = targetSteps - posSteps;
  if (remain < 0) remain = -remain;
  // 정지에 필요한 스텝 v^2/(2a) 보다 남은 거리가 짧으면 감속
  uint32_t v = rate;
  uint32_t stopSteps = (v * v) / (2UL * LIFT_ACCEL);
  uint16_t dv = LIFT_ACCEL / 1000;  // 1ms당 속도 변화
  if (!stopOnLowLimit && (uint32_t)remain <= stopSteps) v = v > dv + LIFT_RATE_MIN ? v - dv : LIFT_RATE_MIN;
  else if (v + dv <= rateCap) v += dv;
  else v = rateCap;
  uint8_t sreg = SREG;
  cli();
  setRate((uint16_t)v);
  SREG = sreg;
}

void liftInit() {
  pinMode(PIN_STEP, OUTPUT);
  pinMode(PIN_DIR, OUTPUT);
  pinMode(PIN_SLEEP, OUTPUT);
  pinMode(PIN_LIMIT_LOW, INPUT_PULLUP);
  pinMode(PIN_LIMIT_HIGH, INPUT_PULLUP);
  digitalWrite(PIN_SLEEP, HIGH);
  // Timer3: CTC(WGM 0100), 분주 8, 인터럽트는 이동할 때만 켠다
  TCCR3A = 0;
  TCCR3B = _BV(WGM32) | _BV(CS31);
  setRate(LIFT_RATE_MIN);
}

static int32_t mmToSteps(float mm) { return (int32_t)((mm - LIFT_HOME_MM) * LIFT_STEPS_PER_MM); }

void liftStartHoming() {
  home = H_FAST_DOWN;
  homeT0 = millis();
  // 최대 스트로크보다 길게 내려가며 하단 리밋을 찾는다
  int32_t span = (int32_t)((LIFT_MAX_MM - LIFT_HOME_MM + 20.0f) * LIFT_STEPS_PER_MM);
  noInterrupts();
  posSteps = span;  // 현재 위치를 모르므로 최상단이라고 가정
  interrupts();
  startMove(-span, HOME_RATE_FAST, true);
}

void liftUpdate() {
  switch (home) {
    case H_FAST_DOWN:
    case H_SLOW_DOWN:
      if (!running) {
        if (!hitLow) { home = H_FAIL; break; }
        if (home == H_FAST_DOWN) {
          noInterrupts();
          posSteps = 0;
          interrupts();
          startMove((int32_t)(HOME_BACKOFF_MM * LIFT_STEPS_PER_MM), HOME_RATE_SLOW, false);
          home = H_BACKOFF;
        } else {
          noInterrupts();
          posSteps = 0;  // 원점 확정
          interrupts();
          startMove(mmToSteps(LIFT_PARK_MM), LIFT_RATE_MAX, false);
          home = H_PARK;
        }
      } else if (millis() - homeT0 > 8000) {
        running = false;
        home = H_FAIL;
      }
      break;
    case H_BACKOFF:
      if (!running) {
        int32_t span = (int32_t)(10.0f * LIFT_STEPS_PER_MM);
        noInterrupts();
        posSteps = span;
        interrupts();
        startMove(-span, HOME_RATE_SLOW, true);
        home = H_SLOW_DOWN;
      }
      break;
    case H_PARK:
      if (!running) home = hitHigh ? H_FAIL : H_DONE;
      break;
    default:
      break;
  }
}

void liftMoveToMm(float mm) {
  if (home != H_DONE) return;
  if (mm > LIFT_MAX_MM) mm = LIFT_MAX_MM;
  if (mm < LIFT_HOME_MM + 1.0f) mm = LIFT_HOME_MM + 1.0f;
  startMove(mmToSteps(mm), LIFT_RATE_MAX, false);
}

bool liftBusy() { return running || (home != H_DONE && home != H_FAIL && home != H_IDLE); }
bool liftHomed() { return home == H_DONE; }
bool liftFault() { return home == H_FAIL || hitHigh; }

float liftPosMm() {
  noInterrupts();
  int32_t p = posSteps;
  interrupts();
  return LIFT_HOME_MM + p / LIFT_STEPS_PER_MM;
}
