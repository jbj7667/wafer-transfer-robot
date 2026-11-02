#include "arm_kin.h"
#include "config.h"
#include <math.h>

static const BasePose BASES[6] = {
    {1, +131.6f, 361.2f, 0},  // 하단 좌
    {2, -131.6f, 361.2f, 0},  // 하단 우
    {3, +101.5f, 326.5f, 1},  // 중단 좌
    {4, -101.5f, 326.5f, 1},  // 중단 우
    {5, +73.4f, 386.0f, 2},   // 상단 좌
    {6, -73.4f, 386.0f, 2},   // 상단 우
};

const BasePose* kinBase(uint8_t n) { return (n >= 1 && n <= 6) ? &BASES[n - 1] : nullptr; }

float kinBasePickZ(const BasePose& b) { return POST_TOP_MM[b.row] - UNDER_WAFER_MM - LIFT_HOME_MM; }

float kinWristRadius(float r_cd) { return r_cd - FORK_OFFSET; }

float kinRcdFromPhi(float phi_deg) { return 2.0f * ARM_L * cosf(phi_deg * DEG_TO_RAD) + FORK_OFFSET; }

float kinWrapDeg(float th) {
  while (th < 0.0f) th += 360.0f;
  while (th >= 360.0f) th -= 360.0f;
  return th;
}

KinStatus kinSolve(float theta_deg, float r_cd, ArmPose& out) {
  float c = kinWristRadius(r_cd) / (2.0f * ARM_L);
  if (c > 1.0f) c = 1.0f;
  if (c < -1.0f) c = -1.0f;
  float phi = acosf(c) * RAD_TO_DEG;
  out.th_deg = kinWrapDeg(theta_deg);
  out.phi_deg = phi;
  if (phi < PHI_MIN_DEG) return KIN_TOO_FAR;
  if (phi > PHI_FOLD_DEG) return KIN_TOO_NEAR;
  return KIN_OK;
}

const __FlashStringHelper* kinStatusName(KinStatus s) {
  switch (s) {
    case KIN_OK: return F("ok");
    case KIN_TOO_FAR: return F("too far (singularity guard)");
    default: return F("too near");
  }
}

float kinApplyDeltaTheta(float theta_deg, float dTheta_deg) { return theta_deg + dTheta_deg; }
float kinCorrectHeading(float theta_deg, float psi_deg) { return theta_deg - psi_deg; }
