# CARLA 환경 세팅

## 0. CARLA?

Unreal Engine을 기반으로 도로와 유사한 가상 환경을 제공하는 시뮬레이터입니다.
자동차, 보행자, 교통 신호, 날씨, sensor를 설정하고 Python 주행 로직을 테스트할 수 있습니다.
이 저장소는 팀의 환경만 통일합니다. 주행 로직과 데이터 수집은 팀원이 직접 구현합니다.

## 1. CARLA Server 다운로드 및 실행

1. [공식 CARLA 0.9.16 release](https://github.com/carla-simulator/carla/releases/tag/0.9.16)에서 Windows 패키지를 다운로드합니다.
   [공식 Quickstart](https://carla.readthedocs.io/en/0.9.16/start_quickstart/)도 참고합니다.
2. 압축을 예를 들어 `C:\CARLA_0.9.16`에 해제합니다. CARLA 본체는 Git 저장소 밖에 둡니다.
3. 해당 폴더의 `CarlaUE4.exe`를 실행하거나 PowerShell에서 아래 명령을 실행합니다.

```powershell
cd C:\CARLA_0.9.16
.\CarlaUE4.exe
```

4. 시뮬레이터 창에 도시가 표시되는지 확인합니다.

설치 경로는 예시이므로 본인의 실제 경로를 사용합니다. 서버는 PC당 하나만 실행합니다.
서버를 실행한 상태에서 별도의 PowerShell을 열어 아래 repository 작업을 진행합니다.

## 2. 공통 저장소 clone 및 Python 환경

사전 준비: Git, **Python 3.11 x64**와 Python Launcher.
CARLA의 다른 Python 버전 지원 여부와 별개로 이 팀은 3.11을 기준으로 통일합니다.
아래 `YOUR_ORG`와 repository 이름은 팀장이 공유한 실제 GitHub 주소로 바꿉니다.

원하는 개발 경로에서 실행합니다.

```powershell
git clone https://github.com/YOUR_ORG/robo404-dataops.git
cd robo404-dataops
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.check_environment
```

`git clone`이 프로젝트 폴더와 공통 파일을 내려받습니다.
프로젝트 디렉터리, YAML, 검증 파일을 각자 새로 만들지 않습니다.
CARLA 본체와 `.venv`는 각 PC에 따로 존재합니다.
이미 `.venv`가 있다면 Python 버전을 확인하고 다른 용도의 환경에는 덮어쓰지 않습니다.

설치가 안 되면 Python 64비트 여부와 버전, pip 오류를 확인합니다.
CARLA server와 Python API는 모두 **0.9.16**이어야 합니다.
현재 의존성은 `carla==0.9.16`, `PyYAML==6.0.3`이며, 개별 pip 명령으로 버전을 바꾸지 않습니다.

## 3. 연결 검증

CARLA server가 실행 중인 상태에서 저장소 root에서 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m scripts.check_connection
```

`client_version`, `server_version`이 모두 `0.9.16`이고 `Connection OK`와 현재 map이 출력되면 성공입니다.
이 단계는 map이나 settings를 바꾸지 않습니다. 현재 map이 Town03이 아니어도 연결은 정상일 수 있습니다.
`connect_test.py`를 따로 만들 필요가 없습니다.

## 4. 팀 공통 환경 설정

설정은 저장소의 실제 파일을 기준으로 합니다. 안내 페이지에 별도 YAML 복사본을 만들어 관리하지 않습니다.

| 파일 | 통일하는 항목 |
|---|---|
| `config/simulation.yaml` | host/port, map, sync, timestep, seed, weather, ego blueprint·spawn index |
| `config/sensors.yaml` | RGB 해상도, FOV, capture 주기, 부착 위치·회전 |
| `requirements.txt` | Python dependency 버전 |

현재 공통값은 Town03, ClearNoon, synchronous mode, dt=0.05초, seed=42,
Tesla Model 3와 spawn index=0, RGB 800×600과 sensor tick=0.05초입니다.
CARLA server의 설치 경로는 통일할 필요가 없습니다.

월드 검증은 다른 실습 프로그램을 종료한 후 실행합니다.
**Town03을 다시 로드하면서 기존 actor가 제거되므로 개인 로컬 서버에서만 실행합니다.**

```powershell
.\.venv\Scripts\python.exe -m scripts.check_world --apply
```

이 스크립트는 공통 map/weather/timestep/seed를 적용하고 10 ticks를 진행합니다.
ego blueprint와 spawn index가 유효한지 확인하지만 **차량이나 camera를 생성하지 않습니다**.
주행 제어와 데이터 수집·저장도 수행하지 않습니다.

`World check OK`가 출력되면 월드 설정 검증 성공입니다.
검증 종료 시 로드한 map에서 변경 전의 settings와 weather를 복원하므로 서버를 synchronous 상태로 남겨 두지 않습니다.
Town03은 남지만 이전 map과 actor는 복원하지 않습니다.
실제 주행 프로그램은 공유 설정을 다시 읽고 적용해야 합니다.
`setup_test.py`를 각자 새로 작성할 필요는 없습니다.

CARLA 없이 가능한 오프라인 테스트:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 5. 팀원이 직접 구현할 것

환경 검증 이후 다음 기능은 팀원이 직접 설계하고 작성합니다.

1. 공통 YAML을 읽고 설정을 적용하는 자신의 simulation 실행 코드.
2. ego vehicle spawn과 주행 agent/controller.
3. camera 생성·부착, callback, frame ID와 timestamp 처리.
4. 위치·속도·control·이벤트 수집과 파일 저장.
5. actor 정리와 오류 처리, 반복 실험과 결과 비교.

설정 로딩만 재사용하고 싶다면 `scripts.settings.load_settings()`를 사용할 수 있습니다.
주행 control과 storage backend를 구현한 예제는 이 초기 저장소에 포함하지 않습니다.

구현 시 맞춰야 하는 규칙:

- 서버 하나에 synchronous tick owner는 하나만 둡니다.
- 제어와 데이터 수집은 서로 다른 책임으로 설계합니다.
- 센서는 simulation frame ID와 timestamp로 연결하고 누락을 명시합니다.
- 프로그램 종료 시 자신이 생성한 actor를 정리하고 변경한 settings를 복원합니다.
- seed는 사용하는 Python/라이브러리 RNG마다 적용합니다. Traffic Manager를 사용하면 해당 seed도 설정합니다.
- 실제 차량·sensor 생성과 자신의 RNG seed 적용은 각자의 구현이 책임집니다.

실험 metadata의 `run_id`, `scenario_id`, `agent_version`, `git_commit`, CARLA 버전, seed,
전체 설정 기록은 앞으로 구현할 요구사항입니다. 이 저장소가 자동 수집하는 기능은 아닙니다.

## 6. 5인 팀의 코드 공유 규칙

- GitHub에는 공통 설정, 환경 검증 코드, dependency 버전, 문서를 공유합니다.
- `.venv/`, CARLA 본체·ZIP, `data/`, `outputs/`, 개인 경로와 인증정보는 올리지 않습니다.
- 각자 작성하는 주행·수집 코드는 개인 브랜치에서 개발하고 팀 검토 후 공유합니다.
- 기본 server는 각자의 `localhost:2000`입니다. 공용 CARLA server에 접속하는 구조가 아닙니다.
- 실행 데이터의 공용 Data Platform 업로드는 이후 단계입니다.
- 같은 설정을 사용하더라도 hardware/driver 차이로 완전 결정성이 보장되지는 않습니다.

## 7. 실행 오류가 발생하면

Fatal error가 반복되면 실행을 멈추고 실행 명령, PowerShell 출력, Fatal error 상세 문구,
OS/GPU/VRAM/Python/client·server 버전을 공유합니다.
한 팀원 PC에서 재시작 시 `listen ... 10014`가 관찰됐으며 원인은 아직 미해결입니다.
전체 팀의 공통 오류로 단정하지 않습니다.

shader compilation 오류가 발생한 PC에서는 아래 옵션으로 실행한 성공 사례가 있습니다.
모든 Fatal error의 해결책은 아닙니다.

```powershell
cd C:\CARLA_0.9.16
.\CarlaUE4.exe -dx12 -quality-level=Epic
```

선택적으로 CARLA가 **완전히 종료된 상태**에서만 port 검사를 할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m scripts.check_environment --check-ports
```

이 검사는 socket bind/listen만 확인하며 CARLA 시작 성공을 보장하지 않습니다.
