// wafer_robot.ino — 웨이퍼 이송로봇 메인: 상태머신(대기/주행/도착)과 임무 계획.
//
// 구조
//   Timer1 1kHz : 라인센서·이벤트·PD 추종·버튼·LED·승강 가감속  (sense.cpp)
//   Timer3      : 승강 스테퍼 스텝 펄스                          (lift.cpp)
//   Timer5      : 주행 PWM                                       (drive.cpp)
//   loop()      : 동작 큐(Action) 실행 + 큐가 비면 다음 단계를 계획(planNext)
//
// 경로 모델: 방위 N/E/S/W, 행 0=하단(y480) 1=중단 2=상단(y130).
// 정지선 이벤트에서는 포크가 기둥 앞 FORK_POCKET_AHEAD_MM 근처에 있고, 넥 접촉 스위치가 눌릴 때까지 크리프한다.
// 시퀀스: mechanism.md §4. 모든 180도 회전은 남쪽 경유(W->E 좌회전, E->W 우회전).

#include "config.h"
#include "drive.h"
#include "lift.h"
#include "sense.h"
#include "comm.h"

// ---------------- 동작 타입 ----------------
// (Arduino 자동 프로토타입이 함수 앞에 삽입되므로 Action은 첫 함수보다 위에 정의해야 한다)
enum ActType : uint8_t {
  A_FOLLOW, A_FWD, A_TURN, A_TURN_PARTIAL, A_LIFT_TO, A_LIFT_WAIT, A_CREEP, A_CREEP_TIMED, A_PROBE
};
struct Action {
  ActType type;
  int16_t a;  // FOLLOW: 1=기둥 근처 감속 / FWD: mm(음수=후진) / TURN·TURN_PARTIAL: 목표 방위 / LIFT_TO: mm
};

// ---------------- 상위 상태 ----------------
enum class Top : uint8_t { Boot, Homing, SelfTest, Idle, Run, Arrived, Fault };
static Top top = Top::Boot;
static uint32_t runStartMs = 0;

static const char *topName(Top t) {
  switch (t) {
    case Top::Boot: return "BOOT";
    case Top::Homing: return "HOMING";
    case Top::SelfTest: return "SELFTEST";
    case Top::Idle: return "IDLE";
    case Top::Run: return "RUN";
    case Top::Arrived: return "ARRIVED";
    default: return "FAULT";
  }
}

static void setTop(Top t) {
  top = t;
  commSendState(topName(t));
  switch (t) {
    case Top::Idle:
    case Top::Arrived:
    case Top::Homing:
    case Top::SelfTest:
      ledSet(LedMode::Blink4Hz);  // 시작·도착 구역: 초당 4회 점멸 (추가기능 5)
      break;
    case Top::Fault:
      ledSet(LedMode::On);
      break;
    default:
      ledSet(LedMode::Off);       // 이동 중 소등
  }
  // 주행 중 눌린 버튼 엣지가 남아 있으면 도착·고장 직후 곧바로 재원점이 시작되므로 비운다
  if (t == Top::Idle || t == Top::Arrived || t == Top::Fault) startButtonTake();
}

// ---------------- 방위 ----------------
enum Heading : uint8_t { N = 0, E = 1, S = 2, W = 3 };
static uint8_t heading = E;  // 출발선에서 동쪽을 보고 출발

// ---------------- 동작 큐 ----------------
constexpr uint8_t Q_SIZE = 24;
static Action q[Q_SIZE];
static uint8_t qHead = 0, qLen = 0;
static bool actActive = false;
static uint32_t actT0 = 0, actDur = 0;
static bool probeResult = false;
static uint16_t creepMs[3] = {0, 0, 0};  // 행별 크리프(스위치 눌림까지) 시간. 놓는 쪽 A_CREEP_TIMED가 재사용
static int8_t pivotDir = 1;              // +1 = 우회전, -1 = 좌회전

// 선 이탈 복구(A_FOLLOW 내부 하위 상태)
enum SearchPhase : uint8_t { SR_NONE, SR_BRAKE1, SR_PIVOT1, SR_BRAKE2, SR_PIVOT2 };
static SearchPhase searchPhase = SR_NONE;
static uint32_t searchT0 = 0;
static int8_t searchDir = 1;             // 첫 탐색 방향(+1 = 우회전)

static void push(ActType t, int16_t a = 0) {
  if (qLen < Q_SIZE) {
    q[(qHead + qLen) % Q_SIZE] = {t, a};
    qLen++;
  }
}

// ---------------- 임무 계획 ----------------
enum Phase : uint8_t { P_START, P_ROW_FIRST, P_FIRST_PROBED, P_SECOND_PROBED, P_ROW_DONE, P_HOME, P_END };
static Phase phase = P_START;
static uint8_t row = 0;
static uint8_t moved = 0;
static const uint8_t FIRST_SIDE = W;  // 예선 웨이퍼는 왼쪽. 본선도 왼쪽부터 확인

static float underWafer() { return POST_TOP_MM[row] - UNDER_WAFER_MM; }
static float carry() { return POST_TOP_MM[row] + CARRY_MM; }
static float clearH() { return POST_TOP_MM[row] + CLEAR_MM; }

// 교차점에서 다른 방위로 회전: 바퀴축을 교차 중심에 맞춘 뒤 회전.
// 상단 행에서 북쪽으로 도착해 동/서로 돌 때는 전진하지 않고 부분 회전(포크 끝이 경계 밖으로 나가는 것을 방지).
static void turnAtCrossing(uint8_t h) {
  if (row == 2 && (h == E || h == W)) {
    push(A_TURN_PARTIAL, h);
    return;
  }
  push(A_FWD, SENSOR_AHEAD_MM);
  push(A_TURN, h);
}

// 정지선 도착 후: 아래 높이 -> 넥 접촉 크리프 -> 감지
static void pushPick() {
  push(A_LIFT_WAIT);                          // 접근 중 올려 둔 높이 도달 확인
  push(A_LIFT_TO, (int16_t)underWafer());
  push(A_LIFT_WAIT);
  push(A_CREEP);
  push(A_PROBE);
}

// 현재 정지선(포크 아래 웨이퍼 있음)에서 집어 맞은편 기둥에 놓고 다시 교차점으로 돌아온다
static void deliverToOpposite(uint8_t pickSide) {
  uint8_t back = (pickSide + 2) & 3;
  push(A_LIFT_TO, (int16_t)carry());
  push(A_LIFT_WAIT);
  push(A_FWD, -(int16_t)RETREAT_MM);
  push(A_TURN, back);                 // 180도 (남쪽 경유)
  push(A_FOLLOW, 0);                  // 트렁크 교차점
  push(A_FWD, CROSS_PASS_MM);         // 교차점 통과
  push(A_FOLLOW, 1);                  // 맞은편 정지선 (운반 높이 유지)
  push(A_CREEP_TIMED);                // 기록한 크리프 시간만큼 전진 (포크가 기둥 위라 스위치는 안 눌림)
  push(A_LIFT_TO, (int16_t)underWafer());  // 내려놓기
  push(A_LIFT_WAIT);
  push(A_FWD, -(int16_t)RETREAT_MM);
  push(A_LIFT_TO, (int16_t)clearH()); // 회전 전 기둥 윗면 + 5
  push(A_LIFT_WAIT);
  push(A_TURN, pickSide);             // 180도 (남쪽 경유)
  push(A_FOLLOW, 0);                  // 교차점으로 복귀
}

static void planNext() {
  switch (phase) {
    case P_START:
      push(A_FOLLOW, 0);  // 출발선 -> 곡선 -> 트렁크 -> 하단 교차점
      phase = P_ROW_FIRST;
      break;

    case P_ROW_FIRST:
      heading = N;  // 출발선(동쪽) -> 곡선 -> 트렁크: 첫 교차점에서는 북쪽을 보고 있다
      turnAtCrossing(FIRST_SIDE);
      push(A_LIFT_TO, (int16_t)clearH());  // 접근 중 포크가 기둥에 걸리지 않게 (비동기)
      push(A_FOLLOW, 1);
      pushPick();
      phase = P_FIRST_PROBED;
      break;

    case P_FIRST_PROBED:
      if (probeResult) {
        deliverToOpposite(FIRST_SIDE);
        moved++;
        phase = P_ROW_DONE;
      } else {
        uint8_t other = (FIRST_SIDE + 2) & 3;
        push(A_LIFT_TO, (int16_t)clearH());
        push(A_LIFT_WAIT);
        push(A_FWD, -(int16_t)RETREAT_MM);
        push(A_TURN, other);                // 180도 (남쪽 경유)
        push(A_FOLLOW, 0);
        push(A_FWD, CROSS_PASS_MM);
        push(A_FOLLOW, 1);
        pushPick();
        phase = P_SECOND_PROBED;
      }
      break;

    case P_SECOND_PROBED: {
      uint8_t second = (FIRST_SIDE + 2) & 3;
      if (probeResult) {
        deliverToOpposite(second);  // 첫 쪽으로 운반
        moved++;
      } else {  // 이 행에는 웨이퍼가 없다: 교차점으로 돌아가 다음 행
        push(A_LIFT_TO, (int16_t)clearH());
        push(A_LIFT_WAIT);
        push(A_FWD, -(int16_t)RETREAT_MM);
        push(A_TURN, FIRST_SIDE);
        push(A_FOLLOW, 0);
      }
      phase = P_ROW_DONE;
      break;
    }

    case P_ROW_DONE:
      if (row < 2) {
        turnAtCrossing(N);
        push(A_FOLLOW, 0);  // 다음 행 교차점
        row++;
        phase = P_ROW_FIRST;
      } else {
        push(A_LIFT_TO, (int16_t)LIFT_PARK_MM);  // 귀환 전 포크 내림 (비동기, 마지막에 대기)
        turnAtCrossing(S);
        push(A_FOLLOW, 0);  // 중단 교차점
        push(A_FWD, CROSS_PASS_MM);
        push(A_FOLLOW, 0);  // 하단 교차점
        push(A_FWD, CROSS_PASS_MM);
        push(A_FOLLOW, 0);  // 곡선을 지나 출발·도착 끝선
        push(A_FWD, 30);    // 몸체가 끝선을 덮도록
        push(A_LIFT_WAIT);
        phase = P_HOME;
      }
      break;

    case P_HOME:
      phase = P_END;
      break;

    default:
      break;
  }
}

// ---------------- 동작 실행 ----------------
static void fault(const char *why) {
  manualBrake();
  liftStop();
  Serial.print("FAULT ");
  Serial.println(why);
  setTop(Top::Fault);
}

// 제자리 회전 출력: 0에서 SPEED_PIVOT까지 PIVOT_RAMP_MS 동안 선형 증가(각가속도 제한)
static void pivotDrive(uint32_t el) {
  int16_t p = el >= PIVOT_RAMP_MS ? SPEED_PIVOT : (int16_t)((uint32_t)SPEED_PIVOT * el / PIVOT_RAMP_MS);
  manualDrive(pivotDir * p, -pivotDir * p);
}

static void startAction(const Action &x) {
  actActive = true;
  actT0 = millis();
  switch (x.type) {
    case A_FOLLOW:
      searchPhase = SR_NONE;
      lineEventClear();
      followStart(SPEED_CRUISE);
      break;
    case A_FWD: {
      int16_t mm = x.a < 0 ? -x.a : x.a;
      actDur = (uint32_t)(mm / MM_PER_MS_SLOW);
      int16_t s = x.a < 0 ? -(int16_t)SPEED_SLOW : (int16_t)SPEED_SLOW;
      manualDrive(s, s);
      break;
    }
    case A_TURN: {
      uint8_t d = (x.a - heading) & 3;
      if (d == 0) { actActive = false; break; }  // 이미 그 방위
      actDur = d == 2 ? PIVOT_MIN_MS_180 : PIVOT_MIN_MS_90;
      if (d == 3) pivotDir = -1;       // 좌회전
      else if (d == 1) pivotDir = 1;   // 우회전
      else pivotDir = (heading == W) ? -1 : 1;  // 180도: 남쪽 경유 (W->S->E 좌, E->S->W 우, N<->S 임의)
      manualDrive(0, 0);               // 램프 0에서 시작
      break;
    }
    case A_TURN_PARTIAL:
      // 북쪽에서 목표(동/서) 쪽으로 약 55도만 돈다
      actDur = PIVOT_MIN_MS_PARTIAL;
      pivotDir = x.a == W ? -1 : 1;
      manualDrive(0, 0);
      break;
    case A_LIFT_TO:
      liftMoveToMm(x.a);
      actActive = false;  // 비동기: 기다리려면 A_LIFT_WAIT
      break;
    case A_CREEP:
      creepMs[row] = 0;
      manualDrive(SPEED_CREEP, SPEED_CREEP);
      break;
    case A_CREEP_TIMED:
      actDur = creepMs[row];
      manualDrive(SPEED_CREEP, SPEED_CREEP);
      break;
    case A_LIFT_WAIT:
    case A_PROBE:
      break;  // 앞 동작이 제동 중일 수 있으므로 구동 출력을 건드리지 않는다
  }
}

// 선 탐색 회전 출력: 0에서 SPEED_SEARCH까지 램프
static void searchDrive(int8_t dir, uint32_t el) {
  int16_t p = el >= PIVOT_RAMP_MS ? SPEED_SEARCH : (int16_t)((uint32_t)SPEED_SEARCH * el / PIVOT_RAMP_MS);
  manualDrive(dir * p, -dir * p);
}

// A_FOLLOW 안에서 선 이탈 후 탐색: 정지 -> 마지막 쪽 회전(최대 SEARCH_MAX_MS) -> 정지 -> 반대쪽 회전(최대 2배)
// 어느 한 채널이라도 흑이면 추종 재개, 끝까지 못 찾으면 고장.
static void runSearch() {
  uint32_t el = millis() - searchT0;
  if ((searchPhase == SR_PIVOT1 || searchPhase == SR_PIVOT2) && lineBits() != 0) {
    manualBrake();
    searchPhase = SR_NONE;
    lineEventClear();
    followStart(SPEED_SLOW);  // 복귀 직후는 저속으로 수렴
    Serial.println("SEARCH OK");
    return;
  }
  switch (searchPhase) {
    case SR_BRAKE1:
    case SR_BRAKE2:
      if (el >= SEARCH_BRAKE_MS) {
        searchPhase = searchPhase == SR_BRAKE1 ? SR_PIVOT1 : SR_PIVOT2;
        searchT0 = millis();
        manualDrive(0, 0);
      }
      break;
    case SR_PIVOT1:
      searchDrive(searchDir, el);
      if (el >= SEARCH_MAX_MS) {
        manualBrake();
        searchPhase = SR_BRAKE2;
        searchT0 = millis();
      }
      break;
    case SR_PIVOT2:
      searchDrive(-searchDir, el);
      if (el >= 2UL * SEARCH_MAX_MS) fault("line lost");
      break;
    default:
      break;
  }
}

// true = 끝남
static bool runAction(const Action &x) {
  uint32_t el = millis() - actT0;
  switch (x.type) {
    case A_FOLLOW:
      if (searchPhase != SR_NONE) {
        if (el > 15000) fault("follow timeout");
        else runSearch();
        return false;
      }
      if (x.a == 1) {  // 기둥에 가까워지면 감속(정지선 오버슈트 감소)
        uint16_t d = sonarMm();
        followSpeed(d && d < SONAR_SLOW_MM ? SPEED_SLOW : SPEED_CRUISE);  // followStart는 D항 상태를 지우므로 속도만 갱신
      }
      if (lineEventTake()) { manualBrake(); return true; }
      if (lineLostMs() > LINE_LOST_MS) {  // 선 이탈: 정지 후 탐색
        manualBrake();
        searchDir = lineLastSide() >= 0 ? 1 : -1;
        searchPhase = SR_BRAKE1;
        searchT0 = millis();
        Serial.println("SEARCH");
        return false;
      }
      if (el > 15000) fault("follow timeout");
      return false;
    case A_FWD:
      if (el >= actDur) { manualBrake(); return true; }
      return false;
    case A_TURN:
      pivotDrive(el);
      if (el >= actDur && (lineBits() & 0b010)) {
        manualBrake();
        heading = x.a;
        return true;
      }
      if (el > 4000) fault("turn timeout");
      return false;
    case A_TURN_PARTIAL:
      pivotDrive(el);
      if (el >= actDur && (lineBits() & 0b010)) {
        heading = x.a;
        followStart(SPEED_SLOW);  // 멈추지 않고 저속 추종으로 이어 가 방향을 수렴시킨다
        return true;
      }
      if (el > 4000) fault("partial turn timeout");
      return false;
    case A_LIFT_WAIT:
      if (liftFault()) fault("lift");
      return !liftBusy();
    case A_CREEP: {
      if (neckPressed()) {
        creepMs[row] = el > 0xFFFF ? 0xFFFF : (uint16_t)el;
        manualBrake();
        Serial.print("CREEP ");
        Serial.println(el);
        return true;
      }
      uint16_t d = sonarMm();
      if (d && d < CREEP_SONAR_MIN_MM) fault("creep sonar");
      else if (el > CREEP_TIMEOUT_MS) fault("creep timeout");
      return false;
    }
    case A_CREEP_TIMED:
      if (el >= actDur) { manualBrake(); return true; }
      return false;
    case A_PROBE:
      if (el < 80) return false;  // 정지 후 진동 가라앉힘
      probeResult = irWaferAdc() > IR_WAFER_ADC_MIN;
      Serial.print("PROBE ");
      Serial.println(probeResult);
      return true;
    default:
      return true;
  }
}

// ---------------- 자가 점검 (추가기능 F4: 센서로 초기 상태 확인) ----------------
// 원점·대기 높이 도달 직후 한 번: 포크 위 IR 비어 있음, 라인센서 응답, 모터 전압.
// 결과는 "T,항목,결과" 줄로 BLE/USB에 보낸다. IR이 비어 있지 않으면 고장.
static uint32_t selfT0 = 0;

static void selfTestBegin() {
  setTop(Top::SelfTest);
  selfT0 = millis();
  if (irWaferAdc() > IR_WAFER_ADC_MIN) {
    commSendTest("IR", "FAIL");
    fault("fork not empty");
    return;
  }
  commSendTest("IR", "OK");
  commSendTest("VBAT", vbatMotor() > VBAT_MOTOR_LOW ? "OK" : "WARN");
}

static void selfTestUpdate() {
  if (lineBits() != 0) {
    commSendTest("LINE", "OK");
  } else if (lineLostMs() >= SELFTEST_LINE_MS && millis() - selfT0 >= SELFTEST_LINE_MS) {
    commSendTest("LINE", "WARN");  // 경고만 하고 계속
  } else {
    return;  // 아직 판정 중
  }
  setTop(Top::Idle);
}

static void resetMission() {
  qHead = qLen = 0;
  actActive = false;
  phase = P_START;
  row = 0;
  moved = 0;
  heading = E;
}

static void runMission() {
  if (millis() - runStartMs > RUN_TIME_LIMIT_MS) { fault("time"); return; }
  if (actActive) {
    if (runAction(q[qHead])) {
      actActive = false;
      qHead = (qHead + 1) % Q_SIZE;
      qLen--;
    }
    return;
  }
  if (qLen == 0) {
    if (phase == P_END) {
      manualBrake();
      setTop(Top::Arrived);
      return;
    }
    planNext();
    return;
  }
  startAction(q[qHead]);
  if (!actActive) {  // 즉시 끝나는 동작
    qHead = (qHead + 1) % Q_SIZE;
    qLen--;
  }
}

// ---------------- setup / loop ----------------
void setup() {
  driveInit();
  liftInit();
  commInit();
  senseInit();  // Timer1 틱 시작 (승강 가감속도 여기서 돈다)
  setTop(Top::Homing);
  liftStartHoming();  // 전원 On 자체 초기화: 하단 리밋 스위치로 원점 잡기
}

void loop() {
  driveBrakeUpdate();
  sonarUpdate();
  liftUpdate();
  commTelemetry();
  Command cmd = commPoll();

  switch (top) {
    case Top::Homing:
      if (liftHomed() && !liftBusy()) selfTestBegin();
      else if (liftFault()) fault("homing");
      break;
    case Top::SelfTest:
      selfTestUpdate();
      break;
    case Top::Idle:
      if (startButtonTake() || cmd == Command::Start) {  // 추가기능 1, 2
        resetMission();
        runStartMs = millis();
        setTop(Top::Run);
      } else if (cmd == Command::Home) {
        setTop(Top::Homing);
        liftStartHoming();
      }
      break;
    case Top::Run:
      runMission();  // 주행 중에는 원격 명령을 무시한다(자율 규정)
      break;
    case Top::Arrived:
    case Top::Fault:
      if (startButtonTake()) {  // 사람이 출발 위치로 옮긴 뒤 버튼: 대기 상태로
        setTop(Top::Homing);
        liftStartHoming();
      }
      break;
    default:
      break;
  }
}
