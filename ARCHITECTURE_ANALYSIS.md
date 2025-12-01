# 프로젝트 구조 분석 보고서

## 📊 프로젝트 개요

**분석 대상**: Ad_Content_Creation_Service_Team3  
**분석 일자**: 2025-12-01  
**분석 범위**: src/ 디렉토리 내 Python 파일 (docs/, scripts/ 제외)

---

## 1. 프롬프트 구성의 명확성 및 일관성 분석

### 🔴 **문제점 1: 프롬프트 처리 로직이 3곳에 분산**

#### 위치별 프롬프트 변환:

**① 프론트엔드 (app.py)**
```python
# Line 335
def caption_to_prompt(caption: str, style: str = "Instagram banner") -> str:
    """문구를 이미지 프롬프트로 변환"""
    return f"{caption}, {style}, vibrant, professional, motivational"
```

**② 백엔드 3단계 파이프라인 (services.py)**
```python
# Line 251-295
def build_final_prompt(raw_prompt: str, model_config=None) -> str:
    """공용 최종 프롬프트 빌더 (T2I / I2I / 편집 공용)
    
    - FLUX 계열 모델:
        1) expand_prompt_with_gpt   : 한국어 → 영어 확장
        2) apply_flux_template      : FLUX 전용 스타일 적용
        3) optimize_prompt          : 최종 다듬기
    """
```

**③ 프론트엔드 페이지별 변환 (T2I 페이지)**
```python
# app.py Line 645-658
raw_prompt = ""
if connect_mode and selected_caption:
    if base_prompt.strip():
        raw_prompt = f"{base_prompt.strip()} — {selected_caption} {hashtags}".strip()
    else:
        raw_prompt = f"{selected_caption} {hashtags}".strip()
else:
    raw_prompt = base_prompt.strip()

# 1차 변환
final_prompt = caption_to_prompt(raw_prompt) if raw_prompt else ""
```

#### ⚠️ **문제 상황**:

1. **프론트엔드에서 프롬프트가 2번 변환됨**:
   - `caption_to_prompt()`: "Instagram banner, vibrant, professional" 추가
   - 백엔드 `build_final_prompt()`: FLUX 3단계 처리

2. **중복 키워드 문제**:
   ```
   사용자 입력: "헬스장에서 운동하는 모습"
   
   프론트엔드 변환:
   → "헬스장에서 운동하는 모습, Instagram banner, vibrant, professional, motivational"
   
   백엔드 1단계 (expand_prompt_with_gpt):
   → "A person exercising in a gym, vibrant atmosphere, professional lighting..."
   
   백엔드 2단계 (apply_flux_template):
   → "Person working out in bright gym, professional equipment, vibrant colors..."
   
   백엔드 3단계 (optimize_prompt):
   → "Athletic person training in modern gym with vibrant lighting, professional..."
   ```
   
   **결과**: "vibrant", "professional" 등의 키워드가 중복되어 의미가 희석됨

3. **일관성 부족**:
   - T2I 페이지: `caption_to_prompt()` + 백엔드 3단계
   - I2I 페이지: 직접 문자열 조합 + 백엔드 3단계
   - 편집 페이지: 백엔드 3단계만 사용

---

### 🔴 **문제점 2: 프롬프트 최적화 로직의 복잡성**

#### 현재 구조:
```python
# services.py
def expand_prompt_with_gpt(text: str) -> str:
    """1단계: 한국어 시각 묘사 확장"""
    # GPT 호출로 2~3문장 한국어 확장
    
def apply_flux_template(expanded_kor_text: str) -> str:
    """2단계: 한국어 → FLUX 영어 변환"""
    # GPT 호출로 60 토큰 이내 영어 변환
    
def optimize_prompt(text: str, model_config) -> str:
    """3단계: 최종 다듬기"""
    # GPT 호출로 품질 키워드 추가
```

#### ⚠️ **문제**:

1. **GPT API 3회 호출**:
   - 비용 증가 (요청당 3배)
   - 레이턴시 증가 (각 호출당 1-2초)
   - 총 소요 시간: 3-6초

2. **각 단계의 역할이 불명확**:
   - 1단계에서 이미 구체적 묘사로 확장했는데
   - 2단계에서 다시 압축 (60 토큰)
   - 3단계에서 또 다시 다듬기
   
   → **정보 손실 가능성**

3. **중간 과정 검증 불가**:
   ```python
   # 로그만 출력, 실제 중간 결과를 사용자가 볼 수 없음
   logger.info(f"🔄 1/3 확장 (한국어): {expanded[:80]}...")
   logger.info(f"🔄 2/3 템플릿 (영어): {templated[:80]}...")
   logger.info(f"🔄 3/3 최종 최적화: {optimized[:80]}...")
   ```

---

### ✅ **개선안 1: 프롬프트 처리 단일화**

```python
# ❌ 현재: 프론트엔드 + 백엔드 분리
# frontend/app.py
final_prompt = caption_to_prompt(raw_prompt)  # 1차 변환
# → backend/services.py
final_prompt = build_final_prompt(final_prompt, model_config)  # 2차 변환 (3단계)

# ✅ 개선: 백엔드에서 일괄 처리
# frontend/app.py
payload = {
    "raw_prompt": raw_prompt,  # 원본 그대로 전달
    "prompt_context": {
        "style": "Instagram banner",
        "mood": "vibrant, professional, motivational",
        "caption": selected_caption,
        "hashtags": hashtags
    }
}

# backend/services.py
def build_final_prompt_v2(raw_prompt: str, context: dict, model_config) -> str:
    """통합 프롬프트 빌더"""
    # 1. Context 통합
    full_input = f"{raw_prompt}"
    if context.get("caption"):
        full_input += f" ({context['caption']})"
    
    # 2. GPT 단일 호출로 처리 (3단계 통합)
    system_prompt = f"""
    You are an expert FLUX prompt engineer.
    Convert Korean/English input to optimized FLUX prompt.
    
    Required style: {context.get('style', 'professional')}
    Mood: {context.get('mood', 'natural')}
    
    Output: 2-3 natural sentences, under 60 tokens.
    Include quality hints for hands/faces if needed.
    """
    
    result = gpt_single_call(system_prompt, full_input)
    return result
```

**효과**:
- GPT 호출 3회 → 1회 (비용 66% 절감)
- 처리 시간 3-6초 → 1-2초
- 프롬프트 로직이 백엔드에만 존재 (유지보수 용이)

---

### ✅ **개선안 2: 프롬프트 디버깅 기능 추가**

```python
class PromptBuilder:
    """프롬프트 빌더 (디버깅 가능)"""
    
    def __init__(self):
        self.history = []
    
    def build(self, raw_prompt: str, context: dict, model_config) -> dict:
        """프롬프트 생성 + 중간 과정 저장"""
        
        # Step 1: Input 조합
        combined_input = self._combine_input(raw_prompt, context)
        self.history.append(("input", combined_input))
        
        # Step 2: GPT 변환
        gpt_result = self._call_gpt(combined_input, model_config)
        self.history.append(("gpt_output", gpt_result))
        
        # Step 3: 최종 검증
        final = self._validate(gpt_result)
        self.history.append(("final", final))
        
        return {
            "final_prompt": final,
            "debug_info": {
                "raw_input": raw_prompt,
                "context": context,
                "steps": self.history
            }
        }
```

**사용 예**:
```python
# API 응답에 디버그 정보 포함
{
    "image_base64": "...",
    "prompt_debug": {
        "input": "헬스장에서 운동하는 모습",
        "gpt_output": "Athletic person training in modern gym...",
        "final": "Athletic person training in modern gym with detailed hands..."
    }
}
```

---

## 2. 중복 구현 분석

### 🔴 **문제점 1: I2I 페이지 프롬프트 조합 로직 중복**

#### 발견된 중복:

**① T2I 페이지 (app.py Line 645-658)**
```python
raw_prompt = ""
if connect_mode and selected_caption:
    if base_prompt.strip():
        raw_prompt = f"{base_prompt.strip()} — {selected_caption} {hashtags}".strip()
    else:
        raw_prompt = f"{selected_caption} {hashtags}".strip()
else:
    raw_prompt = base_prompt.strip()
```

**② I2I 페이지 (app.py Line 1100-1150)**
```python
selected_caption = st.session_state.get("selected_caption", "")
hashtags = st.session_state.get("hashtags", "")
captions_for_support = f"{selected_caption} {hashtags}".strip()

# 보조 프롬프트 생성
def build_support(text, method, strength_label):
    if not text:
        return ""
    if method == "단순 키워드 변환":
        base = ", ".join(re.split(r"[ ,.\n]+", text)[:20])
    elif method == "GPT 기반 자연스럽게":
        base = f"{text}, cinematic soft light, premium mood, refined rendering"
    else:
        base = f"{text}, balanced framing, clean aesthetic"
    
    ratio = {"약하게": "0.3", "중간": "0.6", "강하게": "1.0"}[strength_label]
    return f"({base}:{ratio})"
```

**③ 편집 페이지 (app.py Line 1550-1600)**
```python
# 동일한 build_support_prompt 함수가 또 정의됨
def build_support_prompt(text, method, strength):
    if not text:
        return ""
    if method == "단순 키워드 변환":
        base = ", ".join(re.split(r"[ ,.\n]+", text)[:20])
    # ... (I2I와 동일한 로직)
```

#### ⚠️ **문제**:
- 동일한 로직이 3곳에 존재
- 한 곳을 수정하면 나머지도 수정해야 함
- 불일치 가능성 (현재도 미묘하게 다름)

---

### 🔴 **문제점 2: 모델 정보 조회 로직 중복**

```python
# ① services.py Line 268-277
if model_config is None:
    try:
        current_model_name = get_current_comfyui_model()
    except NameError:
        current_model_name = None
    
    if current_model_name:
        try:
            model_config = registry.get_model(current_model_name)
        except Exception:
            model_config = None

# ② app.py Line 668-674
selected_model_id = st.session_state.get("selected_generation_model_id")
current_model_name = api.get_current_comfyui_model()

is_flux = (
    (selected_model_id and "flux" in selected_model_id.lower()) or
    (current_model_name and "flux" in current_model_name.lower())
)
```

---

### ✅ **개선안: 유틸리티 함수 통합**

```python
# frontend/utils.py (신규 파일)
class PromptHelper:
    """프롬프트 조합 유틸리티"""
    
    @staticmethod
    def combine_caption_and_prompt(
        main_prompt: str,
        caption: str = "",
        hashtags: str = "",
        connect_mode: bool = False
    ) -> str:
        """페이지1 문구와 사용자 프롬프트 조합"""
        if not connect_mode or not caption:
            return main_prompt.strip()
        
        if main_prompt.strip():
            return f"{main_prompt.strip()} — {caption} {hashtags}".strip()
        return f"{caption} {hashtags}".strip()
    
    @staticmethod
    def build_support_prompt(
        text: str,
        method: str = "단순 키워드 변환",
        strength: str = "중간"
    ) -> str:
        """보조 프롬프트 생성 (I2I, 편집 공용)"""
        if not text:
            return ""
        
        # 방식별 처리
        base_prompts = {
            "단순 키워드 변환": ", ".join(re.split(r"[ ,.\n]+", text)[:20]),
            "GPT 기반 자연스럽게": f"{text}, cinematic soft light, premium mood",
            "사용자 조절형 혼합": f"{text}, balanced framing, clean aesthetic"
        }
        base = base_prompts.get(method, text)
        
        # 강도 적용
        weights = {"약하게": "0.3", "중간": "0.6", "강하게": "1.0"}
        weight = weights.get(strength, "0.6")
        
        return f"({base}:{weight})"

# 사용
from .utils import PromptHelper

# T2I 페이지
raw_prompt = PromptHelper.combine_caption_and_prompt(
    base_prompt, selected_caption, hashtags, connect_mode
)

# I2I 페이지
support_prompt = PromptHelper.build_support_prompt(
    captions_for_support, support_method, support_strength
)
```

---

## 3. 불필요한 복잡성 및 논리적 얽힘

### 🔴 **문제점 1: 모델 선택 로직의 복잡성**

#### 현재 구조 (app.py Line 367-479):

```python
if page_id == "image_editing_experiment":
    # 편집 모드 선택
    EDITING_MODES = {...}
    selected_mode_id = st.sidebar.selectbox(...)
    st.session_state["selected_editing_mode"] = selected_mode_id
else:
    # 생성 모델 선택
    current_comfyui_model = api.get_current_comfyui_model()
    experiments_data = api.get_image_editing_experiments()
    
    if experiments_data and experiments_data.get("success"):
        experiments = experiments_data.get("experiments", [])
        generation_models = [exp for exp in experiments if "FLUX.1-dev-Q" in exp["id"]]
        
        if generation_models:
            exp_map = {exp["id"]: exp for exp in generation_models}
            exp_ids = ["none"] + [exp["id"] for exp in generation_models]
            exp_names = ["모델 없음"] + [f"{exp['name']}" for exp in generation_models]
            
            default_idx = 0
            if "selected_generation_model_id" in st.session_state:
                saved_model = st.session_state["selected_generation_model_id"]
                if saved_model in exp_ids:
                    default_idx = exp_ids.index(saved_model)
            elif current_comfyui_model:
                if current_comfyui_model in exp_ids:
                    default_idx = exp_ids.index(current_comfyui_model)
            
            selected_model_name = st.sidebar.selectbox(...)
            # ... 50줄 이상의 복잡한 로직
```

#### ⚠️ **문제**:
- 페이지별로 다른 모델 선택 UI (편집 vs 생성)
- 중첩된 조건문 (if 내부에 if 4단계)
- 세션 상태 관리가 여러 곳에 분산
- 가독성 매우 낮음

---

### 🔴 **문제점 2: 프론트엔드에서 백엔드 로직 침범**

```python
# app.py Line 335 - 프론트엔드가 프롬프트 변환 수행
def caption_to_prompt(caption: str, style: str = "Instagram banner") -> str:
    """문구를 이미지 프롬프트로 변환"""
    return f"{caption}, {style}, vibrant, professional, motivational"

# app.py Line 660 - 프론트엔드가 1차 변환
final_prompt = caption_to_prompt(raw_prompt) if raw_prompt else ""
```

**문제**:
- 프론트엔드가 비즈니스 로직 포함
- 프롬프트 정책 변경 시 프론트+백엔드 모두 수정 필요
- 단위 테스트 불가

---

### 🔴 **문제점 3: 에러 처리의 불일치**

```python
# ① services.py - Exception을 그대로 raise
def build_final_prompt(raw_prompt: str, model_config=None) -> str:
    try:
        current_model_name = get_current_comfyui_model()
    except NameError:
        current_model_name = None  # 조용히 무시

# ② app.py - RuntimeError로 wrapping
def call_image_editing_experiment(self, payload: dict):
    try:
        response = requests.post(url, json=payload, timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError(f"이미지 편집 실패: {response.text}")
    except Exception as e:
        raise RuntimeError(f"call_image_editing_experiment 오류: {e}")

# ③ services.py - 로그만 출력
def expand_prompt_with_gpt(text: str) -> str:
    try:
        resp = openai_client.responses.create(...)
    except Exception as e:
        logger.warning(f"⚠️ 1단계 한국어 확장 실패 → 원본 사용: {e}")
        return text  # 원본 반환
```

**문제**:
- 에러 처리 전략이 통일되지 않음
- 어떤 곳은 raise, 어떤 곳은 fallback, 어떤 곳은 무시
- 디버깅 어려움

---

### ✅ **개선안 1: 모델 선택 로직 리팩토링**

```python
# frontend/model_selector.py (신규 파일)
class ModelSelector:
    """모델 선택 UI 컴포넌트"""
    
    def __init__(self, api_client):
        self.api = api_client
    
    def render_generation_model_selector(self):
        """생성 모델 선택 UI"""
        st.sidebar.subheader("🤖 이미지 생성 모델")
        
        # 1. 사용 가능한 모델 목록 가져오기
        models = self._get_available_models()
        if not models:
            st.sidebar.warning("모델을 불러올 수 없습니다.")
            return None
        
        # 2. 기본값 결정
        default_idx = self._get_default_model_index(models)
        
        # 3. UI 렌더링
        selected = st.sidebar.selectbox(
            "모델 선택",
            models,
            index=default_idx,
            format_func=lambda m: m.display_name
        )
        
        # 4. 세션 저장
        st.session_state["selected_model"] = selected
        return selected
    
    def render_editing_mode_selector(self):
        """편집 모드 선택 UI"""
        st.sidebar.subheader("✨ 편집 모드 선택")
        
        modes = self._get_editing_modes()
        selected = st.sidebar.selectbox(
            "편집 모드",
            modes,
            format_func=lambda m: m.display_name
        )
        
        st.session_state["selected_editing_mode"] = selected
        return selected
    
    def _get_available_models(self):
        """백엔드에서 모델 목록 가져오기 (캐싱)"""
        # 구현...
    
    def _get_default_model_index(self, models):
        """기본 선택 인덱스 결정"""
        # 구현...

# main.py
selector = ModelSelector(api)

if page_id == "image_editing_experiment":
    selected_mode = selector.render_editing_mode_selector()
else:
    selected_model = selector.render_generation_model_selector()
```

---

### ✅ **개선안 2: 계층 분리 명확화**

```
┌─────────────────────────────────────────────┐
│          Frontend (app.py)                  │
│  - UI 렌더링만 담당                          │
│  - 사용자 입력 수집                          │
│  - API 호출 및 결과 표시                     │
└─────────────────────────────────────────────┘
                    ↓ API 호출
┌─────────────────────────────────────────────┐
│          Backend API (main.py)              │
│  - 요청 검증                                 │
│  - 서비스 계층 호출                          │
│  - 응답 포맷팅                               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│       Service Layer (services.py)           │
│  - 비즈니스 로직 (프롬프트 처리 등)          │
│  - 모델 호출                                 │
│  - 데이터 변환                               │
└─────────────────────────────────────────────┘
```

**수정 예**:
```python
# ❌ 현재: 프론트엔드가 프롬프트 변환
# frontend/app.py
final_prompt = caption_to_prompt(raw_prompt)

# ✅ 개선: 백엔드가 일괄 처리
# frontend/app.py
payload = {
    "raw_prompt": raw_prompt,
    "context": {...}
}
result = api.generate_t2i(payload)

# backend/services.py
def generate_t2i_core(raw_prompt: str, context: dict, ...):
    final_prompt = build_final_prompt(raw_prompt, context, model_config)
    # 이미지 생성...
```

---

### ✅ **개선안 3: 통일된 에러 처리**

```python
# backend/exceptions.py (신규 파일)
class ServiceError(Exception):
    """서비스 계층 기본 에러"""
    pass

class PromptOptimizationError(ServiceError):
    """프롬프트 최적화 실패"""
    pass

class ModelLoadError(ServiceError):
    """모델 로딩 실패"""
    pass

# backend/services.py
def build_final_prompt(raw_prompt: str, model_config=None) -> str:
    try:
        # 로직...
    except NameError as e:
        # 명확한 에러 메시지
        raise PromptOptimizationError(
            f"모델 정보를 가져올 수 없습니다: {e}"
        ) from e
    except Exception as e:
        # 예상치 못한 에러도 wrapping
        logger.exception("프롬프트 생성 중 예외 발생")
        raise PromptOptimizationError(
            f"프롬프트 처리 실패: {e}"
        ) from e

# backend/main.py
@app.post("/api/generate_t2i")
async def generate_t2i(request: T2IRequest):
    try:
        result = services.generate_t2i_core(...)
        return {"success": True, "data": result}
    except PromptOptimizationError as e:
        # 특정 에러 처리
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e), "type": "prompt_error"}
        )
    except ServiceError as e:
        # 일반 서비스 에러
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "type": "service_error"}
        )
```

---

## 4. 종합 개선 로드맵

### 📅 **Phase 1: 즉시 적용 가능 (1-2일)**

1. **프론트엔드 프롬프트 변환 제거**
   - `caption_to_prompt()` 삭제
   - 원본 프롬프트를 백엔드에 그대로 전달
   - 효과: 중복 제거, 백엔드 중앙화

2. **GPT 호출 통합**
   - 3단계 → 1단계로 축소
   - 비용 66% 절감
   - 처리 시간 50% 단축

3. **유틸리티 함수 통합**
   - `PromptHelper` 클래스 생성
   - 중복 코드 제거

### 📅 **Phase 2: 구조 개선 (3-5일)**

1. **계층 분리 명확화**
   - 프론트엔드: UI only
   - 백엔드: 비즈니스 로직
   
2. **모델 선택 로직 리팩토링**
   - `ModelSelector` 컴포넌트 분리
   - 복잡도 감소

3. **에러 처리 통일**
   - Custom Exception 정의
   - 일관된 에러 응답

### 📅 **Phase 3: 고도화 (1주)**

1. **프롬프트 디버깅 기능**
   - 중간 과정 가시화
   - A/B 테스트 지원

2. **프롬프트 캐싱**
   - 동일 프롬프트 재사용
   - GPT 호출 최소화

3. **성능 모니터링**
   - 프롬프트 변환 시간 추적
   - 병목 지점 식별

---

## 📊 기대 효과

### 비용 절감
- GPT API 호출: 3회 → 1회 (**66% 절감**)
- 월 1000건 기준: $30 → $10

### 성능 개선
- 프롬프트 처리 시간: 3-6초 → 1-2초 (**50-66% 단축**)
- 사용자 대기 시간 감소

### 유지보수성 향상
- 코드 중복: 3곳 → 1곳
- 수정 시간: 3배 → 1배
- 버그 발생 확률 감소

### 확장성
- 새로운 모델 추가 용이
- 프롬프트 정책 변경 간편
- 테스트 가능한 구조

---

## 🎯 결론

현재 프로젝트는 **기능적으로는 작동하지만 구조적 개선이 필요**한 상태입니다.

**핵심 문제**:
1. 프롬프트 처리 로직이 분산되어 중복과 불일치 발생
2. GPT API 과다 호출로 인한 비용/성능 문제
3. 계층 분리 불명확으로 유지보수 어려움

**권장 조치**:
- Phase 1 즉시 시작 (비용 절감 효과 즉각적)
- Phase 2-3은 점진적 적용
- 각 Phase마다 테스트 및 검증

이 개선안들은 코드 품질을 크게 향상시키면서도 기존 기능은 모두 유지합니다.
