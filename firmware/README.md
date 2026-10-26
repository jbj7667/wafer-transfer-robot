# 웨이퍼 이송로봇 펌웨어 (Arduino Mega 2560)

스케치 폴더: `wafer_robot/`. 기구 기준은 `public/docs/design/mechanism.md`(최종 메커니즘, 행별 시퀀스 §4).

## 1. 모듈 구성

| 파일 | 역할 |
|---|---|
| `wafer_robot.ino` | 상태머신(Boot/Homing/Idle/Run/Arrived/Fault), 비차단 동작 큐 실행(`runAction`), 큐가 비면 다음 단계 계획(`planNext`) |
| `config.h` | 핀 배치, 튜닝 상수. `[측정]` 표시는 실측 필요 |
| `drive.*` | L298 차동 구동. Timer5 PWM 직접 구동, `driveBrake()` 능동 제동(IN 둘 다 HIGH + PWM 255, `BRAKE_MS` 후 프리런) |
| `lift.*` | 승강 스테퍼(DRV8834). Timer3 스텝 펄스 ISR, 1 kHz 틱에서 사다리꼴 가감속, 하단 리밋 원점 잡기, `liftStop()` |
| `sense.*` | Timer1 1 kHz 틱: 라인센서·이벤트, PD 추종(200 Hz), 출발 버튼·넥 스위치 디바운스, LED. 초음파(INT5), 상향 IR |
| `comm.*` | HM-10 BLE(Serial3) 줄 단위 프로토콜, 배터리 전압 텔레메트리, USB 디버그(115200) |

## 2. 타이머 / 인터럽트

| 자원 | 용도 | 설정 |
|---|---|---|
| Timer1 | 1 kHz 제어 틱 (`TIMER1_COMPA`) | CTC, 분주 64, OCR1A=249 |
| Timer3 | 승강 스텝 펄스 (`TIMER3_COMPA`) | CTC, 분주 8(2 MHz), 이동 중에만 인터럽트 허용 |
| Timer5 | 주행 PWM D44(OC5C)/D45(OC5B) | Fast PWM 8bit, 분주 8, 약 7.8 kHz |
| INT5 (D3) | 초음파 ECHO 상승·하강 | CHANGE |
| Timer0 | Arduino `millis()` | 기본값 |

Timer1 틱 안에서 하는 일: 라인 3채널 샘플(PINA) → 전체 흑 이벤트 래치 → PD 추종(5 ms마다) → 출발 버튼(30 ms)·넥 스위치(`NECK_DEBOUNCE_MS`) 디바운스 → LED → `liftTick1ms()`.

## 3. 핀 표

| 핀 | 기능 | 비고 |
|---|---|---|
| D44 / D45 | ENA / ENB (좌/우 PWM) | OC5C / OC5B |
| D30, D31 | 좌 IN1, IN2 | PC7, PC6 |
| D32, D33 | 우 IN3, IN4 | PC5, PC4 |
| D36 / D37 / D38 | 승강 STEP / DIR / SLEEP | PC1 / PC0 / PD7 |
| D22 / D24 / D26 | 라인센서 L / C / R | PA0 / PA2 / PA4, 흑 = LOW |
| D25 | 넥 접촉 레버 스위치 | PA3, 내부 풀업, 눌림 = LOW |
| D23 | 초음파 TRIG | |
| D3 | 초음파 ECHO | INT5 |
| A0 | 상향 IR (GP2Y0A41SK) | |
| A2 / A3 | 제어 / 모터 배터리 전압 | 분압 20k/10k |
| D2 | 승강 하단 리밋(원점) | 내부 풀업, 눌림 = LOW |
| D18 | 승강 상단 리밋(과주행 보호) | |
| D19 | 출발 푸시 스위치 | 내부 풀업, 눌림 = LOW |
| D40 | 상태 LED | |
| D14 / D15 | Serial3 TX / RX (HM-10) | |

## 4. 동작(Action) 종류

| 동작 | 인자 | 설명 |
|---|---|---|
| `A_FOLLOW` | 1 = 기둥 근처 감속 | PD 라인추종, 3채널 흑 이벤트에서 능동 제동 후 종료. 선 이탈 600 ms / 15 s 초과 시 고장 |
| `A_FWD` | mm (음수 = 후진) | 시간 기반 직진·후퇴(`MM_PER_MS_SLOW`) |
| `A_TURN` | 목표 방위 | 제자리 회전. `PIVOT_RAMP_MS` 동안 PWM 램프, 최소 시간 후 중앙 채널 흑이면 정지. 180도는 남쪽 경유(W→E 좌, E→W 우) |
| `A_TURN_PARTIAL` | 목표 방위 (E/W) | 상단 행 교차점 전용. 전진 없이 `PIVOT_MIN_MS_PARTIAL` 이상 돌다 중앙 흑이면 방위 확정, 정지하지 않고 `SPEED_SLOW` 추종으로 이어 감 |
| `A_LIFT_TO` | mm | 승강 이동 시작(비동기) |
| `A_LIFT_WAIT` | - | 승강 이동 완료 대기 |
| `A_CREEP` | - | `SPEED_CREEP` 전진, 넥 스위치 눌림 = 성공(시간을 행별로 기록), `CREEP_TIMEOUT_MS` 또는 초음파 < `CREEP_SONAR_MIN_MM` = 고장 |
| `A_CREEP_TIMED` | - | 기록한 크리프 시간만큼 `SPEED_CREEP` 전진(놓는 쪽, 스위치 미사용) |
| `A_PROBE` | - | 상향 IR로 웨이퍼 유무 판정 |

행 시퀀스(요약): 교차점 회전 → 정지선 → 아래 높이 → 크리프 → 감지 → (있음) 운반 높이 → 후퇴 100 → 180도 → 교차점 통과 → 맞은편 정지선 → 시간 크리프 → 아래 높이로 놓기 → 후퇴 → 기둥+5 → 180도 → 교차점. (없음) 기둥+5 → 후퇴 → 180도 → 맞은편에서 반복 후 첫 쪽으로 운반.

## 5. 빌드 / 업로드

```powershell
$cli = "C:\Program Files\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"
$dir = "<저장소>\public\firmware\wafer_robot"
& $cli compile --fqbn arduino:avr:mega --warnings all $dir
& $cli upload  --fqbn arduino:avr:mega -p COM3 $dir     # 포트는 환경에 맞게
```

Arduino IDE에서는 `wafer_robot.ino`를 열고 보드 "Arduino Mega or Mega 2560"로 업로드한다. 시리얼 모니터 115200 baud로 `STATE/PROBE/CREEP/FAULT` 로그 확인.

## 6. 하드웨어 실측 필요 상수 ([측정])

| 상수 | 현재값 | 측정 절차 |
|---|---|---|
| `MM_PER_MS_SLOW` | 0.12 | 평지에서 `SPEED_SLOW`로 `A_FWD` 500 ms 구동 후 이동 거리(mm)를 재서 거리/500. 3회 평균. 배터리 충전 상태별로 확인 |
| `MM_PER_MS_CREEP` | 0.08 | 현재 코드는 직접 쓰지 않음(참고). `SPEED_CREEP` 로 1 s 구동 후 이동 거리 |
| `PIVOT_MIN_MS_90` | 400 | 교차점 위에서 90도 회전만 시켜 보고, 라인이 센서에 다시 오기 직전 시간으로 설정(램프 300 ms 포함). 너무 짧으면 출발선 자체를 새 선으로 오인 |
| `PIVOT_MIN_MS_180` | 800 | 위와 같은 방식으로 180도. 바닥 재질별로 확인 |
| `PIVOT_MIN_MS_PARTIAL` | 380 | 상단 행 부분 회전. 센서 이벤트 지점에서 회전시켜 약 55도에서 멈추는 시간을 모의경기장에서 각도기로 측정. 포크 끝이 경계 밖으로 나가지 않는지 확인 |
| `LIFT_HOME_MM` | 155 | 하단 리밋이 눌린 상태에서 포크 윗면 높이를 자로 측정 |
| `LIFT_STEPS_PER_MM` | 25 | 이론값(T8 리드 8). 100 mm 이동 지령 후 실제 이동량으로 보정 |
| `LIFT_RATE_MAX`, `LIFT_ACCEL` | 1000, 5000 | 7.2 V에서 탈조 없이 왕복 20회. 탈조(원점 재확인 오차 > 1 mm) 시 낮춘다 |
| `POST_TOP_MM[]` | 200/200/175 | 실제 기둥 윗면 높이 측정(행별) |
| `UNDER_WAFER_MM`, `CARRY_MM`, `CLEAR_MM` | 10, 12, 5 | CD 밑면과 포크 간격을 자로 확인. 아래 높이에서 포크가 CD 밑면에 닿지 않고, 운반 높이에서 CD가 기둥에서 완전히 떠야 함 |
| `LIFT_PARK_MM` | 160 | 주행 대기 높이. 전고 245 이하 확인 |
| `IR_WAFER_ADC_MIN` | 300 | 상향 IR을 CD 있음 / 없음 각각 20회 읽어 두 분포 중간값으로 설정 |
| `SONAR_SLOW_MM` | 150 | 정지선 직전 오버슈트가 최소가 되는 감속 시작 거리. 정지선 이벤트 위치 편차(mm)를 10회 측정해 비교 |
| `CREEP_SONAR_MIN_MM` | 20 | 초음파는 차체 앞면에서 30 mm 뒤에 매립(mechanism.md) → 정상 접촉 시 약 35 mm. 넥 스위치가 눌린 상태의 실측값보다 10 mm 이상 작게 설정 |
| `CREEP_TIMEOUT_MS` | 1500 | 정지선에서 접촉까지 실제 크리프 시간을 10회 재서 2배 이내로 |
| `SPEED_CREEP` | 85 | 넥 스위치 작동력과 베이스 이동량: 접촉 시 베이스 이동 3 mm 이하가 되는 최저 속도 |
| `VBAT_CAL_CTRL`, `VBAT_CAL_MOTOR` | 1.0 | 멀티미터로 실제 전압을 재고 (실측 / 표시) 비율 |
| `KP`, `KD`, `SPEED_*` | - | 모의경기장 곡선·직선에서 진동 없이 가장 빠른 값으로 튜닝 |

## 7. 규칙 요약

- 180도 회전은 항상 남쪽 경유(W→E 좌, E→W 우). 회전 전 포크 높이는 기둥 윗면 + 5 이상, 후퇴 100 mm.
- 상단 행(row 2) 교차점은 전진 없이 부분 회전으로 진입한다.
- 주행 제한시간 `RUN_TIME_LIMIT_MS`(본선 150 s)에 닿으면 정지(고장 상태).
- 고장 시 구동 제동 + 승강 정지. 출발 버튼으로 재원점.
