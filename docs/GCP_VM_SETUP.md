# GCP VM FLUX 테스트 가이드

GCP VM에서 FLUX.1-dev 모델을 사용하여 이미지 생성 테스트를 진행하는 가이드입니다.

---

## 📋 사전 준비

### 1. GCP VM 환경
- **GPU**: NVIDIA L4 (23GB)
- **CUDA**: 13.0
- **모델 위치**: `/home/shared/FLUX.1-dev`

---

## 🚀 설치 및 설정

### Step 1: SSH 접속

```bash
ssh spai0310@lucky-team3
```

### Step 2: Python 및 uv 설치

```bash
# Python 3.11+ 설치
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# 확인
python3 --version
uv --version
```

### Step 3: 프로젝트 클론 및 브랜치 체크아웃

```bash
# 프로젝트 디렉토리로 이동
cd ~/Ad_Content_Creation_Service_Team3

# 최신 리모트 정보 가져오기
git fetch origin

# mscho 브랜치로 체크아웃
git checkout mscho

# 최신 코드 받기
git pull origin mscho
```

### Step 4: 의존성 설치

```bash
# 가상환경 생성
uv venv

# 의존성 설치
uv pip install -e .

# PyTorch CUDA 12.4 버전 설치 (CUDA 13.0과 호환)
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# 확인
uv run python -c "import torch; print(torch.cuda.is_available())"
# True가 나와야 함
```

### Step 5: 모델 파일 전송 (로컬 서버 → GCP VM)

**로컬 서버에서 실행:**

```bash
# FLUX UNET 모델들
rsync -avzP -e "ssh -p 22" /mnt/data4/models/flux1-dev-Q8_0.gguf spai0310@34.70.229.116:/home/shared/
rsync -avzP -e "ssh -p 22" /mnt/data4/models/flux1-dev-Q4_0.gguf spai0310@34.70.229.116:/home/shared/
rsync -avzP -e "ssh -p 22" /mnt/data4/models/flux-fill/FLUX.1-Fill-dev-Q8_0.gguf spai0310@34.70.229.116:/home/shared/
rsync -avzP -e "ssh -p 22" /mnt/data4/models/qwen-image-edit/Qwen-Image-Edit-2509-Q8_0.gguf spai0310@34.70.229.116:/home/shared/

# CLIP 및 텍스트 인코더
rsync -avzP -e "ssh -p 22" /mnt/data4/models/clip/t5-v1_1-xxl-encoder-Q8_0.gguf spai0310@34.70.229.116:/home/shared/
rsync -avzP -e "ssh -p 22" /mnt/data4/models/clip/mmproj-Qwen2.5-VL-7B-Instruct-Q8_0.gguf spai0310@34.70.229.116:/home/shared/

# VAE
rsync -avzP -e "ssh -p 22" /mnt/data4/models/models--diffusers--FLUX.1-dev-bnb-4bit/blobs/f5b59a26851551b67ae1fe58d32e76486e1e812def4696a4bea97f16604d40a3 spai0310@34.70.229.116:/home/shared/ae.safetensors
```

**전송 완료 후 GCP VM에서 확인:**

```bash
ls -lh /home/shared/
```

### Step 6: ComfyUI 모델 경로 설정

**GCP VM에서 실행:**

```bash
cd ~/Ad_Content_Creation_Service_Team3/comfyui

# extra_model_paths.yaml 파일 수정
nano extra_model_paths.yaml
```

**다음 내용 추가:**

```yaml
# ComfyUI 추가 모델 경로 설정

# 로컬 개발 환경
local:
  base_path: /mnt/data4/models/
  checkpoints: ./
  vae: vae/
  loras: loras/
  upscale_models: upscale_models/
  embeddings: embeddings/
  controlnet: controlnet/
  clip: clip/
  diffusers: ./
  unet: ./

# GCP VM 환경
gcp:
  base_path: /home/shared/
  checkpoints: ./
  vae: ./
  clip: ./
  unet: ./
```

저장하고 종료 (Ctrl+X, Y, Enter)

---

## 🎨 이미지 생성 테스트

### 기본 실행

```bash
cd ~/Ad_Content_Creation_Service_Team3

# GCP VM 기본 설정으로 실행
uv run python scripts/test_flux_gcp.py
```

### 설정 파일 수정

프롬프트나 파라미터를 바꾸려면:

```bash
# 설정 파일 수정
nano configs/test_flux_gcp.yaml

# 수정 후 실행
uv run python scripts/test_flux_gcp.py --config configs/test_flux_gcp.yaml
```

### 특정 시나리오만 실행

```bash
# exp01_basic_test만 실행
uv run python scripts/test_flux_gcp.py --scenario exp01_basic_test
```

---

## 📁 출력 결과

생성된 이미지는 다음 위치에 저장됩니다:

```
outputs/flux_gcp/YYYYMMDD_HHMMSS/
  ├── exp01_basic_test_00.png
  ├── exp01_basic_test_metadata.yaml
  ├── exp02_hand_focus_00.png
  ├── exp02_hand_focus_metadata.yaml
  └── test_results.yaml
```

---

## ⚙️ 설정 파라미터 설명

### configs/test_flux_gcp.yaml

```yaml
# 모델 설정
model:
  name: "flux-dev-gcp"  # GCP VM 모델명
  path: "/home/shared/FLUX.1-dev"

# 메모리 최적화
memory_optimization:
  enable_sequential_cpu_offload: true  # 메모리 70% 절약
  enable_vae_tiling: true              # 고해상도 지원
  enable_vae_slicing: true             # 추가 메모리 절약
  dtype: "bfloat16"                    # FLUX 최적화 타입

# 테스트 시나리오
test_scenarios:
  - name: "exp01_basic_test"
    enabled: true
    prompt: "이미지 생성 프롬프트"
    width: 1024
    height: 1024
    num_inference_steps: 28      # 생성 반복 횟수 (높을수록 정교)
    guidance_scale: 3.5          # 프롬프트 강도 (3.5 권장)
    num_images: 2                # 생성할 이미지 개수
    seed: 42                     # 랜덤 시드 (같으면 동일 이미지)
```

### 파라미터 설명

- **num_inference_steps**: 생성 반복 횟수 (28 권장, 높을수록 정교하지만 느림)
- **guidance_scale**: 프롬프트를 얼마나 따를지 (3.5 권장)
- **seed**: 재현성 (같은 값 = 같은 이미지, null = 랜덤)

---

## 🔧 문제 해결

### 1. CUDA 메모리 부족

```yaml
# configs/test_flux_gcp.yaml 수정
memory_optimization:
  enable_sequential_cpu_offload: true  # 이미 활성화됨
  use_8bit: true  # 추가 메모리 절약 (느려짐)
```

### 2. 모델 로딩 실패

```bash
# 모델 경로 확인
ls -la /home/shared/FLUX.1-dev

# 없으면 다시 복사
scp -r /mnt/data4/models/FLUX.1-dev ubuntu@GCP_IP:/home/shared/
```

### 3. GPU 인식 안됨

```bash
# GPU 확인
nvidia-smi

# PyTorch CUDA 확인
uv run python -c "import torch; print(torch.cuda.is_available())"
```

---

## 📊 예상 성능

- **GPU**: NVIDIA L4 (23GB)
- **이미지 크기**: 1024x1024
- **Steps**: 28
- **예상 시간**: 약 30-60초/이미지
- **메모리 사용량**: 약 16-18GB

---

## 📝 참고

- ai-ad 프로젝트의 메모리 최적화 기법 적용
- Sequential CPU offload로 메모리 70% 절약
- bfloat16으로 FLUX 최적화
- VAE tiling/slicing으로 고해상도 지원
