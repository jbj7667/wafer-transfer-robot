# _kb — 창의과제 지식베이스

`contaxt/`(eClass에서 받은 원본 자료 89개)를 검색·인용하기 쉬운 텍스트로 바꾼 것.

| 경로 | 내용 | 쓰는 법 |
|---|---|---|
| `rules.yaml` | 경기장·로봇·모터·센서·추가기능·가공·일정·성적 규정을 항목별로 정리. 각 항목에 원문 출처(src)와 확정도(status) | 규정 확인은 여기부터. 애매하면 src의 원문으로 |
| `teams_summary.md` | 타 팀 제안서·주차 발표(2~7주차)의 메커니즘·센서·실패 사례 비교 | 메커니즘 선정 때 벤치마킹 |
| `catalog.json` | 원본 파일 목록: 분류(official_notice / official_qna / other_team_deck), 글자 수, 이미지 수, 변환본 경로 | 원본을 찾을 때 |
| `sources/<원본경로>.md` | 원본 파일별 전문 텍스트. PPTX는 슬라이드별, PDF는 페이지별, XLSX는 표 | `grep -r "키워드" _kb/sources` |
| `figures/` | 경기장 도면(`rule_page_7·8·10·11.png`), 주요 부품 치수 이미지(`parts_size/`) | 설계 치수 확인 |
| `tools/` | 변환 스크립트. 원본이 바뀌면 다시 실행 | 아래 참고 |

## 다시 만들기

```bash
pip install python-pptx pymupdf openpyxl olefile
python -I _kb/tools/extract.py <DMU_capstone_2-2 경로> <임시폴더>/out
cd <임시폴더> && python -I <repo>/_kb/tools/render.py <DMU_capstone_2-2 경로>
python -I _kb/tools/mirror.py <임시폴더>/out _kb
```

## 주의
- 학과 자료(부품 사이즈 안내 등)에는 "무단 전재·복제·배포 금지"가 적혀 있고, 팀 구성표·타 팀 자료에는 학생 실명이 있다. **`_kb/`와 `contaxt/`는 공개 저장소에 올리지 않는다.**
- Q&A 5번 답변 본문, 일부 공지의 뒷부분은 원본 수집 단계에서 누락돼 있다(원문 재확인 필요).
