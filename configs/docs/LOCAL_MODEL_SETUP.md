# 로컬 튜닝 모델 연결 가이드

## 🎯 상황

- **프로젝트 위치**: `/home/spai0323/Ad_Content_Creation_Service_Team3/`
- **코드 위치**: `src/frontend/`, `src/backend/`
- **튜닝 모델 위치**: `/home/shared/FLUX.1-dev`

---

## ✅ 설정 방법 (3단계)

### 1단계: 모델 경로 확인

```bash
# 모델 디렉토리 구조 확인
ls -la /home/shared/FLUX.1-dev

# 필수 파일 확인
# ✅ 있어야 하는 파일들:
# - model_index.json
# - scheduler/
# - text_encoder/
# - unet/ (또는 transformer/)
# - vae/
# - tokenizer/
```

**예상 구조:**
```
/home/shared/FLUX.1-dev/
├── model_index.json          # 필수!
├── scheduler/
│   └── scheduler_config.json
├── text_encoder/
│   ├── config.json
│   └── pytorch_model.bin
├── transformer/              # FLUX는 transformer 사용
│   ├── config.json
│   └── diffusion_pytorch_model.safetensors
├── vae/
│   ├── config.json
│   └── diffusion_pytorch_model.safetensors
└── tokenizer/
    ├── tokenizer_config.json
    └── ...
```

---

### 2단계: model_config.yaml 수정

**파일 위치**: `/home/spai0323/Ad_Content_Creation_Service_Team3/src/backend/model_config.yaml`

```yaml
models:
  # 🆕 팀 튜닝 모델 추가
  flux-dev-tuned:
    id: "/home/shared/FLUX.1-dev"  # 절대 경로!
    type: "flux"
    requires_auth: false  # 로컬이므로 인증 불필요
    params:
      default_steps: 20
      max_steps: 50
      use_negative_prompt: false
      guidance_scale: null
      supports_i2i: true
      max_tokens: 512
      default_size: [1024, 1024]
      max_size: [2048, 2048]
    description: "팀 튜닝 모델 - 헬스케어 특화"
  
  # 기존 모델들 (폴백용)
  sdxl:
    id: "stabilityai/stable-diffusion-xl-base-1.0"
    type: "sdxl"
    requires_auth: false
    # ... (기존 설정 유지)

runtime:
  primary_model: "flux-dev-tuned"  # 🎯 기본 모델로 설정!
  fallback_models:
    - "sdxl"  # 로컬 모델 실패 시 SDXL로 폴백
  enable_fallback: true
```

---

### 3단계: 실행 및 확인

```bash
# 프로젝트 디렉토리로 이동
cd /home/spai0323/Ad_Content_Creation_Service_Team3

# 백엔드 실행
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000

# 로그에서 확인
# ✅ 성공 시:
# 📦 모델 레지스트리 로드 완료: 6개 모델
# 🎯 Primary 모델 시도: flux-dev-tuned
# 🔄 1차 시도: /home/shared/FLUX.1-dev 로딩 중...
# ✅ flux-dev-tuned 로딩 성공!
```

---

## 🔧 고급 설정

### 환경변수로 오버라이드

```bash
# .env 파일
PRIMARY_MODEL=flux-dev-tuned

# 또는 명령줄에서
PRIMARY_MODEL=flux-dev-tuned uvicorn src.backend.main:app
```

### 여러 튜닝 모델 관리

```yaml
# model_config.yaml
models:
  flux-dev-tuned-v1:
    id: "/home/shared/FLUX.1-dev"
    type: "flux"
    description: "헬스케어 특화 v1"
  
  flux-dev-tuned-v2:
    id: "/home/shared/FLUX.1-dev-v2"
    type: "flux"
    description: "헬스케어 특화 v2 (최신)"
  
  flux-dev-tuned-fitness:
    id: "/home/shared/FLUX.1-dev-fitness"
    type: "flux"
    description: "피트니스 전용"

runtime:
  primary_model: "flux-dev-tuned-v2"  # 최신 버전 사용
```

---

## 🐛 문제 해결

### ❌ "No such file or directory: /home/shared/FLUX.1-dev"

**원인**: 경로가 잘못되었거나 권한 문제

**해결:**
```bash
# 1. 경로 확인
ls -la /home/shared/FLUX.1-dev

# 2. 권한 확인
# 현재 사용자가 읽기 권한이 있는지 확인
whoami
# 출력: spai0323

# 3. 권한 부여 (필요 시)
sudo chmod -R 755 /home/shared/FLUX.1-dev
# 또는
sudo chown -R spai0323:spai0323 /home/shared/FLUX.1-dev
```

### ❌ "model_index.json not found"

**원인**: 모델이 올바른 Diffusers 형식이 아님

**해결:**

모델이 단일 파일(.safetensors, .ckpt)인 경우 Diffusers 형식으로 변환 필요:

```python
# convert_to_diffusers.py
from diffusers import DiffusionPipeline

# 단일 파일 모델 로드 (예: .safetensors)
pipe = DiffusionPipeline.from_single_file(
    "/home/shared/FLUX.1-dev/model.safetensors",
    torch_dtype=torch.float16
)

# Diffusers 형식으로 저장
pipe.save_pretrained("/home/shared/FLUX.1-dev-converted")

# 이제 변환된 경로 사용
# id: "/home/shared/FLUX.1-dev-converted"
```

### ❌ 로딩은 되는데 생성 품질이 이상함

**원인**: 모델 타입이 잘못 설정됨

**해결:**
```yaml
# type을 정확히 지정
models:
  flux-dev-tuned:
    id: "/home/shared/FLUX.1-dev"
    type: "flux"  # 🎯 모델 아키텍처에 맞게!
    # SDXL 기반이면 "sdxl"
    # SD3 기반이면 "sd3"
```

### ⚠️ GPU 메모리 부족

**해결:**
```yaml
# model_config.yaml
runtime:
  memory:
    use_8bit: true  # 메모리 50% 절약
    enable_attention_slicing: true
    enable_vae_slicing: true
```

---

## 📊 로컬 vs HuggingFace 비교

| 항목 | 로컬 모델 | HuggingFace Hub |
|------|-----------|-----------------|
| **경로** | `/home/shared/...` | `"username/model"` |
| **인증** | 불필요 | 필요 (gated 모델) |
| **로딩 속도** | ⚡ 빠름 | 🐢 최초 다운로드 느림 |
| **디스크 사용** | 로컬 저장 필요 | 캐시에 자동 저장 |
| **버전 관리** | 수동 | 자동 (리포지토리) |
| **팀 공유** | 서버 경로 공유 | URL 공유 |

---

## 🎯 팀 워크플로우 권장

### 시나리오 1: 개발 중 (로컬 모델 사용)

```yaml
# model_config.yaml
runtime:
  primary_model: "flux-dev-tuned"  # 로컬 튜닝 모델
  fallback_models: ["sdxl"]
```

### 시나리오 2: 배포 (HuggingFace로 이전)

```bash
# 1. 로컬 모델을 HuggingFace에 업로드
huggingface-cli login
huggingface-cli upload your-org/flux-dev-tuned /home/shared/FLUX.1-dev

# 2. model_config.yaml 수정
models:
  flux-dev-tuned:
    id: "your-org/flux-dev-tuned"  # HF 경로로 변경
    type: "flux"
    requires_auth: true  # private 리포지토리면 필요
```

### 시나리오 3: 버전별 관리

```yaml
models:
  flux-tuned-dev:
    id: "/home/shared/FLUX.1-dev"
    description: "개발 버전"
  
  flux-tuned-staging:
    id: "/home/shared/FLUX.1-dev-staging"
    description: "스테이징 버전"
  
  flux-tuned-prod:
    id: "your-org/flux-tuned-v1.0"  # 프로덕션은 HF에
    description: "프로덕션 버전"

runtime:
  primary_model: "flux-tuned-dev"  # 환경별로 변경
```

---

## 📝 체크리스트

### 초기 설정
- [ ] 모델 경로 확인: `/home/shared/FLUX.1-dev`
- [ ] `model_index.json` 존재 확인
- [ ] 읽기 권한 확인
- [ ] `model_config.yaml` 수정
- [ ] `runtime.primary_model` 설정
- [ ] 백엔드 실행 및 로그 확인

### 문제 발생 시
- [ ] 경로 오타 확인
- [ ] 권한 문제 확인
- [ ] Diffusers 형식 확인
- [ ] 모델 타입(type) 확인
- [ ] 메모리 확인 (nvidia-smi)
- [ ] 폴백 모델 설정 확인

---

## 🚀 빠른 테스트

```bash
# 1. 프로젝트 디렉토리
cd /home/spai0323/Ad_Content_Creation_Service_Team3

# 2. model_config.yaml 확인
cat src/backend/model_config.yaml | grep -A 10 "flux-dev-tuned"

# 3. 백엔드 실행
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000

# 4. 다른 터미널에서 상태 확인
curl http://localhost:8000/status

# 5. 모델 정보 확인
curl http://localhost:8000/models | jq

# 6. 프론트엔드 실행
streamlit run src/frontend/app.py
```

---

## 💡 팁

### 1. 심볼릭 링크 활용

```bash
# 모델 경로가 길면 심볼릭 링크 생성
ln -s /home/shared/FLUX.1-dev /home/spai0323/models/flux-tuned

# model_config.yaml에서
id: "/home/spai0323/models/flux-tuned"
```

### 2. 환경변수로 경로 관리

```bash
# .env
LOCAL_MODEL_PATH=/home/shared/FLUX.1-dev
```

```yaml
# model_config.yaml에서 (주의: YAML은 환경변수 직접 지원 안함)
# 대신 Python에서 처리:
```

```python
# model_registry.py 수정
import os

# 환경변수 확장
model_id = config["id"]
if model_id.startswith("$"):
    env_var = model_id[1:]
    model_id = os.getenv(env_var, model_id)
```

### 3. 모델 검증 스크립트

```python
# validate_local_model.py
import os
from pathlib import Path

model_path = "/home/shared/FLUX.1-dev"

required_files = [
    "model_index.json",
    "scheduler/scheduler_config.json",
    "text_encoder/config.json",
]

print(f"🔍 모델 검증: {model_path}")
for file in required_files:
    full_path = Path(model_path) / file
    if full_path.exists():
        print(f"  ✅ {file}")
    else:
        print(f"  ❌ {file} (없음)")

# 실행: python validate_local_model.py
```

---

**이제 로컬 튜닝 모델을 완벽하게 연결할 수 있습니다!** 🎉

경로만 올바르게 설정하면 HuggingFace 모델과 동일하게 작동합니다.