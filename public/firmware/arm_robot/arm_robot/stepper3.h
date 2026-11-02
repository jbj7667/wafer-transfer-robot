// stepper3 — Timer3 단일 ISR(20 kHz)로 STEP 3축 동시 생성 (DDA 위상 누산기 + 축별 사다리꼴 가감속)
// config.h 에 의존하지 않는다: 핀/방향은 s3Begin() 인자로 받는다 (대회 펌웨어에 그대로 이식 가능).
// ISR 안에서 20틱(=1 ms)마다: 축별 속도 프로파일 갱신, 리밋 스위치 폴링(디바운스 3 ms).
#pragma once
#include <Arduino.h>

constexpr uint8_t S3_AXES = 3;
constexpr uint32_t S3_TICK_HZ = 20000UL;
constexpr uint16_t S3_RATE_ABS_MAX = 10000;  // 한 축 상한 step/s (위상 증분이 16비트를 넘지 않게)

struct S3AxisPins {
  uint8_t step, dir, sleep;
  uint8_t limit;       // 리밋 스위치 핀 (내부 풀업, 눌림 = LOW)
  bool dirInvert;      // true 이면 +방향일 때 DIR=LOW
  int8_t homeDir;      // 스위치 쪽 방향 (+1/-1)
  bool limitIsEnd;     // true: 스위치가 행정 끝 (homeDir 로 이동 중 눌리면 즉시 정지 + 고장)
};

enum S3Stop : uint8_t { S3_STOP_NONE = 0, S3_STOP_ON_HIT = 1, S3_STOP_ON_RELEASE = 2 };

constexpr uint8_t S3_FAULT_END_LIMIT = 1;  // 끝 리밋을 예기치 않게 눌렀음 (비트는 1<<축)

void s3Begin(const S3AxisPins pins[S3_AXES]);

// 파라미터 (정지 중에 호출 권장)
void s3SetSpeed(uint8_t a, uint16_t vmax);   // step/s
void s3SetStartRate(uint8_t a, uint16_t vmin);
void s3SetAccel(uint8_t a, uint16_t accel);  // step/s^2
uint16_t s3GetSpeed(uint8_t a);
void s3SetSoftLimits(uint8_t a, int32_t minS, int32_t maxS, bool enable);

// 동작. 거부되면 false (소프트 한계, 이동 중 반대 방향, 수면 중)
bool s3MoveTo(uint8_t a, int32_t target, uint16_t cap = 0);  // cap=0 이면 vmax
bool s3Seek(uint8_t a, int8_t dir, uint32_t maxSteps, uint16_t cap, S3Stop mode);  // 유한 거리 탐색, 소프트 한계 무시
void s3Stop(uint8_t a);   // 즉시 정지 (위치 유지)
void s3StopAll();

// 상태
bool s3Busy(uint8_t a);
bool s3AnyBusy();
int32_t s3Pos(uint8_t a);
void s3SetPos(uint8_t a, int32_t p);
bool s3Limit(uint8_t a);       // 디바운스된 리밋 상태 (true = 눌림)
bool s3HitLatched(uint8_t a);  // S3_STOP_ON_HIT/ON_RELEASE 로 정지했는가
uint8_t s3Faults();
void s3ClearFaults();
uint32_t s3EstimateMs(uint8_t a, uint32_t steps);  // 사다리꼴 이동 예상 시간
uint16_t s3IsrLoadPct();       // ISR 최대 점유율(%) 측정값 (100 이상이면 틱 누락)
void s3SleepAll(bool sleep);
bool s3IsAsleep();
