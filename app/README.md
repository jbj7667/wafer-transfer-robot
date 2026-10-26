# 로봇 제어 스마트폰 앱 명세 (MIT App Inventor + BluetoothLE)

대회 규정: 지급된 BLE 모듈로 스마트폰에서 출발시키는 것과 배터리 전압 모니터링은 **자체 제작 앱**이어야 한다(일반 블루투스 터미널 앱 불가). 이 문서는 App Inventor 로 처음부터 만드는 방법을 블록 단위로 설명한다. 통신 규약은 [protocol.md](protocol.md), 로봇 없이 시험하는 스케치는 [test_echo/test_echo.ino](test_echo/test_echo.ino).

> 확인 수준 안내: 서비스/특성 UUID 와 확장 다운로드 주소는 웹에서 확인했다. 그러나 BluetoothLE 확장의 **블록 이름·매개변수 순서의 공식 레퍼런스 페이지는 접근하지 못해**(appinventor.mit.edu/iot/reference/bluetoothle 가 404) 아래 블록 이름은 확장의 일반적인 구성과 커뮤니티 글(RegisterForStrings, WriteStrings, WriteStringsWithResponse, StringsReceived 등 언급 확인)에 근거한다. 실제 블록 서랍에서 이름과 소켓 순서를 대조하며 만들 것. 대조가 필요한 곳은 `[확인]` 으로 표시했다. 또 `.aia` 자동 생성은 .scm/.bky 형식의 신뢰할 만한 예제를 확보하지 못해 **하지 않았다**(가져오기에 실패할 추측 파일을 만들지 않기 위함).

## 1. 준비

1. 안드로이드 폰(Android 8 이상 권장; Android 12+ 는 "근처 기기" 권한, 11 이하는 위치 권한 필요). 앱 인벤터 계정(<https://ai2.appinventor.mit.edu>).
2. BluetoothLE 확장 다운로드: <https://appinventor.mit.edu/assets/resources/edu.mit.appinventor.ble.aix> (MIT IoT 안내 페이지 <https://iot.appinventor.mit.edu/> 가 이 링크를 제공). 파일명은 날짜 버전이 붙기도 한다(커뮤니티 글에서 `edu.mit.appinventor.ble-20230728`, `-20240822` 확인). 페이지 자체에는 버전 표기가 없으므로 받은 파일명의 날짜를 기록해 둘 것. 20240822 빌드는 일부 사용자가 가져오기 오류를 보고했다 — 새로고침 후 재시도하거나 20230728 을 사용(출처: <https://community.appinventor.mit.edu/t/bluetoothle-updates-2024/134483/7>, <https://community.appinventor.mit.edu/t/ble-extension-download-not-working/121499>).
3. 프로젝트 `RobotApp` 생성 → 팔레트 맨 아래 **Extension → Import extension → 위 `.aix` 파일** → Screen 에 `BluetoothLE1` 추가. 확장은 .aia 저장 시 함께 저장된다.
4. 개발 중에는 폰에 **MIT AI2 Companion** 으로 시험하고, 최종은 Build → Android App (.apk) 로 설치.

## 2. 화면 설계 (Screen1 하나, 패널 2개 전환)

BLE 연결을 유지해야 하므로 Screen 을 나누지 않고 한 화면 안에서 두 패널의 `Visible` 을 바꾼다.

### 2.1 연결 패널 `ConnectPanel` (VerticalArrangement)
- `LblTitle`: "로봇 컨트롤러"
- `TxtFilter` (TextBox): 이름 필터, 기본값 `HM` (지급 모듈 이름의 일부. 모듈마다 다르므로 현장에서 수정). 비우면 전체 표시.
- `BtnScan` (Button): "스캔" / 스캔 중에는 "중지"
- `LvDevices` (ListView): 필터에 맞는 기기 목록
- `LblConnStatus` (Label): "연결 안 됨" / "연결 중…" / "연결됨: <이름>"
- `BtnDisconnect` (Button): "연결 해제" (연결됐을 때만 활성)

### 2.2 메인 패널 `MainPanel` (VerticalArrangement, 처음엔 Visible=false)
- `LblState` (Label, 큰 글씨 32sp, 가운데): 현재 상태. 색 규칙은 protocol.md 표.
- `BtnStart` (Button, 높이 120+, 글씨 36sp): "START". **연결됨 AND 상태=IDLE AND 수신 정상** 일 때만 `Enabled=true`.
- `LblCtrl` (Label): "제어 9V팩  8.97 V" — 7.5 V 미만이면 글자 빨강
- `LblMotor` (Label): "모터 7.2V팩  7.41 V" — 6.6 V 미만이면 글자 빨강
- `BtnRehome` (Button): "재홈(H)" — IDLE 일 때만 활성 (이동 중 오조작 방지)
- `LblPing` (Label): "지연: -- ms"
- `BtnPing` (Button): "핑"
- (선택) `Canvas1` (너비 채움, 높이 120): 최근 60개 전압 꺾은선(제어=파랑, 모터=주황)
- `LblDebug` (Label, 작은 글씨 10sp): 마지막 수신 줄 (시험 때 확인용)
- `BtnBack` (Button): "연결 화면"

### 2.3 비가시 컴포넌트
- `BluetoothLE1` (확장)
- `ClockPing` : TimerInterval 2000, TimerEnabled=false (자동 핑)
- `ClockWatch` : TimerInterval 500, TimerEnabled=false (수신 감시, 시작 응답 감시)
- `ClockReconnect` : TimerInterval 3000, TimerEnabled=false (자동 재연결)
- `TinyDB1` : 마지막 연결 기기 주소 저장
- `Notifier1` : 알림 메시지

## 3. 전역 변수

| 이름 | 초기값 | 용도 |
|---|---|---|
| `SVC` | `0000FFE0-0000-1000-8000-00805F9B34FB` | HM-10 서비스 UUID |
| `CHR` | `0000FFE1-0000-1000-8000-00805F9B34FB` | HM-10 특성 UUID |
| `rxBuf` | `""` (빈 텍스트) | 수신 줄 재조립 버퍼 |
| `state` | `"BOOT"` | 마지막 상태 |
| `connected` | false | 연결 여부 |
| `lastRx` | 0 | 마지막 V 수신 시각(ms) |
| `pingSent` | 0 | 핑 송신 시각(ms) |
| `startSent` | 0 | 출발 송신 시각(ms), 0 = 대기 없음 |
| `idxMap` | 빈 리스트 | ListView 줄 번호 → DeviceList 번호 |
| `lastAddr` | `""` | 자동 재연결용 주소 |
| `ctrlHist`, `motorHist` | 빈 리스트 | 그래프용(선택) |
| `userDisconnect` | false | 사용자가 직접 끊었는지 |

## 4. 블록 설명 (순서대로)

### 4.1 Screen1.Initialize
1. `set MainPanel.Visible to false`, `set ConnectPanel.Visible to true`
2. `set global lastAddr to call TinyDB1.GetValue(tag "addr", valueIfTagNotThere "")`
3. 상태 표시 초기화: `call ShowState("BOOT")`, `BtnStart.Enabled=false`, `BtnRehome.Enabled=false`

### 4.2 스캔
**when BtnScan.Click**
1. if `BluetoothLE1.Scanning` [확인: 속성명] → `call BluetoothLE1.StopScanning`, `BtnScan.Text="스캔"`
2. else → `set idxMap to 빈 리스트`, `set LvDevices.Elements to 빈 리스트`, `call BluetoothLE1.StartScanning`, `BtnScan.Text="중지"`

**when BluetoothLE1.DeviceFound** (새 기기가 발견될 때마다 발생; 이 이벤트에는 보통 매개변수가 없고 `BluetoothLE1.DeviceList` 속성에 누적 목록이 들어 있다 [확인])
1. `call RefreshList` (아래 절차)

**to RefreshList** (절차)
1. `set LvDevices.Elements to 빈 리스트`, `set idxMap to 빈 리스트`
2. `for each number from 1 to length of list (BluetoothLE1.DeviceList)` 반복:
   - `item = select list item (BluetoothLE1.DeviceList, number)`
   - `if TxtFilter.Text = ""  OR  contains(upcase(item), upcase(TxtFilter.Text))`:
     - `add items to list (LvDevices의 목록용 임시 리스트 tmp, item)`, `add items to list (idxMap, number)`
3. `set LvDevices.Elements to tmp`
   - 각 항목 문자열에는 기기 이름과 주소(와 RSSI)가 들어 있다 [확인: 형식]. 이름이 `null` 로 나오는 기기는 필터에 걸리지 않으므로 필터를 비워 모듈 이름을 먼저 파악한다.

### 4.3 연결
**when LvDevices.AfterPicking**
1. `call BluetoothLE1.StopScanning`, `BtnScan.Text="스캔"`
2. `set userDisconnect to false`
3. `set LblConnStatus.Text to "연결 중…"`
4. `call BluetoothLE1.Connect(index = select list item (idxMap, LvDevices.SelectionIndex))` — `Connect` 의 index 는 `DeviceList` 의 번호이므로 필터된 목록 번호가 아니라 `idxMap` 으로 변환한 값을 넣는다.

**when BluetoothLE1.Connected**
1. `set connected to true`, `set rxBuf to ""`, `set userDisconnect to false`
2. 연결 직후 알림 구독: `call BluetoothLE1.RegisterForStrings(serviceUuid = SVC, characteristicUuid = CHR, utf16 = false)`
   - `utf16 = false` : ASCII/UTF-8 로 해석 (프로토콜이 ASCII 이므로 반드시 false)
   - 재연결할 때마다 다시 호출해야 한다(구독은 연결에 묶여 있음).
3. `set ConnectPanel.Visible=false`, `MainPanel.Visible=true`, `LblConnStatus.Text="연결됨"`
4. `set lastRx to Clock.SystemTime` (`ClockWatch.SystemTime` 같은 시계 메서드 사용), `ClockPing.TimerEnabled=true`, `ClockWatch.TimerEnabled=true`, `ClockReconnect.TimerEnabled=false`
5. 주소 저장은 연결한 `DeviceList` 항목에서 주소를 뽑아 `TinyDB1.StoreValue("addr", 주소)` (주소는 항목 문자열 안에 있음 [확인])
6. `call BluetoothLE1.WriteStrings(SVC, CHR, false, "P\n")` : 연결 직후 핑 1회 겸 상태 확인

**when BtnDisconnect.Click / BtnBack.Click**
1. `set userDisconnect to true`, `call BluetoothLE1.Disconnect`

### 4.4 수신 — 줄 재조립 (가장 중요)
BLE 알림은 20바이트 단위로 쪼개지고 여러 줄이 합쳐질 수도 있다.

**when BluetoothLE1.StringsReceived (serviceUuid, characteristicUuid, stringValues)** [확인: 매개변수 이름과 순서]
1. `stringValues` 는 **문자열 리스트**다. `for each item in list stringValues`:
   - `set global rxBuf to join(rxBuf, item)`
2. `call Drain`

**to Drain**
1. `if length(rxBuf) > 200` → `set rxBuf to ""` 후 종료 (쓰레기 방지)
2. `set rxBuf to replace all (rxBuf, "\r", "")`
3. `local parts = split(text = rxBuf, at = "\n")`
4. `n = length of list(parts)`
5. `for each number from 1 to n-1`: `call HandleLine(select list item(parts, number))`
6. `set rxBuf to select list item(parts, n)` — 마지막 조각(줄이 `\n` 으로 끝났다면 빈 문자열)

- App Inventor 텍스트 블록에서 `\n` 은 줄바꿈으로 해석된다.
- 요점: split 의 마지막 항목은 미완성 조각이므로 버리지 말고 버퍼에 남긴다.

**to HandleLine (line)**
1. `set line to trim(line)`; 빈 문자열이면 종료
2. `set LblDebug.Text to line`
3. `if starts at(line, "V,") = 1`:
   - `f = split(line, ",")`
   - `if length(f) = 3 AND is number?(item 2) AND is number?(item 3)`:
     - `call ShowVolt(item 2, item 3)`, `set lastRx to ClockWatch.SystemTime`
4. `else if starts at(line, "S,") = 1`:
   - `call ShowState(upcase(select list item(split(line, ","), 2)))`
5. `else if line = "K"`:
   - `set LblPing.Text to join("지연: ", ClockWatch.SystemTime - pingSent, " ms")`
6. 그 외는 무시.

**to ShowVolt (c, m)**
1. `LblCtrl.Text = join("제어 9V팩  ", round-to-2-decimals(c), " V")`
2. `LblMotor.Text = join("모터 7.2V팩  ", round-to-2-decimals(m), " V")` (소수 2자리: `format as decimal(number, places 2)`)
3. 색: `if c < 7.5` → `LblCtrl.TextColor = 빨강` else 검정 (또는 초록)
   `if m < 6.6` → `LblMotor.TextColor = 빨강` else 검정
4. (선택) 그래프: `add items to list ctrlHist c`; 길이 > 60 이면 첫 항목 제거; `Canvas1.Clear` 후 값을 y 좌표로 변환해 `Canvas1.DrawLine` 로 이어 그림 (y 범위 5~10 V 고정 권장; 6.6 V/7.5 V 가이드선 추가)

**to ShowState (s)**
1. `set state to s`, `LblState.Text = s`
2. 색: BOOT 회색 / HOMING 주황 / IDLE 초록 / RUN 파랑 / ARRIVED 보라 / FAULT 빨강 / 그 외 회색
3. `call UpdateButtons`
4. `if s = "RUN"` → `set startSent to 0` (출발 확인됨)

**to UpdateButtons**
- `BtnStart.Enabled = (connected AND state = "IDLE" AND (ClockWatch.SystemTime − lastRx < 2000))`
- `BtnRehome.Enabled = (같은 조건)`
- `BtnStart.BackgroundColor`: 활성이면 초록, 아니면 회색

### 4.5 송신
**when BtnStart.Click**
1. `if connected AND state = "IDLE"`:
   - `call BluetoothLE1.WriteStrings(SVC, CHR, false, "S\n")` (또는 WriteStringsWithResponse, 4.7 참조)
   - `set startSent to ClockWatch.SystemTime`
   - `set BtnStart.Enabled to false` (중복 클릭 방지)
2. else `Notifier1.ShowAlert("대기(IDLE) 상태에서만 출발할 수 있습니다")`

**when BtnRehome.Click**: 같은 방식으로 `"H\n"` 송신 (IDLE 일 때만).

**when BtnPing.Click** 및 **ClockPing.Timer**
1. `if connected`: `set pingSent to ClockWatch.SystemTime`, `call BluetoothLE1.WriteStrings(SVC, CHR, false, "P\n")`

(인자 `false` 는 utf16 여부. 시계 시각은 어느 Clock 이든 `Clock.SystemTime` 으로 얻는다.)

### 4.6 감시 타이머와 오류 처리
**when ClockWatch.Timer** (500 ms)
1. `call UpdateButtons` (수신이 2초 끊기면 자동으로 START 비활성)
2. `if connected AND ClockWatch.SystemTime − lastRx > 2000`: `LblState.Text = "수신 끊김"`, 회색
3. `if startSent ≠ 0 AND SystemTime − startSent > 2000 AND state ≠ "RUN"`: `Notifier1.ShowAlert("출발 응답 없음, 다시 시도")`, `set startSent to 0`

**when BluetoothLE1.Disconnected**
1. `set connected to false`, `set rxBuf to ""`, `ClockPing.TimerEnabled=false`, `UpdateButtons`
2. `LblConnStatus.Text = "연결 끊김"`, `LblState.Text = "연결 끊김"`(빨강)
3. `if not userDisconnect AND lastAddr ≠ ""`: `ClockReconnect.TimerEnabled = true` (자동 재연결 시작), 알림 표시
4. else `MainPanel.Visible=false`, `ConnectPanel.Visible=true`

**when ClockReconnect.Timer** (3초마다, 최대 10회 권장: 카운터 변수 추가)
1. `if not connected`: `call BluetoothLE1.ConnectWithAddress(lastAddr)` [확인: 블록 존재 여부. 없으면 StartScanning 후 DeviceFound 에서 주소가 lastAddr 인 항목의 번호로 Connect]
2. 성공하면 `Connected` 이벤트에서 타이머를 끈다. 10회 실패 시 타이머 끄고 연결 화면으로 복귀.

**오류 이벤트**: 확장에 연결 실패/오류 이벤트(`ConnectionFailed`, `Error` 등)가 있으면 [확인] `Notifier1.ShowAlert` 로 메시지를 보여주고 연결 화면으로 복귀한다.

### 4.7 쓰기 방식: WriteStrings vs WriteStringsWithResponse
- `WriteStrings` = 응답 없는 쓰기(Write Without Response)로 알려져 있고, HM-10 FFE1 이 지원하는 일반적 방식이다. 지연이 짧아 START 에 적합.
- `WriteStringsWithResponse` = 응답 있는 쓰기. 모듈(클론)이 Write Without Response 를 광고하지 않고 Write 만 광고하면 이쪽이 필요하다.
- 커뮤니티 보고: 특성 속성과 쓰기 종류가 맞지 않으면 오류 없이 조용히 실패하기도 한다(<https://community.appinventor.mit.edu/t/bluetoothle-extension-cant-send-but-can-receive-at-09-zs-040/159504>, <https://community.appinventor.mit.edu/t/ble-writestrings-not-sending-able-to-receive-device-uuid-information/27359>). 한쪽이 안 되면 다른 쪽으로 바꿔 본다.
- 구현 팁: 전역 `useResp`(체크박스 `ChkResp`)를 두고 모든 송신을 `to Send(text)` 절차 한 곳으로 모아, `if useResp → WriteStringsWithResponse else WriteStrings` 로 분기한다. 현장에서 체크박스만 바꿔 시험할 수 있다.
- 구독 관련 주의: 일부 사용자가 RegisterForStrings 사용 후 재연결이 안 되는 현상을 보고했다(<https://community.appinventor.mit.edu/t/bluetoothle-extension-cant-reconnect-to-ble-device-after-using-registerforstring/124789>). 재연결이 안 되면 `Disconnect` 호출 → 2초 대기 → 다시 `Connect` → `Connected` 에서 재구독 순서를 지키고, 그래도 안 되면 앱을 재시작한다. 대회 전에 반드시 재연결 시험을 해 둘 것.
- 개발 중에 Companion 에서 BLE 권한 오류가 나면 "권한" 설정에서 근처 기기/위치를 허용한다.

## 5. 시험 절차

### 5.1 로봇 없이 (test_echo 스케치)
1. HM-10 을 Mega 의 Serial3(TX3=14 → HM-10 RXD, RX3=15 ← HM-10 TXD; HM-10 은 3.3 V 로직이므로 Mega TX3 → HM-10 RXD 는 분압(1k/2k) 권장, 전원 5 V/GND)에 연결.
2. `test_echo/test_echo.ino` 를 Mega 에 업로드. 시리얼 모니터 115200 에서 `TX S,BOOT` 등이 보이면 정상.
3. 앱에서 스캔 → 모듈 선택 → 연결. 기대 동작:
   - BOOT → HOMING(2 s) → IDLE 로 상태 라벨 변화, 이후 START 활성
   - 제어 ≈ 8.9~9.1 V, 모터 ≈ 7.4 V 가 0.5 초마다 갱신
   - START → `S,RUN` (주황/파랑), 10 초 뒤 `S,ARRIVED`, 5 초 뒤 자동 IDLE
   - 핑 → 지연 ms 표시 (보통 수십~수백 ms)
   - 재홈(H): IDLE 일 때만 HOMING 으로 전환
4. 시험 전용 명령(앱에 임시 버튼을 만들거나 다른 BLE 시험 도구에서 전송): `L` = 저전압 모드 토글 → 제어 7.3 V, 모터 6.5 V 로 빨강 표시 확인. `F` = FAULT 토글.
5. 분할 수신 시험: test_echo 에서 `Serial3.print` 를 잘라 보내거나 `V` 주기를 20 ms 로 줄여 합쳐진 알림에서도 값이 정상인지 확인.
6. 끊김 시험: 스케치 전원을 끊었다 다시 켜 `Disconnected` → 자동 재연결 동작 확인, 폰 BLE 를 껐다 켜기.
7. 수신 감시 시험: 스케치를 멈추면 2 초 뒤 START 가 비활성이 되는지 확인.

### 5.2 로봇과 함께
1. 로봇 펌웨어가 `V`/`S` 를 protocol.md 대로 출력하는지 USB 시리얼 로그로 먼저 확인.
2. 앱 연결 → 로봇 전원 투입 직후 `BOOT → HOMING → IDLE` 이 앱에 표시되는지.
3. 실제 배터리 전압을 멀티미터로 측정해 앱 값과 비교 (±0.1 V 이내, 어긋나면 로봇 쪽 분압 보정).
4. START 로 출발 → RUN → ARRIVED. 주행 중 모터 소음/전압 강하로 BLE 가 끊기는지 확인(안테나 위치, 케이블 분리).
5. 규정 확인: 지급 BLE 모듈 사용, 자체 제작 앱 사용 여부, 일반 터미널 앱 미사용.
6. 최종 .apk 를 대회에 쓸 모든 폰에 설치하고 저전압/끊김/재연결 시험을 반복.

## 6. 체크리스트
- [ ] 확장 임포트 완료, 파일명 날짜 기록
- [ ] `[확인]` 표시 블록 이름·매개변수 실제 서랍과 대조
- [ ] 필터 문자열을 실제 모듈 이름에 맞게 수정
- [ ] WriteStrings / WithResponse 중 동작하는 쪽 확정
- [ ] 재연결 시험 3회 이상 성공
