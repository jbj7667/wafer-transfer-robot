// arm_kin — 2링크 등장 팔(손목 반경 R_w = 2·L·cosφ)의 순/역기구학과 베이스 표
#pragma once
#include <Arduino.h>

enum KinStatus : uint8_t {
  KIN_OK = 0,
  KIN_TOO_FAR,   // φ < φ_min : 특이점 가드 (도달 한계 초과)
  KIN_TOO_NEAR   // φ > φ_fold : 너무 가까움
};

struct ArmPose {
  float th_deg;   // 회전대 방위각 0..360 (정면 0, 왼쪽 +)
  float phi_deg;  // 어깨 링크 각
};

struct BasePose {
  uint8_t n;       // 베이스 번호 1..6
  float theta;     // 정지점 S 기준 방위 (왼쪽 +, 도)
  float r_cd;      // CD 중심 반경 (mm)
  uint8_t row;     // 0=하단, 1=중단, 2=상단
};

// 정지점 S=(500,240) 에서 본 6개 베이스 (arm_option §1.1)
const BasePose* kinBase(uint8_t n);          // 범위 밖이면 nullptr
float kinBasePickZ(const BasePose& b);       // 픽 자세 Z [mm] (기둥 윗면 - 10 - Z0 높이)

float kinWristRadius(float r_cd);            // R_w = R_cd - 64
float kinRcdFromPhi(float phi_deg);          // 순기구학: φ -> CD 중심 반경
float kinWrapDeg(float th);                  // -180..180 입력도 0..360 으로
KinStatus kinSolve(float theta_deg, float r_cd, ArmPose& out);
const __FlashStringHelper* kinStatusName(KinStatus s);

// 헤딩 오차 보정: 로봇이 반시계로 ψ 틀어졌으면 (ψ>0) 명령 θ 에서 ψ 를 뺀다 (arm_option §1.3).
// dTheta 를 직접 더하려면 kinApplyDeltaTheta, ψ 를 주려면 kinCorrectHeading.
float kinApplyDeltaTheta(float theta_deg, float dTheta_deg);
float kinCorrectHeading(float theta_deg, float psi_deg);
