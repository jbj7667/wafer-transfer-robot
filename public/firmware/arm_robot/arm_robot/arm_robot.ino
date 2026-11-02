// arm_robot — 팔 방식(θ-R-Z) 벤치 시제품 펌웨어 골격 (Arduino Mega 2560)
// 시리얼 콘솔 115200. 3축 동시 스텝은 stepper3(Timer3 ISR), 기구학은 arm_kin, 핀/치수는 config.h.
// 명령: h | g th R Z | b n | p | x | s | rep n b1 b2 | trim ax steps | speed ax sps | j ax steps | hc psi
#include <math.h>
#include <string.h>
#include "config.h"
#include "stepper3.h"
#include "arm_kin.h"

static const char* const AXN[3] = {"TH", "R", "Z"};
static const int8_t HOME_DIR[3] = {HOME_DIR_TH, HOME_DIR_R, HOME_DIR_Z};

static bool homed = false;
static bool aborted = false;
static int32_t trimSteps[3] = {0, 0, 0};
static float headingPsi = 0.0f;  // 헤딩 오차 ψ [deg], 양수 = 로봇이 반시계로 틀어짐

// ---------------- 단위 변환 ----------------
static float toCoord(uint8_t a, int32_t steps) { return HOME_COORD[a] + (float)steps / STEPS_PER_UNIT[a]; }
static int32_t toSteps(uint8_t a, float coord) {
  return lroundf((coord - HOME_COORD[a]) * STEPS_PER_UNIT[a]) + trimSteps[a];
}

static void applySoftLimits(bool on) {
  const float lo[3] = {TH_MIN_DEG, R_PHI_MIN_DEG, Z_MIN_MM};
  const float hi[3] = {TH_MAX_DEG, R_PHI_MAX_DEG, Z_MAX_MM};
  for (uint8_t a = 0; a < 3; a++) {
    int32_t s0 = lroundf((lo[a] - HOME_COORD[a]) * STEPS_PER_UNIT[a]);
    int32_t s1 = lroundf((hi[a] - HOME_COORD[a]) * STEPS_PER_UNIT[a]);
    if (s0 > s1) { int32_t t = s0; s0 = s1; s1 = t; }
    s3SetSoftLimits(a, s0, s1, on);
  }
}

// ---------------- 대기·중단 ----------------
static void pollAbort() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'x' || c == 'X') aborted = true;
  }
}

static bool waitDone(uint32_t timeoutMs) {
  uint32_t t0 = millis();
  while (s3AnyBusy()) {
    pollAbort();
    if (aborted) { s3StopAll(); Serial.println(F("ABORT")); return false; }
    if (s3Faults()) {
      s3StopAll();
      Serial.print(F("FAULT end-limit mask=")); Serial.println(s3Faults());
      return false;
    }
    if (millis() - t0 > timeoutMs) { s3StopAll(); Serial.println(F("FAULT timeout")); return false; }
  }
  return true;
}

static bool waitAxis(uint8_t a, uint32_t timeoutMs) {
  uint32_t t0 = millis();
  while (s3Busy(a)) {
    pollAbort();
    if (aborted) { s3StopAll(); Serial.println(F("ABORT")); return false; }
    if (s3Faults()) { s3StopAll(); Serial.println(F("FAULT end-limit")); return false; }
    if (millis() - t0 > timeoutMs) { s3StopAll(); Serial.print(F("FAULT timeout ")); Serial.println(AXN[a]); return false; }
  }
  return true;
}

// ---------------- 홈잉 (Z -> R -> TH, arm_option §5.3) ----------------
static bool homeAxis(uint8_t a) {
  const HomeCfg& h = HOME_CFG[a];
  const int8_t d = HOME_DIR[a];
  const float spu = STEPS_PER_UNIT[a];
  const uint32_t maxS = (uint32_t)(h.maxSearch * spu);
  const uint32_t back = (uint32_t)(h.backoff * spu);
  const uint32_t tmo = HOME_AXIS_TIMEOUT_MS;
  Serial.print(F("[home] ")); Serial.print(AXN[a]); Serial.print(F(" fast=")); Serial.print(h.fast);
  Serial.print(F(" slow=")); Serial.println(h.slow);
  s3SetPos(a, 0);

  if (s3Limit(a)) {  // 이미 눌려 있음 -> 먼저 해제
    Serial.println(F("  switch pressed -> release"));
    if (!s3Seek(a, -d, maxS, h.slow, S3_STOP_ON_RELEASE) || !waitAxis(a, tmo)) return false;
    if (!s3HitLatched(a)) { Serial.println(F("FAULT release not found")); return false; }
    if (!s3MoveTo(a, s3Pos(a) - d * (int32_t)back, h.slow) || !waitAxis(a, tmo)) return false;
  }
  Serial.println(F("  fast approach"));
  if (!s3Seek(a, d, maxS, h.fast, S3_STOP_ON_HIT) || !waitAxis(a, tmo)) return false;
  if (!s3HitLatched(a) && h.reverseSearch) {
    Serial.println(F("  not found -> reverse search"));
    if (!s3Seek(a, -d, 2 * maxS, h.fast, S3_STOP_ON_HIT) || !waitAxis(a, tmo)) return false;
    if (!s3HitLatched(a)) { Serial.println(F("FAULT switch not found")); return false; }
    // 캠을 통과해 반대편으로 나온 뒤 정방향으로 다시 접근
    if (!s3Seek(a, -d, maxS, h.slow, S3_STOP_ON_RELEASE) || !waitAxis(a, tmo)) return false;
    if (!s3MoveTo(a, s3Pos(a) - d * (int32_t)back, h.slow) || !waitAxis(a, tmo)) return false;
    Serial.println(F("  fast approach (retry)"));
    if (!s3Seek(a, d, 2 * maxS, h.fast, S3_STOP_ON_HIT) || !waitAxis(a, tmo)) return false;
  }
  if (!s3HitLatched(a)) { Serial.println(F("FAULT switch not found")); return false; }

  Serial.println(F("  backoff"));
  if (!s3MoveTo(a, s3Pos(a) - d * (int32_t)back, h.slow) || !waitAxis(a, tmo)) return false;
  if (s3Limit(a)) { Serial.println(F("FAULT switch still pressed after backoff")); return false; }
  Serial.println(F("  slow re-approach"));
  if (!s3Seek(a, d, 2 * back + (uint32_t)spu, h.slow, S3_STOP_ON_HIT) || !waitAxis(a, tmo)) return false;
  if (!s3HitLatched(a)) { Serial.println(F("FAULT slow approach no hit")); return false; }

  s3SetPos(a, 0);  // 영점 = 스위치 접점
  Serial.print(F("  zero set -> ")); Serial.println(toCoord(a, 0), 2);
  if (h.park > 0.0f) {
    if (!s3MoveTo(a, -d * (int32_t)(h.park * spu), h.fast) || !waitAxis(a, tmo)) return false;
  }
  return true;
}

static void homeAll() {
  if (s3IsAsleep()) s3SleepAll(false);
  homed = false;
  aborted = false;
  s3StopAll();
  s3ClearFaults();
  applySoftLimits(false);
  uint32_t t0 = millis();
  const uint8_t order[3] = {AX_Z, AX_R, AX_TH};
  for (uint8_t i = 0; i < 3; i++) {
    if (!homeAxis(order[i])) {
      s3StopAll();
      Serial.print(F("HOME FAIL at ")); Serial.println(AXN[order[i]]);
      return;
    }
  }
  applySoftLimits(true);
  homed = true;
  Serial.print(F("HOME OK in ")); Serial.print(millis() - t0); Serial.println(F(" ms"));
}

// ---------------- 이동 ----------------
static void printPos() {
  for (uint8_t a = 0; a < 3; a++) {
    int32_t p = s3Pos(a);
    Serial.print(AXN[a]); Serial.print('='); Serial.print(p);
    Serial.print(F(" ("));
    Serial.print(toCoord(a, p), 2);
    Serial.print(a == AX_Z ? F("mm) ") : F("deg) "));
  }
  Serial.print(F("Rcd="));
  Serial.print(kinRcdFromPhi(toCoord(AX_R, s3Pos(AX_R))), 1);
  Serial.print(F(" lim="));
  for (uint8_t a = 0; a < 3; a++) Serial.print(s3Limit(a) ? '1' : '0');
  Serial.print(F(" isr="));
  Serial.print(s3IsrLoadPct());
  Serial.println('%');
}

// v[a] 가 NAN 이면 그 축은 그대로 둔다. 모든 축 동시 이동 후 정착까지 대기.
static bool moveGoal(const float v[3]) {
  if (!homed) { Serial.println(F("not homed (h)")); return false; }
  int32_t tgt[3];
  uint32_t est = 0;
  for (uint8_t a = 0; a < 3; a++) {
    if (isnan(v[a])) { tgt[a] = s3Pos(a); continue; }
    tgt[a] = toSteps(a, v[a]);
    int32_t d = tgt[a] - s3Pos(a);
    uint32_t e = s3EstimateMs(a, d < 0 ? -d : d);
    if (e > est) est = e;
  }
  Serial.print(F("move"));
  for (uint8_t a = 0; a < 3; a++) {
    if (isnan(v[a])) continue;
    Serial.print(' '); Serial.print(AXN[a]); Serial.print('='); Serial.print(v[a], 1);
    Serial.print('['); Serial.print(tgt[a]); Serial.print(']');
  }
  Serial.print(F(" est=")); Serial.print(est); Serial.println(F("ms"));
  aborted = false;
  s3ClearFaults();
  for (uint8_t a = 0; a < 3; a++) {
    if (isnan(v[a])) continue;
    if (!s3MoveTo(a, tgt[a])) {
      s3StopAll();
      Serial.print(F("REJECT ")); Serial.print(AXN[a]); Serial.println(F(" (soft limit/busy/sleep)"));
      return false;
    }
  }
  uint32_t t0 = millis();
  if (!waitDone(est * 2 + 1500)) return false;
  Serial.print(F("  took=")); Serial.print(millis() - t0); Serial.println(F("ms"));
  delay(SETTLE_MS);
  return true;
}

// 한 방향 접근 규칙(arm_option §2.5)으로 베이스 n 의 픽 자세로 이동.
// 순서: R 운반 반경으로 접기 -> TH,Z (TH 는 +접근각 위로 간 뒤) -> TH 최종(감소 방향) -> R 접근 -> R 최종(펴는 방향)
static bool goBase(uint8_t n) {
  const BasePose* b = kinBase(n);
  if (!b) { Serial.println(F("base 1..6")); return false; }
  ArmPose p, c;
  KinStatus st = kinSolve(kinCorrectHeading(b->theta, headingPsi), b->r_cd, p);
  if (st != KIN_OK) { Serial.print(F("kin: ")); Serial.println(kinStatusName(st)); return false; }
  kinSolve(0.0f, CARRY_R_CD, c);
  float z = kinBasePickZ(*b);
  float phiNow = toCoord(AX_R, s3Pos(AX_R));
  Serial.print(F("base ")); Serial.print(n); Serial.print(F(" th=")); Serial.print(p.th_deg, 1);
  Serial.print(F(" phi=")); Serial.print(p.phi_deg, 1); Serial.print(F(" z=")); Serial.println(z, 1);

  float s1[3] = {NAN, phiNow < c.phi_deg ? c.phi_deg : phiNow, NAN};
  if (!moveGoal(s1)) return false;
  float s2[3] = {p.th_deg + TH_APPROACH_DEG, NAN, z};
  if (!moveGoal(s2)) return false;
  float s3[3] = {p.th_deg, NAN, NAN};
  if (!moveGoal(s3)) return false;
  float s4[3] = {NAN, p.phi_deg + R_APPROACH_DEG, NAN};
  if (!moveGoal(s4)) return false;
  float s5[3] = {NAN, p.phi_deg, NAN};
  return moveGoal(s5);
}

static void printArrival(uint16_t i, uint16_t n, uint8_t base) {
  Serial.print(F("ARR ")); Serial.print(i); Serial.print('/'); Serial.print(n);
  Serial.print(F(" b=")); Serial.print(base);
  Serial.print(F(" steps TH=")); Serial.print(s3Pos(AX_TH));
  Serial.print(F(" R=")); Serial.print(s3Pos(AX_R));
  Serial.print(F(" Z=")); Serial.println(s3Pos(AX_Z));
}

static bool dwell(uint16_t ms) {
  uint32_t t0 = millis();
  while (millis() - t0 < ms) {
    pollAbort();
    if (aborted) { Serial.println(F("ABORT")); return false; }
  }
  return true;
}

static void cmdRep(uint16_t n, uint8_t b1, uint8_t b2) {
  if (!kinBase(b1) || !kinBase(b2) || n == 0) { Serial.println(F("rep n b1 b2")); return; }
  aborted = false;
  Serial.println(F("REP start: 도착마다 손으로 표시 가능 (대기 REP_DWELL_MS)"));
  for (uint16_t i = 1; i <= n; i++) {
    const uint8_t seq[2] = {b1, b2};
    for (uint8_t k = 0; k < 2; k++) {
      if (!goBase(seq[k])) { Serial.println(F("REP stop")); return; }
      printArrival(i, n, seq[k]);
      if (!dwell(REP_DWELL_MS)) return;
    }
  }
  Serial.println(F("REP done"));
}

// ---------------- 콘솔 ----------------
static uint8_t parseAxis(const char* s) {
  if (!s) return 255;
  if (!strcasecmp(s, "th") || s[0] == '0') return AX_TH;
  if (!strcasecmp(s, "r") || s[0] == '1') return AX_R;
  if (!strcasecmp(s, "z") || s[0] == '2') return AX_Z;
  return 255;
}

static void printHelp() {
  Serial.println(F("h | g <th> <Rcd> <Z> | b <1..6> | p | x | s | rep <n> <b1> <b2>"));
  Serial.println(F("trim <th|r|z> <steps> | speed <th|r|z> <sps> | j <ax> <steps> | hc <psi>"));
}

static void handleLine(char* line) {
  char* tok = strtok(line, " \t");
  if (!tok) return;
  char c0 = tok[0];
  if (!strcmp(tok, "h")) { homeAll(); }
  else if (!strcmp(tok, "g")) {
    char* a1 = strtok(nullptr, " \t"); char* a2 = strtok(nullptr, " \t"); char* a3 = strtok(nullptr, " \t");
    if (!a3) { Serial.println(F("g <theta> <Rcd> <Z>")); return; }
    ArmPose p;
    KinStatus st = kinSolve(atof(a1), atof(a2), p);
    if (st != KIN_OK) { Serial.print(F("kin: ")); Serial.println(kinStatusName(st)); return; }
    float v[3] = {p.th_deg, p.phi_deg, (float)atof(a3)};
    Serial.print(F("phi=")); Serial.println(p.phi_deg, 2);
    moveGoal(v);
  }
  else if (!strcmp(tok, "b")) { char* a1 = strtok(nullptr, " \t"); if (a1) goBase(atoi(a1)); else Serial.println(F("b <1..6>")); }
  else if (!strcmp(tok, "p")) { printPos(); }
  else if (c0 == 'x' && tok[1] == 0) { s3StopAll(); Serial.println(F("STOP")); }
  else if (!strcmp(tok, "s")) {
    bool toSleep = !s3IsAsleep();
    s3SleepAll(toSleep);
    if (toSleep) homed = false;  // 수면 = 위상 상실, 다시 홈잉 필요
    Serial.println(toSleep ? F("SLEEP (re-home needed)") : F("AWAKE (re-home needed)"));
    homed = false;
  }
  else if (!strcmp(tok, "rep")) {
    char* a1 = strtok(nullptr, " \t"); char* a2 = strtok(nullptr, " \t"); char* a3 = strtok(nullptr, " \t");
    if (!a3) { Serial.println(F("rep <n> <b1> <b2>")); return; }
    cmdRep(atoi(a1), atoi(a2), atoi(a3));
  }
  else if (!strcmp(tok, "trim")) {
    uint8_t a = parseAxis(strtok(nullptr, " \t")); char* a2 = strtok(nullptr, " \t");
    if (a > 2 || !a2) { Serial.println(F("trim <th|r|z> <steps>")); return; }
    trimSteps[a] = atol(a2);
    Serial.print(F("trim ")); Serial.print(AXN[a]); Serial.print('='); Serial.println(trimSteps[a]);
  }
  else if (!strcmp(tok, "speed")) {
    uint8_t a = parseAxis(strtok(nullptr, " \t")); char* a2 = strtok(nullptr, " \t");
    if (a > 2 || !a2) { Serial.println(F("speed <th|r|z> <sps>")); return; }
    s3SetSpeed(a, (uint16_t)atoi(a2));
    Serial.print(F("speed ")); Serial.print(AXN[a]); Serial.print('='); Serial.println(s3GetSpeed(a));
  }
  else if (!strcmp(tok, "j")) {  // 홈잉 전에도 쓸 수 있는 원시 스텝 이동 (소프트 한계 없음)
    uint8_t a = parseAxis(strtok(nullptr, " \t")); char* a2 = strtok(nullptr, " \t");
    if (a > 2 || !a2) { Serial.println(F("j <th|r|z> <steps>")); return; }
    if (homed) { Serial.println(F("j: only before homing")); return; }
    aborted = false;
    s3ClearFaults();
    if (s3MoveTo(a, s3Pos(a) + atol(a2))) waitDone(30000UL);
    printPos();
  }
  else if (!strcmp(tok, "hc")) {
    char* a1 = strtok(nullptr, " \t");
    if (a1) headingPsi = atof(a1);
    Serial.print(F("heading psi=")); Serial.println(headingPsi, 2);
  }
  else { printHelp(); }
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  static const S3AxisPins pins[3] = {
      {PIN_TH_STEP, PIN_TH_DIR, PIN_TH_SLEEP, PIN_TH_HOME, DIR_INV_TH, HOME_DIR_TH, false},
      {PIN_R_STEP, PIN_R_DIR, PIN_R_SLEEP, PIN_R_HOME, DIR_INV_R, HOME_DIR_R, true},
      {PIN_Z_STEP, PIN_Z_DIR, PIN_Z_SLEEP, PIN_Z_LOW, DIR_INV_Z, HOME_DIR_Z, true},
  };
  s3Begin(pins);
  for (uint8_t a = 0; a < 3; a++) {
    s3SetStartRate(a, VMIN[a]);
    s3SetSpeed(a, VMAX[a]);
    s3SetAccel(a, ACCEL[a]);
  }
  Serial.println(F("arm_robot ready (Timer3 20kHz). 'h' = home all"));
  printHelp();
}

void loop() {
  static char buf[LINE_MAX];
  static uint8_t n = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r' || c == '\n') {
      if (n) { buf[n] = 0; n = 0; handleLine(buf); }
    } else if (n < LINE_MAX - 1) {
      buf[n++] = c;
    }
  }
  if (s3Faults() && !s3AnyBusy()) {
    Serial.print(F("FAULT end-limit mask=")); Serial.println(s3Faults());
    s3ClearFaults();
    homed = false;
  }
}
