# 실험용 3D 수술 게임 실행 및 검증 가이드

갱신: 2026-10-13 | 상태: 실행 가능한 실험용 3D 교육 게임 / **임상 훈련용 검증 없음**

## 실행: Windows PowerShell, Python 3.12+

```powershell
git clone https://github.com/HyunStudio/Cataract_surgery.git
cd Cataract_surgery
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-3d.txt
python -m pytest -q
python -m ophthosim.gl_preview --check
python -m ophthosim.gl_surgery --case normal --seed 7
```

마지막 명령은 **새로운 ModernGL 기반 교육용 3D 수술 모드**를 시작합니다. GPU 드라이버가 OpenGL 3.3 Core Context를 제공하지 못하면 실행이 실패할 수 있습니다. `--check`는 CPU 메시 검사만 수행하며 GPU 검증이 아닙니다.

저사양 모드 또는 OpenGL 문제 발생 시 기존 `python main.py` 명령으로 **2.5D 게임**을 실행할 수 있습니다.

## 단계별 조작

| 단계 | 입력 | 합성 게임 목표 |
|---|---|---|
| PREOP | 1–4 시나리오 선택, Space | 가상 수술 전 확인 |
| ANESTHESIA | Space | 가상 마취팀/환자 준비 확인 |
| ENTRY | 표시된 3개 표식을 마우스 클릭 | 진입 과제 |
| CAPSULE | 동그란 가이드를 왼쪽 버튼으로 따라 이동 | 곡선 경로 과제 |
| PHACO | 수정체 내부에서 버튼 누르고 유지 | 혼탁도 감소 |
| CORTEX | 내부에서 버튼 누르고 유지 | 잔여물 감소 |
| IOL | **새로 클릭**하여 중심 맞춤 | 가상 렌즈 정렬 |
| CLOSE | 숫자 1, 2, 3 | 최종 확인 체크 |
| RECOVERY / ABORTED | S 저장, R 새 사례 | 가상 결과 및 JSONL 재생 데이터 |

공통 단축키: 화살표 = 카메라 회전, `+`/`-` = 확대·축소, `Q`/`E` = 가상 도구 깊이 조절, `A` = 환자 경고 확인, `X` = 안전 중단, `Esc` = 일시정지/재개, `R` = 재시작. 창 닫기 버튼으로 종료. 다음 수술 단계로 전환되면 안전한 기본 깊이값으로 초기화하며, 깊이가 잘못되면 조작은 무시됩니다.

기본 시나리오와 환자 움직임/바이탈/수정체낭 경보 등 네 개의 합성 케이스가 있습니다. 합병증을 강제로 무시하고 계속할 수 없도록 상태 엔진이 제약을 적용합니다.

## 아키텍처

`gl_surgery.py`의 OpenGL GUI → `input3d.py`의 마우스-광선/가상 깊이 입력 → 기존 `ReplayGame` 상태머신 → `AnatomyAppearance` 형태의 합성 외형 상태와 HUD → ModernGL 화면. 모든 단계 변경·점수·경보·수술 중단 판단은 **기존 게임 모델**이 실행합니다. GPU 렌더러는 모델을 직접 바꾸지 않습니다.

이 구현의 깊이 입력은 **정규화된 수술 과제 평면과 가상 깊이 범위**를 사용합니다. 메시별 3차원 접촉, 압력, 동적 절개·봉합, 생체역학, 포도막/수정체낭의 실제 복잡한 물리학을 구현한 것이 아닙니다. 조직 렌더링은 교육용 시각적 추상화입니다.

## 자동 검증 결과

- [Python 3.12/3.13 단위·통합·더티 테스트](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38334178228): **Python 3.12에서 245개 통과**, Python 3.13 작업도 성공.
- [Mesa llvmpipe OpenGL 실수행](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38334142433): 정상 수술 전 과정, 환자 움직임/안전 중단, 백내장 감소 전후 외형, IOL 장면, 최종 결과 등을 렌더링하고 **서로 다른 8개 프레임**을 저장. 재생 로그 무결성 검사 통과.
- [검증 화면 캡처 ZIP](https://github.com/HyunStudio/Cataract_surgery/actions/runs/38334142433/artifacts/11783937737).
- 실행 환경은 **Linux Xvfb + Mesa 소프트웨어 OpenGL**. GPU 드라이버·Windows 4K·실사용 입력/초당 프레임 속도 및 장시간 메모리 테스트는 아직 미완료.
- 보안 및 비정상 입력 검사: 범위 밖 좌표, NaN/Inf/초대형 정수, 임의 시나리오, 잘못된 깊이, 연속 입력으로 IOL을 자동 배치하려는 경우, 일시정지·경보 상태의 조작 무시, 시드 기반 재현성을 확인합니다.

## 앞으로 완성해야 할 주요 기능

1. 실제 Windows 그래픽 카드에서 GL 컨텍스트, 렌더 결과, 1080p/4K 조작 성능 측정.
2. 실제 3D 메시 기반 도구 충돌, 전낭/수정체/각막 변형, 도구 시각화 및 상태 피드백 고도화.
3. IOL 접힘→전개 애니메이션과 수술 마무리 상태를 더 풍부하게 표현.
4. 시각 접근성과 화면 확대/고대비 모드의 GUI 적용 및 실제 기기 검수.
5. 의료 전문가 검토와 별도의 연구 평가 절차. 점수를 환자 결과나 술기 능력으로 해석해서는 안 됨.

실존 환자 치료, 실제 마취 투여, 실수술 단계별 술기 지침, 의학적 경고 임계값 제공을 목적으로 하지 않습니다.

## 프레임 타임 측정 (2026-10-24)

GPU 검증 체크리스트의 GL08 항목(1920×1080 평균/P95 프레임 시간)을 실제 Windows PC에서 재현 가능하게 측정하는 스크립트가 추가되었습니다.

```powershell
python -m ophthosim.gl_benchmark --seconds 60 --size 1920x1080
python -m ophthosim.gl_benchmark --seconds 60 --fullscreen
```

- ENTRY 단계에서 카메라가 정해진 경로로 회전하고 가상 도구가 고정 경로로 호버합니다. 매 프레임 최근접 삼각형 계산 1회, 접촉 링, 도구, HUD 텍스처 업로드, 화면 전환이 모두 실행됩니다.
- 호버는 `Game.action`을 호출하지 않으며, 게임 스냅샷/재생 로그가 바뀌면 실패로 종료합니다.
- 결과는 `build/benchmark/gl-frametime.json`에 저장됩니다: `frame`/`probe`/`render` 구간별 평균·P50·P95·P99·최대(ms), OS·Python·pygame·moderngl 버전, `GL_RENDERER`/`GL_VENDOR`/`GL_VERSION`.
- `gl08.status`: 소프트웨어 렌더러, 1920×1080 미만 창, 60초 미만 측정은 항상 `INSUFFICIENT_EVIDENCE`. 하드웨어 조건을 충족해도 `CANDIDATE_WITHIN_60FPS` / `CANDIDATE_BELOW_60FPS`까지만 표시되며, 최종 판정은 사람이 체크리스트에 기록해야 합니다.
- 측정값은 CPU 벽시계 기준(버퍼 스왑 포함)이며 GPU 실행 시간이 아닙니다. 수직동기화는 제어하지 않으므로 60Hz 모니터에서는 약 16.7ms 근처로 제한될 수 있습니다. 모니터 주사율도 함께 기록하세요.
- 3D 수술 화면에서 **F3** 키를 누르면 최근 프레임 평균/P95(게임 루프 60fps 제한 포함)를 HUD에 표시합니다. 표시 전용이며 점수·단계·재생 로그에 영향이 없습니다.
