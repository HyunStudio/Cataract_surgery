# OphthoSim · Cataract Theatre — Godot 3D 게임

2026-10-26. Godot **4.7.2 stable**, GDScript, Compatibility renderer, Windows x64.

## 실행

이미 빌드한 게임: `godot/build/OphthoSim.exe`. 같은 폴더의 `OphthoSim.pck`를 함께 보관한다. 배포 ZIP 안의 두 파일을 같은 폴더에 풀고 실행한다. Godot나 Python 설치 없이 실행 가능하다.

소스로 실행하는 경우 저장소 루트에서:

```powershell
powershell -ExecutionPolicy Bypass -File tools/run-godot.ps1 -Game
# Godot 편집기
powershell -ExecutionPolicy Bypass -File tools/run-godot.ps1 -Editor
# 자동 검증
powershell -ExecutionPolicy Bypass -File tools/run-godot.ps1 -Test
```

실행 스크립트는 엔진이 없으면 공식 GitHub 릴리스의 고정 버전을 `.tools/`에 내려받는다. 게임 자체는 오프라인으로 작동한다. 기존 `python main.py`의 2.5D 모드는 별도로 유지된다.

범위 정정 후 옵션 없는 실행은 물리 연구 모드로 바뀌었다. 이 문서는 `-Game`으로 명시하는 이전 게임 구현의 안내이며, 현재 수술 시뮬레이터 목표의 완료를 의미하지 않는다.

## 게임 흐름

1. 왼쪽 사례 선택에서 표준/환자 움직임/모니터 이상/수정체낭 손상을 선택한다.
2. 수술 부위·사례 확인 → 준비 완료 버튼을 누르면 현미경으로 진입한다.
3. 필요한 도구를 트레이 또는 숫자키로 선택한다. 왼쪽 안내와 중앙 아래 깊이 표시를 확인한다.
4. 오른쪽 짧은 진입 경로를 왼쪽에서 오른쪽으로 드래그한다. 전낭은 원의 오른쪽 시작점부터 시계 방향으로 연속 드래그한다.
5. 분리 영역에서 캐뉼라를 작동한 다음 유화 도구로 혼탁한 8개 영역, 관류·흡인 도구로 잔여 피질을 차례로 제거한다. 해당 팁 주변 영역만 변한다.
6. 인젝터로 중앙 전달 영역에서 작동을 유지하고, 위치 조정 도구로 중앙에서 렌즈 정렬을 완료한다.
7. 오른쪽 세 항목을 확인한 뒤 최종 확인 완료를 눌러 결과를 본다.
8. 위험 경고가 나타나면 도구가 잠긴다. 상태 평가로 재개하거나 안전 중단한다. 낭 손상 사례는 평가 시 안전 중단으로 종료한다.

단계가 바뀌면 도구 깊이를 해당 게임 단계의 기준으로 맞춘다. 도구를 바꾸거나 시점을 전환하거나 경고를 해제한 뒤에는 버튼을 놓고 새로 눌러야 한다. 카메라 회전 대신 고정 현미경과 수술실 관찰 시점을 제공한다.

## 조작표

| 입력 | 동작 |
|---|---|
| 마우스 이동 | 3D 도구 팁 이동 |
| 왼쪽 클릭/드래그/유지 | 선택한 도구 작동 |
| 오른쪽 클릭 | 현재 작동 해제 |
| 1–7 | 절개도, 집게, 캐뉼라, 유화, 관류·흡인, 인젝터, 위치 조정 |
| 휠 | 현미경 확대·축소 |
| Shift+휠 / Q·E | 게임 내부 도구 깊이 조절 |
| Tab | 현미경 / 수술실 보기 |
| Space | 준비·최종 확인 단계 진행 |
| Esc | 일시정지 / 재개 |
| A | 경고 평가 |
| X | 안전 중단 |
| R | 현재 사례 재시작 |
| S | 종료 후 세션 기록 저장 |

UI 위·시야 밖·일시정지·경고·관찰 시점에서는 수술하지 않는다. 다른 창으로 전환하면 도구 작동을 해제한다. 튜토리얼 가이드, 고대비, 움직임 최소화, 모니터 사운드를 오른쪽에서 설정한다.

## 기록과 평가

평가는 단계 완료, 수정체·피질 제거, IOL 전달·정렬, 최종 확인, 잘못된 도구/영역 조작으로 구성된다. 첫 점수는 0점이며 안전 중단은 완수와 구분한다. 실제 술기 평가척도가 아니다.

종료 후 S 또는 결과 창의 저장 버튼으로 JSONL을 저장한다. 상태 표시줄에 절대 경로가 나온다. Windows 기본 저장 위치는 `%APPDATA%/Godot/app_userdata/OphthoSim · Cataract Theatre/`이며, 최종 경로는 게임에서 확인한다. 파일은 버전 2, 엔진 빌드, 사례·시드, 의미 입력, 결과 digest를 담는다. 개인정보나 원격 전송은 없다. 무결성 digest는 작성자 인증 서명이 아니다.

동일 빌드의 `ProcedureSession.replay_log(raw)`로 최종 상태와 결과를 검증한다. 실제 강체 물리/입자 궤적의 재생이나 과거 Python 버전 1 로그 호환을 제공하지 않는다. 저장 용량 한도를 넘긴 세션은 불완전한 로그 대신 오류를 표시한다.

## 구성과 재빌드

- `godot/scripts/procedure_session.gd`: 유일한 절차 상태, 평가, 위험 시나리오, 의미 기록.
- `godot/scripts/operative_input.gd`: 누름/해제 잠금, 빠른 이동 샘플링.
- `godot/scripts/surgical_world.gd`: 자체 생성 3D 장면과 도구·조직 표시.
- `godot/scripts/main.gd`, `monitor.gd`: 한국어 UI, 3D 좌표 입력, 모니터·깊이 단면.
- `godot/assets/manifest.json`: 자체 제작 메시·셰이더 출처.
- `godot/tests/`: 도메인, 장면, 입력, 통합, 실제 화면 좌표 플레이, GPU 캡처·벤치마크.

재빌드 시 Godot 4.7.2 Windows export templates의 `windows_release_x86_64.exe`와 `windows_debug_x86_64.exe`를 `.tools/`에 둔다. 공식 템플릿 압축 파일에서 해당 두 파일만 추출할 수 있다. `godot/build/`를 만든 후:

```powershell
.tools/godot/Godot_v4.7.2-stable_win64_console.exe --headless --path godot --export-release "Windows Desktop" build/OphthoSim.exe
```

새 Godot 코드는 실제 눈의 조직 역학·수술 광학·장비 설정을 재현하는 임상 훈련기가 아니다. 곡선/영역 기반 조직 표현과 게임 규칙을 가진 3D 교육 게임이다. VR, 햅틱, 자유 보행, 임상적 성능 검증은 포함하지 않는다. Windows GPU와 자동 검증의 실제 결과는 `GODOT_VALIDATION.md`에 구분한다.
