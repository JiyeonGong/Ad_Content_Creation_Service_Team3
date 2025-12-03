# env.example
# 이 파일을 복사하여 .env 파일을 만들고 실제 값으로 수정하세요
# 사용법: cp env.example .env

# ============================================================
# OpenAI API 설정 (필수)
# ============================================================
# https://platform.openai.com/api-keys 에서 생성
OPENAI_API_KEY=sk-proj-your-key-here

# ============================================================
# 이미지 생성 모델 설정
# ============================================================
# 기본 사용할 모델 (model_config.yaml의 모델 이름)
# 옵션: flux-schnell, flux-dev, sdxl, sd3, kandinsky, playground
PRIMARY_MODEL=flux-schnell

# 폴백 활성화 여부
ENABLE_FALLBACK=true

# ============================================================
# Hugging Face 인증 (FLUX, SD3 등 gated 모델 사용 시 필요)
# ============================================================
# 방법 1: 환경변수 설정 (이 방법 사용 시)
# HF_TOKEN=hf_your_token_here

# 방법 2: CLI 로그인 (권장)
# 터미널에서: huggingface-cli login
# 토큰: https://huggingface.co/settings/tokens

# ============================================================
# API 서버 설정
# ============================================================
# FastAPI 백엔드 주소 (프론트엔드에서 사용)
API_BASE_URL=http://localhost:8000

# API 타임아웃 (초)
API_TIMEOUT=180

# GPU OOM 시 재시도 횟수
API_RETRY_ATTEMPTS=2

# ============================================================
# 캐시 디렉토리 설정 (선택)
# ============================================================
# Hugging Face 모델 캐시 위치 (기본: ./cache/hf_models)
# HF_CACHE_DIR=/custom/path/to/cache

# ============================================================
# 메모리 최적화 설정 (선택)
# ============================================================
# 8비트 양자화 사용 (메모리 50% 절약, 약간 느림)
# USE_8BIT=false

# CPU 오프로드 (메모리 70% 절약, 매우 느림)
# ENABLE_CPU_OFFLOAD=false

# 어텐션 슬라이싱 (메모리 절약)
# ENABLE_ATTENTION_SLICING=true

# VAE 슬라이싱 (메모리 절약)
# ENABLE_VAE_SLICING=true

# ============================================================
# 프롬프트 최적화 설정 (선택)
# ============================================================
# 한국어 자동 번역 활성화
# TRANSLATE_KOREAN=true

# 프롬프트 최적화 활성화
# PROMPT_OPTIMIZATION_ENABLED=true

# ============================================================
# 개발 모드 설정 (선택)
# ============================================================
# 디버그 모드
# DEBUG=false

# 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
# LOG_LEVEL=INFO

# ============================================================
# 배포 환경별 설정 예시
# ============================================================

# 개발 환경
# PRIMARY_MODEL=sdxl
# ENABLE_FALLBACK=true
# DEBUG=true

# 프로덕션 환경 (고성능)
# PRIMARY_MODEL=flux-schnell
# USE_8BIT=false
# ENABLE_FALLBACK=true

# 프로덕션 환경 (저메모리)
# PRIMARY_MODEL=sdxl
# USE_8BIT=true
# ENABLE_CPU_OFFLOAD=false
# ENABLE_ATTENTION_SLICING=true
# ENABLE_VAE_SLICING=true