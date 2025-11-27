# ComfyUI 통합 가이드

## 개요

이 프로젝트는 ComfyUI를 백그라운드 워커로 사용하여 모든 이미지 생성 작업을 처리합니다.

```
Streamlit (UI) → Uvicorn (API 중계) → ComfyUI (GPU 전담 Worker)
```

### 주요 특징

- **통합 모델 관리**: 모든 모델(FLUX-bnb-4b, FLUX-bnb-8b, BEN2, FLUX.1-Fill, Qwen-Image)을 ComfyUI에서 관리
- **메모리 효율성**: ComfyUI는 필요할 때만 모델을 로드하고, 유휴 시 ~500MB만 사용
- **후처리 옵션**: 3가지 후처리 방식 선택 가능 (없음, Impact Pack, 기존 ADetailer)
- **백그라운드 실행**: ComfyUI는 포트 8188에서 백그라운드로 실행

---

## 설치

### 1. ComfyUI 설치

```bash
cd /home/mscho/project3/Ad_Content_Creation_Service_Team3
bash scripts/install_comfyui.sh
```

설치 스크립트는 다음을 수행합니다:
- ComfyUI 클론 (`comfyui/` 폴더)
- 의존성 설치
- ComfyUI Manager 설치 (노드 관리)
- 모델 경로 설정 (`/mnt/data4/models`)
- extra_model_paths.yaml 생성

### 2. 필수 커스텀 노드 설치

ComfyUI Manager를 통해 설치:
- **ComfyUI-Impact-Pack**: 얼굴/손 디테일러 (YOLO+SAM)
- **BEN2 노드**: 배경 제거 (필요 시)
- **GGUF 노드**: GGUF 형식 모델 로딩

또는 수동 설치:
```bash
cd comfyui/custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack.git
cd ComfyUI-Impact-Pack
pip install -r requirements.txt
```

### 3. 모델 배치

모델은 `/mnt/data4/models/` 또는 ComfyUI 내부 경로에 배치:

```
/mnt/data4/models/
├── flux-bnb-4b/            # 기존 T2I 모델
├── flux-bnb-8b/            # 기존 T2I 모델
├── FLUX.1-Fill-dev-Q8_0.gguf  # 인페인팅 모델
├── Qwen-Image-Edit-2509/   # 정밀 편집 모델
└── BEN2/                   # 배경 제거 모델
```

또는 ComfyUI 내부:
```
comfyui/models/checkpoints/
├── flux-bnb-4b.safetensors
└── flux-bnb-8b.safetensors
```

---

## 서버 실행

### 전체 서비스 시작 (권장)

```bash
bash scripts/start_all.sh
```

실행 순서:
1. ComfyUI 시작 (포트 8188)
2. 10초 대기 (초기화)
3. Uvicorn 시작 (포트 8000)
4. Streamlit 시작 (포트 8501)

### 개별 서비스 시작

**ComfyUI만 시작**:
```bash
bash scripts/start_comfyui.sh
```

**FastAPI만 시작**:
```bash
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000
```

**Streamlit만 시작**:
```bash
streamlit run src/frontend/app.py --server.port 8501
```

### 서버 중단

```bash
bash scripts/stop_all.sh
```

### 원격 서버 접속 (SSH 포트 포워딩)

원격 서버(예: GPU 서버)에서 서비스를 실행하고 로컬 PC에서 접속하려면 SSH 포트 포워딩을 사용합니다.

#### 전체 포트 포워딩

```bash
ssh -L 8501:localhost:8501 -L 8000:localhost:8000 -L 8188:localhost:8188 사용자@서버주소
```

**예시:**
```bash
ssh -L 8501:localhost:8501 -L 8000:localhost:8000 -L 8188:localhost:8188 mscho@192.168.0.9
```

#### 접속 후 사용

SSH 접속이 유지된 상태에서 로컬 PC 브라우저에서:
- `http://localhost:8501` - Streamlit UI (프론트엔드)
- `http://localhost:8000/docs` - FastAPI Swagger 문서
- `http://localhost:8188` - ComfyUI 웹 UI

#### 포트별 설명

| 포트 | 서비스 | 용도 |
|------|--------|------|
| 8501 | Streamlit | 메인 UI - 문구 생성, 이미지 생성 |
| 8000 | FastAPI | Backend API - 상태 확인, 모델 관리 |
| 8188 | ComfyUI | 워크플로우 관리 - 노드 설치, 워크플로우 편집 |

#### 포트 선택적 포워딩

필요한 포트만 포워딩:

```bash
# Streamlit UI만 필요한 경우
ssh -L 8501:localhost:8501 mscho@192.168.0.9

# Streamlit + FastAPI (ComfyUI 제외)
ssh -L 8501:localhost:8501 -L 8000:localhost:8000 mscho@192.168.0.9

# ComfyUI 워크플로우 편집만 필요한 경우
ssh -L 8188:localhost:8188 mscho@192.168.0.9
```

#### 백그라운드 실행

SSH 연결을 백그라운드로 유지:

```bash
ssh -fN -L 8501:localhost:8501 -L 8000:localhost:8000 -L 8188:localhost:8188 mscho@192.168.0.9
```

옵션 설명:
- `-f`: 백그라운드 실행
- `-N`: 원격 명령 실행 안 함 (포트 포워딩만)

연결 종료:
```bash
# SSH 포트 포워딩 프로세스 찾기
ps aux | grep "ssh.*8501"

# PID로 종료
kill [PID]
```

---

## 아키텍처

### 파일 구조

```
src/backend/
├── comfyui_client.py         # ComfyUI API 클라이언트
├── comfyui_workflows.py      # 워크플로우 템플릿
├── services.py               # 리팩토링된 서비스 (ComfyUI 기반)
├── main.py                   # FastAPI 엔드포인트
└── post_processor.py         # 기존 ADetailer (호환성)

configs/
└── image_editing_config.yaml # ComfyUI 설정 및 실험 정의

scripts/
├── install_comfyui.sh        # 설치 스크립트
├── start_comfyui.sh          # ComfyUI 시작
├── stop_comfyui.sh           # ComfyUI 중단
├── start_all.sh              # 전체 시작
└── stop_all.sh               # 전체 중단
```

### 워크플로우 종류

`comfyui_workflows.py`에 정의된 워크플로우:

1. **T2I (Text-to-Image)**
   - `get_flux_t2i_workflow()`: 기본 텍스트→이미지 생성

2. **T2I + Impact Pack**
   - `get_flux_t2i_with_impact_workflow()`: 얼굴/손 후처리 포함

3. **I2I (Image-to-Image)**
   - `get_flux_i2i_workflow()`: 이미지 편집

4. **BEN2 + FLUX.1-Fill**
   - `get_ben2_flux_fill_workflow()`: 배경 제거 + 인페인팅

5. **BEN2 + Qwen-Image**
   - `get_ben2_qwen_image_workflow()`: 배경 제거 + 정밀 편집

### 데이터 흐름

```
1. Streamlit UI: 사용자 입력
   ↓
2. APIClient: payload 전송
   ↓
3. FastAPI: /api/generate_t2i 또는 /api/generate_i2i
   ↓
4. services.py: generate_t2i_core() 또는 generate_i2i_core()
   ↓
5. ComfyUIClient: 워크플로우 실행 요청
   ↓
6. ComfyUI: 이미지 생성 (GPU)
   ↓
7. services.py: 결과 수신
   ↓ (선택적)
8. post_processor.py: ADetailer 후처리
   ↓
9. FastAPI: 이미지 반환
   ↓
10. Streamlit: 결과 표시
```

---

## 후처리 옵션

### 3가지 방식

사용자는 UI에서 다음 중 하나를 선택할 수 있습니다:

#### 1. 없음 (none)
- 후처리 없이 빠르게 생성
- 속도: 가장 빠름
- 품질: 기본

#### 2. ComfyUI Impact Pack (impact_pack)
- ComfyUI 내장 FaceDetailer 사용
- YOLO + SAM 기반 얼굴/손 감지
- 속도: 중간
- 품질: 높음 (새로운 방식)

#### 3. 기존 ADetailer (adetailer)
- YOLO + MediaPipe 기반
- 기존 구현 유지 (호환성)
- 속도: 느림
- 품질: 높음 (검증된 방식)

### 설정 파일

`frontend_config.yaml`:
```yaml
image:
  post_processing:
    methods:
      - id: "none"
        name: "없음 (빠름)"
      - id: "impact_pack"
        name: "ComfyUI Impact Pack"
      - id: "adetailer"
        name: "기존 ADetailer"

    adetailer_targets:
      - "hand"
      - "face"
```

---

## API 엔드포인트

### T2I 생성

**POST** `/api/generate_t2i`

Request Body:
```json
{
  "prompt": "A fitness instructor in a gym",
  "width": 1024,
  "height": 1024,
  "steps": 28,
  "guidance_scale": 3.5,
  "post_process_method": "impact_pack",
  "enable_adetailer": false,
  "adetailer_targets": null
}
```

### I2I 편집

**POST** `/api/generate_i2i`

Request Body:
```json
{
  "input_image_base64": "base64_encoded_image...",
  "prompt": "Change background to a modern gym",
  "strength": 0.75,
  "width": 1024,
  "height": 1024,
  "steps": 28,
  "guidance_scale": 3.5,
  "post_process_method": "none",
  "enable_adetailer": false,
  "adetailer_targets": null
}
```

### ComfyUI 상태 확인

**GET** `/api/comfyui/status`

Response:
```json
{
  "status": "running",
  "url": "http://localhost:8188"
}
```

---

## 트러블슈팅

### ComfyUI가 시작되지 않음

로그 확인:
```bash
tail -f logs/comfyui.log
```

일반적인 문제:
- **포트 8188 이미 사용 중**: 기존 프로세스 종료 후 재시작
- **CUDA 오류**: GPU 드라이버 확인
- **모델 파일 없음**: `/mnt/data4/models/` 경로 확인

### 워크플로우 실행 실패

원인:
- 커스텀 노드 미설치
- 모델 경로 잘못 설정
- VRAM 부족

해결:
```bash
# ComfyUI 재시작
bash scripts/stop_comfyui.sh
bash scripts/start_comfyui.sh

# 로그 확인
tail -f logs/comfyui.log
```

### Impact Pack 오류

ComfyUI Manager에서 Impact Pack 재설치:
1. ComfyUI 웹 UI 접속 (`http://localhost:8188`)
2. Manager 버튼 클릭
3. "Install Missing Custom Nodes" 실행

### 메모리 부족

ComfyUI는 자동으로 모델을 언로드하지만, 여러 워크플로우 동시 실행 시 VRAM 부족 가능:

해결책:
- 더 작은 모델 사용 (4b 대신 8b)
- 후처리 비활성화
- 이미지 크기 축소

---

## 개발자 참고사항

### 새 워크플로우 추가

1. ComfyUI 웹 UI에서 워크플로우 설계
2. "Save (API Format)" 클릭하여 JSON 저장
3. `comfyui_workflows.py`에 함수 추가:

```python
def get_my_custom_workflow() -> Dict[str, Any]:
    """커스텀 워크플로우"""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "model.safetensors"}
        },
        # ... 나머지 노드
    }
    return workflow
```

4. `services.py`에 호출 로직 추가

### 워크플로우 파라미터 업데이트

기존 `update_flux_t2i_workflow()` 참고:

```python
def update_my_workflow(
    workflow: Dict[str, Any],
    model_name: str,
    prompt: str,
    custom_param: float
) -> Dict[str, Any]:
    # 노드 파라미터 업데이트
    workflow["2"]["inputs"]["ckpt_name"] = f"{model_name}.safetensors"
    workflow["3"]["inputs"]["text"] = prompt
    workflow["5"]["inputs"]["custom_value"] = custom_param
    return workflow
```

### ComfyUI 클라이언트 확장

`comfyui_client.py`의 `ComfyUIClient` 클래스:

```python
class ComfyUIClient:
    def execute_workflow(self, workflow, input_image=None, input_image_node_id=None):
        # 1. 연결 확인
        # 2. 이미지 업로드 (있으면)
        # 3. 워크플로우 큐잉
        # 4. 완료 대기
        # 5. 결과 이미지 추출
        pass
```

---

## 로그 위치

- **ComfyUI**: `logs/comfyui.log`
- **FastAPI**: `logs/uvicorn.log`
- **Streamlit**: `logs/streamlit.log`

실시간 로그 확인:
```bash
tail -f logs/comfyui.log
tail -f logs/uvicorn.log
tail -f logs/streamlit.log
```

---

## 관련 문서

- [이미지 편집 가이드](./IMAGE_EDITING_GUIDE.md)
- [모델 설정 가이드](./MODEL_SETUP_GUIDE.md)
- [프론트엔드 가이드](./frontend_guide.md)
