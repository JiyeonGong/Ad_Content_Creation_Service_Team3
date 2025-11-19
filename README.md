# 🏥 Ad_Content_Creation_Service_Team3

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?logo=streamlit)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)

## 🚀 헬스케어 소상공인을 위한 AI 콘텐츠 제작 서비스

이 프로젝트는 **FastAPI** 백엔드와 **Streamlit** 프론트엔드를 결합하여, 헬스케어 분야(병원, 약국, 헬스장 등) 소상공인을 위한 인스타그램 홍보 콘텐츠(문구, 해시태그, 이미지)를 AI로 쉽고 빠르게 생성하는 서비스입니다.

---

### 🌟 주요 기능

| 기능 | 사용 모델/기술 | 설명 |
| :--- | :--- | :--- |
| **📝 홍보 문구 & 해시태그** | `GPT-5-Mini` (OpenAI) | 업체 정보(이름, 특징, 톤)를 입력하면 인스타그램에 최적화된 감성적인 문구와 해시태그를 생성합니다. |
| **🖼 문구 기반 이미지 (T2I)** | `SDXL-Base-1.0` (Diffusers) | 생성된 문구의 맥락을 이해하여 홍보용 이미지를 자동으로 생성합니다. |
| **🎨 이미지 편집/합성 (I2I)** | `SDXL-Base-1.0` (Diffusers) | 기존 사진을 업로드하고 지시사항을 입력하면 새로운 스타일로 이미지를 변환합니다. |

---

### 🏛️ 시스템 아키텍처

이 서비스는 **Client-Server 구조**로 분리되어 있으며, 무거운 AI 연산은 백엔드 서버가 전담합니다.

| 영역 | 기술 스택 | 역할 |
| :--- | :--- | :--- |
| **Backend** | **FastAPI**, `Diffusers`, `Pydantic` | AI 모델(SDXL) 로드 및 추론, REST API 제공 (`src/backend`) |
| **Frontend** | **Streamlit**, `Requests` | 사용자 UI 제공 및 백엔드 API 호출 (`src/frontend`) |
| **Infra** | **Docker**, **uv** | 컨테이너 기반 배포 및 고속 패키지 관리 |

---

### 📂 프로젝트 구조

```text
Ad_Content_Creation_Service_Team3
├── src
│   ├── backend          # 🧠 AI 서버 (FastAPI)
│   │   ├── core         # 설정 및 초기화
│   │   ├── routers      # API 엔드포인트 (t2i, i2i, caption)
│   │   ├── services     # AI 모델 로직 (Pipeline, OpenAI)
│   │   └── main.py      # 백엔드 실행 파일
│   └── frontend         # 💻 사용자 앱 (Streamlit)
│       ├── pages        # 화면 구성 (Tab)
│       ├── services     # API 통신 모듈
│       └── app.py       # 프론트엔드 실행 파일
├── docker-compose.yaml  # Docker 실행 설정
├── pyproject.toml       # 프로젝트 설정 및 의존성
├── uv.lock              # 패키지 잠금 파일
└── requirements.txt     # pip 호환용 리스트
⚙️ 실행 방법 (Local)
이 프로젝트는 Python 3.10 이상을 필요로 하며, 패키지 관리자로 uv 사용을 권장합니다.

1. 환경 설정
A. 저장소 복제 및 이동

Bash

git clone -b localbjs [https://github.com/JiyeonGong/Ad_Content_Creation_Service_Team3.git](https://github.com/JiyeonGong/Ad_Content_Creation_Service_Team3.git)
cd Ad_Content_Creation_Service_Team3
B. 패키지 설치

Bash

# uv 사용 시 (추천)
uv sync

# pip 사용 시
pip install -r requirements.txt
C. API 키 설정 프로젝트 루트에 .env 파일을 생성하고 OpenAI 키를 입력하세요.

Ini, TOML

OPENAI_API_KEY="sk-your-openai-api-key-here"
2. 서버 실행
두 개의 터미널을 열어 백엔드와 프론트엔드를 각각 실행해주세요. (모두 프로젝트 루트 경로에서 실행)

터미널 1: 백엔드 (Backend)

Bash

# uv 사용 시
uv run uvicorn src.backend.main:app --reload

# pip 사용 시
uvicorn src.backend.main:app --reload
터미널에 Application startup complete 메시지가 뜨면 준비 완료입니다.

터미널 2: 프론트엔드 (Frontend)

Bash

# uv 사용 시
uv run streamlit run src/frontend/app.py

# pip 사용 시
streamlit run src/frontend/app.py
브라우저가 자동으로 열리며 http://localhost:8501로 접속됩니다.

🐳 Docker로 실행 (간편 실행)
로컬 세팅 없이 Docker로 한 번에 실행할 수 있습니다.

Bash

docker-compose up --build
설치가 완료되면 브라우저에서 http://localhost:8501 로 접속하세요.

💡 문제 해결 (Troubleshooting)
CUDA/GPU 오류: torch.cuda.is_available()이 False인 경우, 본인의 CUDA 버전에 맞는 PyTorch를 재설치해야 합니다. (CPU 모드로 실행 시 속도가 느릴 수 있습니다.)

Backend 연결 실패: 프론트엔드에서 API 오류가 발생하면 http://localhost:8000/docs 에 접속하여 백엔드 서버가 정상 작동 중인지 확인하세요.