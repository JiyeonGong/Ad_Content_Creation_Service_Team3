# 프론트엔드 설정 가이드

## 🎯 개선 사항 요약

### Before (하드코딩)
```python
# ❌ 하드코딩된 값들
API_BASE_URL = "http://localhost:8000"
service_types = ["헬스장", "PT", "요가", ...]
image_sizes = ["1080x1350", "1080x1080", ...]
steps_default = 10
```

### After (설정 기반)
```yaml
# ✅ frontend_config.yaml에서 관리
api:
  base_url: "http://localhost:8000"
caption:
  service_types: [...]
image:
  preset_sizes: [...]
```

---

## 📁 파일 구조

```
src/frontend/
├── frontend_config.yaml    # 🆕 프론트엔드 설정
├── app.py                  # ✏️ 리팩토링
└── __init__.py
```

---

## 🚀 사용 방법

### 1. 기본 실행 (변경 없음)

```bash
streamlit run src/frontend/app.py
```

### 2. API URL 변경

**방법 A: 환경변수**
```bash
API_BASE_URL=http://192.168.1.100:8000 streamlit run src/frontend/app.py
```

**방법 B: YAML 수정**
```yaml
# frontend_config.yaml
api:
  base_url: "http://192.168.1.100:8000"
```

---

## ⚙️ 설정 커스터마이징

### 서비스 종류 추가

```yaml
caption:
  service_types:
    - "헬스장"
    - "PT (개인 트레이닝)"
    - "요가/필라테스"
    - "건강 식품/보조제"
    - "크로스핏"           # 🆕 추가
    - "다이어트 프로그램"  # 🆕 추가
```

### 톤 옵션 추가

```yaml
caption:
  tones:
    - "친근하고 동기부여"
    - "전문적이고 신뢰감"
    - "공격적이고 강렬함"  # 🆕 추가
    - "럭셔리하고 세련됨"  # 🆕 추가
```

### 이미지 크기 프리셋 추가

```yaml
image:
  preset_sizes:
    - name: "Instagram 세로 (4:5)"
      width: 1080
      height: 1350
      description: "피드 게시물 최적"
    
    - name: "YouTube 썸네일"  # 🆕 추가
      width: 1280
      height: 720
      description: "16:9 비율"
```

### UI 텍스트 변경

```yaml
ui:
  messages:
    connecting: "서버 연결 중..."
    loading: "잠시만 기다려주세요..."
    success: "완료되었습니다!"
    error: "문제가 발생했습니다"
  
  placeholders:
    service_name: "예: 새해 특별 프로모션"
    features: "예: 한정 기간 50% 할인"
    location: "예: 서울 전지역"
```

---

## 🎨 새 페이지 추가하기

### 1. YAML에 페이지 정의

```yaml
pages:
  - id: "caption"
    icon: "📝"
    title: "홍보 문구+해시태그 생성"
  
  - id: "t2i"
    icon: "🖼"
    title: "인스타그램 이미지 생성"
  
  - id: "video"           # 🆕 새 페이지
    icon: "🎥"
    title: "비디오 생성"
    description: "AI로 짧은 홍보 영상 생성"
```

### 2. app.py에 렌더링 함수 추가

```python
# app.py의 main() 함수에 추가
def main():
    # ... (기존 코드)
    
    if page_id == "caption":
        render_caption_page(config, api)
    elif page_id == "t2i":
        render_t2i_page(config, api, connect_mode)
    elif page_id == "i2i":
        render_i2i_page(config, api, connect_mode)
    elif page_id == "video":  # 🆕 추가
        render_video_page(config, api)

# 새 페이지 함수
def render_video_page(config: ConfigLoader, api: APIClient):
    st.title("🎥 비디오 생성")
    # ... 구현
```

---

## 🔗 백엔드 모델 정보 활용

프론트엔드는 백엔드로부터 실시간으로 모델 정보를 가져옵니다:

```python
# 자동으로 현재 모델의 권장 steps 사용
model_info = api.get_model_info()
if model_info:
    current_model = model_info["models"][model_info["current"]]
    default_steps = current_model["default_steps"]  # 🎯 동적으로 설정
```

**장점:**
- 백엔드에서 모델 변경 시 프론트엔드 자동 조정
- 각 모델의 최적 설정 자동 반영

---

## 🎛️ 고급 기능

### 1. 백엔드 상태 실시간 모니터링

사이드바에 "🔧 시스템 상태" 섹션 자동 표시:
- 현재 로드된 모델
- GPU/CPU 사용 여부
- GPT 상태

### 2. 자동 재시도 로직

```yaml
api:
  retry_attempts: 2  # GPU OOM 시 자동으로 해상도 낮춰서 재시도
```

### 3. 연결 모드 기본값 설정

```yaml
connection_mode:
  enabled_by_default: true  # false로 변경하면 기본 OFF
  description: "페이지 간 데이터 공유 설명..."
```

---

## 🐛 문제 해결

### 설정 파일이 로드되지 않음

**원인:** `frontend_config.yaml` 파일이 없음

**해결:**
1. 파일이 `src/frontend/` 디렉토리에 있는지 확인
2. 없으면 기본 설정으로 작동 (경고 메시지 표시)

### 백엔드 연결 실패

**확인:**
```yaml
api:
  base_url: "http://localhost:8000"  # 올바른 주소인지 확인
  timeout: 180  # 타임아웃 늘리기
```

또는 환경변수:
```bash
API_BASE_URL=http://correct-url:8000 streamlit run src/frontend/app.py
```

### 이미지 크기가 정렬되지 않음

프론트엔드는 자동으로 64의 배수로 정렬합니다:
```python
aligned_w = align_to_64(width)  # 1080 → 1024
```

이는 diffusion 모델의 요구사항입니다.

---

## 📊 설정 우선순위

1. **환경변수** (최우선)
   ```bash
   API_BASE_URL=... streamlit run app.py
   ```

2. **frontend_config.yaml**
   ```yaml
   api:
     base_url: "..."
   ```

3. **코드 내 기본값** (폴백)

---

## 🎯 베스트 프랙티스

### ✅ Do
- 새 옵션 추가는 YAML에서
- UI 텍스트 변경은 YAML에서
- 환경변수로 민감한 정보 관리
- 백엔드 모델 정보 활용

### ❌ Don't
- 코드에 하드코딩 추가
- YAML 없이 실행 (자동 폴백하지만 경고 발생)
- 타임아웃을 너무 짧게 설정

---

## 🔄 전체 시스템 통합

```
┌─────────────────────────┐
│ frontend_config.yaml    │ ← 프론트엔드 설정
│ (UI, 페이지, 옵션)       │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│ app.py (Streamlit)      │ ← 프론트엔드 앱
│ - ConfigLoader          │
│ - APIClient             │
└───────────┬─────────────┘
            │ HTTP
┌───────────▼─────────────┐
│ main.py (FastAPI)       │ ← 백엔드 API
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│ model_config.yaml       │ ← 백엔드 설정
│ (모델, 파라미터)         │
└─────────────────────────┘
```

**완전한 설정 기반 시스템!**
- 프론트/백엔드 각각 YAML로 관리
- 코드 수정 없이 모든 설정 변경 가능
- 환경변수로 배포 환경별 오버라이드

---

## 📝 요약

| 항목 | Before | After |
|------|--------|-------|
| API URL | 코드에 하드코딩 | YAML + 환경변수 |
| 서비스 종류 | 리스트 하드코딩 | YAML 설정 |
| 이미지 크기 | 문자열 하드코딩 | YAML 프리셋 |
| UI 텍스트 | 코드 내 문자열 | YAML 관리 |
| 페이지 추가 | 코드 수정 필요 | YAML + 함수만 추가 |
| 모델 정보 | 정적 | 백엔드에서 동적으로 가져옴 |

**이제 프론트엔드도 완전히 설정 기반!** 🎉
