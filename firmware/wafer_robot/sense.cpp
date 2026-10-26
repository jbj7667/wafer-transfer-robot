#include "sense.h"
#include "config.h"
#include "drive.h"
#include "lift.h"

static volatile uint32_t tickCount = 0;
static volatile uint8_t bits = 0;
static volatile uint16_t allBlackMs = 0, allWhiteMs = 0;
static volatile bool eventLatched = false, eventArmed = true;

static volatile DriveMode mode = DriveMode::Manual;
static volatile uint8_t followBase = 0;
static volatile int8_t lastErr = 0, lastSide = 0;

static volatile uint8_t btnCount = 0;
static volatile bool btnPressed = false, btnEdge = false;
static volatile LedMode ledMode = LedMode::Off;

// 패턴 -> 오차: 왼쪽 센서만 흑 = 로봇이 선의 오른쪽 = 왼쪽으로 돌아야 함 = 음수
static int8_t patternError(uint8_t b) {
  switch (b) {
    case 0b100: return -2;
    case 0b110: return -1;
    case 0b010: return 0;
    case 0b011: return 1;
    case 0b001: return 2;
    default: return 0;
  }
}

ISR(TIMER1_COMPA_vect) {
  tickCount++;

  // 라인센서 D22/D24/D26 = PA0/PA2/PA4, 흑 = LOW
  uint8_t pa = PINA;
  uint8_t b = (!(pa & _BV(PA0)) << 2) | (!(pa & _BV(PA2)) << 1) | (!(pa & _BV(PA4)));
  bits = b;
  if (b == 0b111) {
    if (allBlackMs < 60000) allBlackMs++;
    if (eventArmed && allBlackMs >= EVENT_MIN_MS) {
      eventLatched = true;
      eventArmed = false;  // 흑 구간을 벗어날 때까지 재발생 금지
    }
  } else {
    allBlackMs = 0;
    eventArmed = true;
  }
  if (b == 0) { if (allWhiteMs < 60000) allWhiteMs++; } else allWhiteMs = 0;

  // PD 라인추종, 200Hz
  // (32비트 나눗셈은 ISR에서 수십 us를 먹으므로 8비트 카운터로 분주한다)
  static uint8_t followDiv = 0;
  if (++followDiv >= 5) followDiv = 0;
  if (mode == DriveMode::Follow && followDiv == 0) {
    int8_t e;
    if (b == 0) e = lastSide >= 0 ? 3 : -3;  // 선 이탈: 마지막으로 본 쪽으로 강하게
    else if (b == 0b111 || b == 0b101) e = 0;
    else e = patternError(b);
    if (e > 0) lastSide = 1; else if (e < 0) lastSide = -1;
    int16_t u = KP * e + KD * (e - lastErr);
    lastErr = e;
    driveSet((int16_t)followBase + u, (int16_t)followBase - u);
  }

  // 출발 버튼 D19 = PD2, 눌림 = LOW, 30ms 연속이면 확정
  bool raw = !(PIND & _BV(PD2));
  if (raw) { if (btnCount < 30) btnCount++; } else btnCount = 0;
  bool pressed = btnCount >= 30;
  if (pressed && !btnPressed) btnEdge = true;
  btnPressed = pressed;

  // 외관 LED (D40 = PG1)
  static uint16_t ledDiv = 0;
  static bool ledPhase = false;
  if (++ledDiv >= LED_HALF_PERIOD_MS) { ledDiv = 0; ledPhase = !ledPhase; }
  bool on = ledMode == LedMode::On || (ledMode == LedMode::Blink4Hz && !ledPhase);
  if (on) PORTG |= _BV(PG1); else PORTG &= ~_BV(PG1);

  liftTick1ms();
}

uint8_t lineBits() { return bits; }

bool lineEventTake() {
  noInterrupts();
  bool e = eventLatched;
  eventLatched = false;
  interrupts();
  return e;
}

void lineEventClear() { lineEventTake(); }

uint16_t lineLostMs() {
  noInterrupts();
  uint16_t v = allWhiteMs;
  interrupts();
  return v;
}

void followStart(uint8_t baseSpeed) {
  noInterrupts();
  followBase = baseSpeed;
  lastErr = 0;
  mode = DriveMode::Follow;
  interrupts();
}

void followSpeed(uint8_t baseSpeed) { followBase = baseSpeed; }

void manualDrive(int16_t left, int16_t right) {
  noInterrupts();
  mode = DriveMode::Manual;
  interrupts();
  driveSet(left, right);
}

bool startButtonTake() {
  noInterrupts();
  bool e = btnEdge;
  btnEdge = false;
  interrupts();
  return e;
}

void ledSet(LedMode m) { ledMode = m; }

uint32_t ticks() {
  noInterrupts();
  uint32_t t = tickCount;
  interrupts();
  return t;
}

// ---------------- 초음파 (ECHO = D3 = INT5) ----------------
static volatile uint32_t echoRise = 0;
static volatile uint16_t echoUs = 0;
static volatile bool echoDone = false;
static uint32_t lastTrig = 0;
static uint16_t lastMm = 0;

static void echoIsr() {
  if (PINE & _BV(PE5)) echoRise = micros();
  else {
    uint32_t w = micros() - echoRise;
    echoUs = w > 30000 ? 0 : (uint16_t)w;
    echoDone = true;
  }
}

void sonarUpdate() {
  if (echoDone) {
    noInterrupts();
    uint16_t us = echoUs;
    echoDone = false;
    interrupts();
    lastMm = us ? (uint16_t)(us * 0.1715f) : 0;  // 음속 343m/s 왕복
  }
  if (millis() - lastTrig >= 50) {
    lastTrig = millis();
    digitalWrite(PIN_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_TRIG, LOW);
  }
}

uint16_t sonarMm() { return lastMm; }

uint16_t irWaferAdc() {
  uint16_t s[5];
  for (uint8_t i = 0; i < 5; i++) s[i] = analogRead(PIN_IR_WAFER);
  for (uint8_t i = 1; i < 5; i++)
    for (uint8_t j = i; j > 0 && s[j - 1] > s[j]; j--) { uint16_t t = s[j]; s[j] = s[j - 1]; s[j - 1] = t; }
  return s[2];
}

void senseInit() {
  pinMode(PIN_LINE_L, INPUT);
  pinMode(PIN_LINE_C, INPUT);
  pinMode(PIN_LINE_R, INPUT);
  pinMode(PIN_START_BTN, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_ECHO), echoIsr, CHANGE);
  // Timer1: CTC(WGM 0100), 분주 64, OCR1A 249 -> 16MHz/64/250 = 1kHz
  TCCR1A = 0;
  TCCR1B = _BV(WGM12) | _BV(CS11) | _BV(CS10);
  OCR1A = 249;
  TIMSK1 |= _BV(OCIE1A);
}
