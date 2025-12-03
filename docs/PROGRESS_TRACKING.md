# 🔄 파이프라인 진행상황 추적 시스템 (Progress Tracking System)

## 📋 개요

ComfyUI 기반 이미지 편집 파이프라인의 각 단계를 실시간으로 추적하고 로그로 출력하는 시스템입니다.

### 목적
- **투명성**: 백엔드에서 현재 어떤 작업이 진행 중인지 명확하게 파악
- **디버깅**: 문제 발생 시 어느 단계에서 멈췄는지 즉시 확인
- **모니터링**: 각 단계별 소요 시간 측정 및 성능 최적화

---

## 🏗️ 시스템 아키텍처

### 1. 계층 구조

```
Frontend (Streamlit)
    ↓ 파이프라인 단계 안내 표시
Backend Services (services.py)
    ↓ progress_callback 정의
ComfyUI Client (comfyui_client.py)
    ↓ 노드 완료 감지 → 콜백 호출
ComfyUI Server
    ↓ 실제 이미지 처리
Logs (uvicorn.log)
    ↓ 단계별 진행상황 기록
```

### 2. 주요 구성 요소

| 파일 | 역할 |
|------|------|
| `comfyui_client.py` | ComfyUI API 호출 및 노드 완료 감지 |
| `comfyui_workflows.py` | 노드 ID → 단계명 매핑 정의 |
| `services.py` | 콜백 함수 정의 및 로그 출력 |
| `app.py` | 프론트엔드 파이프라인 단계 표시 |

---

## 📊 모드별 파이프라인 단계

### 👤 인물 모드 (Portrait Mode) - 16단계

```
노드 ID  │ 단계명
─────────┼────────────────────────────────────
1        │ 📥 이미지 로드
10       │ 🔍 얼굴 감지 모델 로드
12       │ 👤 얼굴 영역 감지 중...
13       │ 🎭 얼굴 마스크 생성
14       │ 🔄 마스크 반전 (편집 영역 설정)
20       │ 📊 Depth/Canny 맵 추출 중...
21       │ 🎮 ControlNet 모델 로드
22       │ 🎨 ControlNet 적용
3        │ 📝 CLIP 텍스트 인코딩
4        │ 🧠 GGUF 모델 로드
6        │ ⚙️ Negative 프롬프트 처리
30       │ 🎲 Latent 노이즈 생성
31       │ 🖌️ 마스크 적용 (편집 영역 제한)
40       │ 🚀 이미지 생성 중... (KSampler)
41       │ 🎬 VAE 디코딩
50       │ 💾 결과 저장
```

**파이프라인 흐름**:
1. 얼굴 감지 → 마스크 생성 → 마스크 반전 (얼굴 제외)
2. Depth/Canny 맵 추출 (체형 유지)
3. ControlNet 적용 (구조 가이드)
4. 마스크된 영역만 이미지 생성 (의상/배경 변경)

---

### 📦 제품 모드 (Product Mode) - 14단계

```
노드 ID  │ 단계명
─────────┼────────────────────────────────────
1        │ 📥 이미지 로드
2        │ ✂️ BEN2 배경 제거 중...
3        │ 📝 배경 프롬프트 인코딩
4        │ 🧠 GGUF 모델 로드 (배경 생성)
5        │ 🎲 Latent 노이즈 생성
6        │ 🎨 배경 이미지 생성 중...
7        │ 🎬 VAE 디코딩 (배경)
8        │ 🔗 제품 + 배경 레이어 합성
9        │ 🖼️ FLUX Fill 입력 준비
10       │ 📝 블렌딩 프롬프트 인코딩
11       │ 🧠 FLUX Fill 모델 로드
12       │ 🎨 자연스러운 블렌딩 중...
13       │ 🎬 VAE 디코딩 (최종)
50       │ 💾 결과 저장
```

**파이프라인 흐름**:
1. BEN2로 배경 제거 (제품 분리)
2. T2I로 새 배경 생성
3. 제품 + 배경 레이어 합성
4. FLUX Fill로 자연스러운 블렌딩

---

### ✨ 고급 모드 (Hybrid Mode) - 17단계

```
노드 ID  │ 단계명
─────────┼────────────────────────────────────
1        │ 📥 이미지 로드
10       │ 🔍 얼굴 감지 모델 로드
11       │ 👤 얼굴 영역 감지 중...
12       │ 🎭 얼굴 마스크 생성
20       │ 🔍 제품 감지 모델 로드
21       │ 📦 제품 영역 감지 중...
22       │ 📦 제품 마스크 생성
30       │ 🔗 얼굴+제품 마스크 합성
31       │ 🔄 마스크 반전 (편집 영역 설정)
40       │ 📊 Canny 맵 추출 중...
41       │ 🎮 ControlNet 모델 로드
42       │ 🎨 ControlNet 적용
3        │ 📝 CLIP 텍스트 인코딩
4        │ 🧠 GGUF 모델 로드
6        │ ⚙️ Negative 프롬프트 처리
50       │ 🎲 Latent 노이즈 생성
51       │ 🖌️ 마스크 적용 (편집 영역 제한)
60       │ 🚀 이미지 생성 중... (KSampler)
61       │ 🎬 VAE 디코딩
70       │ 💾 결과 저장
```

**파이프라인 흐름**:
1. 얼굴 + 제품 동시 감지
2. 멀티 마스크 합성 → 반전 (얼굴+제품 제외)
3. Canny 맵 추출 (윤곽선 유지)
4. ControlNet 적용
5. 마스크된 영역만 이미지 생성 (의상/배경 변경)

---

## 💻 코드 구현 상세

### 1. ComfyUI Client (`comfyui_client.py`)

#### `wait_for_completion()` 메서드

```python
def wait_for_completion(
    self,
    prompt_id: str,
    check_interval: int = 2,
    progress_callback: Optional[callable] = None  # 진행상황 콜백
) -> Dict[str, Any]:
    """작업 완료 대기 (진행상황 추적)"""

    completed_nodes = set()  # 완료된 노드 추적

    while True:
        history = self.get_history(prompt_id)

        if history is not None:
            # 완료된 노드 확인
            if progress_callback:
                outputs = history.get("outputs", {})
                for node_id in outputs.keys():
                    if node_id not in completed_nodes:
                        completed_nodes.add(node_id)
                        # 콜백 호출
                        progress_callback(node_id=node_id, elapsed=elapsed)
```

**핵심 로직**:
- ComfyUI `/history` API로 완료된 노드 조회
- 새로 완료된 노드 발견 시 콜백 호출
- 중복 호출 방지 (`completed_nodes` set 사용)

---

### 2. 워크플로우 정의 (`comfyui_workflows.py`)

#### `get_pipeline_steps_for_mode()` 함수

```python
def get_pipeline_steps_for_mode(experiment_id: str) -> Dict[str, str]:
    """
    모드별 노드 ID → 파이프라인 단계명 매핑

    Returns:
        {node_id: step_name} 딕셔너리
    """
    if experiment_id == "portrait_mode":
        return {
            "1": "📥 이미지 로드",
            "10": "🔍 얼굴 감지 모델 로드",
            "12": "👤 얼굴 영역 감지 중...",
            # ... (16개 노드)
        }
    elif experiment_id == "product_mode":
        return {
            "1": "📥 이미지 로드",
            "2": "✂️ BEN2 배경 제거 중...",
            # ... (14개 노드)
        }
    # ...
```

**설계 원칙**:
- 이모지 사용으로 시각적 구분
- 노드 ID는 워크플로우 JSON의 실제 키값과 일치
- 단계명은 사용자 친화적 한글 표현

---

### 3. 서비스 로직 (`services.py`)

#### Progress Callback 구현

```python
# 파이프라인 단계 매핑 로드
pipeline_steps = get_pipeline_steps_for_mode(experiment_id)

# 진행상황 콜백 함수 정의
step_count = [0]  # 완료된 단계 수 (클로저에서 수정 가능)

def progress_callback(node_id: str, elapsed: float):
    """노드 완료 시 호출되는 콜백"""
    step_name = pipeline_steps.get(node_id, f"노드 {node_id}")
    step_count[0] += 1
    logger.info(f"   [{step_count[0]:2d}/{len(pipeline_steps):2d}] {step_name} (경과: {elapsed:.1f}초)")

# 워크플로우 실행
logger.info(f"🔄 워크플로우 실행 시작 (총 {len(pipeline_steps)}단계)")
output_images, history = client.execute_workflow(
    workflow=workflow,
    input_image=input_image_bytes,
    input_image_node_id=input_node_id,
    progress_callback=progress_callback  # 콜백 전달
)
```

**로그 포맷**:
```
[현재단계/전체단계] 단계명 (경과: X초)
```

---

### 4. 프론트엔드 (`app.py`)

#### 파이프라인 단계 안내 표시

```python
# 파이프라인 단계 정의
pipeline_steps = {
    "portrait_mode": [
        "📥 이미지 업로드 및 전처리",
        "🔍 얼굴 영역 자동 감지",
        "🎭 얼굴 마스크 생성 및 반전",
        "📊 체형 가이드 추출 (Depth/Canny)",
        "🎨 ControlNet 적용",
        "🚀 이미지 생성 (의상/배경 변경)",
        "💾 결과 저장 및 후처리"
    ],
    # ...
}

# 진행상황 안내 표시
st.info(f"🎨 **{mode_name} 파이프라인 실행 중...**\n\n" +
       "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)]) +
       "\n\n💡 백엔드 로그를 모니터링하여 실시간 진행상황을 확인하세요!")
```

---

## 📝 로그 출력 예시

### Portrait Mode 실행 로그

```bash
# 시작
🎨 ComfyUI 이미지 편집 시작
   모드: 👤 인물 모드
   설명: 얼굴은 보존하고, 의상과 배경을 자연스럽게 변경
   프롬프트: 핑크색 비키니 수영복을 입고 해수욕장 해변에서
   파라미터: steps=28, guidance=7.0
   ControlNet: type=depth, strength=0.7, denoise=1.0
🔄 워크플로우 실행 시작 (총 16단계)

# 진행상황
   [ 1/16] 📥 이미지 로드 (경과: 0.5초)
   [ 2/16] 🔍 얼굴 감지 모델 로드 (경과: 1.2초)
   [ 3/16] 👤 얼굴 영역 감지 중... (경과: 2.8초)
   [ 4/16] 🎭 얼굴 마스크 생성 (경과: 3.1초)
   [ 5/16] 🔄 마스크 반전 (편집 영역 설정) (경과: 3.3초)
   [ 6/16] 📊 Depth/Canny 맵 추출 중... (경과: 5.2초)
   [ 7/16] 🎮 ControlNet 모델 로드 (경과: 7.8초)
   [ 8/16] 🎨 ControlNet 적용 (경과: 8.1초)
   [ 9/16] 📝 CLIP 텍스트 인코딩 (경과: 8.5초)
   [10/16] 🧠 GGUF 모델 로드 (경과: 12.3초)
   [11/16] ⚙️ Negative 프롬프트 처리 (경과: 12.7초)
   [12/16] 🎲 Latent 노이즈 생성 (경과: 13.0초)
   [13/16] 🖌️ 마스크 적용 (편집 영역 제한) (경과: 13.2초)
   [14/16] 🚀 이미지 생성 중... (KSampler) (경과: 41.5초)
   [15/16] 🎬 VAE 디코딩 (경과: 43.8초)
   [16/16] 💾 결과 저장 (경과: 45.2초)

# 완료
✅ 작업 완료! (소요 시간: 45.2초)
✅ ComfyUI 편집 완료! (소요 시간: 45.8초)
```

---

## 🔍 모니터링 방법

### 1. 백엔드 로그 실시간 모니터링

```bash
# Terminal 1: uvicorn 로그
tail -f logs/uvicorn.log

# Terminal 2: ComfyUI 로그
tail -f logs/comfyui.log
```

### 2. 모니터링 스크립트 사용

```bash
# 백엔드 모니터링 (uvicorn + progress tracking)
./scripts/monitor_backend.sh

# ComfyUI 모니터링
./scripts/monitor.sh
```

---

## 🐛 디버깅 가이드

### 문제: 특정 단계에서 멈춤

**증상**:
```
[ 3/16] 👤 얼굴 영역 감지 중... (경과: 2.8초)
# 여기서 멈춤 (다음 단계 안 나옴)
```

**원인 파악**:
1. ComfyUI 로그 확인: `tail -f logs/comfyui.log`
2. 해당 노드에서 에러 발생 가능성
3. 모델 로딩 실패 또는 메모리 부족

**해결 방법**:
```bash
# ComfyUI 재시작
pkill -f "python comfyui/main.py"
./scripts/start_all.sh

# 메모리 부족 시 모델 언로드
curl -X POST http://localhost:8188/free
```

---

### 문제: 단계 번호가 순서대로 안 나옴

**증상**:
```
[ 1/16] 📥 이미지 로드 (경과: 0.5초)
[ 9/16] 📝 CLIP 텍스트 인코딩 (경과: 1.2초)  # 2번이 아닌 9번
[ 2/16] 🔍 얼굴 감지 모델 로드 (경과: 1.8초)
```

**원인**:
- ComfyUI는 병렬 처리 가능한 노드를 동시에 실행
- 노드 완료 순서는 실행 순서와 다를 수 있음

**정상 동작**:
- 이는 예상된 동작입니다
- 중요한 것은 **모든 단계가 완료**되는지 확인

---

### 문제: 전체 단계 수가 안 맞음

**증상**:
```
🔄 워크플로우 실행 시작 (총 16단계)
   [15/16] 🎬 VAE 디코딩 (경과: 43.8초)
# 16단계가 나오지 않고 완료됨
```

**원인**:
- 마지막 노드(SaveImage)는 outputs에 포함 안 될 수 있음
- 노드 ID 매핑이 실제 워크플로우와 불일치

**해결 방법**:
```python
# comfyui_workflows.py에서 노드 매핑 확인
# 실제 워크플로우 JSON의 노드 ID와 일치하는지 검증
```

---

## 🚀 향후 개선 방향

### 1. WebSocket 실시간 통신
- 현재: 2초마다 polling
- 개선: ComfyUI WebSocket API 사용하여 실시간 이벤트 수신

### 2. 프론트엔드 Progress Bar
- 현재: 백엔드 로그에만 표시
- 개선: Streamlit progress bar로 시각화

### 3. 예상 소요 시간 표시
- 현재: 경과 시간만 표시
- 개선: 각 단계별 평균 시간 기반으로 남은 시간 예측

### 4. 단계별 중간 결과 표시
- 현재: 최종 결과만 표시
- 개선: 마스크, Depth 맵 등 중간 산출물 표시

---

## 📚 참고 자료

### ComfyUI API 문서
- `/history/{prompt_id}`: 작업 히스토리 조회
- `/queue`: 큐 상태 조회
- `/prompt`: 워크플로우 실행

### 관련 파일
- `src/backend/comfyui_client.py`: ComfyUI API 클라이언트
- `src/backend/comfyui_workflows.py`: 워크플로우 정의
- `src/backend/services.py`: 서비스 로직
- `src/frontend/app.py`: 프론트엔드 UI
- `configs/image_editing_config.yaml`: 모드 설정

---

## 📌 요약

### 장점
✅ **투명성**: 현재 진행 중인 단계 명확히 파악
✅ **디버깅**: 문제 발생 지점 즉시 특정
✅ **성능 분석**: 단계별 소요 시간 측정
✅ **사용자 경험**: 대기 시간 동안 진행상황 확인

### 제약사항
⚠️ Streamlit은 동기 실행 → 실시간 UI 업데이트 불가
⚠️ Polling 방식 → 2초 간격으로 체크 (약간의 지연)
⚠️ 백엔드 로그 모니터링 필수

### 사용 방법
1. 프론트엔드에서 편집 시작
2. 파이프라인 단계 목록 확인
3. 백엔드 로그 모니터링 (`tail -f logs/uvicorn.log`)
4. 각 단계 완료 메시지 확인

---

**작성일**: 2025-11-28
**버전**: v1.0.0
**작성자**: Ad Content Creation Service Team3
