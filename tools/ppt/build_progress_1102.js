// 10주차 진행 상황 발표 PPT 생성 (pptxgenjs). 실행:
//   $env:NODE_PATH="<pptxgenjs가 설치된 node_modules>"; node tools/ppt/build_progress_1102.js
// 환경변수: VIDEO(내장 영상 mp4 경로), POSTER(영상 포스터 png/jpg), OUT(출력 pptx 경로)
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(process.env.APPLY_THEME ||
  "C:/Users/gy050/.claude/skills/synced/0fb1f364-20c0-4f1f-85a4-aed8b714298c_ed40d9a4-ba5d-4421-90aa-10532f534713/pptx/scripts/apply_theme.js");

const ROOT = path.resolve(__dirname, "..", "..");
const R = path.join(ROOT, "public/cad/assembly/renders");
const PH = "C:/Users/gy050/Downloads/10주차_진행상황보고/사진";
const OUT = process.env.OUT || "C:/Users/gy050/Downloads/10주차_진행상황보고/[mca]창의과제(캡스톤디자인)_10주차_진행상황.pptx";
const VIDEO = process.env.VIDEO || "C:/Users/gy050/Videos/wafer_robot/out/final_20261029_design.mp4";
const POSTER = process.env.POSTER || path.join(PH, "렌더_등각.png");

// ---- 디자인 토큰 (shadcn/Tailwind slate + indigo) ----
const INK = "0F172A", SLATE = "334155", MUTED = "64748B", LINE = "E2E8F0", SOFT = "F1F5F9", WHITE = "FFFFFF";
const INDIGO = "4F46E5", INDIGO_L = "E0E7FF", EMERALD = "10B981", AMBER = "F59E0B", ROSE = "F43F5E", SKY = "0EA5E9";
const FONT = "Malgun Gothic";
const THEME = {
  name: "MCA Progress", headFontFace: FONT, bodyFontFace: FONT,
  colors: { dk1: INK, lt1: WHITE, dk2: SLATE, lt2: SOFT, accent1: INDIGO, accent2: EMERALD, accent3: AMBER,
    accent4: ROSE, accent5: SKY, accent6: MUTED, hlink: INDIGO, folHlink: MUTED },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.title = "웨이퍼 이송 로봇 — 10주차 진행 상황";
pres.author = "정비제";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

pres.defineSlideMaster({
  title: "LIGHT", background: { color: WHITE },
  objects: [
    { text: { text: "웨이퍼 이송 로봇  |  창의과제 10주차 진행 상황  |  정비제", options: { x: 0.6, y: 7.02, w: 9, h: 0.3, fontSize: 11, color: MUTED, fontFace: FONT, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.02, w: 0.6, h: 0.3, fontSize: 11, color: MUTED, fontFace: FONT, align: "right" },
});
pres.defineSlideMaster({ title: "DARK", background: { color: INK }, objects: [] });

const T = (s, text, o) => s.addText(text, Object.assign({ isTextBox: true, fontFace: FONT, color: INK, margin: 0, valign: "top" }, o));
const title = (s, text) => T(s, text, { x: 0.6, y: 0.4, w: 12.1, h: 0.8, fontSize: 30, bold: true, valign: "middle", objectName: "제목" });
const shadow = () => ({ type: "outer", color: "000000", opacity: 0.1, blur: 8, offset: 2, angle: 90 });
const card = (s, x, y, w, h, fill) => s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.12, fill: { color: fill || SOFT }, line: { color: fill || SOFT, width: 0 }, shadow: shadow() });
const pill = (s, x, y, w, h, text, fill, color, size) => {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: h / 2, fill: { color: fill }, line: { color: fill, width: 0 } });
  T(s, text, { x, y, w, h, fontSize: size || 14, bold: true, color, align: "center", valign: "middle" });
};
const num = (s, x, y, n, fill) => {
  s.addShape(pres.ShapeType.ellipse, { x, y, w: 0.5, h: 0.5, fill: { color: fill || INDIGO }, line: { color: fill || INDIGO, width: 0 } });
  T(s, String(n), { x, y, w: 0.5, h: 0.5, fontSize: 18, bold: true, color: WHITE, align: "center", valign: "middle" });
};
const img = (s, file, x, y, w, h, alt) => s.addImage({ path: file, x, y, w, h, sizing: { type: "cover", w, h }, altText: alt, shadow: shadow() });
const arrow = (s, x1, y1, x2, y2, color) => s.addShape(pres.ShapeType.line, {
  x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), flipH: x2 < x1, flipV: y2 < y1,
  line: { color: color || MUTED, width: 1.75, endArrowType: "triangle" },
});
const box = (s, x, y, w, h, text, fill, color, size) => {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.1, fill: { color: fill }, line: { color: fill === WHITE ? LINE : fill, width: 1 } });
  T(s, text, { x: x + 0.08, y, w: w - 0.16, h, fontSize: size || 13, bold: true, color: color || INK, align: "center", valign: "middle" });
};
const notes = (s, t) => s.addNotes(t);
const bullets = (items, o) => items.map((t, i) => ({ text: t, options: Object.assign({ bullet: { indent: 16 }, breakLine: i < items.length - 1, paraSpaceAfter: 8 }, o || {}) }));

// ===== 1. 표지 =====
{
  const s = pres.addSlide({ masterName: "DARK" });
  T(s, "2026 창의과제(캡스톤디자인)  ·  10주차 진행 상황 발표", { x: 0.8, y: 1.0, w: 6.6, h: 0.4, fontSize: 16, color: "A5B4FC", bold: true });
  T(s, "웨이퍼 이송 로봇", { x: 0.8, y: 1.8, w: 6.6, h: 1.0, fontSize: 48, bold: true, color: WHITE });
  T(s, "U자 포크 + 단일 승강축\n전부 3D 출력으로 제작", { x: 0.8, y: 3.0, w: 6.6, h: 1.1, fontSize: 22, color: "CBD5E1" });
  T(s, "로봇자동화공학부  정비제", { x: 0.8, y: 5.4, w: 6.6, h: 0.5, fontSize: 20, bold: true, color: WHITE });
  T(s, "2026. 11. 02", { x: 0.8, y: 5.95, w: 6.6, h: 0.4, fontSize: 16, color: "94A3B8" });
  s.addImage({ path: path.join(PH, "렌더_등각.png"), x: 7.4, y: 1.3, w: 5.4, h: 3.86, altText: "조립 완성 모델 등각 렌더", shadow: shadow() });
  T(s, "조립 모델(소프트웨어 렌더, 현재 설계)", { x: 7.4, y: 5.3, w: 5.4, h: 0.3, fontSize: 12, color: "94A3B8", align: "center" });
  notes(s, "안녕하세요, 웨이퍼 이송 로봇 진행 상황을 발표하는 정비제입니다. 이번 주는 설계를 확정하고 출력·조립 단계로 넘어간 주입니다.");
}

// ===== 2. 한눈에 요약 =====
{
  const s = pres.addSlide({ masterName: "LIGHT" });
  title(s, "한눈에 보기: 설계 확정, 제작 단계로 진입");
  const st = [["① 설계 확정", "완료", EMERALD, WHITE], ["② 3D 출력", "진행 중", AMBER, INK], ["③ 조립", "진행 중", AMBER, INK], ["④ 주행·승강 시험", "예정", "CBD5E1", SLATE]];
  st.forEach((p, i) => {
    const x = 0.6 + i * 3.08;
    pill(s, x, 1.5, 2.85, 0.62, `${p[0]}  ·  ${p[1]}`, p[2], p[3], 15);
  });
  const stats = [["0건", "조립 점검 간섭", "7개 승강 높이에서 확인"], ["249×210×245", "출발 크기 (mm)", "규정 250³ 이내"], ["약 1.5 kg", "총질량 (추정)", "출력 부품 약 315 g"], ["0.27 g", "급제동 전복 한계", "감속을 2 m/s² 이하로 제한"]];
  stats.forEach((p, i) => {
    const x = 0.6 + i * 3.08, y = 2.55;
    card(s, x, y, 2.85, 3.0);
    T(s, p[0], { x: x + 0.2, y: y + 0.35, w: 2.45, h: 0.9, fontSize: i === 1 ? 26 : 34, bold: true, color: INDIGO, valign: "middle" });
    T(s, p[1], { x: x + 0.2, y: y + 1.35, w: 2.45, h: 0.4, fontSize: 16, bold: true });
    T(s, p[2], { x: x + 0.2, y: y + 1.85, w: 2.45, h: 0.9, fontSize: 14, color: MUTED });
  });
  T(s, "※ 질량·시간은 설계 모델 기반 추정값이며, 주행·승강 실물 시험은 이번 주부터 진행합니다.", { x: 0.6, y: 6.1, w: 12.1, h: 0.4, fontSize: 14, color: SLATE });
  notes(s, "현재 단계는 설계 확정 완료, 출력과 조립 진행 중, 주행·승강 시험은 예정입니다. 숫자는 모두 설계 모델에서 계산한 값이라 추정으로 표기했습니다.");
}

// ===== 3. 과제와 제약 =====
{
  const s = pres.addSlide({ masterName: "LIGHT" });
  title(s, "과제와 설계 제약");
  card(s, 0.6, 1.5, 5.9, 4.9);
  T(s, "경진대회", { x: 0.9, y: 1.7, w: 5.3, h: 0.5, fontSize: 22, bold: true, color: INDIGO });
  T(s, bullets(["예선 120초, 2회: 웨이퍼 3개를 맞은편으로 이송 (이송 수 + 완주, 최대 4점)", "본선 150초, 1:1 토너먼트: 웨이퍼 위치가 무작위라 센서로 자율 감지", "추가기능 5개 (BLE 출발, 푸시 출발, 전압 모니터링, 자체 초기화, 도착 LED)"]),
    { x: 0.9, y: 2.4, w: 5.3, h: 3.8, fontSize: 18 });
  card(s, 6.8, 1.5, 5.9, 4.9);
  T(s, "설계 제약", { x: 7.1, y: 1.7, w: 5.3, h: 0.5, fontSize: 22, bold: true, color: INDIGO });
  T(s, bullets(["출발 크기 250×250×250 mm 이내", "동작 모터 3개 이하 (승강에 스테퍼 1개 사용)", "센서는 지급품만 사용 (라인·IR·초음파)", "사비 120,000원 이하 — 이번 구성은 신규 구매 0원 (지급품 + 보유 자재 + 3D 출력)"]),
    { x: 7.1, y: 2.4, w: 5.3, h: 3.8, fontSize: 18 });
  notes(s, "규정에서 설계에 가장 크게 영향을 주는 것은 웨이퍼 위치가 무작위라는 점과 출발 크기, 동작 모터 개수입니다.");
}

// ===== 4. 설계 개요 =====
{
  const s = pres.addSlide({ masterName: "LIGHT" });
  title(s, "설계 개요: U자 포크 + 단일 승강축");
  img(s, path.join(PH, "렌더_등각.png"), 0.6, 1.5, 6.6, 4.71, "조립 모델 등각 렌더");
  T(s, "승강 원점(포크 윗면 155 mm) 자세", { x: 0.6, y: 6.3, w: 6.6, h: 0.3, fontSize: 12, color: MUTED, align: "center" });
  const rows = [["구조", "U자 포크가 CD를 아래에서 받쳐 들고, 리드스크류 승강축 1개로 올리고 내림 (횡 허용 ±14 mm)"], ["제작", "리드스크류·레일·캐리지까지 전부 3D 출력 — 기성품은 모터·스위치·볼트뿐"], ["규정", "출발 크기 249×210×245 mm, 동작 모터 1개 사용 (한도 3개)"]];
  rows.forEach((r, i) => {
    const y = 1.55 + i * 1.6;
    num(s, 7.6, y, i + 1);
    T(s, r[0], { x: 8.3, y, w: 4.4, h: 0.5, fontSize: 20, bold: true, valign: "middle" });
    T(s, r[1], { x: 8.3, y: y + 0.55, w: 4.4, h: 0.95, fontSize: 15, color: SLATE });
  });
  notes(s, "구조는 포크로 CD를 아래에서 받쳐 들어 올리는 방식입니다. 타 팀 사례를 비교해 신뢰성과 정렬 허용오차를 가장 높게 평가해 선정했습니다.");
}

// ===== 5. 승강부 =====
{
  const s = pres.addSlide({ masterName: "LIGHT" });
  title(s, "승강부: 걸림을 줄이는 3가지 설계");
  const items = [
    ["리드스크류 Tr12×8 (두 줄)", "모터 1회전에 8 mm 이동, 속도 20 mm/s로 제한 — 스테퍼 토크 여유 확보"],
    ["레일 일체 마스트", "하부 블록과 10×10 레일을 한 덩어리로 눕혀 출력 — 접합부와 정렬 오차 감소"],
    ["플로팅 너트", "캐리지 안에서 가로 ±1 mm 움직여 스크류·레일 어긋남을 흡수 (원점 근처 걸림 방지)"],
  ];
  items.forEach((r, i) => {
    const y = 1.5 + i * 1.72;
    card(s, 0.6, y, 6.9, 1.55);
    num(s, 0.85, y + 0.2, i + 1);
    T(s, r[0], { x: 1.6, y: y + 0.18, w: 5.7, h: 0.5, fontSize: 19, bold: true, valign: "middle" });
    T(s, r[1], { x: 1.6, y: y + 0.72, w: 5.7, h: 0.75, fontSize: 14, color: SLATE });
  });
  img(s, path.join(PH, "렌더_승강상한.png"), 7.9, 1.5, 4.8, 3.43, "승강 상한 자세 렌더");
  T(s, "승강 상한(포크 윗면 215 mm) 자세", { x: 7.9, y: 5.0, w: 4.8, h: 0.3, fontSize: 12, color: MUTED, align: "center" });
  T(s, "근거: 기구 검토에서 스크류·레일·모터 축 3점 지지가 과구속으로 걸릴 수 있다고 확인해 반영", { x: 7.9, y: 5.5, w: 4.8, h: 0.9, fontSize: 14, color: SLATE });
  notes(s, "승강부는 전부 출력으로 만들기 때문에 정렬 오차가 가장 큰 위험입니다. 그래서 레일을 일체형으로 만들고, 너트가 가로로 조금 움직이도록 플로팅 구조를 넣었습니다.");
}

// ===== 6. 하체·전장 =====
{
  const s = pres.addSlide({ masterName: "LIGHT" });
  title(s, "하체·전장 구성");
  // 블록 다이어그램 (왼쪽 영역)
  box(s, 0.6, 1.7, 2.2, 0.8, "제어 팩\nAA 6셀", SOFT, INK, 13);
  box(s, 0.6, 2.9, 2.2, 0.8, "모터 팩\nNiMH 7.2 V", SOFT, INK, 13);
  box(s, 3.4, 1.7, 2.3, 2.0, "Arduino Mega 2560\n+ IO 쉴드", INDIGO, WHITE, 15);
  arrow(s, 2.8, 2.1, 3.4, 2.1, MUTED);
  arrow(s, 2.8, 3.3, 3.4, 3.1, MUTED);
  const outs = [["L298 → DC 모터 ×2 (주행)", 1.55], ["스테퍼 드라이버 → 승강 모터", 2.25], ["라인 3ch · IR · 스위치 ×2", 2.95], ["HM-10 BLE → 스마트폰 앱", 3.65]];
  outs.forEach((o) => { box(s, 6.4, o[1], 2.6, 0.55, o[0], WHITE, INK, 12); arrow(s, 5.7, 2.7, 6.4, o[1] + 0.27, MUTED); });
  T(s, "시스템 구성도 (제어·모터 전원 분리)", { x: 0.6, y: 4.5, w: 8.4, h: 0.3, fontSize: 12, color: MUTED });
  img(s, path.join(PH, "모터_시험판_맞춤.jpg"), 0.6, 4.95, 2.6, 1.7, "모터 브래킷 시험판을 모터에 맞춘 사진");
  T(s, "모터 시험판: 구멍 3개가 맞고 고정됨", { x: 3.4, y: 5.1, w: 5.6, h: 1.4, fontSize: 14, color: SLATE });
  const rows = ["모터 브래킷: 실측 축 편심 7.5 mm, 고정 구멍 PCD 30.4 mm 반영", "바퀴: Ø65, 출력 허브 + TPU 타이어", "볼 캐스터: 높이 29 mm에 맞춘 스페이서(높이 23 mm)"];
  T(s, bullets(rows), { x: 9.5, y: 1.55, w: 3.2, h: 4.9, fontSize: 15 });
  notes(s, "전장은 지급품 중심입니다. 제어와 모터 전원을 분리해 모터 노이즈로 보드가 리셋되는 문제를 막았고, 모터 브래킷은 실측한 구멍 배치로 시험판을 먼저 출력해 맞춰 봤습니다.");
}

// ===== 7. 제작 진행 =====
{
  const s = pres.addSlide({ masterName: "LIGHT" });
  title(s, "제작 진행: 출력과 하체 조립");
  img(s, path.join(PH, "출력_진행_프린터_위에서.jpg"), 0.6, 1.45, 4.1, 2.3, "3D 프린터가 부품을 출력하는 모습");
  img(s, path.join(PH, "출력_바퀴_본체.jpg"), 4.9, 1.45, 3.7, 2.3, "바퀴 본체 출력 클로즈업");
  img(s, path.join(PH, "출력_하판.jpg"), 8.8, 1.45, 3.9, 2.3, "하판 출력");
  T(s, "프린터 여러 대로 병행 출력 중", { x: 0.6, y: 3.82, w: 4.1, h: 0.3, fontSize: 12, color: MUTED, align: "center" });
  T(s, "바퀴 본체", { x: 4.9, y: 3.82, w: 3.7, h: 0.3, fontSize: 12, color: MUTED, align: "center" });
  T(s, "하판", { x: 8.8, y: 3.82, w: 3.9, h: 0.3, fontSize: 12, color: MUTED, align: "center" });
  const hdr = (t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: INDIGO }, fontFace: FONT, fontSize: 14 } });
  const cell = (t, o) => ({ text: t, options: Object.assign({ fontFace: FONT, fontSize: 14, color: INK }, o || {}) });
  s.addTable([
    [hdr("차수"), hdr("내용"), hdr("상태")],
    [cell("1차"), cell("하판, 모터 브래킷, 바퀴, 타이어, 배터리 크래들, 시험판"), cell("출력 완료·하체 조립 중", { bold: true, color: EMERALD })],
    [cell("2차"), cell("승강부(스크류·마스트·캐리지·포크), 상판, 패널, 시험 조각"), cell("출력 중", { bold: true, color: "B45309" })],
    [cell("3차"), cell("하판 v3(노치 보완), 바퀴 v3(구멍 관통·필렛)"), cell("출력 예정", { bold: true, color: MUTED })],
  ], { x: 0.6, y: 4.3, w: 12.1, colW: [1.2, 7.7, 3.2], rowH: 0.52, border: { type: "solid", color: LINE, pt: 1 }, valign: "middle" });
  notes(s, "1차 출력은 끝났고 하체를 조립하고 있습니다. 2차는 승강부와 시험 조각을 출력 중이고, 설계 점검에서 나온 수정은 3차로 따로 출력합니다.");
}

// ===== 8. 검증 =====
{
  const s = pres.addSlide({ masterName: "LIGHT" });
  title(s, "검증: 실물 시험 + 조립 모델 점검");
  card(s, 0.6, 1.5, 5.9, 5.0);
  T(s, "실물 시험", { x: 0.9, y: 1.7, w: 5.3, h: 0.5, fontSize: 22, bold: true, color: INDIGO });
  T(s, bullets([
    "모터 시험판: 구멍 3개가 맞고 고정됨 (축이 구멍 안에서 약간 치우쳐 조립 후 재확인)",
    "나사·너트 시험: 나사 부분은 간극 0.3 mm로 잘 맞음. 입구가 막힌 것은 시험 조각 손잡이 설계 오류로 확인",
    "공차 시험 조각(레일 구멍·M3 구멍)을 큰 부품 출력 전에 먼저 출력",
  ]), { x: 0.9, y: 2.4, w: 5.3, h: 4.0, fontSize: 17 });
  card(s, 6.8, 1.5, 5.9, 5.0);
  T(s, "조립 모델 점검 (소프트웨어)", { x: 7.1, y: 1.7, w: 5.3, h: 0.5, fontSize: 22, bold: true, color: INDIGO });
  T(s, bullets([
    "6회 반복 점검: 7개 승강 높이에서 부품 간 간섭 0건",
    "출발 크기 249×210×245 mm (규정 250³ 이내)",
    "급제동 시 앞 전복 한계 0.27 g → 제동 감속 2 m/s² 이하로 제한하는 램프 적용",
    "IR 센서의 렌즈 시야가 포크·캐리지에 가려지지 않음 (광선 18개 확인)",
  ]), { x: 7.1, y: 2.4, w: 5.3, h: 4.0, fontSize: 17 });
  notes(s, "실물 시험은 시험 조각 위주입니다. 조립 모델 점검은 간섭, 출발 크기, 질량 중심, 센서 시야를 확인했습니다. 아직 주행과 승강의 실물 시험은 예정입니다.");
}

// ===== 9. 문제 → 해결 =====
{
  const s = pres.addSlide({ masterName: "LIGHT" });
  title(s, "문제 → 원인 → 해결");
  const hdr = (t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: INDIGO }, fontFace: FONT, fontSize: 14 } });
  const c = (t, o) => ({ text: t, options: Object.assign({ fontFace: FONT, fontSize: 15, color: INK, valign: "middle" }, o || {}) });
  const data = [
    ["IR 센서가 가정한 모델이 아님", "각인 확인: GP2Y0A21 (10~80 cm), 가정은 A41", "트레이 재설계, CD 구분은 실물 시험으로 확인"],
    ["하판에 소나용 노치가 남음", "오른쪽 브래킷 볼트 2개·마스트 아래에 재료 없음", "노치를 메운 하판 v3로 교체 (3차 출력)"],
    ["시험 너트가 입구부터 안 들어감", "시험 손잡이(Ø9.8)가 너트 구멍(약 Ø9.0)보다 큼", "시험 조각 설계 오류, 실제 부품은 영향 없음"],
    ["승강 나사·레일이 걸릴 위험", "스크류·레일·모터 축 3점 과구속", "플로팅 너트 + 저널 구멍 여유"],
    ["넥 스위치가 CD와 겹침", "스위치 윗면이 CD 바닥(Z 155)보다 높음", "스위치를 포크 아래에 매달도록 변경"],
  ];
  const rows = [[hdr("문제"), hdr("원인"), hdr("해결")]].concat(data.map((r, i) => r.map((t, j) => c(t, j === 0 ? { bold: true } : { color: j === 2 ? "047857" : SLATE })).map((x) => { x.options.fill = { color: i % 2 ? WHITE : SOFT }; return x; })));
  s.addTable(rows, { x: 0.6, y: 1.5, w: 12.1, colW: [3.6, 4.4, 4.1], rowH: [0.55, 0.95, 0.95, 0.95, 0.95, 0.95], border: { type: "solid", color: LINE, pt: 1 }, valign: "middle" });
  notes(s, "점검에서 문제를 찾아 출력 전에 바꾼 사례입니다. 특히 센서가 가정한 모델과 달랐던 점은 실물을 직접 확인해서 알게 됐고, 시험으로 한 번 더 검증할 예정입니다.");
}

// ===== 10. 알고리즘 =====
{
  const s = pres.addSlide({ masterName: "LIGHT" });
  title(s, "알고리즘: CD 위치가 무작위여도 완주");
  box(s, 0.6, 1.6, 2.2, 0.8, "행 교차점 도착", SOFT, INK, 14);
  box(s, 3.2, 1.6, 2.6, 0.8, "한쪽으로 90° 회전\n정지선까지 접근", SOFT, INK, 13);
  box(s, 6.2, 1.6, 2.5, 0.8, "포크를 CD 아래로\n올림", SOFT, INK, 14);
  arrow(s, 2.8, 2.0, 3.2, 2.0); arrow(s, 5.8, 2.0, 6.2, 2.0);
  arrow(s, 7.45, 2.4, 7.45, 3.05);
  s.addShape(pres.ShapeType.diamond, { x: 6.2, y: 3.05, w: 2.5, h: 1.3, fill: { color: INDIGO_L }, line: { color: INDIGO, width: 1.5 } });
  T(s, "IR로 CD 판정", { x: 6.2, y: 3.05, w: 2.5, h: 1.3, fontSize: 14, bold: true, color: INDIGO, align: "center", valign: "middle" });
  box(s, 3.4, 5.15, 2.6, 0.95, "있음 → 집어서\n맞은편에 놓기", "D1FAE5", "065F46", 14);
  box(s, 6.4, 5.15, 2.9, 0.95, "없음 → 후진, 180° 회전\n반대쪽에서 집기 → 처음 쪽에 놓기", "FEF3C7", "92400E", 12);
  arrow(s, 6.2, 3.7, 4.7, 5.15, EMERALD); arrow(s, 8.7, 3.7, 7.85, 5.15, AMBER);
  T(s, "CD 있음/없음의 판정 문턱값은 실물 시험으로 확정할 예정", { x: 0.6, y: 3.2, w: 5.2, h: 0.8, fontSize: 14, color: SLATE });
  T(s, "라인추종 PD 제어, 정지선 이벤트로 상태 전이", { x: 0.6, y: 6.4, w: 8.4, h: 0.4, fontSize: 14, color: SLATE });
  card(s, 9.5, 1.5, 3.2, 4.9);
  T(s, "시간 예산 (추정)", { x: 9.75, y: 1.7, w: 2.8, h: 0.5, fontSize: 20, bold: true, color: INDIGO });
  T(s, bullets(["예선 약 66초 (제한 120초)", "본선 최악 약 81초 (제한 150초)", "틀린 쪽을 먼저 확인해도 행마다 약 5초 추가", "접근 정렬 오차 앞 2 mm 이하로 관리"]), { x: 9.75, y: 2.35, w: 2.8, h: 3.9, fontSize: 14 });
  notes(s, "본선은 웨이퍼 위치가 무작위라서, 행마다 한쪽을 먼저 확인하고 없으면 반대쪽으로 갑니다. 틀려도 시간 여유가 있도록 설계했지만, 시간은 모두 추정이라 실측 후 갱신하겠습니다.");
}

// ===== 11. 영상 =====
{
  const s = pres.addSlide({ masterName: "LIGHT" });
  title(s, "제작 과정 영상");
  const b64 = fs.readFileSync(POSTER).toString("base64");
  const ext = path.extname(POSTER).slice(1).replace("jpg", "jpeg");
  s.addMedia({ type: "video", path: VIDEO, x: 2.2, y: 1.4, w: 8.93, h: 5.02, cover: `image/${ext};base64,${b64}`, altText: "제작 과정 영상" });
  T(s, "설계 → 실측 → 출력 → 조립 시뮬레이션   |   영상 파일(final_20261102_progress.mp4)도 함께 제출", { x: 0.6, y: 6.5, w: 12.1, h: 0.4, fontSize: 14, color: SLATE, align: "center" });
  notes(s, "제작 과정을 담은 영상입니다. 재생이 안 될 경우를 대비해 같은 영상 파일을 폴더에 함께 제출했습니다.");
}

// ===== 12. 남은 일정·위험 =====
{
  const s = pres.addSlide({ masterName: "LIGHT" });
  title(s, "남은 일정과 위험");
  const ms = [["11/3", "최종 점검"], ["11/10", "모의대회 1\n1차 동영상"], ["11/17", "모의대회 2"], ["11/24", "경진대회"], ["12/8", "최종보고서\n동영상 제출"]];
  ms.forEach((m, i) => {
    const x = 0.6 + i * 2.45;
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.9, y: 1.6, w: 0.3, h: 0.3, fill: { color: i === 0 ? EMERALD : INDIGO }, line: { color: WHITE, width: 2 } });
    if (i < 4) s.addShape(pres.ShapeType.line, { x: x + 1.2, y: 1.75, w: 2.15, h: 0, line: { color: LINE, width: 3 } });
    T(s, m[0], { x, y: 2.0, w: 2.1, h: 0.4, fontSize: 18, bold: true, align: "center", color: INDIGO });
    T(s, m[1], { x, y: 2.4, w: 2.1, h: 0.7, fontSize: 14, align: "center", color: SLATE });
  });
  const risks = [
    ["IR 센서의 CD 판별", "측정 하한 10 cm인데 CD까지 약 44 mm → 실물로 있음/없음 값을 먼저 확인, 안 되면 지급 A41 요청"],
    ["접근 정렬 오차", "앞으로 2 mm를 넘으면 하체가 기둥 아래 원기둥에 닿음 → 넥 스위치와 제동 램프로 관리"],
    ["출력 정밀도", "레일 간극 0.2 mm, 나사 간극 0.3 mm → 시험 조각으로 먼저 확인"],
  ];
  risks.forEach((r, i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 3.5, 3.9, 2.9);
    num(s, x + 0.25, 3.7, i + 1, ROSE);
    T(s, r[0], { x: x + 0.95, y: 3.7, w: 2.8, h: 0.5, fontSize: 17, bold: true, valign: "middle" });
    T(s, r[1], { x: x + 0.25, y: 4.4, w: 3.45, h: 1.9, fontSize: 16, color: SLATE });
  });
  notes(s, "남은 위험은 세 가지입니다. 이번 주에는 하체 주행 시험과 센서 시험을 먼저 하고, 시험이 맞으면 승강부를 조립하겠습니다.");
}

// ===== 13. 감사합니다 =====
{
  const s = pres.addSlide({ masterName: "DARK" });
  T(s, "감사합니다", { x: 0.8, y: 2.6, w: 11.7, h: 1.2, fontSize: 54, bold: true, color: WHITE, align: "center", valign: "middle" });
  T(s, "웨이퍼 이송 로봇  ·  로봇자동화공학부 정비제", { x: 0.8, y: 4.0, w: 11.7, h: 0.5, fontSize: 18, color: "94A3B8", align: "center" });
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("saved", OUT, fs.statSync(OUT).size);
})();
