# 이미지 편집 가이드

## 개요

이 프로젝트는 BEN2 배경 제거와 고급 이미지 편집 모델을 결합한 실험적 기능을 제공합니다.

### 지원 모델

1. **FLUX.1-Fill-dev (12B, GGUF Q8_0)**
   - 인페인팅 및 아웃페인팅
   - 마스크 기반 영역 채우기
   - 이미지 확장 (outpainting)

2. **Qwen-Image-Edit-2509 (20B)**
   - 외관 편집 (색상, 질감 변경)
   - 의미론적 편집 (객체 추가/제거)
   - 텍스트 편집 (이미지 내 텍스트 수정)
   - 다중 이미지 편집

---

## 사용 방법

### Streamlit UI에서

1. **페이지 선택**: "이미지 편집 실험" 페이지로 이동

2. **실험 선택**:
   - `BEN2 + FLUX.1-Fill`: 배경 제거 후 인페인팅
   - `BEN2 + Qwen-Image`: 배경 제거 후 정밀 편집

3. **이미지 업로드**: PNG/JPG 형식 지원

4. **프롬프트 입력**: 원하는 편집 내용 설명
   ```
   예시:
   - "배경을 현대적인 체육관으로 변경"
   - "파란색 운동복을 빨간색으로 변경"
   - "손에 아령 추가"
   ```

5. **파라미터 조정**:
   - **Steps**: 10-50 (기본 28)
   - **Guidance Scale**: 1.0-15.0 (기본 3.5)
   - **Strength**: 0.0-1.0 (기본 0.8)

6. **편집 실행**: "이미지 편집" 버튼 클릭

7. **결과 확인**:
   - 원본 이미지
   - 배경 제거된 이미지
   - 최종 편집 결과

---

## FLUX.1-Fill 기능

### 1. Inpainting (영역 채우기)

**용도**: 마스크 영역을 새로운 내용으로 채움

**예시**:
```
프롬프트: "배경을 현대적인 체육관으로 변경"
마스크: 배경 영역 (BEN2로 자동 생성)
결과: 배경만 체육관으로 변경, 인물은 유지
```

**파라미터**:
- Steps: 28 (권장)
- Guidance: 3.5
- Strength: 0.8-1.0 (높을수록 변화 큼)

### 2. Outpainting (이미지 확장)

**용도**: 이미지 경계 밖으로 확장

**예시**:
```
프롬프트: "왼쪽에 운동 기구 추가"
결과: 이미지가 왼쪽으로 확장되며 운동 기구 생성
```

**파라미터**:
- Steps: 28-40
- Guidance: 3.5-5.0
- Strength: 0.9-1.0

---

## Qwen-Image 기능

### 1. Appearance Editing (외관 편집)

**용도**: 색상, 질감, 스타일 변경

**예시**:
```
프롬프트: "운동복을 파란색에서 빨간색으로 변경"
```

**파라미터**:
- Steps: 20-30
- Guidance: 2.0-5.0
- Strength: 0.6-0.8

### 2. Semantic Editing (의미론적 편집)

**용도**: 객체 추가/제거, 장면 변경

**예시**:
```
프롬프트: "손에 물병 추가"
프롬프트: "안경 제거"
프롬프트: "배경을 야외 공원으로 변경"
```

**파라미터**:
- Steps: 25-35
- Guidance: 3.0-7.0
- Strength: 0.7-0.9

### 3. Text Editing (텍스트 편집)

**용도**: 이미지 내 텍스트 수정

**예시**:
```
프롬프트: "티셔츠의 'GYM'을 'FITNESS'로 변경"
```

**파라미터**:
- Steps: 20-30
- Guidance: 3.0-5.0
- Strength: 0.5-0.7

### 4. Multi-Image Editing (다중 이미지)

**용도**: 여러 이미지를 참조하여 편집

**예시**:
```
프롬프트: "참조 이미지의 스타일로 변경"
```

---

## 워크플로우 설정

### configs/image_editing_config.yaml

```yaml
comfyui:
  base_url: "http://localhost:8188"
  timeout: 300

experiments:
  - id: "ben2_flux_fill"
    name: "BEN2 + FLUX.1-Fill"
    description: "배경 제거 후 인페인팅/아웃페인팅"
    models:
      - model_id: "BEN2"
        path: "/mnt/data4/models/BEN2"
      - model_id: "FLUX.1-Fill"
        path: "/mnt/data4/models/FLUX.1-Fill-dev-Q8_0.gguf"

    features:
      - id: "inpainting"
        name: "영역 채우기"
        requires_mask: true
      - id: "outpainting"
        name: "이미지 확장"
        requires_mask: false

  - id: "ben2_qwen_image"
    name: "BEN2 + Qwen-Image"
    description: "배경 제거 후 정밀 편집"
    models:
      - model_id: "BEN2"
      - model_id: "Qwen-Image-Edit-2509"
        path: "/mnt/data4/models/Qwen-Image-Edit-2509"

    features:
      - id: "appearance_editing"
        name: "외관 편집"
      - id: "semantic_editing"
        name: "의미론적 편집"
      - id: "text_editing"
        name: "텍스트 편집"
      - id: "multi_image_editing"
        name: "다중 이미지 편집"
```

---

## API 사용법

### 이미지 편집 API

**POST** `/api/edit_with_comfyui`

Request:
```json
{
  "experiment_id": "ben2_flux_fill",
  "input_image_base64": "base64_encoded_image...",
  "prompt": "배경을 현대적인 체육관으로 변경",
  "steps": 28,
  "guidance_scale": 3.5,
  "strength": 0.8
}
```

Response:
```json
{
  "success": true,
  "experiment_id": "ben2_flux_fill",
  "experiment_name": "BEN2 + FLUX.1-Fill",
  "output_image_base64": "base64_result...",
  "background_removed_image_base64": "base64_bg_removed...",
  "elapsed_time": 12.5
}
```

### 실험 목록 조회

**GET** `/api/image_editing/experiments`

Response:
```json
{
  "experiments": [
    {
      "id": "ben2_flux_fill",
      "name": "BEN2 + FLUX.1-Fill",
      "description": "배경 제거 후 인페인팅/아웃페인팅",
      "features": [
        {"id": "inpainting", "name": "영역 채우기"},
        {"id": "outpainting", "name": "이미지 확장"}
      ]
    },
    {
      "id": "ben2_qwen_image",
      "name": "BEN2 + Qwen-Image",
      "description": "배경 제거 후 정밀 편집",
      "features": [
        {"id": "appearance_editing", "name": "외관 편집"},
        {"id": "semantic_editing", "name": "의미론적 편집"},
        {"id": "text_editing", "name": "텍스트 편집"},
        {"id": "multi_image_editing", "name": "다중 이미지 편집"}
      ]
    }
  ]
}
```

---

## 프롬프트 작성 팁

### 효과적인 프롬프트

**구체적으로 작성**:
```
❌ "배경 변경"
✅ "배경을 밝은 현대적인 체육관으로 변경, 운동 기구 포함"
```

**객체 설명 포함**:
```
❌ "색상 변경"
✅ "운동복의 상의를 파란색에서 빨간색으로 변경"
```

**스타일 지정**:
```
❌ "예쁘게"
✅ "전문적이고 깔끔한 스타일, 밝은 조명"
```

### 부정 프롬프트 (Negative Prompt)

워크플로우에 자동 포함:
```
"blurry, low quality, distorted, ugly, deformed"
```

추가 설정 가능:
```python
workflow["5"]["inputs"]["text"] = "blurry, extra fingers, bad hands"
```

---

## 파라미터 가이드

### Steps (추론 단계)

| 값 | 용도 | 속도 | 품질 |
|----|------|------|------|
| 10-15 | 빠른 테스트 | 매우 빠름 | 낮음 |
| 20-30 | 일반 편집 | 중간 | 중간 |
| 35-50 | 고품질 결과 | 느림 | 높음 |

### Guidance Scale (CFG)

| 값 | 효과 |
|----|------|
| 1.0-2.0 | 프롬프트 약하게 적용, 자연스러움 |
| 3.0-5.0 | 균형잡힌 결과 (권장) |
| 6.0-10.0 | 프롬프트 강하게 적용, 과포화 가능 |
| 10.0+ | 매우 강한 효과, 아티팩트 발생 가능 |

### Strength (변화 강도)

| 값 | 효과 |
|----|------|
| 0.0-0.3 | 미세 조정 |
| 0.4-0.7 | 중간 변화 |
| 0.8-1.0 | 큰 변화, 거의 새로운 이미지 |

---

## 트러블슈팅

### 배경 제거 실패

**증상**: 배경이 제대로 제거되지 않음

**원인**:
- 배경과 전경의 구분이 모호
- 이미지 해상도가 너무 낮음

**해결**:
- 더 선명한 이미지 사용
- BEN2 threshold 조정 (기본: 0.5)

### 편집 결과가 이상함

**증상**: 왜곡, 아티팩트, 비현실적인 결과

**원인**:
- Guidance Scale이 너무 높음
- Steps가 너무 적음
- Strength가 적절하지 않음

**해결**:
```
1. Guidance Scale 낮추기 (7.0 → 3.5)
2. Steps 늘리기 (20 → 30)
3. Strength 조정 (0.9 → 0.7)
```

### 메모리 부족

**증상**: CUDA out of memory

**원인**:
- 이미지 해상도가 너무 큼
- VRAM 부족

**해결**:
```
1. 이미지 크기 축소 (2048 → 1024)
2. 더 작은 모델 사용
3. ComfyUI 재시작
```

### 생성 속도가 느림

**일반 소요 시간**:
- FLUX.1-Fill: 30-60초 (1024x1024, 28 steps)
- Qwen-Image: 40-80초 (1024x1024, 30 steps)

**개선 방법**:
```
1. Steps 줄이기 (28 → 20)
2. 이미지 크기 축소
3. 후처리 비활성화
```

---

## 고급 기능

### 커스텀 워크플로우 생성

1. ComfyUI 웹 UI 접속 (`http://localhost:8188`)
2. 노드 배치 및 연결
3. "Save (API Format)" 클릭
4. JSON을 `comfyui_workflows.py`에 추가

예시:
```python
def get_custom_workflow() -> Dict[str, Any]:
    workflow = {
        "1": {"class_type": "LoadImage", ...},
        "2": {"class_type": "BEN2BackgroundRemoval", ...},
        "3": {"class_type": "CustomNode", ...},
        # ...
    }
    return workflow
```

### 마스크 커스터마이징

BEN2 대신 수동 마스크 사용:

```python
workflow["2"] = {
    "class_type": "LoadImage",
    "inputs": {"image": "custom_mask.png"}
}
```

### 배치 처리

여러 이미지 동시 편집:

```python
for image_path in image_list:
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    result = client.execute_workflow(
        workflow=workflow,
        input_image=image_bytes
    )
    save_result(result)
```

---

## 모델 다운로드

### FLUX.1-Fill

```bash
cd /mnt/data4/models
wget https://huggingface.co/black-forest-labs/FLUX.1-Fill-dev-GGUF/resolve/main/flux1-fill-dev-Q8_0.gguf
mv flux1-fill-dev-Q8_0.gguf FLUX.1-Fill-dev-Q8_0.gguf
```

### Qwen-Image-Edit

```bash
cd /mnt/data4/models
git clone https://huggingface.co/Qwen/Qwen-Image-Edit-2509
```

### BEN2

```bash
cd /mnt/data4/models
git clone https://huggingface.co/PramaLLC/BEN2
```

---

## 성능 최적화

### GPU 메모리 절약

1. **낮은 정밀도 모델 사용**:
   - Q8_0 대신 Q6_K 또는 Q4_K (GGUF)

2. **모델 오프로드**:
   ```python
   # ComfyUI 설정에서 CPU 오프로드 활성화
   --lowvram
   ```

3. **작은 배치 크기**:
   - 한 번에 하나의 이미지만 처리

### 속도 향상

1. **xformers 사용**:
   ```bash
   pip install xformers
   ```

2. **컴파일된 모델**:
   - TensorRT, torch.compile() 활용

3. **캐시 활용**:
   - 동일 모델 재사용 시 로딩 시간 단축

---

## 관련 문서

- [ComfyUI 통합 가이드](./COMFYUI_INTEGRATION.md)
- [모델 설정 가이드](./MODEL_SETUP_GUIDE.md)
- [프롬프트 최적화](./PROMPT_OPTIMIZATION.md)
