# 💼 소상공인을 위한 AI 콘텐츠 제작 서비스

> **AI 기반 마케팅 자동화 플랫폼** - 인스타그램 콘텐츠 자동 생성, 이미지 편집, 3D 텍스트 오버레이

![Python](https://img.shields.io/badge/Python-3.12-blue) 
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28-red)
![ComfyUI](https://img.shields.io/badge/ComfyUI-Latest-purple)

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [주요 기능](#주요-기능)
3. [기술 스택](#기술-스택)
4. [시스템 아키텍처](#시스템-아키텍처)
5. [설치 및 실행](#설치-및-실행)
6. [사용 방법](#사용-방법)
7. [API 엔드포인트](#api-엔드포인트)
8. [성능 정보 및 주의사항](#성능-정보-및-주의사항)
9. [ComfyUI 통합](#comfyui-통합)
10. [추후 개선 가능 사항](#추후-개선-가능-사항)
11. [FAQ](#faq)

---

## 프로젝트 개요

이 프로젝트는 **소상공인(의류점, 마사지샵, 카페, 뷰티샵 등)을 위한 AI 기반 마케팅 자동화 플랫폼**입니다.

### 핵심 목표

- ✅ **무료/저비용 마케팅 솔루션**: 소상공인도 전문가급 콘텐츠 제작 가능
- ✅ **자동화된 워크플로우**: 수동 작업 최소화
- ✅ **다채로운 콘텐츠**: 텍스트 문구, 이미지, 3D 비주얼까지 한 곳에서

### 지원하는 비즈니스 분야

- 🏪 **소매점**: 의류, 액세서리, 선물용품
- 💇 **미용/건강**: 마사지, 헤어샵, 네일샵, 필라테스
- ☕ **음식점**: 카페, 베이커리, 레스토랑
- 📚 **서비스**: 학원, 컨설팅, 온라인 강좌
- 🎨 **크리에이티브**: 핸드메이드, 아트, 디자인

---

## 주요 기능

### 페이지 1️⃣: 홍보 문구 & 해시태그 생성

**입력 정보**
- 가게 이름 (필수)
- 서비스 종류 (필수, 사용자 직접 입력)
- 대표 제품/클래스 이름
- 핵심 특징 및 장점 (필수)
- 영업 지역 (필수)
- 톤 선택 (친근함 / 전문성)

**출력**
- 🎯 인스타그램 홍보 문구 3개
- 🔖 추천 해시태그 15개

**기술**
- OpenAI GPT-5 Mini 모델 사용
- 실시간 최적화된 문구 생성

---

### 페이지 2️⃣: 인스타그램 이미지 생성 (T2I)

**입력**
- 페이지 1에서 생성된 문구 (자동 연결) 또는 사용자 프롬프트
- 이미지 크기 선택
- 샘플링 스텝 (1~50, 기본 28)
- Guidance Scale (1.0~10.0, 기본값 3.5)
- 보조 프롬프트 강도 (약함/중간/강함)

**출력**
- 3가지 버전의 프로페셔널 이미지
- 다운로드 가능

**기술**
- **FLUX.1-dev** (ComfyUI via GGUF 양자화)
- 고속 추론 최적화
- FLUX 전용 3단계 프롬프트 변환

**성능**
- ⏱️ **모델 로딩**: 2~3분 (첫 실행)
- ⏱️ **이미지 생성**: 2~3분 이상 (2~3분 소요)

---

### 페이지 3️⃣: 이미지 스타일 변경 (I2I)

**입력**
- 업로드된 이미지 또는 페이지 2 생성본
- 편집 프롬프트 (필수)
- 변화 강도 (0.0~1.0, 기본값 0.75)
- Steps (1~50)
- Guidance Scale

**출력**
- 편집된 이미지
- 원본과 비교 뷰

**특징**
- 페이지 1 문구 자동 반영 (연결 모드)
- FLUX.1-dev 기반 고품질 편집

---

### 페이지 4️⃣: 배경 제거 + 고급 편집

**3가지 편집 모드**

#### 👤 인물 모드 (Portrait Mode)
- ControlNet Depth SDXL + FLUX.1-dev
- 인물 강조, 배경 변경
- 사용 사례: 인물사진, 프로필 이미지

#### 📦 제품 모드 (Product Mode)
- 제품 분석 → 배경 생성 → 자연스러운 합성
- 사용 사례: 상품 카탈로그, 쇼핑몰 이미지

#### ✨ 하이브리드 모드 (Hybrid Mode)
- 심화된 편집 옵션
- 강력한 효과 적용 가능

**기반 기술**
- BEN2 (배경 제거)
- FLUX.1-Fill (배경 영역 채우기/확장)
- ControlNet Depth SDXL (깊이 기반 조정)

---

### 페이지 5️⃣: 3D 캘리그라피 생성

**입력**
- 텍스트 (예: "새해 대박!")
- 폰트 선택
- 색상 선택
- 렌더링 스타일 (default / emboss / carved / floating)

**출력**
- 입체적인 3D 텍스트 이미지
- 투명 배경 (PNG)

**기술**
- ControlNet Depth SDXL
- 3D 뎁스맵 렌더링
- Rembg 배경 제거

**용도**
- 인스타그램 스토리 텍스트
- 바너 디자인
- 썸네일 제작

---

## 기술 스택

### 프론트엔드
- **Streamlit** (1.28+): 웹 UI
- **PyYAML**: 설정 관리
- **Pillow**: 이미지 처리

### 백엔드
- **FastAPI** (0.104+): REST API
- **Pydantic**: 데이터 검증
- **OpenAI API**: 텍스트 생성

### AI/ML 핵심
- **ComfyUI**: 이미지 생성 오케스트레이션
- **FLUX.1-dev** (GGUF 양자화): 고속 T2I/I2I
- **FLUX.1-Fill** (GGUF): 배경 채우기
- **SDXL ControlNet (Depth)**: 깊이 제어
- **BEN2**: 배경 제거
- **Rembg (U2Net)**: 배경 제거 후처리

### GPU 최적화
- CUDA 12.8 기반
- Torch 2.1+ (BF16/FP16 혼합 정밀도)
- CPU Offload: 메모리 효율화
- VAE Tiling: 메모리 사용량 감소

### 데이터베이스 (선택)
- SQLite (로컬)
- PostgreSQL (프로덕션)

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    사용자 (웹 브라우저)                        │
└────────────┬────────────────────────────────────────────────┘
             │ HTTP/Streamlit
             ↓
┌─────────────────────────────────────────────────────────────┐
│          Streamlit 프론트엔드 (포트 8501)                     │
│  • 페이지 네비게이션                                          │
│  • 폼 입력 & 이미지 갤러리                                     │
│  • 세션 상태 관리                                            │
└────────────┬────────────────────────────────────────────────┘
             │ REST API (JSON)
             ↓
┌─────────────────────────────────────────────────────────────┐
│         FastAPI 백엔드 (포트 8000)                           │
│  ├─ /api/caption - 문구 생성 (GPT)                          │
│  ├─ /api/t2i - 이미지 생성 (T2I)                            │
│  ├─ /api/i2i - 이미지 편집 (I2I)                            │
│  ├─ /api/edit_with_comfyui - 고급 편집                      │
│  ├─ /api/generate_calligraphy - 3D 텍스트                   │
│  └─ /status - 헬스 체크                                     │
└────────────┬────────────────────────────────────────────────┘
             │ WebSocket / REST
             ↓
┌─────────────────────────────────────────────────────────────┐
│         ComfyUI 핵심 엔진 (포트 8188)                        │
│  ├─ FLUX.1-dev (GGUF) - T2I/I2I                            │
│  ├─ FLUX.1-Fill (GGUF) - 배경 채우기                         │
│  ├─ SDXL ControlNet Depth - 깊이 제어                       │
│  ├─ BEN2 - 배경 제거                                        │
│  └─ 커스텀 노드 (Impact Pack, Rembg 등)                     │
└─────────────────────────────────────────────────────────────┘
             │
             ↓
    ┌────────────────────┐
    │   NVIDIA GPU 22GB  │
    │   (CUDA 12.8)      │
    │   BF16/FP16 혼합  │
    └────────────────────┘
```

### 데이터 흐름 예시 (페이지 1 → 페이지 2)

```
1. 페이지 1에서 정보 입력
   ├─ 가게 이름: "강남 핸드메이드"
   ├─ 서비스: "악세사리 제작, 맞춤 디자인"
   ├─ 특징: "10년 경력 장인정신, 친환경 소재"
   └─ 톤: "전문적이고 신뢰감"

2. FastAPI /api/caption 호출
   └─ OpenAI GPT-5 Mini 처리
      → "✨ 당신의 개성을 담은 악세사리..."
      → "#수제악세사리 #강남 #..."

3. 생성된 문구 저장 (세션 상태)

4. 페이지 2로 이동 (연결 모드 활성화)
   └─ 문구가 자동으로 보조 프롬프트로 사용

5. 사용자 추가 입력
   └─ "밝고 고급스러운 분위기, 자연광"

6. FastAPI /api/t2i 호출
   ├─ 프롬프트 결합 및 최적화
   └─ ComfyUI 워크플로우 실행
      → FLUX.1-dev 모델로 3개 이미지 생성
      → 후처리 (선택)
      → 결과 반환

7. 이미지 다운로드 / 페이지 3로 이동
```

---

## 설치 및 실행

### 사전 요구사항

- **GPU**: NVIDIA GPU 22GB+ VRAM (RTX 4090 권장)
- **OS**: Linux (Ubuntu 20.04+) 또는 Windows with WSL2
- **Python**: 3.12+
- **CUDA**: 12.8+
- **Docker** (선택사항): 컨테이너화 배포용

### 1단계: 환경 설정

```bash
# 저장소 복제
git clone <repository-url>
cd Ad_Content_Creation_Service_Team3

# 가상 환경 생성
python3.12 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 또는
.venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# ComfyUI 의존성 설치
cd comfyui
pip install -r requirements.txt
cd ..
```

### 2단계: 모델 다운로드

**주요 모델**

```bash
# 로컬 캐시 디렉토리에 다운로드
# (ComfyUI가 자동으로 처리하므로 수동 설치 불필요)
# 단, 첫 실행 시 다운로드에 시간 소요

# 필수 모델 목록
- FLUX.1-dev (GGUF, ~9GB)
- FLUX.1-Fill (GGUF, ~9GB)
- SDXL Base (FP16, ~6GB)
- ControlNet Depth SDXL (~2GB)
- CLIP L (GGUF)
- T5 Encoder (GGUF)
```

### 3단계: 환경 변수 설정

```bash
# .env 파일 생성
cat > .env << EOF
OPENAI_API_KEY=sk-...  # OpenAI API 키
CUDA_VISIBLE_DEVICES=0  # GPU 0번 사용
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True  # 메모리 최적화
EOF
```

### 4단계: 서비스 시작

```bash
# 모든 서비스 자동 시작
bash scripts/start_all.sh

# 개별 시작 (디버깅용)
# 터미널 1: ComfyUI
cd comfyui && python main.py --listen 0.0.0.0 --port 8188

# 터미널 2: FastAPI
cd src/backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 터미널 3: Streamlit
cd src/frontend && streamlit run app.py --server.port 8501
```

### 5단계: 웹 접속

```
- Streamlit 프론트엔드: http://localhost:8501
- FastAPI 문서: http://localhost:8000/docs
- ComfyUI 대시보드: http://localhost:8188
```

---

## 사용 방법

### 시나리오 1: 새로운 가게 콘텐츠 제작

```
1. 페이지 1에서 가게 정보 입력
   └─ "카페 '따뜻한 핸드드립'" 정보 입력
   └─ 3개의 홍보 문구 + 해시태그 자동 생성

2. 마음에 드는 문구 선택

3. 페이지 2로 이동
   └─ 선택한 문구가 자동으로 반영
   └─ 추가 프롬프트 입력 가능
   └─ "밝고 따뜻한 카페 분위기"

4. 이미지 생성
   └─ 3개 버전의 이미지 생성됨

5. 최종 선택 후 다운로드
```

### 시나리오 2: 기존 상품 이미지 개선

```
1. 페이지 3 또는 페이지 4로 이동

2. 기존 상품 이미지 업로드

3. 편집 프롬프트 입력
   └─ "더 밝고 고급스럽게, 스튜디오 조명"

4. 이미지 편집 실행

5. 결과 비교 및 다운로드
```

### 시나리오 3: 브랜드 텍스트 생성

```
1. 페이지 5로 이동

2. 텍스트 입력
   └─ "2024 신상품"

3. 스타일 선택
   └─ "emboss" (입체감)

4. 색상 선택
   └─ "금색"

5. 3D 이미지 생성 (투명 배경)

6. 인스타그램 스토리에 사용
```

---

## API 엔드포인트

### 1. 문구 생성
```http
POST /api/caption
Content-Type: application/json

{
  "shop_name": "강남 마사지샵",
  "service_type": "타이 마사지, 경락 마사지",
  "service_name": "릴렉싱 코스 90분",
  "features": "20년 경력 태국 마스터",
  "location": "강남역 5번 출구",
  "tone": "전문적이고 신뢰감"
}

Response:
{
  "captions": ["✨ 당신의 피로...", "..."],
  "hashtags": "#타이마사지 #강남 #..."
}
```

### 2. 이미지 생성 (T2I)
```http
POST /api/t2i
Content-Type: application/json

{
  "prompt": "밝고 전문적인 마사지 샵 인테리어",
  "width": 1024,
  "height": 1024,
  "steps": 28,
  "guidance_scale": 3.5,
  "post_process_method": "none"
}

Response:
{
  "image_base64": "iVBORw0KGgo..."
}
```

### 3. 이미지 편집 (I2I)
```http
POST /api/i2i
Content-Type: application/json

{
  "input_image_base64": "...",
  "prompt": "더 밝고 고급스럽게",
  "strength": 0.75,
  "width": 1024,
  "height": 1024,
  "steps": 30,
  "guidance_scale": 5.0,
  "post_process_method": "none"
}

Response:
{
  "image_base64": "iVBORw0KGgo..."
}
```

### 4. 고급 이미지 편집
```http
POST /api/edit_with_comfyui
Content-Type: application/json

{
  "experiment_id": "portrait_mode",
  "input_image_base64": "...",
  "prompt": "프로페셔널한 인물 사진",
  "negative_prompt": "",
  "steps": 28,
  "guidance_scale": 3.5
}

Response:
{
  "success": true,
  "experiment_name": "👤 인물 모드",
  "output_image_base64": "..."
}
```

### 5. 3D 캘리그라피 생성
```http
POST /api/generate_calligraphy
Content-Type: application/json

{
  "text": "새해 대박!",
  "font_size": 600,
  "color_hex": "#FFD700",
  "style": "emboss"
}

Response:
  "image_base64": "..."
}
```

### 6. 상태 확인
```http
GET /status

Response:
{
  "backend": "✅ Running",
  "comfyui": "✅ Running",
  "models": {
    "flux_dev": "✅ Loaded",
    "sdxl": "✅ Ready"
  }
}
```

---

## 성능 정보 및 주의사항

### ⏱️ 처리 시간

| 작업 | 시간 | 비고 |
|------|------|------|
| **모델 로딩** | 2~3분 | 첫 실행/재시작 시 |
| **이미지 생성 (T2I)** | 2~3분 이상 | FLUX.1-dev 모델 |
| **이미지 편집 (I2I)** | 1.5~2분 | 변화 강도에 따라 다름 |
| **배경 제거** | 30초~1분 | BEN2 + Rembg |
| **3D 캘리그라피** | 1~2분 | SDXL ControlNet |
| **문구 생성** | 5~10초 | OpenAI API |

### 💾 메모리 요구사항

| 작업 | VRAM | 시스템 RAM |
|------|------|-----------|
| **기본 설정** | 8GB | 16GB |
| **FLUX + SDXL** | 16GB+ | 32GB |
| **모든 모델 로드** | 22GB+ | 64GB |

**현재 설정: 22GB GPU (NVIDIA RTX 4090 권장)**

### ⚠️ 제한 사항 및 주의사항

1. **ComfyUI 통합의 복잡성**
   - 초기에는 Diffusers 라이브러리 기반이었음
   - ComfyUI 도입으로 다중 모델 및 복잡한 워크플로우 관리
   - 일부 엣지 케이스에서 예기치 않은 동작 가능

2. **ComfyUI 통합의 장점**
   - ✅ 수십 개 모델을 한 곳에서 관리
   - ✅ 복잡한 워크플로우 시각화 & 디버깅
   - ✅ 고급 후처리 (Impact Pack, ControlNet 등)
   - ✅ 성능 최적화 (GGUF 양자화, VAE Tiling 등)
   - ✅ 커뮤니티 기반 노드 라이브러리

3. **알려진 이슈**
   - 고메모리 상황에서 GPU OOM 가능
   - Impact Pack 특정 버전과 호환성 문제
   - 일부 프롬프트에서 일관성 떨어질 수 있음

4. **권장 사항**
   - **타임아웃 설정**: 최소 600초 이상
   - **배치 작업**: 동시 요청 1개로 제한
   - **모니터링**: GPU 메모리 상태 주기적 확인
   - **유지보수**: 주기적인 모델 캐시 정리

### 🔧 최적화 팁

```bash
# CUDA 메모리 최적화
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# CPU Offload 활성화 (ComfyUI)
# → 자동으로 설정됨 (텍스트_overlay.py 참고)

# VAE Tiling 활성화
# → 자동으로 설정됨 (comfyui_workflows.py 참고)
```

---

## 📈 추후 개선 가능 사항

### 1. GPU 메모리 최적화

**현재 문제**:
- 여러 페이지의 기능을 연속 사용 시 GPU 메모리 부족 발생
- 각 모델 로드 시 GPU 메모리가 누적되어 최종 기능 실행 불가
- 예: 페이지 1-4 테스트 후 페이지 5 캘리그라피 실행 시 "CUDA out of memory" 발생

**개선 방안**:
- **모델 언로드 메커니즘**: 불필요한 모델을 자동으로 VRAM에서 제거
  ```python
  def unload_unused_models():
      """현재 페이지에 필요 없는 모델 언로드"""
      torch.cuda.empty_cache()
      model = None  # 참조 해제
  ```
- **페이지별 모델 관리**: 각 페이지 진입/이탈 시 필요한 모델만 로드
- **백그라운드 언로드**: 오래 사용하지 않은 모델 자동 언로드
- **메모리 모니터링**: GPU 메모리 사용량 추적 및 임계값 기반 자동 정리

### 2. ComfyUI 워크플로우 안정성 개선

**현재 문제**:
- 노드 연결 복잡도 증가로 인한 오류 가능성
- 입력 이미지 노드 ID 불일치 (e.g., 라인 11 vs 5) 같은 오류 발생
- 워크플로우 작성 및 도입 과정에서 검증 미흡

**개선 방안**:
- **워크플로우 검증 시스템**: 실행 전 워크플로우 구조 자동 검증
  ```python
  def validate_workflow(workflow: Dict) -> Tuple[bool, List[str]]:
      """
      워크플로우 검증 및 오류 목록 반환
      - 모든 노드 ID 존재 확인
      - 노드 간 연결 유효성 확인
      - 입력/출력 타입 호환성 확인
      """
      errors = []
      # 검증 로직
      return len(errors) == 0, errors
  ```
- **단위 테스트**: 각 워크플로우 모드별 독립적 테스트
- **Visual 편집기 도입**: ComfyUI 웹 인터페이스에서 직접 검증
- **버전 관리**: 워크플로우 변경 사항 기록 및 롤백 가능

### 3. extra_model_paths.yaml 활용 개선

**현재 문제**:
- 모델 경로가 코드에 하드코딩되어 있음
- `extra_model_paths.yaml` 설정 미흡
- 모델 디렉토리 변경 시 여러 곳을 수정해야 함

**개선 방안**:
- **중앙 집중식 설정**: 모든 모델 경로를 `extra_model_paths.yaml`에서 관리
  ```yaml
  # extra_model_paths.yaml
  comfyui:
    - base_path: "/home/shared"
      models:
        checkpoints:
          - "*.gguf"
          - "*.safetensors"
        vae:
          - "ae.safetensors"
        clip:
          - "clip_l.safetensors"
          - "t5-v1_1-xxl-encoder-Q8_0.gguf"
  ```
- **동적 경로 로딩**: 실행 시 YAML에서 경로 읽기
  ```python
  def load_model_paths_from_yaml(yaml_path: str) -> Dict:
      with open(yaml_path, 'r') as f:
          config = yaml.safe_load(f)
      return config
  ```
- **경로 검증**: 모델 파일 존재 여부 자동 확인
- **환경별 설정**: 로컬/프로덕션 환경별 다른 경로 설정

### 4. 에러 처리 및 자동 복구

**현재 문제**:
- 메모리 부족 오류 발생 시 자동 복구 없음
- 사용자에게 명확한 오류 해결 방법 제시 안 함
- 일부 오류는 로깅만 되고 사용자에게 알려지지 않음

**개선 방안**:
- **자동 재시도**: 메모리 오류 발생 시 모델 언로드 후 재시도
  ```python
  def with_auto_retry(func):
      """메모리 오류 발생 시 자동 재시도"""
      def wrapper(*args, **kwargs):
          try:
              return func(*args, **kwargs)
          except torch.cuda.OutOfMemoryError as e:
              logger.warning("메모리 부족, 재시도...")
              torch.cuda.empty_cache()
              return func(*args, **kwargs)
      return wrapper
  ```
- **사용자 피드백**: 오류 발생 시 구체적인 해결 단계 제시
- **타임아웃 처리**: 길게 실행되는 작업의 타임아웃 및 재시도
- **로그 상세화**: 디버깅 용이한 구조화된 로깅

### 5. 성능 측정 및 최적화

**개선 방안**:
- **처리 시간 추적**: 각 기능별 소요 시간 로깅
  ```python
  @timer_decorator
  def generate_t2i_core(...):
      # 실행 시간이 자동으로 기록됨
      pass
  ```
- **메모리 프로파일링**: GPU/CPU 메모리 사용량 기록
- **병목 지점 분석**: 느린 작업 식별 및 최적화
- **성능 대시보드**: 실시간 성능 모니터링 (선택사항)

---

## ComfyUI 통합

### 왜 ComfyUI?

초기 프로토타입에서 Diffusers 라이브러리를 사용했지만, 다음 이유로 ComfyUI로 마이그레이션:

1. **모델 관리 간편화**: 10+ 모델을 통합 관리
2. **워크플로우 복잡성 해결**: 시각적 노드 그래프 지원
3. **커뮤니티 생태계**: Impact Pack, ControlNet 등 사용 가능
4. **성능 최적화**: GGUF 양자화, 동적 메모리 관리

### ComfyUI 워크플로우

```
src/backend/comfyui_workflows.py
├─ get_flux_t2i_workflow() - T2I 기본 흐름
├─ get_flux_i2i_workflow() - I2I 기본 흐름
├─ get_workflow_template(experiment_id)
│  ├─ portrait_mode - 인물 편집
│  ├─ product_mode - 제품 편집
│  └─ hybrid_mode - 고급 편집
├─ get_flux_fill_mode_workflow() - 배경 채우기
└─ update_workflow_inputs() - 런타임 파라미터 적용
```

### 커스텀 노드

| 노드 | 출처 | 용도 |
|------|------|------|
| UnetLoaderGGUF | ComfyUI | GGUF 모델 로드 |
| DualCLIPLoaderGGUF | ComfyUI | 멀티 CLIP 로드 |
| ControlNetLoader | ComfyUI | ControlNet 로드 |
| BackgroundEraseNetwork | 커스텀 | BEN2 배경 제거 |
| ControlNetApplyAdvanced | ComfyUI | 깊이 제어 적용 |
| KSampler | ComfyUI | 샘플링 엔진 |
| Impact Pack | 커뮤니티 | YOLO+SAM 후처리 |

---

## 프로젝트 구조

```
Ad_Content_Creation_Service_Team3/
├── README.md                          # 메인 문서
├── requirements.txt                   # Python 의존성
├── .env.example                       # 환경변수 템플릿
├── scripts/
│   ├── start_all.sh                   # 모든 서비스 시작
│   ├── stop_all.sh                    # 모든 서비스 중지
│   └── deploy.sh                      # 배포 스크립트
├── src/
│   ├── frontend/
│   │   ├── app.py                     # Streamlit 메인
│   │   ├── frontend_config.yaml       # UI 설정
│   │   └── utils.py                   # 유틸리티
│   └── backend/
│       ├── main.py                    # FastAPI 앱
│       ├── services.py                # 비즈니스 로직
│       ├── comfyui_client.py          # ComfyUI API 클라이언트
│       ├── comfyui_workflows.py       # 워크플로우 정의
│       ├── text_overlay.py            # 3D 캘리그라피
│       ├── post_processor.py          # 후처리
│       └── exceptions.py              # 예외 정의
├── comfyui/                           # ComfyUI 서브모듈
│   ├── main.py
│   ├── custom_nodes/                  # 커스텀 노드들
│   └── models/                        # 모델 저장소
├── configs/
│   ├── image_editing_config.yaml      # 이미지 편집 설정
│   └── test_flux_gcp.yaml             # 테스트 설정
├── docs/                              # 상세 문서
│   ├── COMFYUI_INTEGRATION.md         # ComfyUI 통합 가이드
│   ├── IMAGE_EDITING_GUIDE.md         # 이미지 편집 가이드
│   └── env_setup_guide.md             # 설치 가이드
├── logs/                              # 실행 로그
│   ├── uvicorn.log
│   ├── comfyui.log
│   └── streamlit.log
└── cache/                             # 모델 캐시
    └── hf_models/
```

---

## FAQ

### Q1: 첫 실행이 너무 오래 걸려요
**A**: 모델을 처음 다운로드하고 로드할 때 2~3분 소요됩니다. 이는 정상입니다. 이후 요청은 더 빠릅니다.

### Q2: GPU 메모리 부족 오류가 발생합니다
**A**: 다음을 시도해보세요:
```bash
# 1. 환경변수 설정
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# 2. 서비스 재시작
bash scripts/restart_all.sh

# 3. 캐시 정리
python -c "import torch; torch.cuda.empty_cache()"
```

### Q3: 이미지 품질이 낮아요
**A**: 다음을 확인하세요:
- **Steps 증가**: 기본 28 → 35~40으로 증가
- **Guidance Scale 조정**: 3.5 → 5.0~7.5
- **프롬프트 상세화**: 더 구체적인 설명 추가

### Q4: API 응답이 느립니다
**A**: 모델 로드 시간일 수 있습니다. 로그를 확인하세요:
```bash
tail -f logs/uvicorn.log
tail -f logs/comfyui.log
```

### Q5: ComfyUI vs Diffusers?
**A**: 
- **ComfyUI**: 복잡한 워크플로우, 다중 모델, 최적화
- **Diffusers**: 간단한 구현, 빠른 프로토타입

현재 프로젝트는 **ComfyUI 기반**입니다.

### Q6: 자체 모델을 추가할 수 있나요?
**A**: 네! `comfyui_workflows.py`에서 새 워크플로우를 정의하고, `render_image_editing_experiment_page()`에서 UI를 추가하면 됩니다.

### Q7: 배포는 어떻게 하나요?
**A**: 다음 옵션을 제공합니다:
- **로컬**: `bash scripts/start_all.sh`
- **Docker**: `docker-compose up` (제공 예정)
- **GCP/AWS**: 클라우드 배포 가이드 참고 (docs/GCP_VM_WEB_GUIDE.md)

---

## 라이선스 및 기여

### 라이선스
[MIT License](LICENSE)

### 기여 가이드
1. Fork 및 Clone
2. Feature 브랜치 생성
3. 변경사항 커밋
4. Pull Request 제출

---

## 참고 자료

### 핵심 문서
- [ComfyUI 통합 가이드](docs/COMFYUI_INTEGRATION.md)
- [이미지 편집 시스템](docs/IMAGE_EDITING_SYSTEM.md)
- [프롬프트 최적화](docs/PROMPT_OPTIMIZATION.md)
- [환경 설정 가이드](docs/env_setup_guide.md)

### 모델 정보
- **FLUX.1-dev**: https://huggingface.co/black-forest-labs/FLUX.1-dev
- **SDXL Base**: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
- **ControlNet Depth**: https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0-small
- **BEN2**: https://huggingface.co/SalesforceIEG/BEN_base

### 관련 프로젝트
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- [Impact Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack)
- [Rembg](https://github.com/danielgatis/rembg)

---

## 기술 지원

### 문제 신고
GitHub Issues에서 문제를 신고해주세요.

### 연락처
- 📧 이메일: team3@example.com
- 💬 슬랙: #project-team3

---

## 변경 이력

### v1.0.1 (2025-12-03)
- ✅ I2I 입력 이미지 노드 ID 버그 수정 (노드 11 → 5)
- ✅ 워크플로우별 입력 노드 ID 함수 개선
- ✅ 페이지 3 I2I payload에 model_name 추가
- ✅ 디버깅 로그 및 메모리 추적 개선
- ✅ Phase 표현 제거 및 추후 개선 사항 문서화

### v1.0.0 (2025-12-03)
- ✅ 프로젝트 리브랜딩: 헬스케어 → 소상공인
- ✅ 페이지 1 UI 개선: selectbox → text_input (서비스 종류)
- ✅ 가게 이름 입력 필드 추가
- ✅ ComfyUI 배경 제거 도입
- ✅ 3D 캘리그라피 완성
- ✅ Impact Pack 호환성 수정
- ✅ README.md 완전 작성

---

**Made with ❤️ for 소상공인**

마지막 업데이트: 2025년 12월 3일
