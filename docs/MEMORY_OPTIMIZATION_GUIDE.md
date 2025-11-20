# 메모리 최적화 완벽 가이드

## 🎯 최적화 옵션 전체 목록

### 1️⃣ 기본 최적화 (항상 권장 ⭐)

```yaml
# model_config.yaml
runtime:
  memory:
    enable_vae_tiling: true           # VAE 타일링
    enable_vae_slicing: true          # VAE 슬라이싱
    enable_attention_slicing: true    # 어텐션 슬라이싱
```

**효과:**
- 메모리 절약: 30-40%
- 속도 영향: 거의 없음 (VAE 타일링은 0%)
- 안정성: 매우 높음
- **권장 대상:** 모든 사용자

---

### 2️⃣ 정밀도 최적화

#### Option A: bfloat16 (FLUX 권장 ⭐)

```yaml
runtime:
  memory:
    use_bfloat16: true
```

**특징:**
- FP16보다 안정적 (오버플로우 적음)
- FLUX 모델에 최적화
- 메모리 사용량 FP32의 50%
- NVIDIA Ampere 이상 권장 (RTX 30/40 시리즈)

#### Option B: 8비트 양자화

```yaml
runtime:
  memory:
    use_8bit: true
```

**효과:**
- 메모리 절약: 50%
- 속도 영향: 20-30% 느려짐
- 품질 영향: 약간 있음 (거의 눈에 안띔)
- **권장 대상:** GPU 메모리 < 8GB

---

### 3️⃣ CPU 오프로드 (최후의 수단 ⚠️)

#### Option A: Model CPU Offload (일반)

```yaml
runtime:
  memory:
    enable_cpu_offload: true
```

**효과:**
- 메모리 절약: 60-70%
- 속도 영향: 2-3배 느림
- **권장 대상:** GPU 메모리 < 6GB

#### Option B: Sequential CPU Offload (FLUX 전용)

```yaml
runtime:
  memory:
    enable_sequential_cpu_offload: true
```

**효과:**
- 메모리 절약: 70-80% (최대!)
- 속도 영향: 3-5배 느림
- FLUX 모델 전용
- **권장 대상:** GPU 메모리 < 4GB

**⚠️ 주의:** CPU 오프로드는 매우 느려지므로 마지막에 시도하세요!

---

### 4️⃣ 고급 최적화 (선택)

#### xFormers

```yaml
runtime:
  memory:
    enable_xformers: true
```

**설치:**
```bash
pip install xformers
```

**효과:**
- 메모리 절약: 20-30%
- 속도 향상: 10-20% 빨라짐 🚀
- **권장 대상:** 모든 사용자 (설치 가능하면)

#### Torch Compile (PyTorch 2.0+)

```yaml
runtime:
  memory:
    enable_torch_compile: true
```

**효과:**
- 첫 실행: 매우 느림 (컴파일 시간)
- 이후 실행: 20-30% 빨라짐 🚀
- **권장 대상:** 반복 실행 시

---

## 📊 시나리오별 권장 설정

### 시나리오 1: 고성능 GPU (RTX 4090, A100 등)

**목표:** 최대 속도

```yaml
runtime:
  memory:
    enable_vae_tiling: true
    enable_vae_slicing: true
    enable_attention_slicing: true
    use_bfloat16: true
    enable_xformers: true          # 설치 시
    enable_torch_compile: true     # 반복 실행 시
    
    # 나머지는 false
    enable_cpu_offload: false
    enable_sequential_cpu_offload: false
    use_8bit: false
```

**예상 성능:**
- 1024x1024 이미지: 5-10초 (FLUX-schnell)
- 메모리 사용: 10-12GB

---

### 시나리오 2: 중급 GPU (RTX 3060 12GB, RTX 4060 Ti)

**목표:** 속도와 메모리 균형

```yaml
runtime:
  memory:
    enable_vae_tiling: true
    enable_vae_slicing: true
    enable_attention_slicing: true
    use_bfloat16: true
    enable_xformers: true
    
    # 메모리 부족 시 활성화
    use_8bit: false  # 필요시 true
    enable_cpu_offload: false
```

**예상 성능:**
- 1024x1024 이미지: 10-20초
- 메모리 사용: 8-10GB

---

### 시나리오 3: 저사양 GPU (RTX 3060 8GB, GTX 1080 Ti)

**목표:** 메모리 최적화 우선

```yaml
runtime:
  memory:
    enable_vae_tiling: true
    enable_vae_slicing: true
    enable_attention_slicing: true
    use_bfloat16: true  # Ampere 이상만
    use_8bit: true      # 🎯 8비트 활성화
    enable_xformers: true
    
    enable_cpu_offload: false  # 아직은 false
```

**예상 성능:**
- 1024x1024 이미지: 20-30초
- 메모리 사용: 6-8GB

---

### 시나리오 4: 초저사양 GPU (RTX 2060, GTX 1660)

**목표:** 작동 우선

```yaml
runtime:
  memory:
    enable_vae_tiling: true
    enable_vae_slicing: true
    enable_attention_slicing: true
    use_8bit: true
    enable_xformers: true
    enable_cpu_offload: true  # 🎯 CPU 오프로드 활성화
```

**예상 성능:**
- 1024x1024 이미지: 40-60초
- 메모리 사용: 4-6GB

**추가 팁:**
- 해상도를 512x512로 낮추기
- SDXL 대신 SD 1.5 사용

---

### 시나리오 5: CPU 전용 (GPU 없음)

**⚠️ 권장하지 않음** (매우 느림)

```yaml
runtime:
  memory:
    enable_vae_tiling: true
    enable_vae_slicing: true
    enable_attention_slicing: true
    use_8bit: false  # CPU는 8bit 지원 안함
```

**예상 성능:**
- 512x512 이미지: 5-10분
- 1024x1024: 권장하지 않음

---

## 🔍 최적화 우선순위

```
1순위: VAE 타일링                  (속도↔ 메모리↑↑↑)
2순위: VAE 슬라이싱                (속도↓ 메모리↑↑)
3순위: 어텐션 슬라이싱             (속도↓ 메모리↑↑)
4순위: bfloat16                   (속도→ 메모리↑↑)
5순위: xFormers                   (속도↑ 메모리↑)
6순위: 8비트 양자화               (속도↓↓ 메모리↑↑↑)
7순위: CPU 오프로드               (속도↓↓↓ 메모리↑↑↑↑)
8순위: Sequential CPU 오프로드    (속도↓↓↓↓ 메모리↑↑↑↑↑)
```

**원칙:** 위에서부터 순서대로 활성화!

---

## 🧪 실험 가이드

### 단계별 테스트

#### 1단계: 기본 설정으로 시작

```yaml
runtime:
  memory:
    enable_vae_tiling: true
    enable_vae_slicing: true
    enable_attention_slicing: true
    use_bfloat16: false
    use_8bit: false
    enable_cpu_offload: false
```

**테스트:**
```bash
# 백엔드 실행
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000

# GPU 메모리 확인
nvidia-smi

# 이미지 생성 테스트 (프론트엔드에서)
```

#### 2단계: bfloat16 추가 (Ampere 이상)

```yaml
use_bfloat16: true
```

**확인:**
- 메모리 사용량 감소 확인
- 속도 변화 없음

#### 3단계: 메모리 부족 시 8비트

```yaml
use_8bit: true
```

**확인:**
- 메모리 사용량 50% 감소
- 생성 시간 20-30% 증가

#### 4단계: 최후의 수단 - CPU 오프로드

```yaml
enable_cpu_offload: true
```

**확인:**
- 메모리 거의 안씀
- 생성 시간 2-3배 증가

---

## 💡 팁 & 트릭

### 1. GPU 메모리 실시간 모니터링

```bash
# 터미널에서
watch -n 1 nvidia-smi

# 또는
gpustat -i 1
```

### 2. 메모리 부족 에러 발생 시

```
RuntimeError: CUDA out of memory
```

**해결 순서:**
1. 해상도 낮추기 (1024 → 768 → 512)
2. `use_8bit: true` 활성화
3. `enable_cpu_offload: true` 활성화
4. 더 작은 모델 사용 (FLUX → SDXL)

### 3. 속도 vs 메모리 트레이드오프

```python
# 빠르지만 메모리 많이 씀
memory: {
    enable_vae_tiling: true,
    use_bfloat16: true
}

# 느리지만 메모리 적게 씀
memory: {
    enable_vae_tiling: true,
    use_8bit: true,
    enable_cpu_offload: true
}
```

### 4. xFormers 설치 (권장)

```bash
# CUDA 11.8
pip install xformers

# CUDA 12.1
pip install xformers --index-url https://download.pytorch.org/whl/cu121

# 확인
python -c "import xformers; print(xformers.__version__)"
```

---

## 🎯 팀원 최적화 비교

### 팀원이 추가한 것들 ✅

1. **VAE 타일링** - 포함됨!
2. **VAE 슬라이싱** - 포함됨!
3. **bfloat16** - 포함됨!
4. **Sequential CPU offload** - 포함됨!

### 추가로 제공하는 것들 🆕

1. **xFormers** - 속도 향상
2. **Torch Compile** - PyTorch 2.0+
3. **8비트 양자화** - 더 많은 메모리 절약
4. **유연한 설정** - 각 옵션 독립적으로 on/off

---

## 📋 최종 권장 설정

### 대부분의 경우 (RTX 3060 12GB 이상)

```yaml
runtime:
  memory:
    # 기본 최적화 (항상 ON)
    enable_vae_tiling: true
    enable_vae_slicing: true
    enable_attention_slicing: true
    
    # 정밀도 최적화
    use_bfloat16: true  # RTX 30/40 시리즈
    use_8bit: false
    
    # CPU 오프로드 (최후의 수단)
    enable_cpu_offload: false
    enable_sequential_cpu_offload: false
    
    # 고급 최적화
    enable_xformers: false  # 설치 후 true
    enable_torch_compile: false
```

### 메모리 부족 시 (RTX 3060 8GB 이하)

```yaml
runtime:
  memory:
    enable_vae_tiling: true
    enable_vae_slicing: true
    enable_attention_slicing: true
    use_bfloat16: true
    use_8bit: true           # 🎯 활성화
    enable_cpu_offload: false  # 그래도 안되면 true
```

---

**이제 모든 최적화 기법을 사용할 수 있습니다!** 🚀

팀원의 최적화 + 추가 옵션으로 완벽한 메모리 관리! 🎉