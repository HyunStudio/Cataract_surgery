# Windows 실행본

이 실행본은 Python 교육용 시뮬레이션 판입니다. 별도로 개발 중인 Godot의
조직 역학 검증판이나 임상 훈련 인증 제품을 뜻하지 않습니다.

## 실행

`OphthoSim` 폴더 전체를 복사하고 `OphthoSim.exe`를 실행합니다.
Python을 별도로 설치할 필요가 없도록 패키징합니다. 실행 파일 옆의
`_internal` 폴더도 필요합니다. 기본은 한국어 3D 화면입니다.

- 2D: `OphthoSim.exe --mode 2d`
- 영어: `OphthoSim.exe --lang en`
- 기본 자동 저장 복원: `OphthoSim.exe --resume`
- 지정 파일 복원: `OphthoSim.exe --resume "D:\cases\case.replay.jsonl"`

저장과 결과 내보내기는 `%LOCALAPPDATA%\OphthoSim` 안에 기록됩니다.
실행 위치에 쓰기 권한이 없어도 저장할 수 있습니다. 상대 경로로 지정한
복원 파일은 실행 명령을 내린 원래 폴더를 기준으로 찾습니다.

현재 조작은 현미경 조작 화면에서만 가능합니다. C로 전환하는 수술실과
접안 카메라는 관찰용입니다. F3은 성능 진단을 표시합니다. 이 제한은
접안 시야의 입력 광선과 실제 렌더링 좌표가 일치하도록 개선할 때까지
유지합니다.

## 재빌드

저장소 루트에서 Windows Python3.12를 사용합니다.

```powershell
python -m venv .venv-build
.venv-build/Scripts/python.exe -m pip install -r requirements-build.txt
.venv-build/Scripts/python.exe -m PyInstaller --noconfirm --workpath build/qualified --distpath dist/qualified OphthoSim.spec
```

결과는 `dist/qualified/OphthoSim`입니다. `.spec`은 필수 의존성이 없으면
빌드를 중단합니다. 패키징 성공만으로 실제 화면이 검증된 것은 아닙니다.

## 검증 범위

OpenGL 드라이버가 필요합니다. 한글은 Windows의 맑은 고딕 등 시스템
글꼴을 사용하며 글꼴 파일을 재배포하지 않습니다. 다른 PC와 AMD GPU,
Python 미설치 PC의 실제 실행은 별도 확인 대상입니다. 현재 검수의 기존
NVIDIA 결과를 새 실행 파일의 검증 결과로 대신하지 않습니다.
