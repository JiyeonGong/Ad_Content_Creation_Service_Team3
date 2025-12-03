# FLUX.1-Fill 및 Qwen-Image-Edit 통합 기록

**날짜**: 2025-12-02  
**작업자**: AI Assistant  
**목적**: 페이지4에 FLUX.1-Fill-dev-Q8 및 Qwen-Image-Edit-2509-Q8 모델 통합

---

## 1. 개요

### 목표
- 페이지4 이미지 편집 페이지에 2개의 새로운 편집 모드 추가
- `/home/shared/FLUX.1-Fill-dev-Q8_0.gguf` (18GB) - 인페인팅/아웃페인팅
- `/home/shared/Qwen-Image-Edit-2509-Q8_0.gguf` (21GB) - 정밀 편집

### 기존 구조
- **페이지4**: 3가지 편집 모드 (portrait_mode, product_mode, hybrid_mode)
- **프레임워크**: Streamlit + FastAPI + ComfyUI
- **모델 포맷**: GGUF (양자화)

---

## 2. 수정 파일 목록

### 2.1 Config 파일
- **`configs/image_editing_config.yaml`**
  - `editing_modes` 섹션에 `flux_fill` 및 `qwen_edit` 모드 추가
  - `models` 섹션에 모델 경로 업데이트
    - `flux_fill.path`: `/home/shared/FLUX.1-Fill-dev-Q8_0.gguf`
    - `qwen_edit.path`: `/home/shared/Qwen-Image-Edit-2509-Q8_0.gguf`

### 2.2 Backend 파일

#### **`src/backend/comfyui_workflows.py`**

**추가된 함수**:
```python
def get_flux_fill_mode_workflow() -> Dict[str, Any]
def get_qwen_edit_mode_workflow() -> Dict[str, Any]
```

**워크플로우 구조**:

**FLUX.1-Fill Mode (15개 노드)**:
- 노드 1: LoadImage (입력 이미지)
- 노드 2: UnetLoaderGGUF (FLUX.1-Fill-dev-Q8_0.gguf)
- 노드 3: DualCLIPLoaderGGUF
- 노드 4: VAELoader (ae.safetensors)
- 노드 5: CLIPTextEncode (positive 프롬프트)
- 노드 6: CLIPTextEncode (negative 프롬프트)
- 노드 7: FluxGuidance
- 노드 10: BackgroundEraseNetwork (BEN2 - 자동 마스크 생성)
- 노드 11: ImageToMask (알파 채널 추출)
- 노드 12: InvertMask (배경 영역만 선택)
- 노드 20: VAEEncode (원본 이미지 인코딩)
- 노드 21: SetLatentNoiseMask (마스크 적용)
- 노드 30: KSampler (인페인팅 실행)
- 노드 31: VAEDecode
- 노드 50: SaveImage

**Qwen-Image-Edit Mode (11개 노드)**:
- 노드 1: LoadImage
- 노드 2: UnetLoaderGGUF (Qwen-Image-Edit-2509-Q8_0.gguf)
- 노드 3: DualCLIPLoaderGGUF
- 노드 4: VAELoader
- 노드 5: CLIPTextEncode (자연어 편집 명령)
- 노드 6: CLIPTextEncode (negative)
- 노드 7: FluxGuidance
- 노드 20: VAEEncode (원본 이미지)
- 노드 30: KSampler (정밀 편집)
- 노드 31: VAEDecode
- 노드 50: SaveImage

**수정된 함수**:
```python
def get_workflow_template(experiment_id: str)
  # flux_fill_mode, qwen_edit_mode 케이스 추가

def update_workflow_inputs(...)
  # FLUX Fill / Qwen 모드 전용 파라미터 업데이트 로직 추가

def get_pipeline_steps_for_mode(experiment_id: str)
  # flux_fill_mode, qwen_edit_mode 파이프라인 단계 매핑 추가
```

#### **`src/backend/services.py`**

**수정된 함수**:
```python
def get_image_editing_experiments() -> dict
```
- `config.get("experiments", [])` → `config.get("editing_modes", {})` 변경
- 새로운 구조에 맞게 모드 목록 생성 로직 업데이트
- flux_fill_mode, qwen_edit_mode 자동 포함

**docstring 업데이트**:
```python
def edit_image_with_comfyui(experiment_id: str, ...)
```
- 가능한 experiment_id 목록에 "flux_fill_mode", "qwen_edit_mode" 추가

### 2.3 Frontend 파일

#### **`src/frontend/model_selector.py`**

**수정된 함수**:
```python
def render_editing_mode_selector(self) -> str
```

**추가 내용**:
```python
EDITING_MODES = {
    # ... 기존 모드 ...
    "flux_fill_mode": {
        "id": "flux_fill_mode",
        "name": "🖌️ 인페인팅 모드",
        "icon": "🖌️"
    },
    "qwen_edit_mode": {
        "id": "qwen_edit_mode",
        "name": "🎯 정밀 편집 모드",
        "icon": "🎯"
    }
}

mode_descriptions = {
    # ... 기존 설명 ...
    "flux_fill_mode": "마스크 영역을 새로운 내용으로 채우거나 이미지 확장 (FLUX.1-Fill)",
    "qwen_edit_mode": "자연어 명령으로 정밀하게 이미지 편집 (Qwen-Image-Edit)"
}
```

#### **`src/frontend/app.py`**

**페이지4 함수 수정**:
```python
def render_image_editing_experiment_page(config, api)
```

**변경 사항**:

1. **모드 이름 매핑 업데이트**:
```python
mode_display_names = {
    # ... 기존 모드 ...
    "flux_fill_mode": "🖌️ 인페인팅 모드",
    "qwen_edit_mode": "🎯 정밀 편집 모드"
}
```

2. **파라미터 UI 로직 개선**:
```python
# ControlNet 옵션 (portrait/hybrid만 해당)
if selected_mode_id in ["portrait_mode", "hybrid_mode"]:
    # ControlNet 설정
    ...
elif selected_mode_id in ["flux_fill_mode", "qwen_edit_mode"]:
    # FLUX Fill / Qwen 전용 denoise_strength만 표시
    denoise_strength = st.slider(
        "편집 강도 (Denoise)",
        0.5, 1.0,
        value=0.9 if selected_mode_id == "flux_fill_mode" else 0.7,
        ...
    )
    
    # FLUX Fill 전용 안내
    if selected_mode_id == "flux_fill_mode":
        st.info("💡 BEN2로 자동 배경 제거하여 마스크 생성합니다")
```

---

## 3. 핵심 기능 설명

### 3.1 FLUX.1-Fill Mode (인페인팅)

**파이프라인**:
1. 입력 이미지 로드
2. **BEN2로 자동 배경 제거** → 마스크 생성
3. 마스크 반전 (배경 영역만 선택)
4. FLUX Fill로 마스크 영역을 프롬프트 기반으로 채우기
5. 결과 저장

**사용 예시**:
- "배경을 현대적인 체육관으로 변경"
- "왼쪽에 운동 기구 추가" (outpainting)

**파라미터**:
- `denoise_strength`: 0.5 ~ 1.0 (기본 0.9)
- `steps`: 28 (권장)
- `guidance_scale`: 3.5

**특징**:
- BEN2가 자동으로 배경 제거 → 사용자는 마스크 그릴 필요 없음
- FLUX Fill의 강력한 인페인팅 능력 활용

### 3.2 Qwen-Image-Edit Mode (정밀 편집)

**파이프라인**:
1. 입력 이미지 로드
2. 자연어 편집 명령 인코딩
3. Qwen으로 이미지 전체를 기반으로 정밀 편집
4. 결과 저장

**사용 예시**:
- "운동복 색상을 파란색에서 빨간색으로 변경"
- "손에 물병 추가"
- "안경 제거"

**파라미터**:
- `strength` (denoise_strength): 0.5 ~ 1.0 (기본 0.7)
- `steps`: 28
- `guidance_scale`: 3.5

**특징**:
- 자연어 이해 능력이 뛰어남 (Qwen 기반)
- 외관 편집(색상, 질감), 의미론적 편집(객체 추가/제거), 텍스트 편집 모두 가능
- 마스크 없이 전체 이미지 기반 편집

---

## 4. 모드 비교표

| 모드 | 모델 | 크기 | 주요 기능 | 마스크 | 속도 | 용도 |
|------|------|------|-----------|--------|------|------|
| **Portrait** | FLUX.1-dev-Q8 | 12GB | 얼굴 보존, 의상/배경 변경 | Face Detector | 중간 | 인물 사진 편집 |
| **Product** | FLUX.1-dev-Q4 + Fill | 6.4GB + 18GB | 제품 보존, 배경 생성 | BEN2 | 느림 | 제품 사진 배경 교체 |
| **Hybrid** | FLUX.1-dev-Q8 | 12GB | 얼굴+제품 보존 | Face + BEN2 | 느림 | 복합 편집 |
| **🆕 FLUX Fill** | FLUX.1-Fill-Q8 | 18GB | 인페인팅/아웃페인팅 | BEN2 (자동) | 중간 | 배경 변경, 객체 추가 |
| **🆕 Qwen Edit** | Qwen-Edit-Q8 | 21GB | 정밀 자연어 편집 | 없음 | 중간 | 색상/객체 변경 |

---

## 5. 검증 결과

### 5.1 코드 검증
```bash
✅ Python 문법 오류 없음 (get_errors)
✅ YAML 파일 문법 검증 성공
✅ Config 로드 성공
```

### 5.2 구조 검증
```
📋 등록된 편집 모드 (5개):
  - portrait_mode: 👤 인물 모드
  - product_mode: 📦 제품 모드
  - hybrid_mode: ✨ 고급 모드
  - flux_fill_mode: 🖌️ 인페인팅 모드
  - qwen_edit_mode: 🎯 정밀 편집 모드

🤖 등록된 모델 경로:
  - FLUX.1-Fill-dev-Q8: /home/shared/FLUX.1-Fill-dev-Q8_0.gguf ✅ (18GB)
  - Qwen-Image-Edit-2509-Q8: /home/shared/Qwen-Image-Edit-2509-Q8_0.gguf ✅ (21GB)
```

### 5.3 워크플로우 템플릿 검증
```
🔧 워크플로우 템플릿 검증:
  - portrait_mode: 21개 노드 ✅
  - product_mode: 21개 노드 ✅
  - hybrid_mode: 23개 노드 ✅
  - flux_fill_mode: 15개 노드 ✅
  - qwen_edit_mode: 11개 노드 ✅
```

### 5.4 워크플로우 업데이트 함수 검증
```
✅ flux_fill_mode:
   입력 프롬프트: 배경을 현대적인 체육관으로 변경
   노드 5 텍스트 설정 확인 ✅

✅ qwen_edit_mode:
   입력 프롬프트: 운동복 색상을 파란색에서 빨간색으로 변경
   노드 5 텍스트 설정 확인 ✅
```

---

## 6. 사용 방법

### 6.1 Streamlit UI에서 사용

1. **모드 선택** (사이드바)
   - "✨ 편집 모드 선택" 섹션에서 선택
   - 🖌️ 인페인팅 모드 또는 🎯 정밀 편집 모드

2. **이미지 업로드**
   - PNG/JPG 파일 업로드

3. **프롬프트 입력**
   - FLUX Fill: "배경을 현대적인 체육관으로 변경"
   - Qwen: "운동복을 빨간색으로 변경"

4. **파라미터 조정**
   - Steps: 28 (권장)
   - Guidance Scale: 3.5
   - 편집 강도: 0.9 (FLUX Fill) / 0.7 (Qwen)

5. **편집 실행**
   - "🚀 이미지 편집 실행" 버튼 클릭

### 6.2 API 직접 호출

**FLUX Fill 예시**:
```python
payload = {
    "experiment_id": "flux_fill_mode",
    "input_image_base64": "...",
    "prompt": "배경을 현대적인 체육관으로 변경",
    "steps": 28,
    "guidance_scale": 3.5,
    "denoise_strength": 0.9
}
result = api.call_image_editing_experiment(payload)
```

**Qwen Edit 예시**:
```python
payload = {
    "experiment_id": "qwen_edit_mode",
    "input_image_base64": "...",
    "prompt": "운동복 색상을 파란색에서 빨간색으로 변경",
    "steps": 28,
    "guidance_scale": 3.5,
    "denoise_strength": 0.7
}
result = api.call_image_editing_experiment(payload)
```

---

## 7. 주의사항 및 제한사항

### 7.1 서버 미실행 상황
- **현재 상태**: ComfyUI 서버가 실행되지 않음
- **영향**: 실제 이미지 생성 테스트 불가
- **해결책**: 서버 실행 후 테스트 필요

### 7.2 메모리 요구사항
- **FLUX Fill**: 18GB (GGUF) + CLIP + VAE ≈ 24GB VRAM
- **Qwen Edit**: 21GB (GGUF) + CLIP + VAE ≈ 27GB VRAM
- **권장**: RTX 4090 (24GB) 이상 또는 A6000 (48GB)

### 7.3 ComfyUI 노드 요구사항

**필수 Custom Nodes**:
1. **ComfyUI-GGUF** (GGUF 모델 로드)
   - `UnetLoaderGGUF`
   - `DualCLIPLoaderGGUF`

2. **BEN2** (배경 제거)
   - `BackgroundEraseNetwork`

3. **FLUX 관련**
   - `FluxGuidance`
   - `SetLatentNoiseMask`

**설치 확인**:
```bash
cd comfyui/custom_nodes
ls -la | grep -E "gguf|ben2|flux"
```

---

## 8. 트러블슈팅

### 8.1 모델 로드 실패
**증상**: "UnetLoaderGGUF not found"

**원인**: ComfyUI-GGUF 노드 미설치

**해결**:
```bash
cd comfyui/custom_nodes
git clone https://github.com/city96/ComfyUI-GGUF.git
pip install -r ComfyUI-GGUF/requirements.txt
```

### 8.2 BEN2 마스크 생성 실패
**증상**: "BackgroundEraseNetwork not found"

**원인**: BEN2 노드 미설치

**해결**:
```bash
cd comfyui/custom_nodes
git clone https://github.com/PramaLLC/BEN2_ComfyUI.git
```

### 8.3 VRAM 부족
**증상**: "CUDA out of memory"

**원인**: 모델이 너무 큼 (21GB+)

**해결책**:
1. Q4 모델로 다운그레이드 (메모리 절약)
2. `--lowvram` 플래그로 ComfyUI 실행
3. 배치 크기를 1로 제한

---

## 9. 향후 개선 사항

### 9.1 수동 마스크 지원 (FLUX Fill)
- 현재: BEN2 자동 마스크만 지원
- 개선: 사용자가 브러시로 직접 마스크 그리기 기능 추가

### 9.2 Qwen 다중 이미지 지원
- 현재: 단일 이미지만 편집
- 개선: 참조 이미지를 추가로 제공하여 스타일 전이

### 9.3 프롬프트 템플릿
- 모드별 자주 사용하는 프롬프트 템플릿 제공
- 예: "배경을 [장소]로 변경", "[색상1]을 [색상2]로 변경"

---

## 10. 참고 자료

### 10.1 모델 정보
- **FLUX.1-Fill**: https://github.com/black-forest-labs/FLUX.1-Fill
- **Qwen-Image-Edit**: https://huggingface.co/Qwen/Qwen-Image-Edit-2509

### 10.2 관련 문서
- `docs/IMAGE_EDITING_GUIDE.md` (첨부 파일)
- `docs/COMFYUI_INTEGRATION.md`
- `recording/2025-12-02_i2i_workflow_fix.md` (I2I 문제 해결)

### 10.3 ComfyUI 워크플로우
- Portrait Mode: 21 노드 (Face Detector + ControlNet)
- Product Mode: 21 노드 (BEN2 + FLUX Fill 블렌딩)
- Hybrid Mode: 23 노드 (Face + Product 복합)
- **FLUX Fill**: 15 노드 (BEN2 마스크 + 인페인팅)
- **Qwen Edit**: 11 노드 (단순 I2I 구조)

---

## 11. 결론

### 완료된 작업
✅ FLUX.1-Fill-dev-Q8 워크플로우 구현 (15개 노드)  
✅ Qwen-Image-Edit-2509-Q8 워크플로우 구현 (11개 노드)  
✅ Config 파일 업데이트 (editing_modes + models)  
✅ Backend 로직 추가 (services.py, comfyui_workflows.py)  
✅ Frontend UI 업데이트 (app.py, model_selector.py)  
✅ 모든 코드 검증 완료 (문법, 구조, 함수)  
✅ 모델 경로 확인 (/home/shared/*.gguf)  

### 테스트 필요
⚠️ ComfyUI 서버 실행 후 실제 이미지 생성 테스트  
⚠️ BEN2 자동 마스크 생성 확인  
⚠️ FLUX Fill 인페인팅 품질 검증  
⚠️ Qwen 자연어 편집 정확도 검증  

### 다음 단계
1. ComfyUI 서버 실행
2. 5가지 모드 각각 테스트 이미지 생성
3. 결과 품질 평가 및 파라미터 튜닝
4. 사용자 문서 업데이트

---

**작성일**: 2025-12-02  
**검증 완료**: ✅ 모든 코드 에러 없음  
**서버 테스트**: ⚠️ 미실행 상태로 실제 생성 테스트 불가
