# 모델 설정 가이드

## 📁 파일 구조

```
src/backend/
├── model_config.yaml      # 모델 설정 파일 (여기만 수정!)
├── model_registry.py      # 설정 로더
├── model_loader.py        # 모델 로딩 로직
├── services.py            # AI 서비스 레이어
└── main.py                # FastAPI 앱
```

---

## 🚀 빠른 시작

### 1. 기본 설정 (SDXL 사용)

**별도 설정 없이 바로 작동합니다!**

```bash
# 백엔드 실행
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000

# 프론트엔드 실행
streamlit run src/frontend/app.py
```

기본적으로 `sdxl` 모델이 폴백으로 자동 로드됩니다.

---

### 2. FLUX 모델 사용 (고품질)

#### 2-1. Hugging Face 인증

```bash
pip install -U huggingface_hub
huggingface-cli login
# 토큰 입력: https://huggingface.co/settings/tokens
```

#### 2-2. 모델 접근 권한 획득

1. https://huggingface.co/black-forest-labs/FLUX.1-schnell 방문
2. "Agree and access repository" 클릭

#### 2-3. 환경변수 설정 (선택)

`.env` 파일 생성:

```bash
PRIMARY_MODEL=flux-schnell
ENABLE_FALLBACK=true
```

또는 `model_config.yaml`에서 `runtime.primary_model` 수정

---

## 🔧 새로운 모델 추가하기

### 예시: Stable Diffusion 3 추가

`model_config.yaml`에 추가:

```yaml
models:
  sd3-medium:
    id: "stabilityai/stable-diffusion-3-medium-diffusers"
    type: "sd3"
    requires_auth: true  # HF 인증 필요 시
    params:
      default_steps: 28
      max_steps: 50
      use_negative_prompt: true
      guidance_scale: 7.0
      supports_i2i: true
      max_tokens: 77
      default_size: [1024, 1024]
      max_size: [2048, 2048]
      negative_prompt: "low quality, blurry"
    description: "SD3 Medium - 텍스트 렌더링 개선"

runtime:
  primary_model: "sd3-medium"  # 여기만 변경!
  fallback_models:
    - "sdxl"
```

**끝! 코드 수정 없이 새 모델 사용 가능**

---

## 🎛️ 고급 설정

### 메모리 최적화

`model_config.yaml`의 `runtime.memory` 섹션:

```yaml
runtime:
  memory:
    enable_cpu_offload: false    # CPU 오프로드 (메모리 부족 시)
    enable_attention_slicing: true   # 어텐션 슬라이싱
    enable_vae_slicing: true         # VAE 슬라이싱
    use_8bit: false                  # 8비트 양자화
```

**메모리 부족 시 권장 설정:**
- `use_8bit: true` → 메모리 50% 절약 (약간 느림)
- `enable_cpu_offload: true` → 메모리 70% 절약 (매우 느림)

---

### 프롬프트 최적화 설정

```yaml
runtime:
  prompt_optimization:
    enabled: true                # GPT 프롬프트 최적화
    translate_korean: true       # 한국어 자동 번역
    max_length_by_model: true    # 모델별 토큰 제한 준수
```

---

## 🌐 환경변수로 오버라이드

`.env` 파일 또는 시스템 환경변수:

```bash
# 기본 모델 지정
PRIMARY_MODEL=flux-schnell

# 폴백 활성화/비활성화
ENABLE_FALLBACK=true

# 캐시 디렉토리 변경
HF_CACHE_DIR=/custom/path

# OpenAI API Key
OPENAI_API_KEY=sk-...
```

환경변수가 `model_config.yaml` 설정보다 우선됩니다.

---

## 📊 API 엔드포인트

### 모델 정보 조회

```bash
curl http://localhost:8000/models
```

**응답 예시:**
```json
{
  "models": {
    "flux-schnell": {
      "id": "black-forest-labs/FLUX.1-schnell",
      "type": "flux",
      "requires_auth": true,
      "default_steps": 4,
      "max_tokens": 512,
      "supports_i2i": true
    },
    "sdxl": { ... }
  },
  "current": "sdxl",
  "primary": "flux-schnell",
  "fallback_chain": ["sdxl", "playground"]
}
```

### 서비스 상태 확인

```bash
curl http://localhost:8000/status
```

---

## 🔥 추천 모델

| 모델 | 용도 | 인증 | 속도 | 품질 |
|------|------|------|------|------|
| **flux-schnell** | 일반 사용 | ✅ 필요 | ⚡ 빠름 | 🌟🌟🌟🌟 |
| **sdxl** | 안정적 | ❌ 불필요 | 🐢 보통 | 🌟🌟🌟 |
| **playground** | 미적 품질 | ❌ 불필요 | 🐢 보통 | 🌟🌟🌟🌟 |
| **flux-dev** | 최고 품질 | ✅ 필요 | 🐌 느림 | 🌟🌟🌟🌟🌟 |

---

## 🐛 문제 해결

### 1. "이미지 파이프라인이 초기화되지 않았습니다"

**원인:** 모든 모델 로딩 실패

**해결:**
```bash
# 백엔드 로그 확인
# 실패한 모델과 에러 메시지 확인 후:

# 옵션 A: SDXL로 폴백 강제
PRIMARY_MODEL=sdxl

# 옵션 B: 인증 문제면
huggingface-cli login
```

### 2. GPU 메모리 부족

**해결:**
`model_config.yaml`에서:
```yaml
runtime:
  memory:
    use_8bit: true
```

또는 더 작은 모델 사용: `sdxl` or `playground`

### 3. 프롬프트 번역 안됨

**확인:**
- `.env`에 `OPENAI_API_KEY` 설정 여부
- `model_config.yaml`에서 `prompt_optimization.enabled: true` 확인

---

## 📝 커스텀 모델 타입 추가

`model_loader.py`의 `_load_model_by_type` 메서드 수정:

```python
elif model_type == "my_custom_type":
    from my_custom_library import CustomPipeline
    t2i = CustomPipeline.from_pretrained(model_id, **load_kwargs)
    i2i = CustomPipeline.from_pretrained(model_id, **load_kwargs)
```

---

## 🎯 결론

**하드코딩 제거 완료!**
- ✅ `model_config.yaml` 하나로 모든 모델 관리
- ✅ 코드 수정 없이 모델 교체
- ✅ 환경변수로 동적 설정
- ✅ 자동 폴백 체인
- ✅ 메모리 최적화 토글

**모델 추가는 이제 3단계:**
1. `model_config.yaml`에 모델 정보 추가
2. `runtime.primary_model` 변경
3. 재시작