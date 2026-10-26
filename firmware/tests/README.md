# 모듈 단독 시험 스케치 (Arduino Mega 2560)

통합 전에 모듈별로 하나씩 올려 시험한다. 핀 번호는 `../wafer_robot/config.h` 와 동일하다. 시리얼 115200, 줄 끝은 어느 쪽이든 무방(HM-10 AT 제외, t06 참고). 각 폴더는 독립이라 서로 include 하지 않는다.

컴파일: `arduino-cli compile --fqbn arduino:avr:mega --warnings all <폴더>`

| 시험 | 결정하는 config.h 상수 |
|---|---|
| t01 | SPEED_*, BRAKE_MS 적정성(모터 기동 PWM, 제동 느낌) |
| t02 | 센서 높이/기울기/전원 선택, `EVENT_MIN_MS`·`LINE_LOST_MS` 근거, `MM_PER_MS_*`(속도 입력 시 진입각 보조) |
| t03 | `LIFT_STEPS_PER_MM`(눈금자 실측), `LIFT_RATE_*`·`LIFT_ACCEL` 탈조 여부, `HOME_*`, `LIFT_HOME_MM`(원점에서 포크 윗면 높이를 자로 [측정]) |
| t04 | `CREEP_SONAR_MIN_MM`, `SONAR_SLOW_MM` |
| t05 | `IR_WAFER_ADC_MIN` |
| t06 | HM-10 연결·이름·통신 (상수 없음) |
| t07 | `VBAT_CAL_CTRL`, `VBAT_CAL_MOTOR`, `VBAT_MOTOR_LOW` 점검 |
| t08 | `LED_HALF_PERIOD_MS`, `NECK_DEBOUNCE_MS` 동작 확인, 출발 버튼/넥 스위치 배선 |

## t01_motor_pwm
- 배선: ENA D44, ENB D45, IN1~IN4 D30~D33, 모터 팩 전원. **바퀴를 띄우고** 시험.
- 명령: `l <-255..255>`, `r <-255..255>`, `b`(단락 제동 40ms 후 프리런), `s`(정지). 목표값으로 5ms당 1단계 램프.
- 기대: `left  -> 150` 등 출력, 해당 바퀴가 부드럽게 가속. 부호가 -이면 반대 회전.
- 합격: 양수 = 전진 방향(반대면 모터선 교체), 좌/우 매핑 일치, 기동 최소 PWM 기록, `b` 후 약 40ms 안에 멈춤, 소음/발열 이상 없음.

## t02_line_sensor
- 배선: L/C/R = D22/D24/D26(흑=LOW), VCC 5V 또는 3.3V.
- 명령: `m` 5초 흑 비율, `v <mm/s>` 속도, `d <mm>` L-R 간격(기본 25), `e` 에지 초기화.
- 출력: 20Hz `L[#] C[.] R[.]` 막대, `transitions/s`, 선을 가로지를 때 `[edge 흑진입] dt=... us 각도=... deg`.
- 진입각 = atan(v·dt / 간격). dt = tR - tL(L이 먼저 흑이면 +). 센서를 손으로 일정 속도로 가로질러 각도를 가늠하는 용도.
- 보정 절차: 백지 위에서 `m` -> 전 채널 0%, 흑 테이프 위에서 `m` -> 100%, 선 경계에서 50% 부근 전환 폭 확인. 중간값이 나오면 높이/기울기/5V vs 3.3V 조정(튜닝 가이드 참조).
- 합격: 백 0~2%, 흑 98~100%, 정지 상태에서 transitions/s = 0(채터링 없음).

## t03_stepper_homing
- 배선: STEP D36, DIR D37, nSLEEP D38, 하단 리밋 D2, 상단 리밋 D18(NO, 내부 풀업). 먼저 `p` 로 리밋을 손으로 눌러 `limLow/limHigh` 가 1이 되는지 확인.
- 명령: `h` 원점(빠르게 하강 -> 2mm 후퇴 -> 저속 재접근), `g <mm>`(하단 리밋 = 0 mm, 0~60), `p`, `x`, `t` 손실 시험.
- 기대: `homing OK: pos=0`. `t` 는 40mm 올라간 뒤 저속으로 하단 리밋까지 내려와 `리밋 도달 시 pos=<n> step` 출력.
- 합격: `|n| <= 5 step`(0.2mm). `g 40` 후 자로 실측해 40mm ±0.5mm(아니면 `LIFT_STEPS_PER_MM` 수정). 탈조/떨림 시 `RATE_MAX`·`ACCEL` 낮춤.

## t04_ultrasonic
- 배선: TRIG D23, ECHO D3(INT5), 5V. 
- 출력: 20Hz 중앙값(5회 슬라이딩) `NNN mm`, 2초마다 `[2s] min max span`.
- 합격: 100/200mm 평면 대상에서 줄자 대비 ±5mm, span <= 5mm. 가까운 거리(차체 매립 30mm 감안)에서 최소 거리를 기록해 `CREEP_SONAR_MIN_MM` 근거로 삼는다. 0 이 자주 나오면 에코 실패.

## t05_ir_wafer
- 배선: GP2Y0A41SK Vo -> A0, 5V/GND(전원 근처 10µF).
- 출력: `ADC=… ~NN mm`, 40mm 미만은 `[무효]`. 거리식 d≈12343.85·adc^-1.15 는 근사(±10%)이므로 임계값 결정에는 ADC 값을 쓴다.
- 절차: 비운 상태에서 `e`, CD를 올린 상태에서 `w` -> `제안 IR_WAFER_ADC_MIN = (empty+wafer)/2`.
- 합격: wafer > empty + 100 정도의 분리, 좌우 마진 각각 50 이상. 형광등/햇빛 아래에서도 empty 값이 변하지 않을 것.

## t06_ble_echo
- 배선: HM-10 TXD -> D15(RX3), D14(TX3) -> 1k/2k 분압 -> RXD, 전원 보드에 맞게 3.3V/5V.
- 사용: 시리얼 모니터 입력이 HM-10 으로 간다(줄 끝 제거). `AT` -> `OK`, `AT+NAME?`, `AT+NAMEwafer`, `AT+BAUD?`(0 = 9600). `!v 10 20` -> `V,10,20` 줄 전송.
- 합격: `AT` 에 `OK`, 앱 연결 후 앱 메시지가 화면에 표시됨. 앱 프로토콜 시험은 `public/app/test_echo` 참고.

## t07_voltage
- 배선: A2 = 제어팩 분압(20k/10k), A3 = 모터팩 분압.
- 출력 500ms마다 `ctrl=… V motor=… V`, 모터 팩 < 6.6V 이면 경고.
- 보정: 멀티미터로 재고 `c ctrl 8.43`, `c motor 7.52` -> 계수 EEPROM 저장 후 출력. `r` 은 1.000 초기화. 얻은 계수를 `VBAT_CAL_CTRL/MOTOR` 에 기입.
- 합격: 보정 후 멀티미터와 ±0.05V, 계수 0.95~1.05 범위. 무부하/모터 구동 중 값 차이도 기록.

## t08_led_button
- 배선: LED D40(330Ω 직렬), 출발 버튼 D19(GND 단락), 넥 스위치 D25(GND 단락). 모두 내부 풀업.
- 출력: 2초마다 `LED 주기 평균=250000 us … 주파수=4.00 Hz`, 버튼/넥 `[START] 눌림 눌림 횟수=n`.
- 합격: 평균 249990~250010 us, 지터 < 100 us. 버튼 1회 누름 = 눌림 횟수 +1(바운스로 더 올라가면 디바운스 불량), 넥 스위치 동일.
