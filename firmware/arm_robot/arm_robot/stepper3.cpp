#include "stepper3.h"
#include <math.h>

namespace {

struct Axis {
  volatile uint8_t* stepPort;
  volatile uint8_t* dirPort;
  volatile uint8_t* limPin;
  uint8_t stepMask, dirMask, limMask;
  bool dirInvert, limitIsEnd;
  int8_t homeDir;
  uint8_t sleepPin;

  volatile int32_t pos, target;
  volatile int8_t dir;
  volatile bool active, pulsed;
  volatile uint16_t phase, inc;
  volatile uint32_t vq;          // 현재 속도 [step/s << 8]
  volatile uint16_t cap;         // 이번 이동의 최고 속도
  volatile S3Stop mode;
  volatile bool hit;
  volatile bool limState;
  volatile uint8_t limCnt;

  uint16_t vmax, vmin, accel;
  int32_t minS, maxS;
  bool softOn;
};

Axis ax[S3_AXES];
volatile uint8_t faults = 0;
volatile uint8_t tickN = 0;
volatile uint8_t maxCnt = 0;
bool asleep = false;

constexpr uint8_t DEBOUNCE_MS = 3;

// 20 kHz 틱당 위상 증분 = v * 65536 / 20000 = v * 3.2768  (13421/4096 = 3.27686)
inline uint16_t rateToInc(uint16_t v) {
  uint32_t r = ((uint32_t)v * 13421UL) >> 12;
  return r > 32768UL ? 32768 : (uint16_t)r;
}

inline void setDirPin(Axis& a, int8_t d) {
  bool high = (d > 0) != a.dirInvert;
  uint8_t sr = SREG;
  cli();
  if (high) *a.dirPort |= a.dirMask; else *a.dirPort &= ~a.dirMask;
  SREG = sr;
}

inline void haltAxis(Axis& a) {
  a.active = false;
  a.inc = 0;
  a.vq = 0;
  a.target = a.pos;
}

// 1 ms 마다 축별 호출: 사다리꼴 속도 갱신
inline void profile(Axis& a) {
  if (!a.active) return;
  uint16_t acc = a.accel;
  int32_t rem = a.target - a.pos;
  if (rem < 0) rem = -rem;
  uint16_t v = (uint16_t)(a.vq >> 8);
  uint32_t dvq = ((uint32_t)acc << 8) / 1000UL;
  uint32_t capq = (uint32_t)a.cap << 8;
  uint32_t minq = (uint32_t)a.vmin << 8;
  // 정지에 필요한 거리 v^2/(2a) 이상 남지 않았으면 감속 (유한 탐색에서도 동일)
  uint32_t stopDist = ((uint32_t)v * v) / (2UL * acc);
  uint32_t q = a.vq;
  if ((uint32_t)rem <= stopDist + 1) {
    q = (q > minq + dvq) ? q - dvq : minq;
  } else if (q < capq) {
    q = (q + dvq < capq) ? q + dvq : capq;
  } else {
    q = capq;
  }
  a.vq = q;
  a.inc = rateToInc((uint16_t)(q >> 8));
}

inline void pollLimit(Axis& a, uint8_t idx) {
  bool raw = !(*a.limPin & a.limMask);  // 눌림 = LOW
  if (raw) {
    if (a.limCnt < DEBOUNCE_MS) a.limCnt = a.limCnt + 1;
    if (a.limCnt >= DEBOUNCE_MS) a.limState = true;
  } else {
    if (a.limCnt > 0) a.limCnt = a.limCnt - 1;
    if (a.limCnt == 0) a.limState = false;
  }
  if (!a.active) return;
  if (a.mode == S3_STOP_ON_HIT && a.limState) {
    a.hit = true;
    haltAxis(a);
  } else if (a.mode == S3_STOP_ON_RELEASE && !a.limState) {
    a.hit = true;
    haltAxis(a);
  } else if (a.mode == S3_STOP_NONE && a.limitIsEnd && a.limState && a.dir == a.homeDir) {
    faults = faults | (uint8_t)(S3_FAULT_END_LIMIT << idx);
    haltAxis(a);
  }
}

}  // namespace

ISR(TIMER3_COMPA_vect) {
  // 1) 이전 틱의 STEP 펄스 하강 (펄스 폭 = 1틱 = 50 us)
  for (uint8_t i = 0; i < S3_AXES; i++) {
    Axis& a = ax[i];
    if (a.pulsed) {
      *a.stepPort &= ~a.stepMask;
      a.pulsed = false;
    }
  }
  // 2) DDA: 위상 누산기가 넘치면 스텝
  for (uint8_t i = 0; i < S3_AXES; i++) {
    Axis& a = ax[i];
    if (!a.active) continue;
    uint16_t p = a.phase;
    uint16_t np = (uint16_t)(p + a.inc);
    a.phase = np;
    if (np < p) {
      *a.stepPort |= a.stepMask;
      a.pulsed = true;
      a.pos = a.pos + a.dir;
      if (a.pos == a.target) haltAxis(a);
    }
  }
  // 3) 1 ms 구간 작업을 틱 슬롯에 분산
  uint8_t t = tickN;
  if (t < S3_AXES) profile(ax[t]);
  else if (t == 5) {
    for (uint8_t i = 0; i < S3_AXES; i++) pollLimit(ax[i], i);
  }
  t++;
  tickN = (t >= 20) ? 0 : t;
  uint8_t c = (uint8_t)TCNT3;  // 2 MHz 카운트, TOP=99 이므로 99 가 100%
  if (c > maxCnt) maxCnt = c;
}

void s3Begin(const S3AxisPins pins[S3_AXES]) {
  for (uint8_t i = 0; i < S3_AXES; i++) {
    Axis& a = ax[i];
    const S3AxisPins& p = pins[i];
    pinMode(p.step, OUTPUT);
    pinMode(p.dir, OUTPUT);
    pinMode(p.sleep, OUTPUT);
    pinMode(p.limit, INPUT_PULLUP);
    digitalWrite(p.step, LOW);
    digitalWrite(p.sleep, HIGH);  // DRV8834: HIGH = 동작
    a.stepPort = portOutputRegister(digitalPinToPort(p.step));
    a.stepMask = digitalPinToBitMask(p.step);
    a.dirPort = portOutputRegister(digitalPinToPort(p.dir));
    a.dirMask = digitalPinToBitMask(p.dir);
    a.limPin = portInputRegister(digitalPinToPort(p.limit));
    a.limMask = digitalPinToBitMask(p.limit);
    a.dirInvert = p.dirInvert;
    a.limitIsEnd = p.limitIsEnd;
    a.homeDir = p.homeDir;
    a.sleepPin = p.sleep;
    a.pos = a.target = 0;
    a.dir = 1;
    a.active = a.pulsed = false;
    a.phase = a.inc = 0;
    a.vq = 0;
    a.mode = S3_STOP_NONE;
    a.hit = a.limState = false;
    a.limCnt = 0;
    a.vmax = 500;
    a.vmin = 100;
    a.accel = 3000;
    a.cap = a.vmax;
    a.softOn = false;
    a.minS = a.maxS = 0;
  }
  asleep = false;
  // Timer3 CTC, 분주 8 (2 MHz), TOP = 99 -> 20 kHz
  noInterrupts();
  TCCR3A = 0;
  TCCR3B = _BV(WGM32) | _BV(CS31);
  OCR3A = (uint16_t)(2000000UL / S3_TICK_HZ - 1);
  TCNT3 = 0;
  TIMSK3 = _BV(OCIE3A);
  interrupts();
}

void s3SetSpeed(uint8_t a, uint16_t v) {
  if (v > S3_RATE_ABS_MAX) v = S3_RATE_ABS_MAX;
  if (v < ax[a].vmin) v = ax[a].vmin;
  ax[a].vmax = v;
}
void s3SetStartRate(uint8_t a, uint16_t v) { ax[a].vmin = v < 1 ? 1 : v; }
void s3SetAccel(uint8_t a, uint16_t acc) { ax[a].accel = acc < 100 ? 100 : acc; }
uint16_t s3GetSpeed(uint8_t a) { return ax[a].vmax; }

void s3SetSoftLimits(uint8_t a, int32_t minS, int32_t maxS, bool enable) {
  noInterrupts();
  ax[a].minS = minS;
  ax[a].maxS = maxS;
  ax[a].softOn = enable;
  interrupts();
}

static bool startMove(uint8_t i, int32_t target, uint16_t cap, S3Stop mode) {
  Axis& a = ax[i];
  if (asleep) return false;
  uint8_t sr = SREG;
  cli();
  int32_t d = target - a.pos;
  if (d == 0) {
    SREG = sr;
    return true;
  }
  int8_t nd = d > 0 ? 1 : -1;
  if (a.active && (nd != a.dir || mode != S3_STOP_NONE)) {
    SREG = sr;
    return false;
  }
  if (cap == 0 || cap > a.vmax) cap = a.vmax;
  if (mode != S3_STOP_NONE && cap > S3_RATE_ABS_MAX) cap = S3_RATE_ABS_MAX;
  if (cap < a.vmin) cap = a.vmin;
  a.target = target;
  a.mode = mode;
  a.hit = false;
  a.cap = cap;
  if (!a.active) {
    a.dir = nd;
    SREG = sr;
    setDirPin(a, nd);  // DIR 를 먼저 확정한 뒤 활성화 (ISR 은 active 일 때만 스텝)
    cli();
    a.vq = (uint32_t)a.vmin << 8;
    a.inc = rateToInc(a.vmin);
    a.phase = 0;
    a.active = true;
  }
  SREG = sr;
  return true;
}

bool s3MoveTo(uint8_t i, int32_t target, uint16_t cap) {
  Axis& a = ax[i];
  if (a.softOn && (target < a.minS || target > a.maxS)) return false;
  return startMove(i, target, cap, S3_STOP_NONE);
}

bool s3Seek(uint8_t i, int8_t dir, uint32_t maxSteps, uint16_t cap, S3Stop mode) {
  int32_t t = s3Pos(i) + (int32_t)dir * (int32_t)maxSteps;
  return startMove(i, t, cap, mode);
}

void s3Stop(uint8_t i) {
  uint8_t sr = SREG;
  cli();
  haltAxis(ax[i]);
  SREG = sr;
}

void s3StopAll() {
  for (uint8_t i = 0; i < S3_AXES; i++) s3Stop(i);
}

bool s3Busy(uint8_t i) { return ax[i].active; }
bool s3AnyBusy() {
  for (uint8_t i = 0; i < S3_AXES; i++)
    if (ax[i].active) return true;
  return false;
}

int32_t s3Pos(uint8_t i) {
  uint8_t sr = SREG;
  cli();
  int32_t p = ax[i].pos;
  SREG = sr;
  return p;
}

void s3SetPos(uint8_t i, int32_t p) {
  uint8_t sr = SREG;
  cli();
  ax[i].pos = p;
  if (!ax[i].active) ax[i].target = p;
  SREG = sr;
}

bool s3Limit(uint8_t i) { return ax[i].limState; }
bool s3HitLatched(uint8_t i) { return ax[i].hit; }
uint8_t s3Faults() { return faults; }
void s3ClearFaults() { faults = 0; }
uint16_t s3IsrLoadPct() {
  uint8_t m = maxCnt;
  return m;  // TOP=99 -> 카운트 값이 곧 퍼센트
}

uint32_t s3EstimateMs(uint8_t i, uint32_t steps) {
  if (steps == 0) return 0;
  float v = ax[i].vmax, acc = ax[i].accel;
  float d = (float)steps;
  float da = v * v / acc;  // 가속+감속 합 거리
  float t = (d >= da) ? d / v + v / acc : 2.0f * sqrtf(d / acc);
  return (uint32_t)(t * 1000.0f) + 1;
}

void s3SleepAll(bool sleep) {
  if (sleep) s3StopAll();
  asleep = sleep;
  for (uint8_t i = 0; i < S3_AXES; i++) digitalWrite(ax[i].sleepPin, sleep ? LOW : HIGH);
  if (!sleep) delay(2);  // DRV8834 기상 시간
}

bool s3IsAsleep() { return asleep; }
