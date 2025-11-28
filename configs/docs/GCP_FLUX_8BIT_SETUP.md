# GCP FLUX 8-bit 양자화 설정 가이드

> 2025-11-22 작성
> GCP L4 GPU (22GB VRAM) 환경에서 FLUX 모델을 8-bit 양자화로 빠르게 실행하는 방법

---

## 📋 요약

| 항목 | 값 |
|------|-----|
| 모델 | `diffusers/FLUX.1-dev-bnb-8bit` |
| 양자화 방식 | bitsandbytes 8-bit |
| GPU 메모리 | ~21GB |
| 생성 시간 | 77초/이미지 (1024x1024, 28 steps) |
| 품질 | 정상 (모자이크 없음) |

---

## 🔧 의존성 버전 (호환성 검증됨)

```toml
# pyproject.toml
dependencies = [
    "diffusers>=0.26,<0.35",
    "transformers>=4.44.0,<4.57.0",
    "torchao>=0.9.0",
    "bitsandbytes>=0.41.0",
]
```

### ⚠️ 버전 호환성 주의사항

1. **diffusers 0.35.x + transformers 4.57.x**: `AutoImageProcessor` import 에러 발생
2. **torchao 0.7.0**: `Int4WeightOnlyConfig` import 에러 발생
3. **위 버전 조합이 검증된 안정적인 조합임**

---

## 📦 사용 가능한 모델

### ✅ 권장: `flux-dev-bnb-8bit`

```yaml
# model_config.yaml
models:
  flux-dev-bnb-8bit:
    id: "diffusers/FLUX.1-dev-bnb-8bit"
    type: "flux-bnb-8bit"
    requires_auth: false
    params:
      default_steps: 28
      max_steps: 50
      use_negative_prompt: false
      guidance_scale: 3.5
      supports_i2i: true
      max_tokens: 512
      default_size: [1024, 1024]
      max_size: [2048, 2048]
    description: "FLUX.1-dev 8-bit 사전 양자화 (bitsandbytes)"

runtime:
  primary_model: "flux-dev-bnb-8bit"
```

### ❌ 사용 불가: `flux-dev-fp8-pre` (torchao FP8)

```
diffusers/FLUX.1-dev-torchao-fp8
```

- **문제**: torchao 버전 호환 문제
- **에러**: `The size of tensor a (4096) must match the size of tensor b (10240)`
- **원인**: 모델이 구버전 torchao로 양자화되어 현재 버전과 호환 안 됨
- **경고 메시지**: `Models quantized with version 1 of Float8DynamicActivationFloat8WeightConfig is deprecated`

### ❌ 사용 불가: 직접 FP8 양자화 (TorchAO)

```python
from torchao.quantization import quantize_
from torchao.quantization.quant_api import Float8WeightOnlyConfig
quantize_(transformer, Float8WeightOnlyConfig())
```

- **문제**: 양자화가 실제로 적용되지 않음
- **증상**: 양자화 전후 모델 크기 동일 (22GB → 22GB)

### ❌ 사용 시 모자이크 발생: optimum-quanto FP8

```python
from optimum.quanto import quantize, freeze, qfloat8
quantize(transformer, weights=qfloat8)
freeze(transformer)
```

- **문제**: 이미지가 픽셀 모자이크로 출력됨
- **원인**: VAE 또는 인코더 관련 문제 추정

---

## 🚀 설정 방법

### 1. pyproject.toml 수정

```toml
dependencies = [
    "diffusers>=0.26,<0.35",
    "transformers>=4.44.0,<4.57.0",
    "torchao>=0.9.0",
    "bitsandbytes>=0.41.0",
]
```

### 2. model_config.yaml 수정

```yaml
runtime:
  primary_model: "flux-dev-bnb-8bit"
```

### 3. test_flux_gcp.yaml 수정 (테스트용)

```yaml
model:
  name: "flux-dev-bnb-8bit"
```

### 4. 환경 설정 및 실행

```bash
# .venv 삭제 후 재설치
rm -rf .venv && uv sync

# 테스트 실행
uv run python scripts/test_flux_gcp.py
```

---

## 📊 GPU 메모리 사용량 분석

8-bit 양자화 적용 후에도 ~21GB 사용되는 이유:

| 컴포넌트 | 크기 | 양자화 |
|----------|------|--------|
| Transformer | ~12GB | ✅ 8-bit 적용 |
| T5 텍스트 인코더 | ~8GB | ✅ 8-bit 적용 |
| VAE | ~1GB | ❌ 원본 |
| CLIP | ~1GB | ❌ 원본 |

**로그에서 확인:**
```
The module 'T5EncoderModel' has been loaded in `bitsandbytes` 8bit
The module 'FluxTransformer2DModel' has been loaded in `bitsandbytes` 8bit
```

---

## 🔍 문제 해결 히스토리

### 시도 1: TorchAO FP8 사전 양자화 모델

```
모델: diffusers/FLUX.1-dev-torchao-fp8
결과: 실패
에러: The size of tensor a (4096) must match the size of tensor b (10240)
원인: torchao 버전 호환 문제
```

### 시도 2: device_map="balanced"

```
결과: 실패
에러: You are attempting to perform cpu/disk offload with a pre-quantized torchao model
원인: torchao 양자화 모델은 CPU offload 미지원
```

### 시도 3: device_map="cuda:0"

```
결과: 실패
에러: cuda:0 not supported. Supported strategies are: balanced
원인: diffusers에서 cuda:0 직접 지정 미지원
```

### 시도 4: TorchAO 직접 양자화

```
방식: Float8WeightOnlyConfig()
결과: 실패
문제: 양자화가 적용되지 않음 (모델 크기 변화 없음)
```

### 시도 5: optimum-quanto FP8

```
방식: quantize(transformer, weights=qfloat8)
결과: 이미지 생성 성공 (69초)
문제: 전체가 픽셀 모자이크
```

### 시도 6: bitsandbytes 8-bit 사전 양자화 ✅

```
모델: diffusers/FLUX.1-dev-bnb-8bit
결과: 성공
시간: 77초/이미지
품질: 정상
```

---

## 📝 코드 구현

### model_loader.py 관련 코드

```python
if model_type == "flux-bnb-8bit":
    # 사전 양자화 8-bit 모델 (diffusers/FLUX.1-dev-bnb-8bit)
    # 공식 문서: pipe.to("cuda") 사용
    from diffusers import FluxPipeline

    t2i = FluxPipeline.from_pretrained(
        model_id,
        torch_dtype=self.dtype,
        cache_dir=self.cache_dir
    )
    # bitsandbytes 모델은 자동으로 GPU에 로드됨

    # I2I 파이프라인
    try:
        i2i = AutoPipelineForImage2Image.from_pipe(t2i)
    except:
        i2i = t2i
```

---

## ⚠️ 주의사항

1. **버전 고정 필수**: 위에 명시된 버전 범위를 벗어나면 호환성 문제 발생
2. **캐시 정리**: 버전 변경 시 `uv cache clean && rm -rf .venv && uv sync` 필수
3. **GPU 메모리**: 최소 22GB VRAM 필요 (L4, A10G, A100 등)
4. **CPU offload 불가**: bitsandbytes 양자화 모델은 CPU로 이동 불가

---

## 📚 참고 자료

- [diffusers/FLUX.1-dev-bnb-8bit](https://huggingface.co/diffusers/FLUX.1-dev-bnb-8bit)
- [Diffusers bitsandbytes 문서](https://huggingface.co/docs/diffusers/en/quantization/bitsandbytes)
- [Diffusers 양자화 개요](https://huggingface.co/docs/diffusers/quantization/overview)
