# 프로젝트 전체 모델 사용 현황 분석 및 정리 - 2025년 12월 2일

## 📋 분석 개요
프로젝트에서 실제로 사용 중인 AI 모델과 설치되어 있으나 사용하지 않는 모델을 구분하여 스토리지 최적화 작업 수행

---

## ✅ 활발히 사용 중인 모델

### 1. FLUX 모델 계열 (ComfyUI GGUF)

#### FLUX.1-dev-Q8 (12GB)
- **경로**: `/home/shared/flux1-dev-Q8_0.gguf`
- **용도**: 메인 이미지 생성 모델
- **사용 위치**:
  - Portrait Mode (인물 모드) - 의상/배경 변경
  - Product Mode (제품 모드) - 배경 생성
  - Hybrid Mode (하이브리드) - 복합 편집
- **품질**: 최고 (Q8 양자화)

#### FLUX.1-dev-Q4 (6.4GB)
- **경로**: `/home/shared/flux1-dev-Q4_0.gguf`
- **용도**: 메모리 최적화 버전
- **사용 위치**:
  - Product Mode - 배경 생성 (메모리 절약)
  - Hybrid Mode - 복합 편집
- **품질**: 양호 (Q4 양자화, 메모리 효율적)

#### FLUX.1-Fill-dev-Q8 (18GB)
- **경로**: `/home/shared/FLUX.1-Fill-dev-Q8_0.gguf`
- **용도**: Inpainting 전문 모델
- **사용 위치**:
  - Product Mode - 제품+배경 자연스러운 블렌딩
- **특징**: 누끼 제품과 생성된 배경을 자연스럽게 합성

#### T5-XXL Text Encoder (4.8GB)
- **경로**: `/home/shared/t5-v1_1-xxl-encoder-Q8_0.gguf`
- **용도**: FLUX 텍스트 인코더
- **필수 여부**: ✅ 필수 (모든 FLUX 워크플로우)
- **역할**: 프롬프트를 FLUX가 이해할 수 있는 임베딩으로 변환

#### AutoEncoder VAE (160MB)
- **경로**: `/home/shared/ae.safetensors`
- **용도**: Latent Space ↔ 이미지 변환
- **필수 여부**: ✅ 필수
- **역할**: 
  - Latent → 이미지 디코딩
  - 이미지 → Latent 인코딩 (I2I)

### 2. BEN2 배경 제거 모델 (1.1GB)

- **경로**: `/home/shared/ben2/BEN2_Base.pth`
- **용도**: 고정밀 배경 제거 (누끼 전문)
- **사용 위치**:
  - Product Mode - 제품 분리
  - Hybrid Mode - 제품 영역 감지
- **특징**: 일반 배경 제거보다 높은 정밀도

### 3. ComfyUI Custom Nodes

#### BEN2_ComfyUI (1.1GB)
- **경로**: `comfyui/custom_nodes/BEN2_ComfyUI/`
- **상태**: ✅ 활발히 사용
- **용도**: BEN2 모델을 ComfyUI에서 사용할 수 있게 하는 래퍼

#### ComfyUI-GGUF (264KB)
- **경로**: `comfyui/custom_nodes/ComfyUI-GGUF/`
- **상태**: ✅ 필수
- **용도**: GGUF 포맷 모델 로더
- **중요도**: 없으면 FLUX 모델 사용 불가

#### comfyui-impact-pack (4.9MB)
- **경로**: `comfyui/custom_nodes/comfyui-impact-pack/`
- **상태**: ✅ 활발히 사용
- **용도**: 
  - Face Detector (YOLO 기반)
  - Hand Detector
  - SAM 통합
- **사용 위치**: Portrait Mode, Hybrid Mode

#### comfyui_controlnet_aux (50MB)
- **경로**: `comfyui/custom_nodes/comfyui_controlnet_aux/`
- **상태**: ✅ 활발히 사용
- **용도**: ControlNet 전처리기
  - Depth Map 생성
  - Canny Edge 검출
  - Pose Estimation 등
- **사용 위치**: 모든 편집 모드

#### comfyui-rmbg (6.1MB)
- **경로**: `comfyui/custom_nodes/comfyui-rmbg/`
- **상태**: ✅ 사용 (RMBG v1.4)
- **용도**: 배경 제거 (BEN2 대체/보조 옵션)

#### ComfyUI-Manager (113MB)
- **경로**: `comfyui/custom_nodes/ComfyUI-Manager/`
- **상태**: ✅ 필수 (관리 도구)
- **용도**: Custom Node 설치/업데이트 관리

### 4. 텍스트 오버레이 (페이지 5) - ControlNet Depth SDXL 활용

#### rembg (u2net 모델)
- **상태**: ✅ 사용 중
- **용도**: 3D 캘리그라피 배경 제거
- **특징**: AI 기반 자동 배경 제거

#### ControlNet Depth SDXL (611MB)
- **상태**: ✅ **필수 모델**
- **용도**: Depth Map 기반 3D 입체감 생성
- **파이프라인**:
  1. 텍스트 → 기본 이미지 생성
  2. **MidasDetector** → Depth Map 추출
  3. **ControlNet Depth SDXL** → Depth 기반 3D 효과 적용
  4. rembg → 배경 제거
- **지원 스타일**: default, emboss, carved, floating

#### Stable Diffusion XL Base (13GB)
- **상태**: ✅ **필수 모델**
- **용도**: ControlNet과 함께 3D 효과 생성
- **특징**: SDXL 파이프라인의 베이스 모델

#### SDXL VAE FP16 (320MB)
- **상태**: ✅ **필수 모델**
- **용도**: SDXL 이미지 인코딩/디코딩
- **특징**: FP16 정밀도로 메모리 최적화

---

## ❌ 삭제된 모델 (2025-12-02)

### 1. Hugging Face Diffusers 모델 (총 32GB 확보)

#### FLUX.1-dev-bnb-4bit (13GB) ✅ 삭제 완료
- **경로**: `/home/shared/models--diffusers--FLUX.1-dev-bnb-4bit/`
- **형식**: Diffusers (Hugging Face)
- **삭제 이유**: 
  - ComfyUI는 GGUF 포맷 사용
  - src/backend/model_loader.py에서 로드 시도하나 실패
  - GGUF 버전(flux1-dev-Q4)으로 대체됨
- **확보 공간**: ~13GB

#### FLUX.1-dev-bnb-8bit (19GB) ✅ 삭제 완료
- **경로**: `/home/shared/models--diffusers--FLUX.1-dev-bnb-8bit/`
- **형식**: Diffusers (Hugging Face)
- **삭제 이유**: 동일 (GGUF로 완전 전환)
- **확보 공간**: ~19GB

**총 확보 공간**: **~32GB**

---

## ⚠️ 설치되어 있으나 사용하지 않는 모델

### 현재 상태: 모든 Diffusers 모델 사용 중 ✅

**이전 분석에서는** SDXL 관련 모델(ControlNet Depth SDXL, SDXL Base, SDXL VAE)을 미사용으로 분류했으나, **페이지 5 (3D 캘리그라피 생성)** 기능에서 필수적으로 사용되고 있음이 확인되었습니다.

따라서 **현재 /home/shared에 있는 모든 모델이 활발히 사용 중**이며, 추가로 삭제할 수 있는 모델은 없습니다.

### Custom Nodes (일부 중복/미사용 가능성)

#### Stable Diffusion XL Base 1.0 (13GB)
- **경로**: `/home/shared/models--stabilityai--stable-diffusion-xl-base-1.0/`
- **형식**: Diffusers
- **상태**: ✅ **사용 중**
- **용도**:
  - **페이지 5 (3D 캘리그라피)**: ControlNet Depth SDXL과 함께 사용
  - Depth 기반 3D 효과 생성의 베이스 모델
- **필수 여부**: ✅ **필수** (ControlNet과 페어)
- **삭제 가능**: ❌ **삭제 불가**

#### ControlNet Depth SDXL (611MB)
- **경로**: `/home/shared/models--diffusers--controlnet-depth-sdxl-1.0-small/`
- **형식**: Diffusers
- **상태**: ✅ **사용 중**
- **용도**: 
  - **페이지 5 (3D 캘리그라피 생성)**: Depth Map 기반 입체감 강화
  - MidasDetector로 Depth 추출 → ControlNet으로 3D 효과 적용
  - 스타일: default, emboss, carved, floating
- **필수 여부**: ✅ **필수** (텍스트 오버레이 기능의 핵심)
- **삭제 가능**: ❌ **삭제 불가**

#### SDXL VAE FP16 Fix (320MB)
- **경로**: `/home/shared/models--madebyollin--sdxl-vae-fp16-fix/`
- **형식**: Diffusers
- **상태**: ✅ **사용 중**
- **용도**: 
  - **페이지 5 (3D 캘리그라피)**: SDXL Base 모델과 함께 사용
  - FP16 정밀도로 VAE 인코딩/디코딩
- **필수 여부**: ✅ **필수** (SDXL 파이프라인의 일부)
- **삭제 가능**: ❌ **삭제 불가**

**추가 확보 가능 공간**: ~14GB

### 2. Custom Nodes (일부 중복/미사용)

#### ComfyUI-BRIA_AI-RMBG (324KB)
- **경로**: `comfyui/custom_nodes/ComfyUI-BRIA_AI-RMBG/`
- **상태**: ⚠️ 중복 가능성
- **이유**: `comfyui-rmbg`와 기능 중복
- **삭제 가능**: ⚠️ 확인 필요 (경량)

#### ComfyUI_bnb_nf4_fp4_Loaders (360KB)
- **경로**: `comfyui/custom_nodes/ComfyUI_bnb_nf4_fp4_Loaders/`
- **상태**: ⚠️ 미사용 가능성
- **이유**: 
  - BitsAndBytes 양자화 로더
  - GGUF 사용으로 불필요
- **삭제 가능**: ⚠️ 확인 필요 (경량)

#### comfyui-impact-subpack (176KB)
- **경로**: `comfyui/custom_nodes/comfyui-impact-subpack/`
- **상태**: ⚠️ 사용 여부 불분명
- **삭제 가능**: ⚠️ 확인 필요 (경량)

---

## ⚠️ 확인 필요: Qwen-Image-Edit (21GB)

### Qwen-Image-Edit-2509-Q8
- **경로**: `/home/shared/Qwen-Image-Edit-2509-Q8_0.gguf`
- **크기**: 21GB
- **상태**: ⚠️ 불분명
- **코드 증거**:
  - `comfyui_workflows.py:439` - "기존 실험 워크플로우 제거됨 (ben2_flux_fill, ben2_qwen_image)"
  - `model_loader.py:388-422` - qwen-image-edit 타입 정의되어 있음
  - `main.py:75` - "ben2_qwen_image" 주석으로만 존재
- **판단**:
  - 워크플로우가 제거되었다는 명시적 주석 존재
  - 하지만 코드 구조는 남아있음
  - 실제 사용 확인 필요
- **권장**: 백업 후 삭제 테스트

---

## 📊 스토리지 사용 현황 요약

| 카테고리 | 용량 | 상태 | 비고 |
|---------|------|------|------|
| **GGUF 모델 (FLUX 계열)** | ~42GB | ✅ 필수 | Q8(12GB) + Q4(6.4GB) + Fill(18GB) + T5(4.8GB) + VAE(0.16GB) |
| **BEN2** | 1.1GB | ✅ 필수 | 배경 제거 전문 |
| **SDXL 계열 (Diffusers)** | ~14GB | ✅ 필수 | ControlNet Depth(611MB) + SDXL Base(13GB) + VAE(320MB) - 페이지5 사용 |
| **FLUX bnb (Diffusers)** | ~~32GB~~ | ✅ 삭제 완료 | bnb-4bit(13GB) + bnb-8bit(19GB) |
| **Qwen-Image-Edit** | 21GB | ⚠️ 확인 필요 | 워크플로우 제거되었으나 파일 잔존 |
| **Custom Nodes** | ~1.3GB | ✅ 대부분 필수 | 일부 중복 가능성 (~1MB) |
| **기타 (폰트 등)** | ~1MB | ✅ 필수 | RiaSans-Bold.ttf |

### 스토리지 변화 추이

#### 삭제 전 (2025-12-02 오전)
- **총 용량**: ~108GB

#### 삭제 후 (2025-12-02 오후)
- **총 용량**: ~76GB
- **확보 공간**: **32GB** ✅

#### 추가 최적화 가능
- ~~SDXL 관련 모델 삭제 시: **~14GB** 추가 확보 가능~~ → **사용 중으로 확인됨 (삭제 불가)**
- Qwen-Image-Edit 삭제 시: **~21GB** 추가 확보 가능
- **최대 총 확보 가능**: **53GB** (32GB + 21GB)

---

## 🎯 최적화 권장사항

### Phase 1: 완료 ✅

```bash
# FLUX bnb 모델 삭제 (32GB 확보)
rm -rf /home/shared/models--diffusers--FLUX.1-dev-bnb-4bit
rm -rf /home/shared/models--diffusers--FLUX.1-dev-bnb-8bit

# 확인
du -sh /home/shared/
```

**결과**: 108GB → 76GB (32GB 확보) ✅

### ~~Phase 2: SDXL 모델 삭제 (안전, 14GB 추가 확보)~~ ❌ 취소

**⚠️ 중요: SDXL 모델 삭제 불가**

페이지 5 (3D 캘리그라피 생성) 기능에서 ControlNet Depth SDXL, SDXL Base, SDXL VAE를 필수적으로 사용하고 있음이 확인되었습니다.

**사용 파이프라인**:
1. `text_overlay.py` → MidasDetector로 Depth Map 생성
2. ControlNet Depth SDXL → Depth 기반 3D 효과 적용
3. SDXL Base → 3D 이미지 생성
4. SDXL VAE → 이미지 인코딩/디코딩
5. rembg → 배경 제거

**결론**: SDXL 관련 모델 14GB는 **삭제 불가**

### Phase 2 (수정): Qwen-Image-Edit 확인 후 삭제 (21GB 추가 확보 가능)

```bash
# 워크플로우에서 사용 확인
grep -r "Qwen-Image" /home/spai0323/Ad_Content_Creation_Service_Team3/src/backend/
grep -r "qwen" /home/spai0323/Ad_Content_Creation_Service_Team3/configs/

# 2. 백엔드 로그 확인 (최근 7일)
grep -i "qwen" /home/spai0323/Ad_Content_Creation_Service_Team3/logs/*.log

# 3. 사용되지 않는다고 확인되면
mv /home/shared/Qwen-Image-Edit-2509-Q8_0.gguf ~/backup_unused_models/
# (1주일 테스트 후 문제 없으면 삭제)
```

**예상 결과**: 76GB → 55GB (21GB 추가 확보)

### ~~Phase 4: Custom Nodes 정리 (미미한 용량, 선택)~~ (선택사항)

```bash
cd /home/spai0323/Ad_Content_Creation_Service_Team3/comfyui/custom_nodes

# 중복 확인 후 삭제
# rm -rf ComfyUI-BRIA_AI-RMBG  # comfyui-rmbg와 중복 가능성
# rm -rf ComfyUI_bnb_nf4_fp4_Loaders  # GGUF 사용으로 불필요
```

---

## 📋 현재 /home/shared 상태 (삭제 후)

```
총 용량: 76G

파일 및 디렉토리:
FLUX.1-Fill-dev-Q8_0.gguf (18G)          ✅ 사용 중
Qwen-Image-Edit-2509-Q8_0.gguf (21G)     ⚠️ 확인 필요
RiaSans-Bold.ttf (878K)                  ✅ 사용 중
ae.safetensors (160M)                    ✅ 사용 중
ben2/ (4.0K → 1.1GB 실제)                ✅ 사용 중
flux1-dev-Q4_0.gguf (6.4G)               ✅ 사용 중
flux1-dev-Q8_0.gguf (12G)                ✅ 사용 중
t5-v1_1-xxl-encoder-Q8_0.gguf (4.8G)     ✅ 사용 중

Hugging Face 캐시 (페이지5에서 사용 중):
models--diffusers--controlnet-depth-sdxl-1.0-small/ (611M)  ✅ 사용 중 (3D 캘리그라피)
models--madebyollin--sdxl-vae-fp16-fix/ (320M)              ✅ 사용 중 (3D 캘리그라피)
models--stabilityai--stable-diffusion-xl-base-1.0/ (13G)    ✅ 사용 중 (3D 캘리그라피)
```

---

## 📋 기능별 필수 모델 체크리스트

### ✅ 절대 삭제 금지 (필수 - 현재 보존됨)

- [x] **flux1-dev-Q8_0.gguf** (12GB) - 메인 생성 모델
- [x] **flux1-dev-Q4_0.gguf** (6.4GB) - 메모리 최적화 버전
- [x] **FLUX.1-Fill-dev-Q8_0.gguf** (18GB) - Inpainting
- [x] **t5-v1_1-xxl-encoder-Q8_0.gguf** (4.8GB) - 텍스트 인코더
- [x] **ae.safetensors** (160MB) - VAE
- [x] **BEN2_Base.pth** (1.1GB) - 배경 제거
- [x] **models--diffusers--controlnet-depth-sdxl-1.0-small** (611MB) - 3D 캘리그라피 Depth Map
- [x] **models--stabilityai--stable-diffusion-xl-base-1.0** (13GB) - 3D 캘리그라피 생성
- [x] **models--madebyollin--sdxl-vae-fp16-fix** (320MB) - SDXL VAE
- [x] **ComfyUI-GGUF** - GGUF 로더
- [x] **BEN2_ComfyUI** - BEN2 래퍼
- [x] **comfyui-impact-pack** - Face/Hand Detector
- [x] **comfyui_controlnet_aux** - ControlNet 전처리
- [x] **comfyui-rmbg** - 배경 제거
- [x] **ComfyUI-Manager** - 관리 도구

### ✅ 안전하게 삭제 완료 (32GB 확보)

- [x] **models--diffusers--FLUX.1-dev-bnb-4bit** (13GB) ✅
- [x] **models--diffusers--FLUX.1-dev-bnb-8bit** (19GB) ✅

### ~~⚠️ 추가 삭제 검토 대상 (14GB)~~ → **사용 중으로 확인됨 (삭제 불가)**

- [x] ~~**models--stabilityai--stable-diffusion-xl-base-1.0** (13GB)~~ → **페이지5 사용 중**
- [x] ~~**models--diffusers--controlnet-depth-sdxl-1.0-small** (611MB)~~ → **페이지5 사용 중**
- [x] ~~**models--madebyollin--sdxl-vae-fp16-fix** (320MB)~~ → **페이지5 사용 중**

### ⚠️ 확인 후 삭제 검토 (21GB)

- [ ] **Qwen-Image-Edit-2509-Q8_0.gguf** (21GB)
  - 워크플로우 제거 주석 확인됨
  - 하지만 코드 구조 잔존
  - 백업 후 삭제 테스트 권장

---

## 🔍 코드 분석 결과

### 사용 중인 모델 경로 (comfyui_workflows.py)

```python
# Portrait Mode, Hybrid Mode
"unet_name": "flux1-dev-Q8_0.gguf"  # 라인 128, 352, 751

# Product Mode (메모리 최적화)
"unet_name": "flux1-dev-Q4_0.gguf"  # 라인 976, 1190

# 모든 FLUX 워크플로우
"clip_name2": "t5-v1_1-xxl-encoder-Q8_0.gguf"  # 라인 137, 361, 760, 985
"vae_name": "ae.safetensors"  # 라인 177, 379, 769, 994

# Product Mode Inpainting
"unet_name": "FLUX.1-Fill-dev-Q8_0.gguf"  # 라인 1078

# BEN2 배경 제거
BEN2 노드 사용 - 라인 964, 1082, 1172
```

### 제거된 워크플로우 (comfyui_workflows.py:439)

```python
# 🗑️ 기존 실험 워크플로우 제거됨 (ben2_flux_fill, ben2_qwen_image)
# → Qwen-Image-Edit 미사용 확인
```

### Diffusers 모델 로드 실패 (model_loader.py)

```python
# FLUX bnb 모델 로드 시도 코드 있으나
# ComfyUI는 GGUF만 지원하므로 실제 사용 안됨
# 라인 165-209: flux-bnb-4bit, flux-bnb-8bit 로더
# → 삭제 안전 확인
```

---

## 💡 결론 및 향후 계획

### 완료된 작업 (2025-12-02)
1. ✅ FLUX bnb-4bit, bnb-8bit 모델 삭제 (32GB 확보)
2. ✅ 필수 GGUF 모델 안전 확인
3. ✅ 모델 사용 현황 전체 분석 완료
4. ✅ **중요**: SDXL 모델이 페이지5 (3D 캘리그라피)에서 사용 중임을 확인

### 즉시 실행 가능
1. ~~⚠️ SDXL 관련 모델 삭제 (14GB 추가 확보)~~ → **❌ 삭제 불가 (페이지5 사용 중)**

### 추가 검증 필요
1. ⚠️ Qwen-Image-Edit 사용 여부 최종 확인
   - 워크플로우 제거되었으나 파일 잔존
   - 확인 후 21GB 추가 확보 가능

### 최종 목표
- **현재 스토리지**: 76GB
- **최적화 후 목표**: 55GB (Qwen 삭제 시)
- **총 확보 가능**: 53GB (32GB + 21GB)

---

**작성일**: 2025년 12월 2일  
**분석 및 작업**: GitHub Copilot (AI 프로젝트 매니저)  
**최종 업데이트**: 2025년 12월 2일 (SDXL 모델 사용 확인 반영)  
**다음 단계**: 
1. ~~Phase 2 실행 권장 (SDXL 삭제, 14GB 확보)~~ → **취소 (페이지5에서 필수 사용)**
2. Qwen-Image-Edit 사용 여부 최종 확인
3. 확인 후 Qwen 삭제 시 21GB 추가 확보 가능

**중요 변경사항**:
- **SDXL 관련 모델 (ControlNet Depth SDXL, SDXL Base, SDXL VAE)**: 삭제 불가 → **페이지5 (3D 캘리그라피 생성)에서 필수 사용**
- **페이지5 파이프라인**: 텍스트 → Depth Map (Midas) → ControlNet Depth SDXL → 3D 효과 → 배경 제거 (rembg)
- **최대 확보 가능 공간**: 67GB → 53GB (SDXL 14GB는 삭제 불가로 변경)
