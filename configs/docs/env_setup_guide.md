# .env 파일 설정 가이드

## 🚀 빠른 시작 (3분)

### 1단계: .env 파일 생성

```bash
# 프로젝트 루트 디렉토리에서
cp .env.example .env
```

또는 직접 생성:
```bash
touch .env
```

### 2단계: 필수 설정 입력

`.env` 파일을 열고 최소한 이것만 설정:

```bash
# 필수!
OPENAI_API_KEY=sk-proj-여기에-실제-키-입력

# 권장
PRIMARY_MODEL=sdxl
ENABLE_FALLBACK=true
```

### 3단계: 실행

```bash
# 백엔드
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000

# 프론트엔드
streamlit run src/frontend/app.py
```

**끝!** 이제 작동합니다. 🎉

---

## 📋 상황별 설정 가이드

### 시나리오 1: 처음 시작 (SDXL 사용)

```bash
# .env
OPENAI_API_KEY=sk-proj-your-key

# 나머지는 기본값 사용
# PRIMARY_MODEL은 설정 안하면 자동으로 SDXL 폴백
```

**장점:**
- ✅ 인증 불필요
- ✅ 즉시 작동
- ✅ 안정적

---

### 시나리오 2: FLUX 사용 (최고 품질)

#### 2-1. Hugging Face 계정 생성 및 토큰 발급

1. https://huggingface.co/ 회원가입
2. https://huggingface.co/settings/tokens 방문
3. "New token" 클릭 → "Read" 권한 선택 → 생성
4. 토큰 복사 (예: `hf_xxxxx...`)

#### 2-2. 모델 접근 권한 획득

1. https://huggingface.co/black-forest-labs/FLUX.1-schnell 방문
2. "Agree and access repository" 클릭

#### 2-3. 인증 방법 (둘 중 하나 선택)

**방법 A: CLI 로그인 (권장)**
```bash
pip install -U huggingface_hub
huggingface-cli login
# 토큰 입력: hf_xxxxx...
```

**방법 B: 환경변수**
```bash
# .env
OPENAI_API_KEY=sk-proj-your-key
PRIMARY_MODEL=flux-schnell
ENABLE_FALLBACK=true
HF_TOKEN=hf_your_token_here
```

---

### 시나리오 3: 메모리 부족 (GPU 8GB 이하)

```bash
# .env
OPENAI_API_KEY=sk-proj-your-key
PRIMARY_MODEL=sdxl
USE_8BIT=true
ENABLE_ATTENTION_SLICING=true
ENABLE_VAE_SLICING=true
```

또는 `model_config.yaml`에서:
```yaml
runtime:
  memory:
    use_8bit: true
    enable_attention_slicing: true
    enable_vae_slicing: true
```

**효과:**
- 메모리 사용량 50% 감소
- 생성 속도 20% 감소

---

### 시나리오 4: CPU만 사용 (GPU 없음)

```bash
# .env
OPENAI_API_KEY=sk-proj-your-key
PRIMARY_MODEL=sdxl
ENABLE_FALLBACK=false  # CPU 폴백 방지
```

**주의:**
- 이미지 생성이 매우 느림 (5-10분)
- 작은 해상도 권장 (512x512)

---

### 시나리오 5: 프로덕션 배포

```bash
# .env (프로덕션)
OPENAI_API_KEY=sk-prod-production-key
PRIMARY_MODEL=flux-schnell
ENABLE_FALLBACK=true
API_BASE_URL=https://api.yourdomain.com
USE_8BIT=false  # 고성능 모드
DEBUG=false
LOG_LEVEL=WARNING
```

---

## 🔧 환경변수 상세 설명

### 필수 변수

#### `OPENAI_API_KEY`
- **필수도**: ⭐⭐⭐ 필수
- **설명**: OpenAI API 키 (문구 생성용)
- **획득**: https://platform.openai.com/api-keys
- **예시**: `sk-proj-abc123...`
- **없으면**: 문구 생성 기능 불가

---

### 모델 설정

#### `PRIMARY_MODEL`
- **필수도**: ⭐⭐ 권장
- **설명**: 기본 사용 모델
- **옵션**: 
  - `flux-schnell` (빠름, 고품질, 인증 필요)
  - `flux-dev` (느림, 최고 품질, 인증 필요)
  - `sdxl` (안정적, 인증 불필요) ← 기본값
  - `playground` (미적 품질)
  - `sd3` (텍스트 렌더링 개선)
  - `kandinsky` (다국어)
- **기본값**: `sdxl` (설정 안하면 자동 폴백)

#### `ENABLE_FALLBACK`
- **필수도**: ⭐ 선택
- **설명**: Primary 모델 실패 시 자동 폴백
- **값**: `true` / `false`
- **기본값**: `true`
- **권장**: `true` (안정성)

---

### Hugging Face 인증

#### `HF_TOKEN`
- **필수도**: ⭐⭐ (FLUX, SD3 사용 시 필요)
- **설명**: Hugging Face API 토큰
- **획득**: https://huggingface.co/settings/tokens
- **예시**: `hf_abc123...`
- **대안**: `huggingface-cli login` 사용 (권장)

---

### API 서버

#### `API_BASE_URL`
- **필수도**: ⭐ 선택
- **설명**: FastAPI 백엔드 주소
- **기본값**: `http://localhost:8000`
- **프로덕션 예시**: `https://api.yourdomain.com`

#### `API_TIMEOUT`
- **필수도**: ⭐ 선택
- **설명**: API 타임아웃 (초)
- **기본값**: `180`
- **권장**: `180` (이미지 생성은 시간 소요)

#### `API_RETRY_ATTEMPTS`
- **필수도**: ⭐ 선택
- **설명**: GPU OOM 시 재시도 횟수
- **기본값**: `2`

---

### 메모리 최적화

#### `USE_8BIT`
- **필수도**: ⭐ 선택
- **설명**: 8비트 양자화 (메모리 50% 절약)
- **값**: `true` / `false`
- **기본값**: `false`
- **권장**: GPU 메모리 < 12GB 시 `true`

#### `ENABLE_CPU_OFFLOAD`
- **필수도**: ⭐ 선택
- **설명**: CPU로 일부 작업 오프로드
- **값**: `true` / `false`
- **기본값**: `false`
- **주의**: 매우 느려짐

#### `ENABLE_ATTENTION_SLICING`
- **필수도**: ⭐ 선택
- **설명**: 어텐션 슬라이싱 (메모리 절약)
- **값**: `true` / `false`
- **기본값**: `true`

#### `ENABLE_VAE_SLICING`
- **필수도**: ⭐ 선택
- **설명**: VAE 슬라이싱 (메모리 절약)
- **값**: `true` / `false`
- **기본값**: `true`

---

### 프롬프트 최적화

#### `TRANSLATE_KOREAN`
- **필수도**: ⭐ 선택
- **설명**: 한국어 프롬프트 자동 번역
- **값**: `true` / `false`
- **기본값**: `true`
- **권장**: `true` (SDXL 사용 시)

#### `PROMPT_OPTIMIZATION_ENABLED`
- **필수도**: ⭐ 선택
- **설명**: GPT로 프롬프트 최적화
- **값**: `true` / `false`
- **기본값**: `true`

---

## 🎯 우선순위 체계

환경변수는 설정 파일보다 우선합니다:

```
1. 환경변수 (.env 또는 시스템)     ← 최우선
2. model_config.yaml (백엔드)
3. frontend_config.yaml (프론트)
4. 코드 내 기본값                  ← 최하위
```

**예시:**
```yaml
# model_config.yaml
runtime:
  primary_model: "sdxl"
```

```bash
# .env
PRIMARY_MODEL=flux-schnell  # 이게 우선!
```

결과: `flux-schnell` 사용

---

## 🐛 문제 해결

### Q1: `.env` 파일이 인식 안됨

**확인사항:**
1. 파일 위치: 프로젝트 루트에 있어야 함
2. 파일명: `.env` (점 포함!)
3. 인코딩: UTF-8
4. 재시작: 서버 재시작 필수

**테스트:**
```python
# Python에서 확인
import os
from dotenv import load_dotenv

load_dotenv()
print(os.getenv("OPENAI_API_KEY"))  # None이 아니어야 함
```

### Q2: Hugging Face 인증 실패

**증상:**
```
401 Client Error: Unauthorized
```

**해결:**
```bash
# 방법 1: CLI 재로그인
huggingface-cli logout
huggingface-cli login

# 방법 2: 토큰 재확인
# https://huggingface.co/settings/tokens
# .env의 HF_TOKEN 업데이트
```

### Q3: 환경변수가 적용 안됨

**원인:** 서버가 이미 실행 중

**해결:**
```bash
# 서버 중단 (Ctrl+C)
# .env 수정
# 서버 재시작
uvicorn src.backend.main:app --reload
```

### Q4: GPU 메모리 부족

**에러:**
```
CUDA out of memory
```

**해결 1 (빠름):**
```bash
# .env에 추가
USE_8BIT=true
ENABLE_ATTENTION_SLICING=true
ENABLE_VAE_SLICING=true
```

**해결 2 (안전):**
```bash
# .env
PRIMARY_MODEL=sdxl  # 더 작은 모델로
```

---

## 📝 체크리스트

### 초기 설정
- [ ] `.env.example` 복사하여 `.env` 생성
- [ ] `OPENAI_API_KEY` 입력
- [ ] `PRIMARY_MODEL` 선택
- [ ] (FLUX 사용 시) Hugging Face 인증
- [ ] 서버 재시작

### 프로덕션 배포
- [ ] `.env`를 `.gitignore`에 추가 (보안!)
- [ ] 프로덕션 API 키 사용
- [ ] `DEBUG=false` 설정
- [ ] `API_BASE_URL` 수정
- [ ] HTTPS 사용

### 문제 발생 시
- [ ] `.env` 파일 위치 확인
- [ ] 서버 재시작
- [ ] 백엔드 로그 확인
- [ ] `/status` 엔드포인트 확인

---

## 🔒 보안 주의사항

### ⚠️ 절대 금지
```bash
# ❌ Git에 커밋하지 마세요!
git add .env

# ❌ 공개 저장소에 푸시 금지!
```

### ✅ 올바른 방법
```bash
# .gitignore에 추가
echo ".env" >> .gitignore

# 예시 파일만 공유
git add .env.example
```

### 🔐 민감 정보 관리
```bash
# 프로덕션: 환경변수로 관리
export OPENAI_API_KEY=sk-prod-...
export HF_TOKEN=hf_prod-...

# 또는 Docker secrets, AWS Secrets Manager 등 사용
```

---

## 🎓 팁

### 개발 vs 프로덕션 분리

**방법 1: 별도 파일**
```bash
.env.development
.env.production
```

```bash
# 개발 시
cp .env.development .env

# 배포 시
cp .env.production .env
```

**방법 2: 스크립트**
```bash
# start_dev.sh
export $(cat .env.development | xargs)
uvicorn src.backend.main:app --reload

# start_prod.sh
export $(cat .env.production | xargs)
uvicorn src.backend.main:app --host 0.0.0.0
```

---

## 📚 참고 자료

- OpenAI API Keys: https://platform.openai.com/api-keys
- Hugging Face Tokens: https://huggingface.co/settings/tokens
- FLUX 모델: https://huggingface.co/black-forest-labs/FLUX.1-schnell
- python-dotenv 문서: https://pypi.org/project/python-dotenv/

---

**이제 `.env` 파일을 완벽하게 설정할 수 있습니다!** 🎉
