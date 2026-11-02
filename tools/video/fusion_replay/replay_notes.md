# Fusion 작업 이력 재생 (모델이 자라는 영상)

대상: 파라메트릭(타임라인 있는) 문서. 예: wafer_robot_print_v1 (타임라인 487, 피처 157).

1. 문서 활성화 후 `timeline.moveToEnd()`, 뷰를 IsoTopRight + fit 하고 camera eye/target/viewExtents를 `camera.json`에 저장(프레임마다 재fit 금지).
2. `replay_batch.py`: Extrude/Revolve 피처 인덱스 목록을 만들고, 피처마다 `timeline.markerPosition=i+1` -> `doEvents` -> `refresh` -> `saveAsImageFile(1920x1080)`. 카메라는 저장값 고정, eye만 Z축 기준 총 40도 천천히 회전. 프레임별 부품명은 `frames.csv`에 기록.
   START/END를 바꿔 40프레임 정도씩 나눠 실행(프레임당 약 1.5초, 한 호출 100초 이내). 끝나면 반드시 `moveToEnd()`. 문서는 저장하지 않는다.
3. `build_video.py`: frames.csv로 concat 목록 생성(P13/P12 쇼케이스는 8fps, 나머지 20fps, 마지막 3초 정지), 부품 자막(Malgun Gothic 44px, textfile=) + 첫 3초 제목, H.264 CRF20 faststart. 용량 크면 인자로 CRF 지정.
4. 다른 문서에 쓰려면 문서 이름, 쇼케이스 부품명(SHOW), 제목 문구만 바꾼다.

주의: 팔/배치 문서는 direct-design(이력 없음)이라 이 방식 불가. 부품(바디/오큐런스)별 `isLightBulbOn` 가시성을 순서대로 켜며 촬영하는 방식이 필요하다.
