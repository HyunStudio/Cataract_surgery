# 비주얼·인터랙션 디자인 기획서 v1.0 (2.5D → 3D)

## 디자인 컨셉
**Surgical microscope realism + clean clinical telemetry.**
환자의 눈이 화면의 주인공이다. 화려한 RPG 효과 대신 현실적인 광학 표현, 시야·깊이의 연속성, 정교하고 읽기 쉬운 조작 피드백을 지향한다. 연구용 실험에서는 시각적 정보의 가변성이 통제 가능해야 한다.

## 화면 레이아웃: 1920×1080 기준
- **중앙 수술 현미경 뷰** x=280~1510, y=95~880 (메인 약 64%): 원형/타원형 비네팅, 전방·홍채·수정체, 도구 오버레이, 최소 HUD.
- **왼쪽 작업 패널** x=20~260: 단계 이름, 현재 목표, 도구 트레이, 체크리스트, 도움 요청. 교육 모드는 맥락 설명, 숙련 모드는 축약.
- **오른쪽 환자/마취 패널** x=1540~1900: HR/ECG, BP, SpO2, 움직임/불안, 알람, '마취팀 호출'. 바 그래프는 보조, 상태 텍스트 필수.
- **아래 깊이 단면도 + 타임라인** y=890~1050: cornea/iris/lens/IOL 단면, 도구 Z축 위치, 단계 진행, pause. 원근 뷰와 단면 뷰는 동일한 anatomical state 참조.
- 반응형 레이아웃: 1600×900에서 패널 축소, 4K에서는 물리 픽셀을 늘리는 대신 UI scale 적용.

## 참고 색상 (초기 디자인 토큰, 검증 필요)
Background #091621 / Panel #152536 / Divider #324659 / Primary text #E6F1F7 / Secondary #A9BEC9 / Focus cyan #6ECBE4 / Stable mint #6EE0AD / Warning amber #F4C46B / Critical rose #EF7B86.
색상만으로 이벤트를 구분하지 않는다(아이콘·레이블·텍스트 병행). 암실 수술실 분위기와 가독성 간 균형.

## 장기·도구 아트 디렉션
- **각막**: 투명 재질, 프레넬 반사, 약한 왜곡, 상태에 따른 혼탁; 투명 효과가 조작 타깃을 가리지 않아야 함.
- **홍채/동공**: 방사형 질감, 동공 크기 변화, 움직임시 자연스러운 변위.
- **수정체**: 혼탁 영역 분리, 상태에 따른 파편/투명도 변화, 낭은 별도 레이어.
- **IOL**: 접힌 형상에서 펼친 형태로 부드러운 보간; 정렬 가이드라인은 초보 모드에서만.
- **도구**: 얇고 고정밀, 커서와 실제 팁의 대응이 명확해야 함. 팁 위치·깊이 경고는 미세하지만 인지 가능.
- 혈액/조직 묘사는 의학 교육에 필요한 범위로 한정하고 과도한 고어 연출 지양.

## 2.5D 렌더링 경로
레이어: 후방 반사/수정체 → 전낭/홍채 → 전방 및 각막 → 도구 → 광학 효과 → 비네팅 → HUD. Depth buffer 유사 정렬과 정규화 Z값; object-space 조직 충돌은 게임 모델이 계산한다. UI는 Pygame surface에 표시하고 3D 출력은 별도 surface/texture로 합성한다.

## 선택적 진짜 3D 경로
독립된 Mesh/Material/Light/Camera의 scene graph 사용. Blender에서 자체 제작한 메시를 glTF 등으로 내보내고, OpenGL/ModernGL에서 렌더링. 심도는 **현미경처럼 제한된 화각**을 기본으로 하고 orbit camera는 해부학 학습 모드에서만 허용. 쉐이더: clear-cornea/refraction approximations, lens opacity, subsurface-like stylization, depth cues. 3D 도구 충돌은 렌더 메시와 분리한 단순 collider로 처리.

## 카메라와 조작
- Pan: 보조키+드래그, Zoom: 휠, Focus: 별도 슬라이더/키, Depth: 휠+보조키 또는 키 입력.
- Tool: 왼쪽 도구 선택 → 도구 팁을 현미경 공간에 매핑 → 클릭/드래그 상호작용 → 안전 피드백.
- Interactions must be **resolution-independent** and convertible between screen, camera, and anatomical coordinates.
- Assistance levels: ghost path (tutorial only), near-miss highlighting, optional hold-to-confirm for destructive simulated actions.
- 시각장애 접근성: UI 글자 14~16pt 이상 선호 옵션, 수술 뷰 전용 확대, 고대비 텍스트, 보조 단면도 확대, motion reduction, eye fatigue breaks.

## 각 단계별 특별 애니메이션
1. 프리오프: 수술실 카드/검증 체크
2. 마취: 드레이핑 전환, 협조 신호, 환자 상태 표시
3. 진입: 현미경 포커스, 도구 팁·표면 상호작용
4. 전낭: 닫힌 곡선이 생성되는 연속 애니메이션
5. Phaco: 가상 조각과 입자 흡인; 혼탁이 점진적으로 감소
6. 정리: 잔여 재질 페이드/흡인 표시
7. IOL: 접힘→삽입→펼침→중심 맞춤
8. 마무리: 전방 안정화, 미세 누출 경보, 인계
9. 결과: 눈의 투명도 before/after, 점수 항목, 이벤트 타임라인

## 예외 이벤트 디자인 원칙
합병증 경보는 주 수술 뷰 일부를 가리지 않는 주변 경고 + 오디오 + 일시정지 선택지로 제공. 심각한 이벤트에서 실수로 연속 입력이 누적되지 않도록 상태 잠금/재확인. 사용자에게 실존 환자 안전 처치법을 지시하지 않는다.

## 사운드
현미경 조작, UI 확인, 장비 주변음, 점진적 알람. 소리 OFF에서도 모든 상태는 텍스트로 전달. 심박음을 과하게 드라마틱하게 연출하지 않고 상태 기반으로 제어.

## 화면 설계 산출물 & 에셋
assets/concepts/, assets/models/, assets/materials/, assets/audio/ 위치. 메인 수술 화면, 마취/바이탈, IOL 상태, 합병증, 결과 화면의 와이어프레임 및 3D asset specification을 후속 큐에서 제작. 모델별 제작자·출처·라이선스 기록; 환자 식별 이미지 사용 금지.

## 수용 기준
각 패널의 정보 우선순위가 명확하고, 1080p/4K 확대 테스트 통과, 컬러 외 비색상 알림 제공, depth view와 operative view의 정합성, 60fps 목표에서 가독성 유지, motion reduction 설정에도 이벤트 피드백 보존.
