# 📘 COMFYUI_INTEGRATION.md
**헬스케어 AI 콘텐츠 제작 서비스 – ComfyUI 통합 가이드**

---

## 1. 개요

본 프로젝트는 모든 이미지 생성/편집 연산을 **ComfyUI(GPU 백엔드 워커)**로 위임하는 구조를 사용합니다:

```
Streamlit (UI)
   → FastAPI (API 서버)
      → ComfyUI (GPU 워커, 포트 8188)
```

### 특징

- 중앙 집중식 모델 관리 (FLUX-bnb-4b, 8b, Fill, Qwen-Image, BEN2 등)
- ComfyUI는 필요할 때만 모델을 로드하여 **VRAM 최적화**
- 후처리 옵션 3종 지원: 없음 / Impact Pack / ADetailer
- 모든 이미지 생성 요청은 통합된 `ComfyUIClient`를 통해 처리됨

---

## 2. 설치

### 2.1 ComfyUI 설치

```bash
cd /home/spai0323/Ad_Content_Creation_Service_Team3
bash scripts/install_comfyui.sh
```

설치 스크립트는 다음을 수행합니다:

- `comfyui/` 폴더 clone
- Python dependency 설치
- ComfyUI Manager 설치
- `/mnt/data4/models` 경로 등록
- `extra_model_paths.yaml` 자동 생성

---

## 3. 커스텀 노드 설치

총 10여 개의 커스텀 노드를 사용하며, **설치 방식이 두 종류**로 나뉩니다.

---

### 3.1 직접 설치(필수 git clone)

#### (1) ComfyUI_bnb_nf4_fp4_Loaders  
Flux bnb 모델을 로딩하기 위한 핵심 노드.

```bash
cd comfyui/custom_nodes
git clone https://github.com/excosy/ComfyUI_bnb_nf4_fp4_Loaders
pip install -r ComfyUI_bnb_nf4_fp4_Loaders/requirements.txt
```

---

#### (2) BEN2_ComfyUI  
고품질 배경제거 & 세그멘테이션 제공.

```bash
cd comfyui/custom_nodes
git clone https://github.com/PramaLLC/BEN2_ComfyUI
pip install -r BEN2_ComfyUI/requirements.txt
```

✔ BEN2 모델 파일 추가 필요  
아래에서 `BEN2_Base.pth` 다운로드:

```
https://huggingface.co/PramaLLC/BEN2/tree/main
```

그리고 복사:

```bash
cp BEN2_Base.pth comfyui/custom_nodes/BEN2_ComfyUI/
```

---

### 3.2 ComfyUI Manager에서 설치하는 노드

아래 노드들은 8188 포트 접속 후:

```
http://localhost:8188
→ Manager
→ Custom Nodes Manager
→ Install
```

에서 설치합니다.

| 노드명 | 역할 |
|-------|------|
| comfyui-impact-pack | SAM + YOLO 기반 Face/Hand 디테일 |
| comfyui-impact-subpack | Submodule for Impact |
| comfyui-rmbg | 기본 배경제거 |
| ComfyUI-BRIA_AI-RMBG | 고품질 BRIA 배경제거 |
| ComfyUI-GGUF | GGUF 모델용 로더 |
| comfyui_controlnet_aux | ControlNet 보조 모델 |

---

## 4. 모델 배치 구조

모든 모델은 서버 공통 경로에 배치합니다:

```
/mnt/data4/models/
```

### 구조 예시

```
/mnt/data4/models/
├── flux-4b/
├── flux-8b/
├── flux-fill/
│   └── FLUX.1-Fill-dev-Q8_0.gguf
├── clip/
│   ├── t5-v1_1-xxl-encoder-Q8_0.gguf
│   └── clip_l.safetensors
├── qwen-image-edit/
│   └── qwen2-image-0.5b-edit.gguf
└── BEN2/
    └── BEN2_Base.pth
```

### ComfyUI 경로 연결 (자동 생성)

```
comfyui/models/unet/ → flux-fill (symlink)
comfyui/models/clip/ → clip/ (symlink)
...
```

---

## 5. 서버 실행

### 전체 실행 (Streamlit + FastAPI + ComfyUI)

```bash
bash scripts/start_all.sh
```

> ComfyUI → 10초 대기 → FastAPI → Streamlit 순서로 실행

---

### 개별 실행

#### ComfyUI

```bash
bash scripts/start_comfyui.sh
```

#### FastAPI

```bash
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000
```

#### Streamlit

```bash
streamlit run src/frontend/app.py --server.port 8501
```

---

## 6. SSH 포트 포워딩

### 전체 포트 포워딩

```bash
ssh -L 8501:localhost:8501 \
    -L 8000:localhost:8000 \
    -L 8188:localhost:8188 \
    spai0323@서버IP
```

### 브라우저 접속

- Streamlit → http://localhost:8501  
- FastAPI → http://localhost:8000/docs  
- ComfyUI → http://localhost:8188  

### 백그라운드 실행

```bash
ssh -fN -L 8501:localhost:8501 \
        -L 8000:localhost:8000 \
        -L 8188:localhost:8188 \
        spai0323@서버IP
```

---

## 7. 아키텍처

### 백엔드 구조

```
src/backend/
├── comfyui_client.py       # ComfyUI API 통신
├── comfyui_workflows.py    # 워크플로우 템플릿
├── services.py             # T2I/I2I 로직
├── post_processor.py       # 기존 ADetailer
└── main.py                 # FastAPI 엔드포인트
```

---

## 8. 데이터 흐름

```
1. Streamlit UI 입력
2. FastAPI로 전달
3. services.py → ComfyUIClient 호출
4. ComfyUI GPU 생성
5. (선택) ADetailer 후처리
6. 응답 이미지 반환
7. Streamlit 렌더링
```

---

## 9. 후처리 옵션

| 옵션 | 설명 | 속도 |
|------|------|------|
| none | 후처리 없음 | 가장 빠름 |
| impact_pack | YOLO+SAM 기반 디테일러 | 중간 |
| adetailer | 기존 YOLO 기반 후처리 | 느림 |

---

## 10. API 예시

### T2I

```
POST /api/generate_t2i
```

```json
{
  "prompt": "A fitness trainer",
  "width": 1024,
  "height": 1024,
  "steps": 28,
  "post_process_method": "impact_pack"
}
```

---

### I2I

```
POST /api/generate_i2i
```

```json
{
  "input_image_base64": "...",
  "prompt": "replace background",
  "strength": 0.7
}
```

---

## 11. 커스텀 노드 설치 요약

| 노드 | 설치 방식 | 비고 |
|------|-----------|------|
| ComfyUI_bnb_nf4_fp4_Loaders | git clone | bnb 모델 로더 |
| BEN2_ComfyUI | git clone | BEN2_Base.pth 필요 |
| comfyui-impact-pack | Manager | 후처리 |
| comfyui-impact-subpack | Manager | 서브모듈 |
| comfyui-rmbg | Manager | 배경제거 |
| BRIA_AI-RMBG | Manager | 고품질 배경제거 |
| ComfyUI-GGUF | Manager | GGUF 모델 |
| controlnet_aux | Manager | ControlNet |

---

## 12. 트러블슈팅

### ComfyUI 실행 오류

확인:

```bash
tail -f logs/com

