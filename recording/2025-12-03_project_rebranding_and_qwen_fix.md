# 프로젝트 리브랜딩 및 페이지4 개선 시도

**날짜**: 2025-12-03  
**시간**: 오전 9시 58분 ~ 오전 10시 20분 (KST, UTC+09:00)  
**작성자**: AI Assistant

---

## 📋 작업 개요

1. 프로젝트를 "헬스케어 소상공인"에서 "소상공인" 전반으로 확장
2. 페이지1 서비스 종류 선택 방식을 selectbox → text_input으로 변경
3. ~~Qwen-Image-Edit 모드 워크플로우 오류 수정~~ → **미해결** (ComfyUI 모델 인식 실패)

---

## ✅ 완료된 작업

### 1. 프로젝트 리브랜딩 (헬스케어 → 소상공인)

#### 1.1 프로젝트 제목 변경

**수정 파일 5개:**

| 파일 | 변경 내용 |
|------|----------|
| `README.md` | "💪 헬스케어 AI 콘텐츠 제작 서비스" → "💪 소상공인 AI 콘텐츠 제작 서비스" |
| `src/frontend/frontend_config.yaml` | title: "헬스케어 AI 콘텐츠 제작" → "소상공인 AI 콘텐츠 제작" |
| `src/frontend/app.py` | 파일 주석 헬스케어 제거 |
| `src/backend/main.py` | FastAPI title: "헬스케어 AI 콘텐츠 API" → "소상공인 AI 콘텐츠 API" |
| `src/backend/services.py` | GPT 프롬프트: "헬스케어 소상공인" → "소상공인" |

#### 1.2 헬스케어 관련 콘텐츠 제거

**frontend_config.yaml**:
```yaml
# 삭제된 부분
caption:
  service_types:
    - "헬스장"
    - "PT (개인 트레이닝)"
    - "요가/필라테스"
    - "건강 식품/보조제"
    - "기타"
```

**새로운 placeholder 예시**:
```yaml
placeholders:
  service_type: "예: 카페, 미용실, 온라인 쇼핑몰 등"
  service_name: "예: 신메뉴 출시 이벤트, 봄맞이 할인"
  features: "예: 신선한 재료 사용, 전문가 시술, 무료 배송 등"
  location: "예: 강남, 마포구, 온라인"
  caption: "예: 💪 새로운 시작, 함께 해요!"
  edit_prompt: "예: 더 밝고 활기찬 분위기로, 파란색 배경 추가"
```

#### 1.3 app.py placeholder 변경

| 변경 전 | 변경 후 |
|---------|---------|
| "밝고 에너지 넘치는 필라테스 스튜디오" | "밝고 현대적인 카페 내부" |
| "따뜻한 조명, 편안한 분위기의 요가 공간" | "따뜻한 조명, 편안한 분위기의 가게 내부" |

---

### 2. 페이지1: 서비스 종류 입력 방식 변경

#### 2.1 변경 내용

**변경 전 (selectbox)**:
```python
service_type = st.selectbox(
    "서비스 종류",
    config.get("caption.service_types", [])
)
```

**변경 후 (text_input)**:
```python
service_type = st.text_input(
    "서비스 분야 (직접 입력)",
    placeholder=config.get("ui.placeholders.service_type", "예: 카페, 미용실, 온라인 쇼핑몰 등"),
    help="귀하의 비즈니스 분야를 입력하세요 (예: 카페, 패션, 피트니스 등)"
)
```

#### 2.2 GPT 프롬프트 호환성

**services.py** GPT 프롬프트는 여전히 `service_type` 변수를 사용하므로 정상 작동:

```python
prompt = f"""
당신은 소상공인을 위한 전문 인스타그램 콘텐츠 크리에이터입니다.
아래 정보를 바탕으로 인스타그램 게시물에 최적화된 콘텐츠를 생성해 주세요.

...

[정보]
서비스 종류: {info.get('service_type')}  # ✅ 사용자 직접 입력값
서비스명: {info.get('service_name')}
핵심 특징: {info.get('features')}
지역: {info.get('location')}
```

---

### 3. Qwen-Image-Edit 워크플로우 오류 수정

#### 3.1 문제 상황

**에러 메시지**:
```
큐 등록 실패: 400 - {"error": {"type": "prompt_outputs_failed_validation", ...}}
node_errors: {"2": {"errors": [{"type": "value_not_in_list", 
  "message": "unet_name: 'Qwen-Image-Edit-2509-Q8_0.gguf' 
  not in ['FLUX.1-Fill-dev-Q8_0.gguf', 'flux1-dev-Q4_0.gguf', 'flux1-dev-Q8_0.gguf']"
}]}}
```

**원인**:
- `UnetLoaderGGUF` 노드는 FLUX 모델만 지원 (화이트리스트 방식)
- Qwen 모델은 별도의 로더 사용 필요

#### 3.2 해결 방법

**A. 모델 파일 준비**

Qwen 모델을 ComfyUI의 unet 폴더에 심볼릭 링크 생성:

```bash
cd /home/spai0323/Ad_Content_Creation_Service_Team3/comfyui/models/unet
ln -sf /home/shared/Qwen-Image-Edit-2509-Q8_0.gguf .
```

**확인**:
```bash
ls -lh Qwen*.gguf
# lrwxrwxrwx 1 spai0323 spai0323 43 Dec  3 09:56 Qwen-Image-Edit-2509-Q8_0.gguf -> /home/shared/Qwen-Image-Edit-2509-Q8_0.gguf
```

**B. 워크플로우 노드 변경**

`src/backend/comfyui_workflows.py`의 `get_qwen_edit_mode_workflow()` 수정:

| 노드 | 변경 전 | 변경 후 | 이유 |
|------|---------|---------|------|
| **노드 2** (UNET) | `UnetLoaderGGUF`<br>- `unet_name` | `UNETLoader`<br>- `unet_name`<br>- `weight_dtype: "default"` | UnetLoaderGGUF는 FLUX만 지원 |
| **노드 3** (CLIP) | `DualCLIPLoaderGGUF`<br>- `clip_name1: "clip_l.safetensors"`<br>- `clip_name2: "t5-...gguf"`<br>- `type: "flux"` | `CLIPLoader`<br>- `clip_name: "t5-...gguf"`<br>- `type: "qwen_image"` | Qwen은 단일 CLIP 사용 |

**수정 후 워크플로우 (노드 2, 3)**:

```python
# 노드 2: Qwen UNET 로드 (일반 UNETLoader 사용)
"2": {
    "class_type": "UNETLoader",
    "inputs": {
        "unet_name": "Qwen-Image-Edit-2509-Q8_0.gguf",
        "weight_dtype": "default"
    }
},

# 노드 3: CLIP 로드 (qwen_image 타입)
"3": {
    "class_type": "CLIPLoader",
    "inputs": {
        "clip_name": "t5-v1_1-xxl-encoder-Q8_0.gguf",
        "type": "qwen_image"
    }
},
```

**C. 올바른 폴더에 모델 배치 (중요!)**

ComfyUI 노드별 모델 폴더:
- `UNETLoader` → `comfyui/models/diffusion_models/`
- `CLIPLoader` → `comfyui/models/text_encoders/`
- `VAELoader` → `comfyui/models/vae/`

**심볼릭 링크 생성**:

```bash
# UNET 모델 (diffusion_models 폴더에!)
cd /home/spai0323/Ad_Content_Creation_Service_Team3/comfyui/models/diffusion_models
ln -sf /home/shared/Qwen-Image-Edit-2509-Q8_0.gguf .

# CLIP 모델
cd /home/spai0323/Ad_Content_Creation_Service_Team3/comfyui/models/text_encoders
ln -sf /home/shared/t5-v1_1-xxl-encoder-Q8_0.gguf .

# 확인
ls -lh Qwen*.gguf
ls -lh t5*.gguf
```

**⚠️ 주의사항**:
- 처음에 `unet/` 폴더에 링크했으나, `UNETLoader`는 `diffusion_models/` 폴더를 사용함
- 폴더 위치가 잘못되면 ComfyUI가 모델을 인식하지 못함 (빈 리스트 반환)

#### 3.3 ComfyUI 노드 분석

**UNETLoader** (`comfyui/nodes.py:913`):
- 범용 UNET 로더
- `diffusion_models` 폴더의 모든 파일 지원
- weight_dtype 옵션: default, fp8_e4m3fn, fp8_e5m2 등

**CLIPLoader** (`comfyui/nodes.py:934`):
- 지원 타입: `qwen_image`, `flux2`, `stable_diffusion` 등
- Qwen은 `qwen_image` 타입 사용
- T5 인코더 단일 사용 (CLIP L 불필요)

---

## ❌ 미해결 이슈: 페이지4 Qwen 정밀 편집 모드

### 문제 상황

**최종 오류 메시지**:
```json
{
  "error": {"type": "prompt_outputs_failed_validation"},
  "node_errors": {
    "2": {
      "errors": [{
        "type": "value_not_in_list",
        "details": "unet_name: 'Qwen-Image-Edit-2509-Q8_0.gguf' not in []"
      }],
      "class_type": "UNETLoader"
    },
    "3": {
      "errors": [{
        "type": "value_not_in_list", 
        "details": "clip_name: 't5-v1_1-xxl-encoder-Q8_0.gguf' not in ['clip_l.safetensors']"
      }],
      "class_type": "CLIPLoader"
    }
  }
}
```

### 시도한 해결 방법

#### 1차 시도: 워크플로우 노드 타입 변경
- **변경**: `UnetLoaderGGUF` → `UNETLoader`
- **변경**: `DualCLIPLoaderGGUF` → `CLIPLoader(type="qwen_image")`
- **결과**: ❌ 실패 (노드 타입은 올바르나 모델 인식 안 됨)

#### 2차 시도: 모델 파일 올바른 폴더 배치
```bash
# UNET 모델
comfyui/models/diffusion_models/Qwen-Image-Edit-2509-Q8_0.gguf (심볼릭 링크)

# CLIP 모델  
comfyui/models/text_encoders/t5-v1_1-xxl-encoder-Q8_0.gguf (심볼릭 링크)
```
- **확인**: `ls -lh` 결과 심볼릭 링크 정상 생성됨
- **결과**: ❌ 실패 (ComfyUI가 스캔하지 못함)

#### 3차 시도: 서버 재시작
```bash
scripts/stop_all.sh
scripts/start_all.sh
```
- **결과**: ❌ 실패 (ComfyUI 로그에서 모델 목록 여전히 비어있음)

#### 4차 시도: 동적 폴백 로직 추가
- **코드 수정**: `comfyui_workflows.py`에 T5 파일 존재 여부 체크
- **폴백**: T5 없으면 `DualCLIPLoader`로 대체
- **결과**: ❌ 실패 (근본 원인 미해결)

### 근본 원인 분석

**ComfyUI 로그 확인 결과**:
```
CLIPLoader 3:
  - Value not in list: clip_name: 't5-v1_1-xxl-encoder-Q8_0.gguf' not in ['clip_l.safetensors']
UNETLoader 2:
  - Value not in list: unet_name: 'Qwen-Image-Edit-2509-Q8_0.gguf' not in []
```

**문제점**:
1. **UNETLoader의 diffusion_models 목록이 빈 배열** `[]`
   - `folder_paths.get_filename_list("diffusion_models")`가 빈 리스트 반환
   - 심볼릭 링크가 있어도 ComfyUI가 스캔하지 못함
   
2. **CLIPLoader의 text_encoders 목록에 T5 없음**
   - `clip_l.safetensors`만 인식
   - T5 GGUF 파일을 텍스트 인코더로 인식하지 못함

3. **가능한 원인**:
   - ComfyUI의 `folder_paths` 모듈이 GGUF 파일을 필터링함
   - 모델 스캔 시 확장자나 파일 형식 검증 실패
   - Custom nodes의 GGUF 지원이 특정 폴더에만 적용됨

### 대안 검토

#### 옵션 A: CheckpointLoaderSimple 사용
- Qwen을 전체 체크포인트로 로드
- **문제**: 21GB Qwen 모델이 체크포인트 형식이 아님 (GGUF만 존재)

#### 옵션 B: UnetLoaderGGUF 화이트리스트 수정
- ComfyUI-GGUF 노드의 허용 모델 목록 확장
- **문제**: 소스 코드 수정 필요, 업데이트 시 초기화됨

#### 옵션 C: 정밀 편집 모드 비활성화
- 현재 작동하는 4가지 모드만 제공
- **장점**: 안정성 우선, 사용자 혼란 방지
- **단점**: Qwen의 강력한 자연어 편집 기능 사용 불가

### 최종 결정

**페이지4에서 Qwen 정밀 편집 모드 제외**

**이유**:
1. ComfyUI가 GGUF 형식 Qwen 모델을 `diffusion_models` 폴더에서 인식하지 못함
2. 여러 시도에도 불구하고 근본 원인 해결 실패
3. 나머지 4가지 모드는 정상 작동 (FLUX Fill, Portrait, Product, Hybrid)

**조치 사항**:
- `configs/image_editing_config.yaml`에서 `qwen_edit` 모드 주석 처리
- Frontend에서 "🎯 정밀 편집 모드" 선택 항목 제거
- 문서에 미해결 이슈로 기록

---

## 📊 수정 통계 (최종)

```
변경된 파일: 5개
 README.md                         |  8 줄 변경
 src/backend/main.py               |  2 줄 변경
 src/backend/services.py           |  2 줄 변경
 src/frontend/app.py               | 14 줄 변경
 src/frontend/frontend_config.yaml | 16 줄 변경

시도했으나 미완료:
 src/backend/comfyui_workflows.py  | 20 줄 변경 (Qwen 워크플로우 - 작동 안 함)
```

---

## 🧪 테스트 방법

### 1. 서버 재시작
```bash
scripts/stop_all.sh
scripts/start_all.sh
```

### 2. 페이지1 테스트 (리브랜딩) ✅
1. Streamlit 앱 접속
2. 페이지1에서 "서비스 분야" 텍스트 입력란 확인
3. 다양한 업종 입력 테스트 (예: "베이커리", "온라인 강의")
4. GPT 문구 생성 정상 작동 확인

### 3. 페이지4 편집 모드 테스트 ✅
**작동하는 4가지 모드**:
1. 👤 인물 모드 (Portrait Mode)
2. 📦 제품 모드 (Product Mode)  
3. 🎭 하이브리드 모드 (Hybrid Mode)
4. 🖼️ FLUX Fill 모드

**제외된 모드**:
- ~~🎯 정밀 편집 모드 (Qwen-Image-Edit)~~ → ComfyUI 모델 인식 실패

---

## 🎯 달성된 효과

1. **확장성**: 헬스케어에서 모든 소상공인 업종으로 확장 ✅
2. **유연성**: 사용자가 직접 업종 입력 → 더 다양한 분야 커버 ✅
3. ~~**안정성**: Qwen 워크플로우 오류 해결~~ → ❌ 미해결

---

## 📝 관련 이슈 및 향후 과제

### 미해결 이슈
- **Issue**: Qwen-Image-Edit GGUF 모델을 ComfyUI UNETLoader가 인식하지 못함
- **Status**: 보류 (대안 없음)
- **Impact**: 페이지4의 5가지 편집 모드 중 1가지(정밀 편집) 비활성화

### 향후 개선 방향
1. ComfyUI-GGUF 업데이트 대기 (Qwen 모델 공식 지원 여부)
2. Qwen 모델의 diffusers 형식 버전 탐색
3. 별도 Qwen 전용 백엔드 구현 (ComfyUI 우회)

---

## 🔗 참고 자료

- ComfyUI `UNETLoader`: `comfyui/nodes.py:913`
- ComfyUI `CLIPLoader`: `comfyui/nodes.py:934`
- ComfyUI `folder_paths` 모듈: 모델 스캔 및 검증 로직
- Qwen 지원 타입: `qwen_image` (CLIPLoader에서 지원)
- T5 인코더: `/home/shared/t5-v1_1-xxl-encoder-Q8_0.gguf`

---

## 🔤 페이지5: 3D 캘리그라피 생성 문제 확인

### 문제 증상

사용자 보고: "3D 스타일과 색상이 적용되지 않고 있습니다"

### 원인 분석

**코드 확인 결과** (`src/backend/text_overlay.py`):

1. **프롬프트 생성 정상**:
   ```python
   style_prompts = {
       "default": f"3D {color_name} calligraphy text, natural embossed letters, professional studio lighting...",
       "emboss": f"3D {color_name} embossed calligraphy, raised metallic surface...",
       # ... 다른 스타일들
   }
   ```

2. **ControlNet 파이프라인 호출 정상**:
   ```python
   result = pipeline(
       prompt=prompt,
       negative_prompt=negative_prompt,
       image=base_image,  # 흑백 이미지를 깊이 맵으로 사용
       num_inference_steps=30,
       controlnet_conditioning_scale=0.8,
       guidance_scale=7.5,
       width=base_image.width,
       height=base_image.height
   ).images[0]
   ```

3. **로그 출력 확인**:
   - `print(f"🎨 ControlNet 3D 렌더링 시작 (색상: {color_hex}, 스타일: {style})")`
   - `print(f"  프롬프트: {prompt}")`
   - 로그가 출력되는지 확인 필요

### 가능한 원인

1. **ControlNet 파이프라인 로드 실패**:
   - `get_calligraphy_pipeline()` 함수에서 모델 로드 오류
   - `device_map="auto"` 설정 문제 (이전 수정 사항)

2. **CUDA 메모리 부족**:
   - ControlNet + SDXL 모델 동시 로드 시 메모리 부족
   - CPU offload 미작동

3. **ControlNet 모델 미다운로드**:
   - `diffusers/controlnet-depth-sdxl-1.0-small` 모델 누락

### 해결 방법

**1단계: 로그 확인**

```bash
# 백엔드 로그에서 캘리그라피 관련 메시지 확인
tail -f logs/backend.log | grep -E "캘리그라피|ControlNet|3D 렌더링"

# 테스트 요청 보내기
# Streamlit 페이지5에서 텍스트 생성 시도
```

**2단계: ControlNet 모델 확인**

```bash
# ControlNet 모델 다운로드 여부 확인
ls -lh comfyui/models/controlnet/ | grep depth
```

**3단계: 파이프라인 로드 확인**

`src/backend/text_overlay.py:get_calligraphy_pipeline()` 함수:

```python
def get_calligraphy_pipeline():
    global _calligraphy_pipeline
    if _calligraphy_pipeline is None:
        print("🔧 ControlNet 캘리그라피 파이프라인 로딩 중...")
        
        # ControlNet 로드
        controlnet = ControlNetModel.from_pretrained(
            "diffusers/controlnet-depth-sdxl-1.0-small",
            torch_dtype=torch.float16,
            cache_dir="./cache/hf_models"
        )
        
        # 파이프라인 생성 (device_map="auto" 사용)
        _calligraphy_pipeline = StableDiffusionXLControlNetPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            controlnet=controlnet,
            torch_dtype=torch.float16,
            cache_dir="./cache/hf_models",
            device_map="auto"  # ✅ 이전 수정사항
        )
        
        print("✅ ControlNet 캘리그라피 파이프라인 로드 완료")
    
    return _calligraphy_pipeline
```

**4단계: 예외 처리 확인**

`apply_controlnet_3d_rendering()` 함수에 예외 처리가 있어, 오류 발생 시 원본 이미지 반환:

```python
except Exception as e:
    print(f"⚠️ ControlNet 렌더링 실패, 원본 반환: {e}")
    import traceback
    print(traceback.format_exc())
    return base_image  # ❌ 흑백 원본 반환 → 3D 효과 없음
```

→ 로그에서 이 메시지가 출력되는지 확인 필요!

### 임시 해결책

ControlNet이 작동하지 않는 경우, 간단한 PIL 기반 3D 효과로 대체:

```python
def apply_simple_3d_effect(image: Image.Image, color_hex: str) -> Image.Image:
    """
    ControlNet 대신 간단한 PIL 기반 3D 효과
    (그림자 + 색상 오버레이)
    """
    # RGB 변환
    rgb_image = image.convert("RGB")
    
    # HEX를 RGB로 변환
    color_rgb = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    
    # 색상 오버레이
    colored = Image.new("RGB", rgb_image.size, color_rgb)
    result = Image.blend(rgb_image, colored, alpha=0.5)
    
    return result
```

---

## ✅ 체크리스트

- [x] 프로젝트 제목 변경 (5개 파일)
- [x] 헬스케어 관련 콘텐츠 제거
- [x] selectbox → text_input 변경
- [x] GPT 프롬프트 호환성 유지
- [x] ~~Qwen 모델 심볼릭 링크 생성~~ (생성했으나 ComfyUI 인식 실패)
- [x] ~~Qwen 워크플로우 노드 수정~~ (수정했으나 작동 안 함)
- [ ] ~~Qwen 정밀 편집 모드 작동~~ (미해결 - 제외)
- [x] 에러 분석 및 문서화
- [x] 미해결 이슈 기록
- [x] README.md 트러블슈팅 섹션 업데이트

---

## 💡 교훈 및 인사이트

### ComfyUI GGUF 모델 로딩 제약사항

1. **UNETLoader의 제한**:
   - `folder_paths.get_filename_list("diffusion_models")`가 모든 GGUF를 인식하지 않음
   - 특정 포맷이나 메타데이터 검증을 거침
   - 심볼릭 링크로 배치해도 스캔 단계에서 필터링될 수 있음

2. **CLIPLoader의 text_encoders 폴더**:
   - CLIP 모델(.safetensors)과 T5 인코더(.gguf)를 구분
   - GGUF 형식 T5가 일부 환경에서 인식되지 않을 수 있음
   - `type="qwen_image"` 지정해도 허용 목록에 없으면 검증 실패

3. **워크플로우 검증 타이밍**:
   - ComfyUI는 큐 등록 시점에 노드 입력값 검증
   - 백엔드에서 워크플로우 생성 시점에는 에러 없음
   - ComfyUI 서버로 전송 후 검증 실패 확인 가능

### 개발 프로세스 개선점

1. **단계별 검증 필요**:
   - 모델 파일 배치 → ComfyUI 재시작 → API로 모델 목록 조회
   - 워크플로우 JSON을 ComfyUI Web UI에서 직접 테스트
   - 백엔드 통합 전에 ComfyUI 레벨 검증 완료

2. **폴백 전략 수립**:
   - 신규 모델 추가 시 기존 모델로 대체 가능한 플랜 B 마련
   - 사용자 경험을 위해 일부 기능 비활성화 옵션 고려

3. **문서화의 중요성**:
   - 실패한 시도도 상세히 기록하여 중복 작업 방지
   - 제약사항과 한계를 명확히 문서화
