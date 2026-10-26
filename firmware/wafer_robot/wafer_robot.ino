// wafer_robot.ino — 웨이퍼 이송로봇 메인: 상태머신(대기/주행/도착)과 임무 계획.
//
// 구조
//   Timer1 1kHz : 라인센서·이벤트·PD 추종·버튼·LED·승강 가감속  (sense.cpp)
//   Timer3      : 승강 스테퍼 스텝 펄스                          (lift.cpp)
//   Timer5      : 주행 PWM                                       (drive.cpp)
//   loop()      : 동작 큐(Action) 실행 + 큐가 비면 다음 단계를 계획(planNext)
//
// 경로 모델: 방위 N/E/S/W, 행 0=하단(y480) 1=중단 2=상단(y130).
// 포크 U 중심이 라인센서보다 FORK_AHEAD_MM 앞에 있으므로 정지선 이벤트에서 멈추면 포크가 기둥 중심에 온다.

#include "config.h"
#include "drive.h"
#include "lift.h"
#include "sense.h"
#include "comm.h"

// ---------------- 동작 타입 ----------------
// (Arduino 자동 프로토타입이 함수 앞에 삽입되므로 Action은 첫 함수보다 위에 정의해야 한다)
enum ActType : uint8_t { A_FOLLOW, A_FWD, A_TURN, A_LIFT_TO, A_LIFT_WAIT, A_PROBE };
struct Action {
  ActType type;
  int16_t a;  // FOLLOW: 1=기둥 근처 감속 / FWD: mm(음수=후진) / TURN: 목표 방위 / LIFT_TO: mm
};

// ---------------- 상위 상태 ----------------
enum class Top : uint8_t { Boot, Homing, Idle, Run, Arrived, Fault };
static Top top = Top::Boot;
static uint32_t runStartMs = 0;

static const char *topName(Top t) {
  switch (t) {
    case Top::Boot: return "BOOT";
    case Top::Homing: return "HOMING";
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
      ledSet(LedMode::Blink4Hz);  // 시작·도착 구역: 초당 4회 점멸 (추가기능 5)
      break;
    case Top::Fault:
      ledSet(LedMode::On);
      break;
    default:
      ledSet(LedMode::Off);       // 이동 중 소등
  }
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

// 교차점에서 다른 방위로 회전: 바퀴축을 교차 중심에 맞춘 뒤 회전
static void turnAtCrossing(uint8_t h) {
  push(A_FWD, SENSOR_AHEAD_MM);
  push(A_TURN, h);
}

// 현재 정지선(포크 아래 웨이퍼 있음)에서 집어 맞은편 기둥에 놓고 다시 교차점으로 돌아온다
static void deliverToOpposite(uint8_t pickSide) {
  uint8_t back = (pickSide + 2) & 3;
  push(A_LIFT_TO, (int16_t)carry());
  push(A_LIFT_WAIT);
  push(A_FWD, -(int16_t)RETREAT_MM);
  push(A_TURN, back);
  push(A_FOLLOW, 0);                  // 트렁크 교차점
  push(A_FWD, 40);                    // 교차점 통과
  push(A_FOLLOW, 1);                  // 맞은편 정지선
  push(A_LIFT_TO, (int16_t)underWafer());  // 내려놓기
  push(A_LIFT_WAIT);
  push(A_FWD, -(int16_t)RETREAT_MM);
  push(A_LIFT_TO, (int16_t)LIFT_PARK_MM);
  push(A_TURN, pickSide);
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
      push(A_LIFT_TO, (int16_t)underWafer());
      turnAtCrossing(FIRST_SIDE);
      push(A_FOLLOW, 1);
      push(A_LIFT_WAIT);
      push(A_PROBE);
      phase = P_FIRST_PROBED;
      break;

    case P_FIRST_PROBED:
      if (probeResult) {
        deliverToOpposite(FIRST_SIDE);
        moved++;
        phase = P_ROW_DONE;
      } else {
        uint8_t other = (FIRST_SIDE + 2) & 3;
        push(A_FWD, -(int16_t)RETREAT_MM);
        push(A_TURN, other);
        push(A_FOLLOW, 0);
        push(A_FWD, 40);
        push(A_FOLLOW, 1);
        push(A_PROBE);
        phase = P_SECOND_PROBED;
      }
      break;

    case P_SECOND_PROBED: {
      uint8_t second = (FIRST_SIDE + 2) & 3;
      if (probeResult) {
        deliverToOpposite(second);
        moved++;
      } else {  // 이 행에는 웨이퍼가 없다: 교차점으로 돌아가 다음 행
        push(A_FWD, -(int16_t)RETREAT_MM);
        push(A_LIFT_TO, (int16_t)LIFT_PARK_MM);
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
        turnAtCrossing(S);
        push(A_FOLLOW, 0);  // 중단 교차점
        push(A_FWD, 40);
        push(A_FOLLOW, 0);  // 하단 교차점
        push(A_FWD, 40);
        push(A_FOLLOW, 0);  // 곡선을 지나 출발·도착 끝선
        push(A_FWD, 30);    // 몸체가 끝선을 덮도록
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
  driveStop();
  manualDrive(0, 0);
  Serial.print("FAULT ");
  Serial.println(why);
  setTop(Top::Fault);
}

static void startAction(const Action &x) {
  actActive = true;
  actT0 = millis();
  switch (x.type) {
    case A_FOLLOW:
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
      actDur = d == 2 ? PIVOT_MIN_MS_180 : PIVOT_MIN_MS_90;
      int16_t s = SPEED_PIVOT;
      if (d == 3) manualDrive(-s, s);   // 좌회전
      else if (d != 0) manualDrive(s, -s);  // 우회전, 180°도 우회전
      else actActive = false;           // 이미 그 방위
      break;
    }
    case A_LIFT_TO:
      liftMoveToMm(x.a);
      actActive = false;  // 비동기: 기다리려면 A_LIFT_WAIT
      break;
    case A_LIFT_WAIT:
    case A_PROBE:
      manualDrive(0, 0);
      break;
  }
}

// true = 끝남
static bool runAction(const Action &x) {
  uint32_t el = millis() - actT0;
  switch (x.type) {
    case A_FOLLOW:
      if (x.a == 1) {  // 기둥에 가까워지면 감속(정지선 오버슈트 감소)
        uint16_t d = sonarMm();
        followSpeed(d && d < 150 ? SPEED_SLOW : SPEED_CRUISE);  // followStart는 D항 상태를 지우므로 속도만 갱신
      }
      if (lineEventTake()) { manualDrive(0, 0); return true; }
      if (lineLostMs() > LINE_LOST_MS) fault("line lost");
      if (el > 15000) fault("follow timeout");
      return false;
    case A_FWD:
      if (el >= actDur) { manualDrive(0, 0); return true; }
      return false;
    case A_TURN:
      if (el >= actDur && (lineBits() & 0b010)) {
        manualDrive(0, 0);
        heading = x.a;
        return true;
      }
      if (el > 4000) fault("turn timeout");
      return false;
    case A_LIFT_WAIT:
      if (liftFault()) fault("lift");
      return !liftBusy();
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
      manualDrive(0, 0);
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
  sonarUpdate();
  liftUpdate();
  commTelemetry();
  Command cmd = commPoll();

  switch (top) {
    case Top::Homing:
      if (liftHomed() && !liftBusy()) setTop(Top::Idle);
      else if (liftFault()) fault("homing");
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
