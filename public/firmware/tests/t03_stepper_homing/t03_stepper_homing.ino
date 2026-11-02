// t03_stepper_homing — DRV8834 승강 스테퍼 + 리밋 단독 시험 (lift.cpp 방식: Timer3 CTC, 사다리꼴 가감속)
// 핀: STEP=D36(PC1) DIR=D37(PC0) nSLEEP=D38, 하단 리밋 D2(PE4), 상단 리밋 D18(PD3), 눌림 = LOW, 내부 풀업.
// 위치 단위: 하단 리밋 위치를 0 mm 로 하는 mm (25 step/mm). 높이 기준 LIFT_HOME_MM 은 여기선 쓰지 않는다.
// 명령: h 원점 탐색 | g <mm> 이동 | p 위치 | x 정지 | t 스텝 손실 시험(홈 -> 40mm 위 -> 하단 리밋까지 내려감)
// 주의: 실제 기구에서는 상단 리밋이 반드시 동작하는지 먼저 손으로 눌러 확인할 것(p로 리밋 상태 출력).

const uint8_t PIN_STEP = 36, PIN_DIR = 37, PIN_SLEEP = 38;
const uint8_t PIN_LIMIT_LOW = 2, PIN_LIMIT_HIGH = 18;

const float STEPS_PER_MM = 25.0f;
const float MAX_MM = 60.0f;           // 행정 (LIFT_MAX_MM - LIFT_HOME_MM)
const uint16_t RATE_MAX = 1000;       // step/s
const uint16_t RATE_MIN = 300;
const uint16_t ACCEL = 5000;          // step/s^2
const uint16_t HOME_RATE_FAST = 800;
const uint16_t HOME_RATE_SLOW = RATE_MIN;
const float HOME_BACKOFF_MM = 2.0f;

#define STEP_HIGH() (PORTC |= _BV(PC1))
#define STEP_LOW() (PORTC &= ~_BV(PC1))
#define DIR_UP() (PORTC |= _BV(PC0))
#define DIR_DOWN() (PORTC &= ~_BV(PC0))
#define LIMIT_LOW_HIT() (!(PINE & _BV(PE4)))
#define LIMIT_HIGH_HIT() (!(PIND & _BV(PD3)))

volatile int32_t posSteps = 0;
volatile int32_t targetSteps = 0;
volatile int8_t dir = 0;
volatile bool running = false;
volatile bool stopOnLowLimit = false;
volatile bool hitLow = false, hitHigh = false;
volatile uint16_t rate = 0;
volatile uint16_t rateCap = RATE_MAX;

enum Stage : uint8_t { S_IDLE, H_FAST, H_BACKOFF, H_SLOW, T_UP, T_DOWN };
Stage stage = S_IDLE;
bool homed = false;
uint32_t stageT0 = 0, lastTick = 0;

void setRate(uint16_t r) {
  if (r < RATE_MIN) r = RATE_MIN;
  rate = r;
  uint16_t top = (uint16_t)(2000000UL / r) - 1;  // 분주 8 -> 2MHz
  OCR3A = top;
  if (TCNT3 >= top) TCNT3 = top - 1;
}

void startMove(int32_t target, uint16_t cap, bool untilLowLimit) {
  uint8_t sreg = SREG;
  cli();
  targetSteps = target;
  stopOnLowLimit = untilLowLimit;
  hitLow = hitHigh = false;
  rateCap = cap;
  dir = target > posSteps ? 1 : (target < posSteps ? -1 : 0);
  if (dir > 0) DIR_UP(); else DIR_DOWN();
  running = dir != 0;
  setRate(RATE_MIN);
  TCNT3 = 0;
  if (running) TIMSK3 |= _BV(OCIE3A);
  SREG = sreg;
}

ISR(TIMER3_COMPA_vect) {
  if (!running) { TIMSK3 &= ~_BV(OCIE3A); return; }
  if (dir < 0 && LIMIT_LOW_HIT()) { hitLow = true; running = false; return; }
  if (dir > 0 && LIMIT_HIGH_HIT()) { hitHigh = true; running = false; return; }
  STEP_HIGH();
  __builtin_avr_delay_cycles(32);  // DRV8834 최소 펄스폭 1.9us 이상
  STEP_LOW();
  posSteps += dir;
  if (posSteps == targetSteps) running = false;
}

// 1ms 마다 호출: 가감속
void tick1ms() {
  if (!running) return;
  int32_t remain = targetSteps - posSteps;
  if (remain < 0) remain = -remain;
  uint32_t v = rate;
  const uint32_t TWO_A = 2UL * ACCEL;
  const uint16_t dv = ACCEL / 1000;
  if (!stopOnLowLimit && (uint32_t)remain * TWO_A <= v * v) v = v > dv + RATE_MIN ? v - dv : RATE_MIN;
  else if (v + dv <= rateCap) v += dv;
  else v = rateCap;
  uint8_t sreg = SREG;
  cli();
  setRate((uint16_t)v);
  SREG = sreg;
}

int32_t getPos() {
  noInterrupts();
  int32_t p = posSteps;
  interrupts();
  return p;
}

void setPos(int32_t p) {
  noInterrupts();
  posSteps = p;
  interrupts();
}

void startHoming() {
  stage = H_FAST;
  stageT0 = millis();
  int32_t span = (int32_t)((MAX_MM + 20.0f) * STEPS_PER_MM);
  setPos(span);  // 위치를 모르므로 최상단이라 가정
  startMove(-span, HOME_RATE_FAST, true);
  homed = false;
  Serial.println(F("homing: fast down"));
}

void stopAll() {
  uint8_t sreg = SREG;
  cli();
  running = false;
  TIMSK3 &= ~_BV(OCIE3A);
  targetSteps = posSteps;
  SREG = sreg;
  if (stage != S_IDLE) { Serial.println(F("stage aborted")); }
  stage = S_IDLE;
}

void printPos() {
  int32_t p = getPos();
  Serial.print(F("pos = ")); Serial.print(p); Serial.print(F(" step = "));
  Serial.print(p / STEPS_PER_MM, 2); Serial.print(F(" mm  homed=")); Serial.print(homed);
  Serial.print(F("  limLow=")); Serial.print(LIMIT_LOW_HIT());
  Serial.print(F(" limHigh=")); Serial.print(LIMIT_HIGH_HIT());
  Serial.print(F(" rate=")); Serial.println(rate);
}

void stageUpdate() {
  if (stage == S_IDLE || running) {
    if (running && stage != S_IDLE && millis() - stageT0 > 15000) { stopAll(); Serial.println(F("FAIL: timeout")); }
    return;
  }
  switch (stage) {
    case H_FAST:
      if (!hitLow) { stage = S_IDLE; Serial.println(F("FAIL: 하단 리밋 미검출")); break; }
      setPos(0);
      startMove((int32_t)(HOME_BACKOFF_MM * STEPS_PER_MM), HOME_RATE_SLOW, false);
      stage = H_BACKOFF;
      Serial.println(F("homing: backoff"));
      break;
    case H_BACKOFF: {
      int32_t span = (int32_t)(10.0f * STEPS_PER_MM);
      setPos(span);
      startMove(-span, HOME_RATE_SLOW, true);
      stage = H_SLOW;
      Serial.println(F("homing: slow down"));
      break;
    }
    case H_SLOW:
      if (!hitLow) { stage = S_IDLE; Serial.println(F("FAIL: 정밀 접근 리밋 미검출")); break; }
      setPos(0);
      homed = true;
      stage = S_IDLE;
      Serial.println(F("homing OK: pos=0"));
      break;
    case T_UP:
      Serial.print(F("test: up reached pos=")); Serial.println(getPos());
      startMove(-(int32_t)(80.0f * STEPS_PER_MM) + getPos(), HOME_RATE_SLOW, true);  // 느리게 하단 리밋까지
      stage = T_DOWN;
      break;
    case T_DOWN: {
      if (!hitLow) { stage = S_IDLE; Serial.println(F("FAIL: 내려가도 하단 리밋 없음")); break; }
      int32_t p = getPos();  // 이상적으로 0 (40mm = 1000 step 올라갔다 정확히 1000 step 내려옴)
      Serial.print(F("test: 리밋 도달 시 pos=")); Serial.print(p);
      Serial.print(F(" step -> 손실 ")); Serial.print(p); Serial.print(F(" step (")); Serial.print(p / STEPS_PER_MM, 2);
      Serial.println(F(" mm). 판정: |손실| <= 5 step 이면 합격"));
      setPos(0);
      stage = S_IDLE;
      break;
    }
    default: stage = S_IDLE; break;
  }
  stageT0 = millis();
}

void handle(char *line) {
  char c = line[0];
  float v = atof(line + 1);
  if (c == 'h') {
    startHoming();
  } else if (c == 'g') {
    if (!homed) { Serial.println(F("먼저 h")); return; }
    if (v < 0) v = 0;
    if (v > MAX_MM) v = MAX_MM;
    stage = S_IDLE;
    startMove((int32_t)(v * STEPS_PER_MM), RATE_MAX, false);
    Serial.print(F("move to ")); Serial.print(v, 2); Serial.println(F(" mm"));
  } else if (c == 'p') {
    printPos();
  } else if (c == 'x') {
    stopAll();
    Serial.println(F("stopped"));
  } else if (c == 't') {
    if (!homed) { Serial.println(F("먼저 h")); return; }
    stage = T_UP;
    stageT0 = millis();
    startMove((int32_t)(40.0f * STEPS_PER_MM), RATE_MAX, false);
    Serial.println(F("test: up 40mm"));
  } else {
    Serial.println(F("? h | g <mm> | p | x | t"));
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_STEP, OUTPUT);
  pinMode(PIN_DIR, OUTPUT);
  pinMode(PIN_SLEEP, OUTPUT);
  pinMode(PIN_LIMIT_LOW, INPUT_PULLUP);
  pinMode(PIN_LIMIT_HIGH, INPUT_PULLUP);
  digitalWrite(PIN_SLEEP, HIGH);
  // Timer3: CTC, 분주 8, 이동할 때만 인터럽트 허용
  TCCR3A = 0;
  TCCR3B = _BV(WGM32) | _BV(CS31);
  setRate(RATE_MIN);
  Serial.println(F("t03_stepper_homing ready. h = 원점 탐색"));
}

void loop() {
  static char buf[20];
  static uint8_t n = 0;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (n) { buf[n] = 0; handle(buf); n = 0; }
    } else if (n < sizeof(buf) - 1) {
      buf[n++] = ch;
    }
  }
  if (millis() != lastTick) { lastTick = millis(); tick1ms(); }
  stageUpdate();
}
