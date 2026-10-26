# 상태머신·임무 계획 (v1)

근거: `public/firmware/wafer_robot/wafer_robot.ino`(현재 코드), `mechanism.md`(넥 접촉 정지, 상단 행 부분 회전). 펌웨어에 **A_CREEP / A_CREEP_TIMED / A_TURN_PARTIAL**과 넥 접촉 스위치 핀이 추가되는 중이다. 그 부분은 `mechanism.md` 기준으로 기술하며, 핀은 `config.h` 참조.

## 1. 상위 상태

```
          전원 On
             |
             v
        +---------+   하단 리밋으로 원점(②④)      +----------+
        |  BOOT   |------------------------------>| HOMING   |  LED 4Hz
        +---------+     setup(): 초기화             +----------+
                                                     |  liftHomed && !busy
                                  liftFault          v
                              +--------------+  +----------+  'H' 명령(BLE)
                              |              |<-|  IDLE    |<-------+
                              |    FAULT     |  +----------+        |
                              |  LED 상시 On |       | 푸시버튼(②) 또는 BLE 'S'(①)
                              +--------------+       v
                                  ^   |         +----------+
              fault(원인) -----+  |   |         |   RUN    |  LED Off
         (선 이탈, 타임아웃,       |   |         +----------+
          시간 초과, 승강 오류)    |   |              | 계획 끝(P_END) & 큐 비어 있음
                                  |   |              v
                                  |   |         +----------+
              버튼(재원점) <-------+---+---------| ARRIVED  |  LED 4Hz
                                                 +----------+
```

| 상태 | LED(추가기능 ⑤) | 진입 조건 | 이탈 조건 |
|---|---|---|---|
| BOOT | — | 전원 On | setup() 끝 -> HOMING |
| HOMING | 4Hz | 부팅, IDLE에서 BLE 'H', ARRIVED/FAULT에서 버튼 | 원점 완료 -> SELFTEST, 승강 오류 -> FAULT |
| SELFTEST | 4Hz | 원점·대기 높이 도달 | IR 비어 있음·라인 응답·전압 확인 후 -> IDLE, 포크에 물체 -> FAULT |
| IDLE | 4Hz | 원점 완료 | 버튼 또는 BLE 'S' -> RUN (미션 리셋, 타이머 시작) |
| RUN | Off | IDLE에서 출발 | 미션 종료 -> ARRIVED, 오류 -> FAULT |
| ARRIVED | 4Hz | 계획의 마지막 동작 완료 | 버튼 -> HOMING |
| FAULT | On | 선 이탈, 타임아웃, 시간 초과 등 | 버튼 -> HOMING |

- RUN 중에는 BLE 원격 명령을 무시한다(자율 규정).
- 시작·도착 구역에서는 4Hz 점멸, 주행 중에는 소등. 본선에서 동작하지 않으면 가산점 취소이므로 RUN 중 점멸 금지를 코드로 보장한다.

## 2. 임무 계획기 (행당 단계)

```
  P_START ──(출발선 -> 곡선 -> 트렁크 -> 하단 교차점)──> P_ROW_FIRST
                                                          |
         +------------------------------------------------+
         v
  P_ROW_FIRST   (행 시작: 교차점)
     LIFT_TO 아래높이 -> (교차점 FWD+TURN FIRST_SIDE) -> FOLLOW(1) 정지선
     -> [CREEP: 넥 접촉까지] -> LIFT_WAIT -> PROBE
         |
         v
  P_FIRST_PROBED
     있음 -> deliverToOpposite(FIRST) ──────────────┐ moved++
     없음 -> 후퇴, 반대 방향 회전, 교차점 통과,    │
             반대 정지선, PROBE                      │
         |  (없음 경로)                              │
         v                                          │
  P_SECOND_PROBED                                   │
     있음 -> deliverToOpposite(반대쪽), moved++ ───┤
     없음 -> 후퇴, 승강 복귀, 회전, 교차점          │
         |                                          │
         +──────────────────────────────────────────┘
         v
  P_ROW_DONE
     row < 2 -> 북쪽으로 회전, 다음 행 교차점 -> row++ -> P_ROW_FIRST
     row = 2 -> 남쪽으로 회전, 중단·하단 교차점 -> 출발·도착 끝선 -> P_HOME
         |
         v
  P_HOME -> P_END -> (큐 비면) ARRIVED
```

- 상단 행(row=2)은 `mechanism.md` 3절 규칙을 적용한다: 교차점에서 전진 없이 **TURN_PARTIAL(약 55°, 시간 기반 + 중앙 채널 흑 확인)** 후 저속 라인추종. 상단 행의 180°는 항상 남쪽을 경유(서→동은 좌회전, 동→서는 우회전).
- 예선 웨이퍼는 왼쪽(1, 3, 5)에 있으므로 FIRST_SIDE = W. 본선도 왼쪽부터 확인한다.
- 같은 행의 두 기둥 높이는 같으므로 승강 높이 계산은 행 단위 (`POST_TOP_MM[row]`).

## 3. 동작(Action) 종류

| 동작 | 인자 | 종료 조건 | 비고 |
|---|---|---|---|
| A_FOLLOW | 0 일반 / 1 기둥 근처 감속 | 3채널 흑 이벤트 (`EVENT_MIN_MS`) | 선 이탈 `LINE_LOST_MS`, 15s 타임아웃 -> FAULT |
| A_FWD | mm (음수=후진) | 시간 경과 (`MM_PER_MS_SLOW`) | 교차점 정렬(SENSOR_AHEAD_MM), 교차점 통과 40, 후퇴 |
| A_TURN | 목표 방위 | 최소 시간 후 중앙 채널 흑 | 4 s 초과 -> FAULT |
| A_LIFT_TO | 높이 mm | 비동기(바로 반환) | 완료는 A_LIFT_WAIT |
| A_LIFT_WAIT | — | 승강 이동 끝 | 승강 오류 -> FAULT |
| A_PROBE | — | 80 ms 정지 후 IR 판정 | `irWaferAdc() > IR_WAFER_ADC_MIN` |
| A_CREEP (추가 중) | — | 넥 접촉 스위치 눌림 | 시간 초과 1.5 s, 초음파 거리 하한 보호. **크리프 시간을 기록** |
| A_CREEP_TIMED (추가 중) | — | 기록한 크리프 시간 경과 | 플레이스 시 사용. 포크가 기둥 위라 넥 스위치는 안 눌림 |
| A_TURN_PARTIAL (추가 중) | 각도/시간 | 약 55° 시간 후 중앙 채널 흑 확인 | 상단 행 전용 (포크 끝이 경계 밖으로 나가지 않게) |

### 한 행의 전형적 동작 열 (mechanism.md 4절)

```
정지선 이벤트 -> LIFT_TO(아래) -> CREEP(스위치) -> PROBE
  있음: LIFT_TO(운반) -> FWD(-100) -> TURN(남쪽 경유 180) -> FOLLOW(교차점) -> FWD(40)
        -> FOLLOW(1, 맞은편 정지선) -> CREEP_TIMED(기록 시간) -> LIFT_TO(아래, 내려놓기)
        -> FWD(-100) -> TURN(복귀) -> FOLLOW(교차점)
  없음: LIFT_TO(기둥 윗면+5) -> FWD(-100) -> TURN(180) -> 맞은편에서 CREEP/PROBE/운반
```

현재 코드는 후퇴 `RETREAT_MM`=80, 크리프 없음(정지선 이벤트 직후 PROBE)이다. 설계안(후퇴 100, 넥 접촉)에 맞추는 변경은 펌웨어 담당이 반영한다.

## 4. 예선 이벤트 카운팅 내비게이션 표

출발선(동쪽을 봄) -> 곡선 -> 트렁크. 모든 웨이퍼가 왼쪽에 있고 각 행에서 FIRST_SIDE = W에서 "있음"이 나오는 정상 경로의 이벤트 순서.

| # | 동작 | 기다리는 이벤트 | 방위(이벤트 후) | 비고 |
|---|---|---|---|---|
| 1 | FOLLOW | 하단 교차점 (행 0) | N | 출발선 -> 곡선 -> 트렁크 |
| 2 | FWD 60, TURN W, FOLLOW(1) | 좌 정지선 (행 0) | W | 크리프·PROBE·들기 |
| 3 | 후퇴, TURN E, FOLLOW | 트렁크 교차점 (행 0) | E | 운반 중 |
| 4 | FWD 40, FOLLOW(1) | 우 정지선 (행 0) | E | 내려놓기 |
| 5 | 후퇴, TURN W, FOLLOW | 행 0 교차점 | W | 복귀 |
| 6 | FWD 60, TURN N, FOLLOW | 중단 교차점 (행 1) | N | 다음 행 |
| 7~10 | (행 1 반복: 좌 정지선, 교차점, 우 정지선, 교차점) | 4 이벤트 | W | |
| 11 | FWD 60, TURN N, FOLLOW | 상단 교차점 (행 2) | N | 상단: TURN_PARTIAL 55° 규칙 |
| 12~15 | (행 2 반복: 좌 정지선, 교차점, 우 정지선, 교차점) | 4 이벤트 | | 상단은 175 높이 |
| 16 | FWD 60, TURN S, FOLLOW | 중단 교차점 | S | 복귀 시작 |
| 17 | FWD 40, FOLLOW | 하단 교차점 | S | |
| 18 | FWD 40, FOLLOW | 출발·도착 끝선 | | FWD 30으로 끝선 덮음 -> P_END |

합계 약 18 이벤트(정상 경로). 행마다 이벤트 4개(좌 정지선, 교차점, 우 정지선, 교차점) + 다음 행 이동 1개.

## 5. 본선 분기

```
행 시작 (FIRST_SIDE = W)
  좌 정지선: PROBE
     CD 있음 ──> 운반 -> 우 기둥에 배치 ──> 다음 행        (정상, 시간 손실 없음)
     CD 없음 ──> 후퇴 100 -> 180(남쪽 경유) -> 교차점 통과 -> 우 정지선 -> CREEP -> PROBE
                    CD 있음 ──> 운반 -> 좌 기둥에 배치 ──> 다음 행   (+약 5 s)
                    CD 없음 ──> 후퇴 -> 승강 복귀 -> 교차점 ──> 다음 행   (행에 웨이퍼 없음)
```

- 본선 최악(세 행 모두 먼저 확인한 쪽에 없음): 추가 약 15 s (PLAN 1.3절 추정).
- 배치 후 시간이 남으면 이송을 계속한다. 3개 모두 옮기지 못했어도 도착 판정과 득점은 별개.
- 웨이퍼 위치를 사람이 입력하지 않는다(규정). 감지만 사용.

## 6. 추가기능 F1~F5 매핑

| 기능 | 상태/수단 | 타이머·인터럽트 | 비고 |
|---|---|---|---|
| F1 BLE 출발 | IDLE에서 BLE 'S' -> RUN | Serial3 폴링 (`commPoll`) | 전용 앱(터미널 앱 불가) |
| F2 푸시 출발 | IDLE에서 `startButtonTake()` -> RUN | INT2(D19) + 50 ms 디바운스(Timer1 틱) | 로봇에 부착 |
| F3 전압 표시 | 전 상태에서 텔레메트리 | 500 ms (`TELEMETRY_MS`) `V,<ctrl>,<motor>` | A2/A3 ADC |
| F4 자체 초기화 | BOOT -> HOMING (하단 리밋 탐색 -> 후퇴 2 mm -> 저속 재탐색 -> 0점) | INT4(D2), Timer3 스텝 | 센서 기반이라 인정 |
| F5 LED | RUN: Off, IDLE/HOMING/ARRIVED: 4 Hz (125 ms 토글), FAULT: 상시 On | Timer1 1 kHz 틱에서 카운트 | `LED_HALF_PERIOD_MS`=125 |

## 7. 인터럽트·타이머

| 자원 | 설정 | 역할 | 우선 주의 |
|---|---|---|---|
| Timer0 | 기본 | `millis()` | 변경 금지 |
| Timer1 | CTC 1 kHz | 라인센서 샘플링·이벤트 판정·PD 추종·버튼 디바운스·LED·승강 가감속 갱신 | ISR 짧게 |
| Timer3 | CTC, OCR3A 가변 | 스테퍼 STEP 펄스 | 포트 직접 접근 |
| Timer5 | Fast PWM 약 7.8 kHz | L298 ENA/ENB | D44/D45 |
| INT2 (D19) | 엣지 | 출발 버튼 | |
| INT3 (D18) | 엣지 | 상한 리밋 (과주행 보호) | |
| INT4 (D2) | 엣지 | 하한 리밋 (원점) | |
| INT5 (D3) | 엣지 | 초음파 ECHO 측정 | |
| 넥 접촉 스위치 | config.h 참조 | 크리프 중 폴링 또는 PCINT | 핀은 펌웨어에서 확정 |

## 8. 실패 처리

| 상황 | 감지 | 처리 | 이후 |
|---|---|---|---|
| 선 이탈 | 3채널 백 `LINE_LOST_MS`(600 ms) 초과 | SEARCH: 제동 → 마지막으로 본 쪽 회전(최대 `SEARCH_MAX_MS`) → 제동 → 반대쪽 회전(최대 2배). 어느 채널이든 흑이면 추종 재개 | 실패 시 fault("line lost") |
| 자가 점검 IR | SELFTEST에서 포크 위 IR이 "있음" | `T,IR,FAIL` 송신, fault("fork not empty") | FAULT |
| 자가 점검 라인·전압 | SELFTEST에서 라인 3채널 백 200 ms / 모터팩 저전압 | `T,LINE,WARN` / `T,VBAT,WARN` 송신 | 경고만, IDLE 진입 |
| 추종 타임아웃 | FOLLOW 15 s | fault("follow timeout") | FAULT |
| 회전 타임아웃 | TURN 4 s | fault("turn timeout") | FAULT |
| 승강 오류 | liftFault (리밋 미도달 등) | fault("lift") / fault("homing") | FAULT |
| 전체 시간 초과 | RUN_TIME_LIMIT_MS (150 s) | fault("time") | FAULT |
| 크리프 시간 초과 (추가 중) | 1.5 s 넥 스위치 미접촉 | 정지 후 PROBE(CD 없음 처리) 또는 FAULT | 모의경기장에서 정책 확정 |
| 초음파 거리 하한 (추가 중) | 하단 원기둥과 `APPROACH_STOP_MM` 이하 | 크리프 정지 | 베이스 밀림 방지 |
| 전압 저하 | 모터팩 < `VBAT_MOTOR_LOW` (6.6 V) | 앱 경고 (3점) | 대회 전 팩 교체 |
| Mega 리셋 | 전원 강하/노이즈 | 재부팅 -> HOMING | 배선 점검 (wiring.md 7절) |

- FAULT 후에는 로봇을 출발 위치로 옮기고 버튼을 눌러 재원점 → SELFTEST → IDLE → 다시 출발한다. 이것이 규정의 **재출발**이다(경기당 2회까지 허용, 추가 시간·벌점 없음, 3번째 요청은 0점, 재출발 시 웨이퍼 재배치·이전 득점 무효).
- 상위 상태에 **SELFTEST**가 HOMING과 IDLE 사이에 추가되었다(추가기능 ④ 보강: 원점 잡기 + 센서 확인). LED는 4 Hz 점멸을 유지한다. 결과는 `T,<IR|LINE|VBAT>,<OK|WARN|FAIL>` 줄로 앱에 보낸다 — 앱은 상태 라벨 옆에 표시하면 된다(`app/protocol.md` 확장 항목).
