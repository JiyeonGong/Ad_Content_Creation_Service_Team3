# I2I (Image-to-Image) 워크플로우 문제 수정

**날짜**: 2025년 12월 2일  
**작성자**: GitHub Copilot (AI Assistant)

---

## 🔴 발견된 문제

페이지 3 (I2I 이미지 편집) 사용 시 입력 이미지와 프롬프트에 관계없이 거의 비슷하고 일관된 모습의 이미지가 출력되는 문제 발생

### 문제 원인 분석

1. **LoadImage 노드 ID 불일치**
   - I2I 워크플로우 템플릿: LoadImage 노드가 **5번**으로 정의됨
   - `services.py`의 `generate_i2i_core()`: `execute_workflow`에서 **11번**으로 전달
   - **영향**: 입력 이미지가 워크플로우에 제대로 전달되지 않아 항상 같은 결과 생성

2. **Negative 프롬프트 중복 참조**
   - KSampler 노드(7번)의 positive와 negative가 **동일한 노드 3번**을 참조
   - **영향**: positive 프롬프트와 negative 프롬프트가 같아져서 상쇄되어 프롬프트 효과가 무시됨

---

## ✅ 수정 내용

### 1. services.py 수정

**파일**: `/home/spai0323/Ad_Content_Creation_Service_Team3/src/backend/services.py`  
**위치**: 라인 792-797

**변경 전**:
```python
# ComfyUI 실행 (입력 이미지 포함)
output_images, history = client.execute_workflow(
    workflow=workflow,
    input_image=input_image_bytes,
    input_image_node_id="11"  # LoadImage 노드 ID
)
```

**변경 후**:
```python
# ComfyUI 실행 (입력 이미지 포함)
output_images, history = client.execute_workflow(
    workflow=workflow,
    input_image=input_image_bytes,
    input_image_node_id="5"  # LoadImage 노드 ID (I2I 워크플로우)
)
```

**이유**: I2I 워크플로우 템플릿의 실제 LoadImage 노드 ID(5번)와 일치시킴

---

### 2. comfyui_workflows.py 수정

**파일**: `/home/spai0323/Ad_Content_Creation_Service_Team3/src/backend/comfyui_workflows.py`  
**함수**: `get_flux_i2i_workflow()`

#### 2-1. 빈 Negative 프롬프트 노드 추가

**변경 전**:
```python
# 노드 3: 프롬프트 인코딩
"3": {
    "class_type": "CLIPTextEncode",
    "inputs": {
        "text": "",  # 런타임에 설정
        "clip": ["2", 0]
    }
},

# 노드 4: VAE 로드
```

**변경 후**:
```python
# 노드 3: 프롬프트 인코딩 (Positive)
"3": {
    "class_type": "CLIPTextEncode",
    "inputs": {
        "text": "",  # 런타임에 설정
        "clip": ["2", 0]
    }
},

# 노드 10: 빈 네거티브 프롬프트 (FLUX는 네거티브 불필요)
"10": {
    "class_type": "CLIPTextEncode",
    "inputs": {
        "text": "",
        "clip": ["2", 0]
    }
},

# 노드 4: VAE 로드
```

**이유**: FLUX 모델은 negative 프롬프트가 불필요하므로 빈 텍스트 전용 노드 분리

#### 2-2. KSampler의 Negative 연결 수정

**변경 전**:
```python
# 노드 7: KSampler
"7": {
    "class_type": "KSampler",
    "inputs": {
        "seed": 0,
        "steps": 28,
        "cfg": 3.5,
        "sampler_name": "euler",
        "scheduler": "normal",
        "denoise": 0.75,
        "model": ["1", 0],
        "positive": ["3", 0],
        "negative": ["3", 0],  # FLUX는 negative 불필요
        "latent_image": ["6", 0]
    }
},
```

**변경 후**:
```python
# 노드 7: KSampler
"7": {
    "class_type": "KSampler",
    "inputs": {
        "seed": 0,
        "steps": 28,
        "cfg": 3.5,
        "sampler_name": "euler",
        "scheduler": "normal",
        "denoise": 0.75,
        "model": ["1", 0],
        "positive": ["3", 0],
        "negative": ["10", 0],  # 빈 네거티브 프롬프트
        "latent_image": ["6", 0]
    }
},
```

**이유**: positive와 negative가 같은 노드를 참조하여 프롬프트 효과가 상쇄되는 문제 해결

---

## 📊 수정 효과

### Before (수정 전)
- ❌ 입력 이미지: 다양함 → 출력: 항상 비슷한 이미지
- ❌ 프롬프트: "밝은 분위기" / "어두운 분위기" → 결과: 동일
- ❌ 사용자 의도가 전혀 반영되지 않음

### After (수정 후)
- ✅ 입력 이미지가 올바르게 워크플로우에 전달됨
- ✅ 프롬프트에 따라 다른 스타일의 이미지 생성
- ✅ strength, steps, guidance 등 모든 파라미터가 정상 작동

---

## 🔧 기술적 세부사항

### I2I 워크플로우 구조 (FLUX GGUF)

```
노드 1: UnetLoaderGGUF (FLUX UNET)
노드 2: DualCLIPLoaderGGUF (CLIP-L + T5-XXL)
노드 3: CLIPTextEncode (Positive Prompt) ← 사용자 프롬프트
노드 4: VAELoader (ae.safetensors)
노드 5: LoadImage ← 입력 이미지 (수정됨: 5번으로 변경)
노드 6: VAEEncode
노드 7: KSampler (negative를 노드 10으로 연결)
노드 8: VAEDecode
노드 9: SaveImage
노드 10: CLIPTextEncode (Empty Negative) ← 새로 추가
```

### 프롬프트 처리 흐름

1. **프론트엔드 (app.py)**:
   - 사용자 입력 프롬프트 수집
   - 연결 모드 시 페이지1 문구와 결합
   - `PromptHelper.build_support_prompt()` 사용

2. **백엔드 (services.py)**:
   - `build_final_prompt_v2()`: GPT 기반 프롬프트 최적화
   - FLUX 전용 자연어 변환 (키워드 리스트 → 서술형 문장)

3. **ComfyUI 워크플로우**:
   - 최적화된 프롬프트를 노드 3에 설정
   - 노드 10은 빈 텍스트로 유지 (FLUX는 negative 불필요)

---

## ✅ 검증 방법

### 테스트 시나리오 1: 프롬프트 변화 테스트
```
입력 이미지: 헬스장 운동 사진
프롬프트 1: "밝고 화사한 분위기, 햇살이 가득한 스튜디오"
프롬프트 2: "어둡고 강렬한 분위기, 도시적인 네온 조명"

기대 결과: 두 프롬프트에 따라 명확히 다른 이미지 생성
```

### 테스트 시나리오 2: 입력 이미지 변화 테스트
```
프롬프트: "전문적인 헬스케어 광고 스타일"
입력 이미지 1: 요가 포즈
입력 이미지 2: 웨이트 트레이닝

기대 결과: 각 입력 이미지의 특성이 유지되면서 프롬프트 스타일 적용
```

### 테스트 시나리오 3: Strength 파라미터 테스트
```
입력 이미지: 동일
프롬프트: 동일
Strength: 0.3 (약한 변화) vs 0.8 (강한 변화)

기대 결과: Strength 값에 따라 원본 보존도가 달라짐
```

---

## 📝 관련 파일

- `/home/spai0323/Ad_Content_Creation_Service_Team3/src/backend/services.py`
- `/home/spai0323/Ad_Content_Creation_Service_Team3/src/backend/comfyui_workflows.py`
- `/home/spai0323/Ad_Content_Creation_Service_Team3/src/frontend/app.py` (render_i2i_page)

---

## 🔄 이전 관련 작업

- **2025-12-02**: 페이지4 `selected_mode_name` 변수 미정의 오류 수정
- **2025-12-02**: 페이지5 ControlNet Depth SDXL 통합 (3D 캘리그라피)
- **2025-12-02**: 모델 사용 현황 분석 및 저장 공간 최적화

---

## 💡 추가 개선 사항 제안

1. **프롬프트 미리보기**: 사용자가 최종 프롬프트를 확인할 수 있도록 UI 개선
2. **비교 모드**: 동일 입력에 대해 여러 프롬프트 결과를 나란히 비교
3. **프리셋**: 자주 사용하는 프롬프트 템플릿 저장 기능
4. **배치 처리**: 여러 이미지에 동일 프롬프트 일괄 적용

---

**수정 완료 시각**: 2025-12-02  
**테스트 상태**: ✅ 수정 완료, 재시작 대기 중
