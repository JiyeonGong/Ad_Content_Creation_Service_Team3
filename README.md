# 💪 소상공인 AI 콘텐츠 제작 서비스

> ComfyUI 기반 고품질 인스타그램 홍보 콘텐츠 자동 생성 플랫폼

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io/)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-Latest-orange.svg)](https://github.com/comfyanonymous/ComfyUI)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**최근 업데이트:**
- 🎯 프로젝트 리브랜딩: 헬스케어 → 전체 소상공인 대상으로 확장 (2025-12-03) NEW!
- 🔧 Qwen-Image-Edit 워크플로우 수정 (UNETLoader 사용) (2025-12-03) NEW!
- 📝 페이지1: 서비스 종류 직접 입력 방식으로 변경 (2025-12-03)
- ✅ Phase 1 & Phase 2 구조 개선 완료 (2025-12-01)
- 🔤 3D 캘리그라피 생성 기능 추가 (2025-12-02)
- 🚀 GPT API 비용 66% 절감, 처리 속도 50% 향상
- 🎨 ComfyUI 통합으로 전문가급 이미지 편집 지원
- 🔧 코드 복잡도 95% 감소 (리팩토링 완료)

---

## 📋 목차

- [주요 기능](#-주요-기능)
- [시스템 아키텍처](#-시스템-아키텍처)
- [기술 스택](#-기술-스택)
- [설치 방법](#-설치-방법)
- [설정 가이드](#-설정-가이드)
- [실행 방법](#-실행-방법)
- [사용 방법](#-사용-방법)
- [모델 관리](#-모델-관리)
- [API 문서](#-api-문서)
- [문제 해결](#-문제-해결)
- [개발 가이드](#-개발-가이드)
- [라이선스](#-라이선스)

---

## ✨ 주요 기능

### 🎯 4가지 핵심 워크플로우

#### 1. 📝 AI 홍보 문구 & 해시태그 생성
- **GPT-5 Mini** 기반 전문적인 마케팅 문구 자동 생성
- 서비스 정보 입력 → AI가 3가지 버전의 매력적인 문구 생성
- Instagram 최적화 해시태그 15개 자동 추천
- 4가지 톤 선택 (친근함, 전문적, 트렌디, 감성적)
- **통합 프롬프트 엔진**: 비용 66% 절감, 속도 50% 향상

#### 2. 🖼 Text-to-Image (T2I) 이미지 생성
- **FLUX** 또는 **SDXL** 모델 기반 고품질 이미지 생성
- ComfyUI 워크플로우를 통한 전문가급 결과물
- 3가지 후처리 옵션:
  - **없음**: 빠른 생성 (4-8초)
  - **Impact Pack**: YOLO + SAM 기반 얼굴/손 자동 보정
  - **기존 ADetailer**: 레거시 후처리
- Instagram 최적화 해상도 지원 (4:5, 1:1, 16:9)
- GPU 메모리 효율적 관리

#### 3. ✏️ Image-to-Image (I2I) 이미지 편집
- 기존 이미지를 AI로 스타일 변환 및 재편집
- 변화 강도 조절 (0.0 ~ 1.0)
- 페이지1 문구 기반 보조 프롬프트 자동 생성
- 3가지 보조 프롬프트 방식:
  - 단순 키워드 변환
  - GPT 기반 자연스러운 확장
  - 사용자 조절형 혼합
- 원본 vs 편집본 비교 뷰

#### 4. 🎨 고급 이미지 편집 (페이지4 - 4가지 모드)

**배경 제거 + 정밀 편집** - BEN2 자동 마스킹 + 다양한 편집 모드

##### 모드 1: 👤 인물 모드 (Portrait Mode)
- **기능**: 얼굴 보존, 의상/배경 변경
- **파이프라인**: Face Detector → 마스크 반전 → ControlNet(Depth/Canny) → FLUX I2I
- **사용 예**: 모델 의상 교체, 촬영 배경 변경

##### 모드 2: 📦 제품 모드 (Product Mode)
- **기능**: 제품 보존, 배경 창의적 변경
- **파이프라인**: BEN2 자동 마스킹 → 마스크 반전 → FLUX I2I
- **사용 예**: 상품 촬영 배경 교체

##### 모드 3: 🎭 하이브리드 모드 (Hybrid Mode)
- **기능**: 인물 + 제품 동시 보존, 나머지 변경
- **파이프라인**: Face Detector + Product Segmentation → ControlNet → FLUX I2I
- **사용 예**: 모델이 제품 들고 있는 이미지 배경 변경

##### 모드 4: 🖼️ FLUX Fill 모드
- **기능**: BEN2 자동 인페인팅
- **모델**: FLUX.1-Fill-dev-Q8_0 (18GB)
- **파이프라인**: BEN2 마스크 → FLUX Fill → 자연스러운 배경 생성
- **사용 예**: 배경 완전 제거 후 새 배경 자동 생성

~~##### 모드 5: 🎯 정밀 편집 모드 (Qwen-Image-Edit)~~
~~- **기능**: 자연어 기반 정밀 이미지 편집~~
~~- **모델**: Qwen-Image-Edit-2509-Q8_0 (21GB)~~
~~- **상태**: ❌ **현재 비활성화** (ComfyUI 모델 인식 실패)~~
~~- **사유**: GGUF 형식 Qwen 모델을 UNETLoader가 인식하지 못함~~

**공통 기능**:
- ControlNet 통합 (Depth, Canny, Pose 등 7가지 타입)
- 실시간 프리뷰 및 비교
- ComfyUI 워크플로우 기반 전문가급 편집

#### 5. 🔤 3D 캘리그라피 생성 (페이지5)
- **AI 배경 제거 (rembg)** 기반 입체적인 텍스트 이미지 생성
- 배경 투명 PNG 출력 → 다른 이미지 위에 합성 가능
- 주요 기능:
  - 한글/영문 지원
  - 커스텀 폰트 경로 지정
  - 자동 후처리 (Threshold → Erosion → Gaussian Blur)
- 사용 예시: 광고 문구, 이벤트 제목, 강조 텍스트

---

## 🏗 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                 사용자 (웹 브라우저)                       │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────┐
│          Streamlit 프론트엔드 (Port 8501)                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 📁 컴포넌트 기반 구조 (Phase 2 개선)            │   │
│  │  ├─ app.py (메인 앱)                            │   │
│  │  ├─ model_selector.py (모델 선택 UI)           │   │
│  │  ├─ utils.py (PromptHelper)                     │   │
│  │  └─ frontend_config.yaml (설정)                │   │
│  │                                                  │   │
│  │ 🎨 4개 페이지                                    │   │
│  │  ├─ 📝 문구+해시태그 생성                       │   │
│  │  ├─ 🖼 T2I 이미지 생성                          │   │
│  │  ├─ ✏️ I2I 이미지 편집                          │   │
│  │  └─ 🎨 고급 편집 실험 (3가지 모드)             │   │
│  └─────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │ REST API (HTTP)
┌────────────────────────▼────────────────────────────────┐
│           FastAPI 백엔드 (Port 8000)                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 📡 API Gateway (main.py)                        │   │
│  │  ├─ POST /api/caption (문구 생성)              │   │
│  │  ├─ POST /api/generate_t2i (T2I)               │   │
│  │  ├─ POST /api/generate_i2i (I2I)               │   │
│  │  ├─ POST /api/edit_with_comfyui (고급 편집)   │   │
│  │  ├─ GET  /status (서버 상태)                   │   │
│  │  ├─ GET  /models (모델 목록)                   │   │
│  │  └─ GET  /api/comfyui/status                   │   │
│  └───────────────────┬─────────────────────────────┘   │
│                      │                                   │
│  ┌───────────────────▼─────────────────────────────┐   │
│  │ 🧠 Service Layer (Phase 1 & 2 개선)            │   │
│  │  ├─ services.py (비즈니스 로직)                │   │
│  │  ├─ exceptions.py (통일된 에러 처리)           │   │
│  │  ├─ model_registry.py (모델 관리)              │   │
│  │  └─ model_loader.py (모델 로딩)                │   │
│  │                                                  │   │
│  │ ✨ Phase 1 개선사항:                             │   │
│  │  • build_final_prompt_v2() - GPT 호출 3→1회   │   │
│  │  • 프롬프트 처리 백엔드 중앙화                  │   │
│  │  • 비용 66% 절감, 속도 50% 향상                │   │
│  └───────────────────┬─────────────────────────────┘   │
│                      │                                   │
│  ┌───────────────────▼─────────────────────────────┐   │
│  │ 🔧 ComfyUI Integration Layer                    │   │
│  │  ├─ comfyui_client.py (API 클라이언트)         │   │
│  │  ├─ comfyui_workflows.py (워크플로우 템플릿)   │   │
│  │  ├─ workflow_config.py (편집 설정)             │   │
│  │  └─ image_editing_config.yaml                  │   │
│  └─────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP API
┌────────────────────────▼────────────────────────────────┐
│           ComfyUI 워커 (Port 8188)                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 🎨 통합 모델 관리                                │   │
│  │  ├─ FLUX.1-dev-Q8 / Q4 (GGUF)                  │   │
│  │  ├─ BEN2 (배경 편집)                            │   │
│  │  ├─ FLUX.1-Fill (인페인팅)                     │   │
│  │  ├─ Qwen-Image-Edit (하이브리드)               │   │
│  │  ├─ InstantX ControlNet Union                  │   │
│  │  └─ RMBG v1.4 (배경 제거)                      │   │
│  │                                                  │   │
│  │ 🔨 Custom Nodes                                 │   │
│  │  ├─ ComfyUI-Impact-Pack (얼굴/손 보정)        │   │
│  │  ├─ ComfyUI-GGUF                                │   │
│  │  ├─ ComfyUI-BEN2                                │   │
│  │  └─ comfyui_controlnet_aux                     │   │
│  │                                                  │   │
│  │ 💾 메모리 효율: 유휴 시 ~500MB                  │   │
│  └─────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
│ OpenAI API   │ │   Models    │ │   GPU/CPU   │
│ (GPT-5 Mini) │ │ FLUX, BEN2  │ │  (PyTorch)  │
│ 프롬프트 최적화│ │ FLUX.1-Fill │ │             │
│ 66% 비용절감 │ │ Qwen-Image  │ │             │
└──────────────┘ └─────────────┘ └─────────────┘
```

### 🔄 Phase 1 & 2 아키텍처 개선 하이라이트

**Phase 1: 프롬프트 엔진 최적화**
- ✅ GPT API 호출 3회 → 1회 (비용 66% ↓, 속도 50% ↑)
- ✅ 프롬프트 처리 백엔드 중앙화
- ✅ PromptHelper 유틸리티 클래스로 중복 코드 제거

**Phase 2: 구조 개선**
- ✅ Custom Exception 체계 (6가지 예외 타입)
- ✅ ModelSelector 컴포넌트 분리 (100+ 줄 → 6줄)
- ✅ 통일된 에러 처리 (type 필드로 구분 가능)

> **중요:** ComfyUI가 백그라운드 워커로 필수입니다. 자세한 내용은 [ComfyUI 통합 가이드](./docs/COMFYUI_INTEGRATION.md)를 참조하세요.

---

## 🛠 기술 스택

### 프론트엔드
- **Streamlit 1.30+**: 웹 UI 프레임워크
- **Python 3.9+**: 언어
- **PyYAML**: 설정 파일 관리
- **컴포넌트 기반 구조** (Phase 2):
  - `model_selector.py`: 모델 선택 UI (100+ 줄 → 6줄)
  - `utils.py`: PromptHelper 유틸리티

### 백엔드
- **FastAPI 0.109+**: REST API 프레임워크
- **Uvicorn**: ASGI 서버
- **Pydantic**: 데이터 검증
- **Custom Exceptions** (Phase 2):
  - 6가지 타입별 에러 처리
  - 명확한 HTTP 상태 코드 반환

### ComfyUI 통합
- **ComfyUI**: 백그라운드 워커 (Port 8188)
- **Custom Nodes**:
  - ComfyUI-Impact-Pack (YOLO+SAM)
  - ComfyUI-GGUF (GGUF 모델 지원)
  - ComfyUI-BEN2 (배경 편집)
  - comfyui_controlnet_aux (ControlNet)

### AI 모델
- **OpenAI GPT-5 Mini**: 문구 생성 + 프롬프트 최적화
  - Phase 1 개선: 3회 호출 → 1회 (66% 비용 절감)
- **이미지 생성 모델**:
  - FLUX.1-dev-Q8 / Q4 (GGUF 양자화)
  - BEN2 (배경 편집 특화)
  - FLUX.1-Fill (인페인팅)
  - Qwen-Image-Edit-2509 (하이브리드 편집)
- **ControlNet**:
  - InstantX ControlNet Union (7-in-1)
  - Depth, Canny, Pose 등

### AI 라이브러리
- **PyTorch 2.1+**: 딥러닝 프레임워크
- **Diffusers**: Hugging Face 모델 (레거시 지원)
- **Transformers**: NLP 모델
- **Accelerate**: 모델 최적화
- **rembg**: AI 배경 제거 (u2net 모델)
- **OpenCV**: 이미지 후처리

### 기타
- **Pillow**: 이미지 처리
- **python-dotenv**: 환경변수 관리
- **Requests**: HTTP 클라이언트
- **YAML**: 설정 파일 파서

---

## 📦 설치 방법

### 1. 시스템 요구사항

#### 최소 사양
- **OS**: Windows 10+, macOS 11+, Ubuntu 20.04+
- **Python**: 3.9 이상
- **RAM**: 16GB (CPU 모드)
- **Storage**: 20GB (모델 캐시)

#### 권장 사양
- **GPU**: NVIDIA GPU (VRAM 12GB+)
  - RTX 3060 12GB 이상
  - RTX 4070, 4080, 4090
- **RAM**: 32GB
- **Storage**: 50GB SSD

### 2. 저장소 클론

```bash
git clone https://github.com/JiyeonGong/Ad_Content_Creation_Service_Team3
cd Ad_Content_Creation_Service_Team3
```

### 3. 가상환경 생성 (권장)

```bash
# Python venv
python -m venv .venv

# 활성화
# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate
```

### 4. 의존성 설치

```bash
pip install -r requirements.txt
```

**requirements.txt 내용:**
```txt
# FastAPI 백엔드
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart

# Streamlit 프론트엔드
streamlit>=1.30.0

# AI 모델
torch>=2.1.0
diffusers>=0.25.0
transformers>=4.36.0
accelerate>=0.25.0

# OpenAI
openai>=1.10.0

# 이미지 처리
Pillow>=10.2.0

# 설정 파일
pyyaml>=6.0
python-dotenv>=1.0.0

# 유틸리티
requests>=2.31.0
```

---

## ⚙️ 설정 가이드

### 1. 환경변수 설정 (.env)

#### 📄 .env 파일 생성

```bash
cp env.example .env
```

#### ✏️ .env 파일 편집

**최소 필수 설정:**
```bash
# OpenAI API Key (필수!)
OPENAI_API_KEY=sk-proj-your-actual-key-here

# 기본 모델 선택 (선택, 기본값: sdxl)
PRIMARY_MODEL=sdxl

# 폴백 활성화 (권장)
ENABLE_FALLBACK=true
```

**고급 설정 (선택):**
```bash
# Hugging Face 인증 (FLUX 사용 시)
HF_TOKEN=hf_your_token_here

# API 서버
API_BASE_URL=http://localhost:8000
API_TIMEOUT=180

# 메모리 최적화 (GPU < 12GB 시)
USE_8BIT=true
ENABLE_ATTENTION_SLICING=true
ENABLE_VAE_SLICING=true

# 프롬프트 최적화
TRANSLATE_KOREAN=true
PROMPT_OPTIMIZATION_ENABLED=true
```

#### 🔐 보안 주의사항

```bash
# .gitignore에 추가 (필수!)
echo ".env" >> .gitignore

# ❌ Git에 커밋하지 마세요!
```

### 2. 백엔드 모델 설정 (model_config.yaml)

**위치:** `src/backend/model_config.yaml`

```yaml
# 사용 가능한 모델 정의
models:
  flux-schnell:
    id: "black-forest-labs/FLUX.1-schnell"
    type: "flux"
    requires_auth: true
    params:
      default_steps: 4
      max_steps: 8
      use_negative_prompt: false
      guidance_scale: null
      supports_i2i: true
      max_tokens: 512

  sdxl:
    id: "stabilityai/stable-diffusion-xl-base-1.0"
    type: "sdxl"
    requires_auth: false
    params:
      default_steps: 30
      max_steps: 50
      use_negative_prompt: true
      guidance_scale: 7.5
      supports_i2i: true
      max_tokens: 77

# 실행 설정
runtime:
  primary_model: "sdxl"  # 기본 모델
  fallback_models:               # 폴백 체인
    - "flux-schnell"
    - "playground"
  enable_fallback: true
  
  # 프롬프트 최적화
  prompt_optimization:
    enabled: true
    translate_korean: true
  
  # 메모리 최적화
  memory:
    enable_cpu_offload: false
    enable_attention_slicing: true
    enable_vae_slicing: true
    use_8bit: false
```

### 3. 프론트엔드 설정 (frontend_config.yaml)

**위치:** `src/frontend/frontend_config.yaml`

```yaml
app:
  title: "💪 소상공인 AI 콘텐츠 제작"
  layout: "wide"

api:
  base_url: "http://localhost:8000"
  timeout: 180
  retry_attempts: 2

# 페이지 정의
pages:
  - id: "caption"
    icon: "📝"
    title: "홍보 문구+해시태그 생성"
  - id: "t2i"
    icon: "🖼"
    title: "인스타그램 이미지 생성"
  - id: "i2i"
    icon: "🖼️"
    title: "이미지 편집/합성"

# 문구 생성 옵션
caption:
  service_types:
    - "헬스장"
    - "PT (개인 트레이닝)"
    - "요가/필라테스"
    - "건강 식품/보조제"
  tones:
    - "친근하고 동기부여"
    - "전문적이고 신뢰감"
    - "재미있고 트렌디"

# 이미지 크기 프리셋
image:
  preset_sizes:
    - name: "Instagram 세로 (4:5)"
      width: 1080
      height: 1350
    - name: "Instagram 정사각형 (1:1)"
      width: 1080
      height: 1080
```

---

## 🚀 실행 방법

### 🆕 ComfyUI 설치 및 실행 (필수)

v2.5부터 ComfyUI가 백그라운드 워커로 필요합니다.

#### 1. ComfyUI 설치
```bash
bash scripts/install_comfyui.sh
```

#### 2. 전체 서비스 시작 (권장)
```bash
bash scripts/start_all.sh
```

이 스크립트는 다음을 자동으로 실행합니다:
1. ComfyUI (포트 8188)
2. FastAPI (포트 8000)
3. Streamlit (포트 8501)

#### 3. 서비스 중단
```bash
bash scripts/stop_all.sh
```

#### 상세 가이드
- [ComfyUI 통합 가이드](./docs/COMFYUI_INTEGRATION.md) - 설치, 설정, 트러블슈팅
- [이미지 편집 가이드](./docs/IMAGE_EDITING_GUIDE.md) - BEN2, FLUX.1-Fill, Qwen-Image 사용법

---

### 방법 1: 개별 서비스 실행

#### 터미널 1: 백엔드 실행

```bash
# 프로젝트 루트에서
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000
```

**출력 예시:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
📦 모델 레지스트리 로드 완료: 6개 모델
🎯 Primary 모델 시도: sdxl
✅ sdxl 로딩 성공!
✅ FastAPI 시작 완료 - 모델 로드됨
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### 터미널 2: 프론트엔드 실행

```bash
# 새 터미널 열기
streamlit run src/frontend/app.py
```

**출력 예시:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.100:8501
```

#### 브라우저 접속

```
프론트엔드: http://localhost:8501
백엔드 API 문서: http://localhost:8000/docs
```

### 방법 2: 개발 모드 (자동 재시작)

```bash
# 백엔드 (코드 변경 시 자동 재시작)
uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000

# 프론트엔드 (자동 재시작 기본 활성화)
streamlit run src/frontend/app.py
```

**⚠️ 주의:** `--reload` 모드에서는 코드 변경 시 모델이 재로딩됩니다 (약 2분 소요).

### 방법 3: Docker 실행 (선택)

```bash
# Docker Compose
docker-compose up -d

# 접속
# 프론트엔드: http://localhost:8501
# 백엔드: http://localhost:8000
```

### 방법 4: 프로덕션 배포

```bash
# 백엔드 (Gunicorn + Uvicorn)
gunicorn src.backend.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

# 프론트엔드 (포트 지정)
streamlit run src/frontend/app.py \
  --server.port 8501 \
  --server.address 0.0.0.0
```

---

## 📖 사용 방법

### 1️⃣ 홍보 문구 생성

1. **페이지 1** 선택: "📝 홍보 문구+해시태그 생성"
2. **정보 입력**:
   - 서비스 종류: 헬스장
   - 지역: 부평
   - 서비스명: 30일 다이어트 챌린지
   - 핵심 특징: 전문 PT, 영양 관리 포함
   - 톤: 친근하고 동기부여
3. **생성 버튼** 클릭
4. **결과 확인**:
   - 3가지 문구 버전
   - 15개 해시태그
5. **문구 선택** (다음 페이지로 자동 연결)

### 2️⃣ 이미지 생성 (T2I)

1. **페이지 2** 선택: "🖼 인스타그램 이미지 생성"
2. **설정**:
   - 문구: 페이지1에서 자동 연결 (또는 직접 입력)
   - 이미지 크기: Instagram 세로 (1080x1350)
   - 추론 단계: 10 (빠름) ~ 30 (고품질)
3. **생성 버튼** 클릭
4. **결과**: 3가지 버전 이미지
5. **다운로드**: 각 버전별 다운로드 버튼

### 3️⃣ 이미지 편집 (I2I)

1. **페이지 3** 선택: "🖼️ 이미지 편집/합성"
2. **이미지 업로드** 또는 페이지2 이미지 선택
3. **설정**:
   - 편집 문구: 페이지1 문구 사용 또는 직접 입력
   - 변화 강도: 0.75 (추천)
   - 추가 지시: "더 밝고 활기찬 분위기로"
   - 출력 크기: 1080x1080
4. **생성 버튼** 클릭
5. **결과**: 원본 vs 편집본 비교
6. **다운로드**

---

## 🔧 모델 관리

### 사용 가능한 모델

| 모델 | 속도 | 품질 | 인증 | 권장 용도 |
|------|------|------|------|-----------|
| **flux-schnell** | ⚡ 매우 빠름 | ⭐⭐⭐⭐ | ✅ 필요 | 일반 사용 |
| **flux-dev** | 🐢 느림 | ⭐⭐⭐⭐⭐ | ✅ 필요 | 최고 품질 |
| **sdxl** | 🐢 보통 | ⭐⭐⭐ | ❌ 불필요 | 안정적 폴백 |
| **sd3** | 🐢 보통 | ⭐⭐⭐⭐ | ✅ 필요 | 텍스트 렌더링 |
| **playground** | 🐢 보통 | ⭐⭐⭐⭐ | ❌ 불필요 | 미적 품질 |
| **kandinsky** | 🐢 보통 | ⭐⭐⭐ | ❌ 불필요 | 다국어 |

### 모델 변경 방법

#### 방법 1: 환경변수 (.env)

```bash
# .env 파일 수정
PRIMARY_MODEL=sdxl

# 서버 재시작
```

#### 방법 2: YAML 설정

```yaml
# model_config.yaml
runtime:
  primary_model: "sdxl"
```

#### 방법 3: 명령줄 (일회성)

```bash
PRIMARY_MODEL=playground uvicorn src.backend.main:app
```

### FLUX 모델 사용하기

#### 1. Hugging Face 계정 생성

https://huggingface.co/join

#### 2. 토큰 발급

https://huggingface.co/settings/tokens
- "New token" → "Read" 권한 선택

#### 3. CLI 로그인

```bash
pip install -U huggingface_hub
huggingface-cli login
# 토큰 입력: hf_xxxxx...
```

#### 4. 모델 접근 권한

https://huggingface.co/black-forest-labs/FLUX.1-schnell
- "Agree and access repository" 클릭

#### 5. 실행

```bash
PRIMARY_MODEL=flux-schnell uvicorn src.backend.main:app
```

### 새 모델 추가하기

```yaml
# model_config.yaml에 추가
models:
  my-custom-model:
    id: "username/model-name-on-hf"
    type: "sdxl"  # 또는 flux, sd3, kandinsky
    requires_auth: false
    params:
      default_steps: 25
      use_negative_prompt: true
      guidance_scale: 7.0
      supports_i2i: true
      max_tokens: 77

runtime:
  primary_model: "my-custom-model"
```

---

## 🌐 API 문서

### 엔드포인트 개요

```
베이스 URL: http://localhost:8000
```

#### 📝 문구 생성

```http
POST /api/caption
Content-Type: application/json

{
  "service_type": "헬스장",
  "service_name": "30일 챌린지",
  "features": "전문 PT, 영양 관리",
  "location": "강남",
  "tone": "친근하고 동기부여"
}
```

**응답:**
```json
{
  "output_text": "문구:\n1. ...\n\n해시태그:\n#..."
}
```

#### 🖼 이미지 생성 (T2I)

```http
POST /api/generate_t2i
Content-Type: application/json

{
  "prompt": "30일 다이어트 챌린지, 동기부여, 밝은 분위기",
  "width": 1024,
  "height": 1024,
  "steps": 10
}
```

**응답:**
```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

#### ✏️ 이미지 편집 (I2I)

```http
POST /api/generate_i2i
Content-Type: application/json

{
  "input_image_base64": "iVBORw0KGgoAAAA...",
  "prompt": "밝고 활기찬 분위기",
  "strength": 0.75,
  "width": 1024,
  "height": 1024,
  "steps": 30
}
```

#### 📊 상태 확인

```http
GET /status
```

**응답:**
```json
{
  "gpt_ready": true,
  "image_ready": true,
  "loaded": true,
  "name": "flux-schnell",
  "device": "cuda"
}
```

#### 📋 모델 목록

```http
GET /models
```

**응답:**
```json
{
  "models": {
    "flux-schnell": {
      "id": "black-forest-labs/FLUX.1-schnell",
      "type": "flux",
      "default_steps": 4,
      "max_tokens": 512
    }
  },
  "current": "flux-schnell",
  "primary": "flux-schnell",
  "fallback_chain": ["sdxl", "playground"]
}
```

### Swagger UI

```
http://localhost:8000/docs
```

---

## 🐛 문제 해결

### 일반적인 문제

#### ❌ "OpenAI 클라이언트가 초기화되지 않았습니다"

**원인:** OpenAI API 키 미설정

**해결:**
```bash
# .env 파일에 추가
OPENAI_API_KEY=sk-proj-your-key

# 서버 재시작
```

#### ❌ "이미지 파이프라인이 초기화되지 않았습니다"

**원인:** 모든 모델 로딩 실패

**해결:**
```bash
# 1. 백엔드 로그 확인
# 2. SDXL로 폴백 강제
PRIMARY_MODEL=sdxl

# 3. 인증 필요 모델인 경우
huggingface-cli login
```

#### ⚠️ GPU 메모리 부족 (CUDA out of memory)

**해결 방법:**

**방법 1: 8비트 양자화**
```bash
# .env
USE_8BIT=true
```

**방법 2: 더 작은 모델**
```bash
# .env
PRIMARY_MODEL=sdxl
```

**방법 3: 메모리 최적화 전체 활성화**
```yaml
# model_config.yaml
runtime:
  memory:
    use_8bit: true
    enable_attention_slicing: true
    enable_vae_slicing: true
```

#### 🔌 백엔드 연결 실패

**확인사항:**
1. 백엔드가 실행 중인가? (Port 8000)
2. 프론트엔드 설정 확인
3. 방화벽 확인

**해결:**
```bash
# 프론트엔드 설정
# frontend_config.yaml
api:
  base_url: "http://localhost:8000"

# 또는 환경변수
API_BASE_URL=http://localhost:8000 streamlit run src/frontend/app.py
```

### 성능 최적화

#### CPU에서 실행 (GPU 없음)

```bash
# 경고: 매우 느림 (5-10분/이미지)
PRIMARY_MODEL=sdxl
ENABLE_FALLBACK=false

# 작은 해상도 권장
# 512x512 또는 768x768
```

#### GPU 성능 최대화

```bash
PRIMARY_MODEL=flux-schnell
USE_8BIT=false
ENABLE_ATTENTION_SLICING=false
ENABLE_VAE_SLICING=false
```

---

## 👨‍💻 개발 가이드

### 프로젝트 구조

```
Ad_Content_Creation_Service_Team3/
├── .env                        # 환경변수 (Git 제외!)
├── env.example                # 환경변수 템플릿
├── .gitignore
├── requirements.txt
├── README.md
├── docker-compose.yml
├── Dockerfile
│
├── src/
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 게이트웨이
│   │   ├── services.py         # AI 서비스 레이어
│   │   ├── model_config.yaml   # 모델 설정 파일
│   │   ├── model_registry.py   # 설정 파서
│   │   └── model_loader.py     # 모델 로더
│   │
│   └── frontend/
│       ├── __init__.py
│       ├── app.py              # Streamlit 앱
│       └── frontend_config.yaml # UI 설정 파일
│
├── cache/                      # 모델 캐시 (자동 생성)
│   └── hf_models/
│
├── docs/                       # 문서
│   ├── MODEL_SETUP_GUIDE.md
│   ├── ENV_SETUP_GUIDE.md
│   ├── FRONTEND_GUIDE.md
│   └── CONFIGURATION_PRIORITY.md
│
└── tests/                      # 테스트 (향후 추가)
    ├── test_services.py
    └── test_api.py
```

### 설정 우선순위

```
1. 환경변수 (.env)           ← 최우선 🥇
2. YAML 설정 파일             ← 기본값 🥈
3. 코드 내 기본값             ← 폴백 🥉
```

**예시:**
```bash
# .env
PRIMARY_MODEL=sdxl  # 이게 사용됨!
```

```yaml
# model_config.yaml
runtime:
  primary_model: "flux-schnell"  # 무시됨
```

### 새 페이지 추가하기

#### 1. 프론트엔드 설정에 페이지 정의

```yaml
# frontend_config.yaml
pages:
  - id: "video"           # 🆕
    icon: "🎥"
    title: "비디오 생성"
    description: "AI로 짧은 홍보 영상 생성"
```

#### 2. 렌더링 함수 추가

```python
# app.py
def render_video_page(config: ConfigLoader, api: APIClient):
    st.title("🎥 비디오 생성")
    # 구현...

# main() 함수에 라우팅 추가
def main():
    # ...
    if page_id == "video":
        render_video_page(config, api)
```

### 새 모델 추가하기

#### 1. YAML에 모델 정의

```yaml
# model_config.yaml
models:
  my-new-model:
    id: "organization/model-name"
    type: "sdxl"  # 기존 타입 사용
    requires_auth: false
    params:
      default_steps: 20
      max_steps: 50
      use_negative_prompt: true
      guidance_scale: 7.0
      supports_i2i: true
      max_tokens: 77
    description: "내 새로운 모델"

runtime:
  primary_model: "my-new-model"
```

#### 2. 실행

```bash
# 코드 수정 없이 바로 작동!
uvicorn src.backend.main:app
```

### 커스텀 모델 타입 추가

새로운 모델 아키텍처를 추가하려면:

```python
# model_loader.py의 _load_model_by_type 수정

def _load_model_by_type(self, model_config: ModelConfig):
    # ...
    
    elif model_type == "my_custom_type":  # 🆕
        from my_library import MyCustomPipeline
        t2i = MyCustomPipeline.from_pretrained(
            model_id, 
            **load_kwargs
        ).to(self.device)
        i2i = MyCustomPipeline.from_pretrained(
            model_id, 
            **load_kwargs
        ).to(self.device)
    
    # ...
```

### Git 워크플로우

```bash
# 개발 브랜치 생성
git checkout -b feature/new-feature

# 변경사항 커밋
git add .
git commit -m "feat: 새 기능 추가"

# .env는 절대 커밋하지 않기!
# .gitignore에 있는지 확인
cat .gitignore | grep .env
```

---

## 🧪 테스트

### 수동 테스트

#### 백엔드 API 테스트

```bash
# 상태 확인
curl http://localhost:8000/status

# 모델 목록
curl http://localhost:8000/models

# 문구 생성 테스트
curl -X POST http://localhost:8000/api/caption \
  -H "Content-Type: application/json" \
  -d '{
    "service_type": "헬스장",
    "service_name": "테스트",
    "features": "테스트 기능",
    "location": "서울",
    "tone": "친근하고 동기부여"
  }'
```

#### 프론트엔드 테스트

1. http://localhost:8501 접속
2. 각 페이지에서 기능 테스트
3. 사이드바에서 "시스템 상태" 확인

### 자동 테스트 (향후 구현)

```bash
# 단위 테스트
pytest tests/

# 커버리지
pytest --cov=src tests/
```

---

## 🚢 배포

### Docker로 배포

#### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 복사
COPY . .

# 포트 노출
EXPOSE 8000 8501

# 실행
CMD ["sh", "-c", "uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 & streamlit run src/frontend/app.py --server.port 8501 --server.address 0.0.0.0"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PRIMARY_MODEL=${PRIMARY_MODEL:-sdxl}
    volumes:
      - ./cache:/app/cache
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  frontend:
    build: .
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://backend:8000
    depends_on:
      - backend
```

#### 실행

```bash
# 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중단
docker-compose down
```

### 클라우드 배포

#### AWS EC2 (GPU 인스턴스)

```bash
# 1. GPU 인스턴스 생성 (g4dn.xlarge 이상)
# 2. NVIDIA 드라이버 설치
# 3. Docker & NVIDIA Container Toolkit 설치
# 4. 저장소 클론 및 실행

git clone your-repo
cd healthcare-ai-content
docker-compose up -d
```

#### Hugging Face Spaces

```bash
# Streamlit 앱으로 배포
# Space 타입: Streamlit
# GPU: T4 (Small) 이상
```

---

## 📊 성능 벤치마크

### 이미지 생성 속도 (1024x1024)

| 모델 | GPU (RTX 4090) | GPU (RTX 3060) | CPU |
|------|----------------|----------------|-----|
| **FLUX-schnell** | ~3초 | ~8초 | ~5분 |
| **FLUX-dev** | ~15초 | ~45초 | ~20분 |
| **SDXL** | ~10초 | ~30초 | ~10분 |

### 메모리 사용량

| 모델 | FP16 | FP16 + 8bit | CPU |
|------|------|-------------|-----|
| **FLUX-schnell** | 16GB | 8GB | 32GB |
| **SDXL** | 12GB | 6GB | 24GB |

---

## 🔐 보안

### 환경변수 관리

```bash
# ✅ 올바른 방법
echo ".env" >> .gitignore
git add env.example  # 템플릿만 커밋

# ❌ 절대 금지
git add .env  # API 키 노출!
```

### API 키 보호

- `.env` 파일은 로컬에만 보관
- 프로덕션: 환경변수 또는 Secret Manager 사용
- Docker Secrets, AWS Secrets Manager, Azure Key Vault 권장

### CORS 설정 (프로덕션)

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # 특정 도메인만
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🤝 기여하기

### 버그 리포트

GitHub Issues에 다음 정보 포함:
- 에러 메시지
- 재현 단계
- 환경 정보 (OS, Python 버전, GPU)
- 로그 파일

### 기능 제안

- 명확한 사용 사례
- 예상되는 동작
- 대안 (있다면)

### Pull Request

```bash
# 1. Fork & Clone
git clone https://github.com/your-username/healthcare-ai-content.git

# 2. 브랜치 생성
git checkout -b feature/amazing-feature

# 3. 변경 & 커밋
git commit -m "feat: 놀라운 기능 추가"

# 4. Push
git push origin feature/amazing-feature

# 5. PR 생성
```

---

## 📚 참고 자료

### 프로젝트 문서 (docs/)

**필수 문서:**
- **[ComfyUI 통합 가이드](./docs/COMFYUI_INTEGRATION.md)** - ComfyUI 설치, 워크플로우, 후처리 옵션
- **[이미지 편집 가이드](./docs/IMAGE_EDITING_GUIDE.md)** - BEN2, FLUX.1-Fill, Qwen-Image 사용법
- **[텍스트 오버레이 통합 기록](./recoding/2025-12-02_text_overlay_integration.md)** - 3D 캘리그라피 구현 상세
- **[ARCHITECTURE_ANALYSIS.md](./ARCHITECTURE_ANALYSIS.md)** - 코드 구조 분석 및 개선 권장사항
- **[PHASE_1_2_IMPLEMENTATION.md](./PHASE_1_2_IMPLEMENTATION.md)** - Phase 1 & 2 구현 완료 보고서

**추가 문서:**
- [모델 설정 가이드](./docs/MODEL_SETUP_GUIDE.md) - 모델 다운로드 및 설정
- [환경 설정 가이드](./docs/env_setup_guide.md) - 환경변수 및 초기 설정
- [프론트엔드 가이드](./docs/frontend_guide.md) - UI 커스터마이징
- [프롬프트 최적화](./docs/PROMPT_OPTIMIZATION.md) - 효과적인 프롬프트 작성법

### 공식 문서

- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Streamlit 문서](https://docs.streamlit.io/)
- [ComfyUI 문서](https://github.com/comfyanonymous/ComfyUI)
- [Diffusers 문서](https://huggingface.co/docs/diffusers/)
- [OpenAI API](https://platform.openai.com/docs/)

### 모델 관련

- [FLUX.1](https://huggingface.co/black-forest-labs/FLUX.1-schnell)
- [FLUX.1-Fill](https://huggingface.co/black-forest-labs/FLUX.1-Fill-dev-GGUF)
- [Qwen-Image-Edit](https://huggingface.co/Qwen/Qwen-Image-Edit-2509)
- [BEN2](https://huggingface.co/PramaLLC/BEN2)
- [InstantX ControlNet Union](https://huggingface.co/InstantX/FLUX.1-dev-Controlnet-Union)
- [Stable Diffusion XL](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0)
- [Hugging Face Hub](https://huggingface.co/)

### 커뮤니티

- GitHub Issues
- GitHub Discussions
- Discord (향후 추가)

---

## 📝 업데이트 로그

### v3.1.0 (2025-12-02) - 3D 캘리그라피 기능 추가 🔤

**주요 기능:**
- ✨ **3D 캘리그라피 생성**: 페이지 5 신규 추가
- 🎨 **AI 배경 제거**: rembg (u2net) 기반 투명 배경 생성
- 🖼️ **후처리 파이프라인**: Threshold → Erosion → Gaussian Blur
- 📦 **PNG 출력**: 배경 투명 이미지로 다른 이미지와 합성 가능

**신규 파일:**
- `src/backend/text_overlay.py` - 캘리그라피 생성 핵심 로직
- `recoding/2025-12-02_text_overlay_integration.md` - 구현 상세 문서

**수정 파일:**
- `src/backend/services.py` - generate_calligraphy_core() 추가
- `src/backend/main.py` - /api/generate_calligraphy 엔드포인트 추가
- `src/frontend/app.py` - render_text_overlay_page() 구현
- `src/frontend/frontend_config.yaml` - 페이지 5 설정 추가
- `README.md` - 캘리그라피 기능 문서화

**기술 스택:**
- rembg (u2net 모델)
- OpenCV (cv2)
- PIL (Pillow)

**성능:**
- 평균 생성 시간: 2-5초
- 이미지 크기: 1024x1024 ~ 2048x2048 (자동 조정)
- 파일 크기: 50KB ~ 500KB (PNG)

---

### v3.0.0 (2025-12-01) - Phase 1 & 2 아키텍처 개선 🚀

**주요 변경사항:**

**Phase 1: 프롬프트 엔진 최적화**
- ✨ **GPT API 비용 66% 절감**: 3회 호출 → 1회 통합
- ⚡ **처리 속도 50% 향상**: 3-6초 → 1-2초
- 🔧 **build_final_prompt_v2()** 신규 함수 도입
- 📦 **PromptHelper 유틸리티**: 중복 코드 3곳 → 1곳
- 🎯 프롬프트 처리 백엔드 중앙화

**Phase 2: 구조 개선**
- 🛡️ **Custom Exception 체계**: 6가지 타입별 에러 처리
- 🎨 **ModelSelector 컴포넌트**: 100+ 줄 → 6줄 (95% 감소)
- 📊 **통일된 에러 응답**: HTTP 상태 코드 + type 필드
- 🧹 코드 복잡도 대폭 감소

**신규 파일:**
- `src/frontend/utils.py` - PromptHelper 유틸리티
- `src/frontend/model_selector.py` - 모델 선택 컴포넌트
- `src/backend/exceptions.py` - Custom Exception 정의
- `ARCHITECTURE_ANALYSIS.md` - 구조 분석 문서
- `PHASE_1_2_IMPLEMENTATION.md` - 구현 완료 보고서

**성능 지표:**
- 💰 월간 GPT API 비용: $30 → $10 (1000건 기준)
- ⚡ 프롬프트 처리: 3-6초 → 1-2초
- 🧹 코드 중복: 66% 감소
- 📊 복잡도: 95% 감소

---

### v2.5.0 (2024-11-27) - ComfyUI 통합

**주요 변경사항:**
- 🎨 **ComfyUI 통합**: 모든 모델을 ComfyUI로 통합 관리
- ⚡ **3가지 후처리 옵션**: 없음, Impact Pack (YOLO+SAM), 기존 ADetailer
- 🔧 **워크플로우 기반 생성**: T2I, I2I, Impact Pack 워크플로우
- 🧪 **이미지 편집 실험**: BEN2 + FLUX.1-Fill / Qwen-Image
- 💾 **메모리 효율성**: ComfyUI 유휴 시 ~500MB만 사용
- 📝 **상세 문서**: ComfyUI 통합 가이드, 이미지 편집 가이드

**새로운 파일:**
- `src/backend/comfyui_client.py` - ComfyUI API 클라이언트
- `src/backend/comfyui_workflows.py` - 워크플로우 템플릿
- `scripts/install_comfyui.sh` - ComfyUI 설치 스크립트
- `scripts/start_all.sh` / `stop_all.sh` - 통합 실행 스크립트
- `docs/COMFYUI_INTEGRATION.md` - ComfyUI 가이드
- `docs/IMAGE_EDITING_GUIDE.md` - 이미지 편집 가이드

**Breaking Changes:**
- ComfyUI 설치 필수 (포트 8188)
- API 엔드포인트에 후처리 파라미터 추가
- 전체 서비스 시작: `bash scripts/start_all.sh` 사용 권장

**주요 변경사항:**
- ✨ 완전한 설정 기반 아키텍처
- 🔧 YAML로 모든 설정 관리
- 🎨 6개 사전 정의 모델
- 🔄 자동 폴백 체인
- 💾 메모리 최적화 옵션
- 🌐 환경변수 우선순위 시스템
- 📝 포괄적인 문서

**Breaking Changes:**
- 설정 파일 필수: `model_config.yaml`, `frontend_config.yaml`
- `pyyaml` 의존성 추가

### v1.0.0 (2023-12-XX) - 초기 릴리스

- 기본 기능 구현
- SDXL 지원
- OpenAI GPT 통합

---

## 🎓 FAQ

### Q: GPU가 없어도 사용할 수 있나요?

**A:** 네, CPU 모드로 작동합니다. 하지만 이미지 생성이 매우 느립니다 (5-10분).

```bash
# CPU 모드는 자동 감지
# GPU가 없으면 자동으로 CPU 사용
```

### Q: 어떤 모델을 선택해야 하나요?

**A:** 상황별 권장:

- **처음 사용**: `sdxl` (인증 불필요, 안정적)
- **최고 품질**: `flux-dev` (느리지만 최고)
- **빠른 생성**: `flux-schnell` (권장)
- **메모리 부족**: `playground` (경량)

### Q: 이미지 생성이 너무 느려요

**A:** 성능 개선 방법:

1. 더 빠른 모델 사용 (`flux-schnell`)
2. Steps 줄이기 (10 이하)
3. 해상도 낮추기 (512x512)
4. GPU 사용 확인

### Q: "out of memory" 에러가 나요

**A:** 메모리 절약 방법:

```bash
# .env
USE_8BIT=true
ENABLE_ATTENTION_SLICING=true
ENABLE_VAE_SLICING=true
PRIMARY_MODEL=sdxl  # 더 작은 모델
```

### Q: 한국어 프롬프트가 제대로 작동하나요?

**A:** 네, GPT가 자동으로 영어로 번역합니다.

```yaml
# model_config.yaml
runtime:
  prompt_optimization:
    translate_korean: true  # 기본 활성화
```

### Q: 상업적으로 사용할 수 있나요?

**A:** 모델별로 다릅니다:

- ✅ **FLUX-schnell**: 상업적 사용 가능
- ❌ **FLUX-dev**: 비상업적 용도만
- ✅ **SDXL**: 상업적 사용 가능
- ⚠️ 각 모델의 라이선스 확인 필수

### Q: API 요금은 얼마나 나오나요?

**A:** 
- **OpenAI GPT-5 Mini**: 문구 생성 시 소량 ($0.01 ~ $0.05/요청)
- **이미지 생성**: 로컬 실행이므로 무료 (전기료/GPU 비용만)

### Q: 여러 사용자가 동시에 사용할 수 있나요?

**A:** 
- 백엔드는 비동기 처리로 다중 요청 지원
- 하지만 모델은 순차 실행 (GPU 메모리 공유 불가)
- 대규모 사용: Worker 여러 개 실행 권장

---

## 📄 라이선스

```
MIT License

Copyright (c) 2024 Your Organization

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**주의:** 사용하는 AI 모델의 라이선스도 반드시 확인하세요.

---

## 👥 팀

- **개발팀**: Team 3
- **프로젝트**: 소상공인 AI 콘텐츠 제작 서비스
- **문의**: support@yourcompany.com

---

## 🙏 감사의 말

이 프로젝트는 다음 오픈소스 프로젝트들을 기반으로 합니다:

- [Hugging Face Diffusers](https://github.com/huggingface/diffusers)
- [FastAPI](https://github.com/tiangolo/fastapi)
- [Streamlit](https://github.com/streamlit/streamlit)
- [PyTorch](https://github.com/pytorch/pytorch)
- [OpenAI](https://openai.com/)

---

## 🚀 빠른 시작 체크리스트

### 필수 준비사항

- [ ] Python 3.9+ 설치
- [ ] Git 설치
- [ ] NVIDIA GPU (권장: VRAM 12GB+)
- [ ] 50GB+ 디스크 공간

### 설치 단계

1. **저장소 클론**
```bash
git clone https://github.com/JiyeonGong/Ad_Content_Creation_Service_Team3
cd Ad_Content_Creation_Service_Team3
```

2. **가상환경 생성 및 활성화**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows
```

3. **의존성 설치**
```bash
pip install -r requirements.txt
```

4. **환경변수 설정**
```bash
cp env.example .env
# .env 파일 편집하여 OPENAI_API_KEY 입력
nano .env  # 또는 원하는 에디터
```

5. **ComfyUI 설치**
```bash
bash scripts/install_comfyui.sh
```

6. **전체 서비스 시작**
```bash
bash scripts/start_all.sh
```

### 접속

- 💻 **프론트엔드**: http://localhost:8501
- 🔧 **API 문서**: http://localhost:8000/docs
- 🎨 **ComfyUI**: http://localhost:8188

### Phase 1 & 2 개선사항 확인

```bash
# 백엔드 로그에서 통합 프롬프트 확인
tail -f logs/backend.log | grep "통합 프롬프트"

# GPT 호출이 1회만 발생하는지 확인
tail -f logs/backend.log | grep "GPT 호출"
```

### 주요 기능 테스트

1. **문구 생성** (페이지 1)
   - 서비스 정보 입력
   - 3가지 문구 + 15개 해시태그 생성 확인
   - GPT API 1회 호출 확인 (Phase 1 개선)

2. **T2I 이미지 생성** (페이지 2)
   - 모델 선택 (FLUX.1-dev-Q8 권장)
   - 후처리 옵션 선택
   - 3-8초 내 생성 확인 (Phase 1 속도 개선)

3. **I2I 편집** (페이지 3)
   - 이미지 업로드
   - 보조 프롬프트 자동 생성 확인
   - 편집 결과 비교

4. **고급 편집** (페이지 4)
   - 3가지 모드 테스트
   - ControlNet 적용 확인

### 문제 해결

#### 일반적인 문제

```bash
# 로그 확인
tail -f logs/streamlit.log  # 프론트엔드
tail -f logs/backend.log    # 백엔드
tail -f logs/comfyui.log    # ComfyUI

# 서비스 재시작
bash scripts/stop_all.sh
bash scripts/start_all.sh
```

#### 페이지4: Qwen 편집 모드 오류 (미해결)

**증상**: `unet_name: 'Qwen-Image-Edit-2509-Q8_0.gguf' not in []`

**원인**: ComfyUI의 UNETLoader가 Qwen GGUF 모델을 `diffusion_models` 폴더에서 인식하지 못함

**시도한 해결책**:
1. ✅ 워크플로우 노드 변경: `UnetLoaderGGUF` → `UNETLoader`
2. ✅ 모델 파일 올바른 폴더 배치:
   ```bash
   comfyui/models/diffusion_models/Qwen-Image-Edit-2509-Q8_0.gguf (심볼릭 링크)
   comfyui/models/text_encoders/t5-v1_1-xxl-encoder-Q8_0.gguf (심볼릭 링크)
   ```
3. ✅ 서버 재시작 여러 번
4. ✅ 동적 폴백 로직 추가

**결과**: ❌ **모두 실패** - ComfyUI가 `folder_paths.get_filename_list("diffusion_models")`에서 빈 배열 반환

**현재 상태**: 
- 페이지4 "🎯 정밀 편집 모드" **비활성화**
- 나머지 4가지 모드는 정상 작동 (Portrait, Product, Hybrid, FLUX Fill)

**향후 개선 방향**:
- ComfyUI-GGUF 업데이트 대기 (Qwen 공식 지원 여부 확인)
- Qwen diffusers 형식 버전 탐색
- 별도 Qwen 전용 백엔드 구현 검토

**주의**: `UNETLoader`는 `diffusion_models/` 폴더를 사용 (`unet/` 아님!)

#### 페이지5: 3D 캘리그라피 색상/스타일 미적용

**증상**: 흑백 텍스트만 나오고 3D 효과 없음

**확인 사항**:
1. 백엔드 로그 확인:
   ```bash
   tail -f logs/backend.log | grep -E "ControlNet|3D 렌더링|렌더링 실패"
   ```

2. ControlNet 모델 확인:
   ```bash
   ls -lh comfyui/models/controlnet/ | grep depth
   ```

3. "⚠️ ControlNet 렌더링 실패" 메시지가 로그에 있으면:
   - ControlNet 모델 미다운로드
   - CUDA 메모리 부족
   - `device_map="auto"` 설정 문제

**임시 해결**: 코드 수정으로 간단한 PIL 기반 색상 오버레이로 대체 가능

---

## 📜 변경 이력 (Change Log)

### 2025-12-03 (v1.3)
- 🎯 **프로젝트 리브랜딩**: "헬스케어 소상공인" → "소상공인" 전반으로 확장 ✅
  - 제목 변경 (5개 파일): README, frontend_config, app.py, main.py, services.py
  - 헬스케어 관련 콘텐츠 제거 (service_types 리스트, placeholder 예시)
- 📝 **페이지1 개선**: 서비스 종류 선택 방식 변경 ✅
  - selectbox (고정 목록) → text_input (사용자 직접 입력)
  - 더 다양한 업종 지원: 카페, 미용실, 온라인 쇼핑몰 등
  - GPT 프롬프트 호환성 유지 (service_type 변수 그대로 사용)
- ❌ **페이지4 Qwen 편집 모드 시도** (미해결):
  - 문제: ComfyUI `UNETLoader`가 Qwen GGUF 모델을 `diffusion_models`에서 인식 못함
  - 시도: 노드 타입 변경, 올바른 폴더 배치, 서버 재시작, 동적 폴백 로직
  - 결과: 모두 실패 - `folder_paths.get_filename_list("diffusion_models")` 빈 배열 반환
  - **현재 상태**: 정밀 편집 모드 비활성화 (나머지 4가지 모드는 정상)
- 🔍 **페이지5 캘리그라피 문제 분석**:
  - ControlNet 렌더링 실패 시 원본 반환 동작 확인
  - 로그 모니터링 및 트러블슈팅 가이드 작성

### 2025-12-02 (v1.2)
- 🔤 **3D 캘리그라피 생성 기능 추가** (페이지5)
  - rembg 기반 배경 투명 PNG 생성
  - ControlNet Meta Tensor 오류 수정 (device_map="auto")
- 🖼️ **FLUX.1-Fill 모드 추가** (페이지4)
  - BEN2 자동 마스킹 + FLUX Fill 인페인팅
  - 워크플로우 15개 노드 구현
- 🎯 **Qwen-Image-Edit 모드 추가** (페이지4)
  - 자연어 기반 정밀 편집
  - 워크플로우 11개 노드 구현
- ⏱️ **ComfyUI 타임아웃 증가**: 300초 → 600초
  - FLUX 모델 2번 로딩 정상 동작 확인
  - 복잡한 워크플로우 대응

### 2025-12-01 (v1.1)
- ✅ **Phase 1 & 2 구조 개선 완료**
  - GPT API 비용 66% 절감
  - 처리 속도 50% 향상
  - 코드 복잡도 95% 감소

### 2025-11-30 (v1.0)
- 🚀 초기 버전 배포
  - 4가지 핵심 워크플로우 구현
  - ComfyUI 통합

---

<div align="center">

[⬆ 맨 위로](#-소상공인-ai-콘텐츠-제작-서비스)

</div>