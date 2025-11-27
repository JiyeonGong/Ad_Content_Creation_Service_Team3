# app.py (페이지 2 + 3 개선)
"""
헬스케어 AI 콘텐츠 제작 앱 - Streamlit 프론트엔드
설정 기반 아키텍처로 하드코딩 최소화
"""
import os
import re
import streamlit as st
import requests
from io import BytesIO
from PIL import Image
import base64
import yaml
from typing import Optional, Dict, Any, List
from pathlib import Path

# ============================================================
# 설정 로더
# ============================================================
class ConfigLoader:
    """설정 파일 로더"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "frontend_config.yaml")
        
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """YAML 설정 파일 로드"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            st.warning(f"⚠️ 설정 파일이 없습니다: {self.config_path}")
            return self._default_config()
        except Exception as e:
            st.error(f"❌ 설정 파일 로드 실패: {e}")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "app": {"title": "AI 콘텐츠 제작", "layout": "wide"},
            "api": {"base_url": "http://localhost:8000", "timeout": 180, "retry_attempts": 2},
            "caption": {
                "service_types": ["헬스장", "PT", "요가/필라테스", "기타"],
                "tones": ["친근하고 동기부여", "전문적이고 신뢰감"]
            },
            "image": {
                "preset_sizes": [
                    {"name": "1024x1024", "width": 1024, "height": 1024}
                ],
                "steps": {"min": 1, "max": 50, "default": 10}
            }
        }
    
    def get(self, path: str, default=None):
        """점 표기법으로 설정 값 가져오기 (예: 'api.base_url')"""
        keys = path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        return value if value is not None else default

# ============================================================
# API 클라이언트
# ============================================================
class APIClient:
    """백엔드 API 클라이언트"""

    def __init__(self, config: ConfigLoader):
        self.base_url = os.getenv("API_BASE_URL") or config.get("api.base_url")
        self.timeout = config.get("api.timeout", 180)
        self.retry_attempts = config.get("api.retry_attempts", 2)

        # 백엔드 모델 정보 캐싱
        self._model_info = None
        self._backend_status = None

        # 서버 시작 시간 (재시작 감지용)
        self._server_start_time = None
    
    def get_backend_status(self, force_refresh: bool = False) -> Optional[Dict]:
        """백엔드 상태 조회 (캐싱)"""
        if self._backend_status and not force_refresh:
            return self._backend_status

        try:
            resp = requests.get(f"{self.base_url}/status", timeout=5)
            resp.raise_for_status()
            self._backend_status = resp.json()

            # 서버 재시작 감지
            new_start_time = self._backend_status.get("server_start_time")
            if new_start_time and self._server_start_time:
                if new_start_time != self._server_start_time:
                    # 서버가 재시작됨 - 캐시 무효화
                    self._model_info = None
                    self._server_start_time = new_start_time
                    return {"server_restarted": True, **self._backend_status}
            self._server_start_time = new_start_time

            return self._backend_status
        except Exception as e:
            st.error(f"❌ 백엔드 연결 실패: {e}")
            return None
    
    def get_model_info(self, force_refresh: bool = False) -> Optional[Dict]:
        """모델 정보 조회 (캐싱)"""
        if self._model_info and not force_refresh:
            return self._model_info

        try:
            resp = requests.get(f"{self.base_url}/models", timeout=5)
            resp.raise_for_status()
            self._model_info = resp.json()
            return self._model_info
        except Exception as e:
            st.warning(f"⚠️ 모델 정보 조회 실패: {e}")
            return None

    def switch_model(self, model_name: str) -> Dict:
        """모델 전환 (비동기 방식)"""
        import time

        # 1. 비동기 전환 시작
        try:
            resp = requests.post(
                f"{self.base_url}/api/switch_model_async",
                json={"model_name": model_name},
                timeout=10
            )
            resp.raise_for_status()
        except Exception as e:
            raise Exception(f"모델 전환 시작 실패: {e}")

        # 2. 폴링으로 완료 대기 (최대 5분)
        max_wait = 300
        poll_interval = 2
        elapsed = 0

        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval

            try:
                status_resp = requests.get(
                    f"{self.base_url}/api/switch_model_status",
                    timeout=5
                )
                status_resp.raise_for_status()
                status = status_resp.json()

                # 전환 완료 확인
                if not status.get("in_progress", True):
                    if status.get("success"):
                        # 캐시 무효화
                        self._model_info = None
                        self._backend_status = None
                        return {
                            "success": True,
                            "message": status.get("message", "모델 전환 완료")
                        }
                    else:
                        raise Exception(status.get("error", "모델 전환 실패"))
            except requests.exceptions.RequestException:
                # 네트워크 오류는 무시하고 재시도
                pass

        raise Exception("모델 전환 타임아웃 (5분 초과)")
    
    def load_model(self, model_name: str) -> Dict:
        """모델 로드"""
        try:
            # 로딩은 시간이 걸릴 수 있으므로 타임아웃 넉넉히
            resp = requests.post(
                f"{self.base_url}/api/load_model",
                json={"model_name": model_name},
                timeout=300
            )
            resp.raise_for_status()
            self._model_info = None # 캐시 초기화
            return resp.json()
        except Exception as e:
            raise Exception(f"모델 로드 실패: {e}")

    def unload_model(self) -> Dict:
        """모델 언로드"""
        try:
            resp = requests.post(
                f"{self.base_url}/api/unload_model",
                timeout=60
            )
            resp.raise_for_status()
            self._model_info = None # 캐시 초기화
            return resp.json()
        except Exception as e:
            raise Exception(f"모델 언로드 실패: {e}")
    
    def call_caption(self, payload: Dict) -> str:
        """문구 생성 API 호출"""
        try:
            resp = requests.post(
                f"{self.base_url}/api/caption",
                json=payload,
                timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()["output_text"]
        except Exception as e:
            raise Exception(f"문구 생성 실패: {e}")
    
    def call_t2i(self, payload: Dict) -> Optional[BytesIO]:
        """T2I 이미지 생성 (자동 재시도 포함)"""
        current_payload = payload.copy()
        
        for attempt in range(self.retry_attempts + 1):
            try:
                resp = requests.post(
                    f"{self.base_url}/api/generate_t2i",
                    json=current_payload,
                    timeout=self.timeout
                )
                resp.raise_for_status()
                b64 = resp.json()["image_base64"]
                return BytesIO(base64.b64decode(b64))
            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 503 and attempt < self.retry_attempts:
                    # GPU OOM 시 해상도 줄여서 재시도
                    detail = e.response.json().get("detail", "")
                    if "메모리" in detail or "GPU" in detail:
                        w = current_payload["width"]
                        h = current_payload["height"]
                        new_w = max(64, align_to_64(w // 2))
                        new_h = max(64, align_to_64(h // 2))
                        st.info(f"⚠️ 메모리 부족 - 해상도 낮춤: {w}x{h} → {new_w}x{new_h}")
                        current_payload["width"] = new_w
                        current_payload["height"] = new_h
                        continue
                raise Exception(f"T2I 생성 실패: {e.response.json().get('detail', str(e))}")
            except Exception as e:
                raise Exception(f"T2I 요청 실패: {e}")
        
        return None
    
    def call_i2i(self, payload: Dict) -> Optional[BytesIO]:
        """I2I 이미지 편집 (자동 재시도 포함)"""
        current_payload = payload.copy()
        
        for attempt in range(self.retry_attempts + 1):
            try:
                resp = requests.post(
                    f"{self.base_url}/api/generate_i2i",
                    json=current_payload,
                    timeout=self.timeout
                )
                resp.raise_for_status()
                b64 = resp.json()["image_base64"]
                return BytesIO(base64.b64decode(b64))
            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 503 and attempt < self.retry_attempts:
                    detail = e.response.json().get("detail", "")
                    if "메모리" in detail or "GPU" in detail:
                        w = current_payload["width"]
                        h = current_payload["height"]
                        new_w = max(64, align_to_64(w // 2))
                        new_h = max(64, align_to_64(h // 2))
                        st.info(f"⚠️ 메모리 부족 - 해상도 낮춤: {w}x{h} → {new_w}x{new_h}")
                        current_payload["width"] = new_w
                        current_payload["height"] = new_h
                        continue
                raise Exception(f"I2I 편집 실패: {e.response.json().get('detail', str(e))}")
            except Exception as e:
                raise Exception(f"I2I 요청 실패: {e}")
        
        return None

# ============================================================
# 유틸리티 함수
# ============================================================
def align_to_64(val: int) -> int:
    """64의 배수로 정렬"""
    v = max(64, int(val))
    return (v // 64) * 64

def parse_caption_output(output: str) -> tuple:
    """GPT 출력 파싱"""
    captions, hashtags = [], ""
    try:
        m = re.search(r"문구:(.*?)해시태그:(.*)", output, re.S)
        if m:
            caption_text = m.group(1).strip()
            hashtags = m.group(2).strip()
            captions = [
                line.split(".", 1)[1].strip() if "." in line else line.strip()
                for line in caption_text.split("\n") if line.strip()
            ]
        else:
            captions = [output]
    except:
        captions = [output]
    return captions, hashtags

def caption_to_prompt(caption: str, style: str = "Instagram banner") -> str:
    """문구를 이미지 프롬프트로 변환"""
    return f"{caption}, {style}, vibrant, professional, motivational"

# ============================================================
# 메인 앱
# ============================================================
def main():
    # 설정 로드
    config = ConfigLoader()
    api = APIClient(config)
    
    # 앱 설정
    st.set_page_config(
        page_title=config.get("app.title"),
        layout=config.get("app.layout", "wide")
    )
    
    # 사이드바
    st.sidebar.title("메뉴")
    
    # 페이지 목록 (설정 파일 기반)
    pages_config = config.get("pages", [])
    page_options = [f"{p['icon']} {p['title']}" for p in pages_config]
    menu = st.sidebar.radio("페이지 선택", page_options)
    
    # 선택된 페이지 ID 찾기
    selected_idx = page_options.index(menu)
    page_id = pages_config[selected_idx]["id"]
    
    # 모델 선택
    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 이미지 생성 모델")

    model_info = api.get_model_info()
    if model_info:
        current_model = model_info.get("current") # None이면 언로드 상태
        available_models = list(model_info.get("models", {}).keys())
        
        # 상태 아이콘 및 텍스트
        if current_model:
            st.sidebar.success(f"💡 **ON** (Loaded: {current_model})")
        else:
            st.sidebar.markdown(f"⚫ **OFF** (Unloaded)")

        # 모델 선택 드롭다운 (로드할 모델 또는 전환할 모델 선택)
        # 현재 로드된 모델이 있으면 그걸 기본값으로, 없으면 첫 번째 모델
        default_idx = 0
        if current_model and current_model in available_models:
            default_idx = available_models.index(current_model)
            
        selected_model = st.sidebar.selectbox(
            "모델 선택",
            available_models,
            index=default_idx,
            key="model_selector"
        )

        # 선택한 모델 설명
        if selected_model in model_info["models"]:
            model_desc = model_info["models"][selected_model].get("description", "")
            if model_desc:
                st.sidebar.caption(f"📝 {model_desc}")

        # 제어 버튼 영역
        col_btn1, col_btn2 = st.sidebar.columns(2)
        
        if current_model:
            # 로드된 상태: 언로드 버튼 + (다른 모델 선택 시) 전환 버튼
            if st.sidebar.button("🔌 모델 끄기 (Unload)", type="secondary"):
                with st.spinner("모델 언로드 중..."):
                    try:
                        api.unload_model()
                        st.sidebar.success("모델이 꺼졌습니다.")
                        api.get_model_info(force_refresh=True)
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"❌ {e}")
            
            # 모델이 다르면 전환 버튼 표시
            if selected_model != current_model:
                if st.sidebar.button("🔄 모델 전환", type="primary"):
                    with st.spinner(f"'{selected_model}' 로 전환 중..."):
                        try:
                            # 전환은 기존 switch_model 사용 (비동기)
                            result = api.switch_model(selected_model)
                            st.sidebar.success(result["message"])
                            api.get_model_info(force_refresh=True)
                            st.rerun()
                        except Exception as e:
                            st.sidebar.error(f"❌ {e}")
        else:
            # 언로드 상태: 로드 버튼
            if st.sidebar.button("⚡ 모델 켜기 (Load)", type="primary"):
                with st.spinner(f"'{selected_model}' 로딩 중... (잠시만 기다려주세요)"):
                    try:
                        api.load_model(selected_model)
                        st.sidebar.success(f"'{selected_model}' 로드 완료!")
                        api.get_model_info(force_refresh=True)
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"❌ {e}")
    else:
        st.sidebar.warning("⚠️ 모델 정보를 가져올 수 없습니다")

    # 연결 모드
    st.sidebar.markdown("---")
    connect_mode = st.sidebar.checkbox(
        "🔗 페이지 연결 모드",
        value=config.get("connection_mode.enabled_by_default", True)
    )
    st.sidebar.info(config.get("connection_mode.description", ""))

    # 백엔드 상태 표시
    with st.sidebar.expander("🔧 시스템 상태"):
        status = api.get_backend_status(force_refresh=True)
        if status:
            # 서버 재시작 감지 시 자동 새로고침
            if status.get("server_restarted"):
                st.warning("🔄 서버가 재시작되었습니다. 상태를 새로고침합니다...")
                api.get_model_info(force_refresh=True)
                st.rerun()

            st.json(status)
            if st.button("🔄 새로고침"):
                api.get_backend_status(force_refresh=True)
                api.get_model_info(force_refresh=True)
                st.rerun()
        else:
            st.error("백엔드 연결 안됨")
    
    # 연결 모드 OFF 시 세션 초기화
    if not connect_mode:
        for key in ["captions", "hashtags", "generated_images", "selected_caption", "edit_prompt_i2i", "strength_i2i", "steps_i2i", "negative_prompt_i2i", "selected_size_i2i"]:
            if key in st.session_state:
                del st.session_state[key]
    
    # 페이지 라우팅
    if page_id == "caption":
        render_caption_page(config, api)
    elif page_id == "t2i":
        render_t2i_page(config, api, connect_mode)
    elif page_id == "i2i":
        render_i2i_page(config, api, connect_mode)

# ============================================================
# 페이지 1: 문구 생성
# ============================================================
def render_caption_page(config: ConfigLoader, api: APIClient):
    st.title("📝 홍보 문구 & 해시태그 생성")
    
    with st.form("content_form"):
        service_type = st.selectbox(
            "서비스 종류",
            config.get("caption.service_types", [])
        )
        
        location = st.text_input(
            "지역",
            placeholder=config.get("ui.placeholders.location", "예: 강남")
        )
        
        service_name = st.text_input(
            "제품/클래스 이름",
            placeholder=config.get("ui.placeholders.service_name", "")
        )
        
        features = st.text_area(
            "핵심 특징 및 장점",
            placeholder=config.get("ui.placeholders.features", "")
        )
        
        tone = st.selectbox(
            "톤 선택",
            config.get("caption.tones", [])
        )
        
        submitted = st.form_submit_button("✨ 문구+해시태그 생성")
    
    if submitted:
        if not service_name.strip() or not features.strip() or not location.strip():
            st.warning(config.get("ui.messages.no_input"))
            return
        
        payload = {
            "service_type": service_type,
            "service_name": service_name,
            "features": features,
            "location": location,
            "tone": tone
        }
        
        with st.spinner(config.get("ui.messages.loading")):
            try:
                output = api.call_caption(payload)
                captions, hashtags = parse_caption_output(output)
                
                st.session_state["captions"] = captions
                st.session_state["hashtags"] = hashtags
            except Exception as e:
                st.error(f"{config.get('ui.messages.error')}: {e}")
                return
    
    # 생성된 문구 표시
    if "captions" in st.session_state and st.session_state["captions"]:
        st.markdown("### 💬 생성된 문구")
        for i, caption in enumerate(st.session_state["captions"], 1):
            st.write(f"**{i}.** {caption}")
        
        st.markdown("---")
        selected_idx = st.radio(
            "다음 페이지에서 사용할 문구 선택:",
            range(len(st.session_state["captions"])),
            format_func=lambda x: f"문구 {x+1}",
            key="caption_selector"
        )
        st.session_state["selected_caption"] = st.session_state["captions"][selected_idx]
        
        st.success(f"✅ 선택: {st.session_state['selected_caption'][:50]}...")
        
        st.markdown("### 🔖 추천 해시태그")
        st.code(st.session_state["hashtags"], language="")

# ============================================================
# 페이지 2: T2I 이미지 생성 (향상된 프롬프트 제어 통합)
# ============================================================
def render_t2i_page(config: ConfigLoader, api: APIClient, connect_mode: bool):
    st.title("🖼 문구 기반 이미지 생성 (향상된 프롬프트 제어 포함)")

    # ============================================================
    # 📌 1) 페이지1 선택 문구 + 사용자 입력 프롬프트
    # ============================================================
    base_prompt = ""
    selected_caption = st.session_state.get("selected_caption", "")
    
    if connect_mode and selected_caption:
        st.info(f"🔗 연결 모드 활성화 — 페이지1 문구가 보조 요소로 사용됩니다.\n\n**선택 문구:** {selected_caption}")
        base_prompt = st.text_area(
            "메인 프롬프트 (사용자 입력)",
            placeholder="예: 밝고 에너지 넘치는 필라테스 스튜디오, 건강하고 활기찬 느낌",
            help="연결 모드가 켜져 있어도 이 입력은 항상 반영됩니다.",
            value=st.session_state.get("base_prompt_t2i", "") # 상태 유지
        )
    else:
        if connect_mode:
            st.warning("⚠️ 페이지1에서 문구를 먼저 생성하세요")
        base_prompt = st.text_area(
            "메인 프롬프트",
            placeholder=config.get("ui.placeholders.caption", "예: 따뜻한 조명, 편안한 분위기의 요가 공간"),
            help="연결 모드가 꺼져 있을 때는 이 프롬프트만 사용됩니다.",
            value=st.session_state.get("base_prompt_t2i", "") # 상태 유지
        )
        
    st.session_state["base_prompt_t2i"] = base_prompt # 세션 저장

    # 페이지1 보조 프롬프트 원본
    captions_for_support = f"{selected_caption} {st.session_state.get('hashtags','')}".strip()

    # ============================================================
    # 📌 2) 보조 프롬프트 옵션 UI
    # ============================================================
    st.markdown("---")
    st.markdown("### 🎚 보조 프롬프트 설정 (페이지1 문구 사용 시)")

    support_strength = st.select_slider(
        "보조 프롬프트 강도",
        options=["약하게", "중간", "강하게"],
        value=st.session_state.get("support_strength", "중간"), # 세션 상태 유지
        help="보조 분위기 요소가 메인 프롬프트에 얼마나 영향을 줄지 결정합니다."
    )

    support_method = st.selectbox(
        "보조 프롬프트 생성 방식",
        ["단순 키워드 변환", "GPT 기반 자연스러운 스타일 변환", "사용자 조절형 혼합"],
        index=["단순 키워드 변환", "GPT 기반 자연스러운 스타일 변환", "사용자 조절형 혼합"].index(st.session_state.get("support_method", "단순 키워드 변환")), # 세션 상태 유지
        help="페이지1 문구를 어떻게 이미지 스타일 요소로 변환할지 선택합니다."
    )

    enable_negative = st.checkbox(
        "NEGATIVE 프롬프트 자동 생성",
        value=st.session_state.get("enable_negative", True), # 세션 상태 유지
        help="원치 않는 요소(노이즈, 왜곡, 비현실적 비율 등)를 자동 억제합니다."
    )

    # 세션 저장 (UI 조작 후 값 업데이트)
    st.session_state["support_strength"] = support_strength
    st.session_state["support_method"] = support_method
    st.session_state["enable_negative"] = enable_negative

    # ============================================================
    # 📌 3) 보조 프롬프트 생성 로직
    # ============================================================
    def build_support_prompt(text, method, strength):
        if not text:
            return ""

        if method == "단순 키워드 변환":
            prompt = ", ".join(re.split(r"[ ,.\n]+", text)[:30])
        elif method == "GPT 기반 자연스러운 스타일 변환":
            prompt = f"{text}, cinematic soft light, refined composition, premium studio mood"
        else:  # 사용자 조절형 혼합
            prompt = f"{text}, warm tone, clean aesthetic, balanced framing"

        # 프롬프트 강도 적용 (Weighted Prompting)
        if strength == "약하게":
            return f"({prompt}:0.3)"
        elif strength == "중간":
            return f"({prompt}:0.6)"
        else:
            return f"({prompt}:1.0)"

    support_prompt = build_support_prompt(captions_for_support, support_method, support_strength)

    # ============================================================
    # 📌 4) NEGATIVE 프롬프트 생성
    # ============================================================
    negative_prompt = ""
    if enable_negative:
        negative_prompt = (
            "distorted body, extra limbs, blur, noise, low quality, artifacts,"
            "mutated hands, unrealistic anatomy, text, watermark, bad hands, lowres, worse quality"
        )

    # ============================================================
    # 📌 5) 최종 프롬프트 구성
    # ============================================================
    if connect_mode and selected_caption: 
        final_prompt = f"{base_prompt}, {support_prompt}".strip(", ")
    else:
        final_prompt = base_prompt

    # 최종 프롬프트 미리보기 (디버깅/정보용)
    if final_prompt:
        st.caption(f"**최종 PROMPT:** {final_prompt[:150]}...")
    if negative_prompt:
        st.caption(f"**NEGATIVE PROMPT:** {negative_prompt}")

    # ============================================================
    # 📌 6) 나머지 기존 로직 (모델/크기/steps/UI/생성/표시)
    # ============================================================
    st.markdown("---")
    
    # 현재 모델 정보 가져오기 (크기 권장을 위해)
    model_info = api.get_model_info()
    current_model_name = model_info.get("current") if model_info else None
    is_flux = current_model_name and "flux" in current_model_name.lower()

    # 이미지 크기 (설정 기반)
    preset_sizes = config.get("image.preset_sizes", [])

    # FLUX 모델 사용 시 권장 크기 표시 로직
    size_options = []
    for s in preset_sizes:
        label = f"{s['name']} ({s['width']}x{s['height']})"
        # FLUX 모델이고 1024x1024인 경우 권장 표시
        if is_flux and s['width'] == 1024 and s['height'] == 1024:
            label += " ⭐ 권장"
        size_options.append(label)

    # 세션 상태에 마지막 선택된 크기 저장 (선택 박스 기본값으로 사용)
    default_size_idx = 0
    if "selected_size_t2i" in st.session_state and st.session_state["selected_size_t2i"] in size_options:
         default_size_idx = size_options.index(st.session_state["selected_size_t2i"])
        
    selected_size = st.selectbox("이미지 크기", size_options, index=default_size_idx, key="size_selector_t2i")
    st.session_state["selected_size_t2i"] = selected_size # 선택 상태 저장

    # 선택된 크기 파싱
    size_idx = size_options.index(selected_size)
    width = preset_sizes[size_idx]["width"]
    height = preset_sizes[size_idx]["height"]
    
    # Steps & Guidance Scale (모델 정보 기반)
    if model_info and model_info.get("current"):
        current_model_name = model_info["current"]
        current_model = model_info["models"].get(current_model_name, {})
        default_steps = current_model.get("default_steps", config.get("image.steps.default", 20))
        default_guidance = current_model.get("guidance_scale")

        st.info(f"ℹ️ 현재 모델: **{current_model_name}** (권장 steps: {default_steps}, guidance: {default_guidance if default_guidance else 'N/A'})")
    else:
        default_steps = config.get("image.steps.default", 20)
        default_guidance = None
        st.warning("⚠️ 현재 로드된 모델이 없습니다. 기본 설정으로 진행합니다.")

    col1, col2 = st.columns(2)

    # Steps (세션 상태 유지)
    with col1:
        steps = st.slider(
            "추론 단계 (Steps)",
            min_value=config.get("image.steps.min", 1),
            max_value=config.get("image.steps.max", 50),
            value=st.session_state.get("steps_t2i", default_steps),
            step=1,
            help="생성 반복 횟수 (높을수록 정교하지만 느림)",
            key="steps_slider"
        )
        st.session_state["steps_t2i"] = steps

    # Guidance Scale (모델이 지원하는 경우만, 세션 상태 유지)
    with col2:
        if default_guidance is not None:
            guidance_scale = st.slider(
                "Guidance Scale",
                min_value=1.0,
                max_value=10.0,
                value=st.session_state.get("guidance_t2i", float(default_guidance)),
                step=0.5,
                help="프롬프트 준수 강도 (높을수록 프롬프트를 더 따름)",
                key="guidance_slider"
            )
            st.session_state["guidance_t2i"] = guidance_scale
        else:
            guidance_scale = None
            st.caption("(현재 모델은 Guidance Scale 미사용)")

    # 생성 개수 선택 (세션 상태 유지)
    num_images = st.slider(
        "생성할 이미지 개수",
        min_value=1,
        max_value=5,
        value=st.session_state.get("num_images_t2i", 1),
        step=1,
        help="여러 개 생성 시 각각 다른 랜덤 seed 사용 (시간: 약 30-60초/이미지)",
        key="num_images_slider"
    )
    st.session_state["num_images_t2i"] = num_images

    # 생성 중 상태 확인
    is_generating = st.session_state.get("is_generating_t2i", False)

    # 버튼 로직
    if is_generating:
        st.warning("⏳ 이미지 생성 중입니다... 페이지를 이동하지 마세요!")
        submitted = False
    else:
        is_disabled = not base_prompt.strip() # 메인 프롬프트가 비어있으면 비활성화
        submitted = st.button(f"🖼 이미지 생성 ({num_images}개)", type="primary", disabled=is_disabled)
        if is_disabled:
            st.caption("문구를 입력하세요.")

    if submitted: 
        # 생성 시작 - 상태 설정
        st.session_state["is_generating_t2i"] = True
        st.rerun() # 재실행하여 상태 변경 반영 (Streamlit 표준 패턴)

    if st.session_state.get("is_generating_t2i") and base_prompt.strip(): # is_generating 플래그가 True일 때만 실행
        # 재실행 시 실제 생성 로직 시작
        
        # 해상도 정렬
        aligned_w = align_to_64(width)
        aligned_h = align_to_64(height)
        if aligned_w != width or aligned_h != height:
            st.info(f"해상도 정렬: {width}x{height} → {aligned_w}x{aligned_h}")

        st.session_state["generated_images"] = []
        progress_bar = st.progress(0, text="이미지 생성 준비 중...")

        for i in range(num_images):
            # 최종 프롬프트 사용
            prompt_to_send = final_prompt
            
            # 원본 코드와 같이 variation 추가 로직을 삭제하고, 최종 프롬프트를 그대로 사용.
            # (variation 추가는 프롬프트 제어 로직과 겹쳐서 혼란을 줄 수 있음)

            payload = {
                "prompt": prompt_to_send,
                "negative_prompt": negative_prompt if enable_negative else None,
                "width": aligned_w,
                "height": aligned_h,
                "steps": steps,
                "guidance_scale": guidance_scale
            }

            try:
                progress_bar.progress(i / num_images, text=f"이미지 {i+1}/{num_images} 생성 중...")
                img_bytes = api.call_t2i(payload)
                if img_bytes:
                    st.session_state["generated_images"].append({
                        "prompt": prompt_to_send,
                        "bytes": img_bytes,
                        "index": i + 1
                    })
            except Exception as e:
                progress_bar.empty()
                st.error(f"이미지 {i+1} 생성 실패: {e}")
                break
        
        progress_bar.empty()

        # 생성 완료 - 상태 해제 후 재실행하여 결과 표시
        st.session_state["is_generating_t2i"] = False
        st.rerun() 
    
    # 이미지 생성 완료 후 결과 표시 (재실행 후 이 부분 실행됨)
    if not st.session_state.get("is_generating_t2i") and st.session_state.get("generated_images"):
        
        if st.session_state.get("generated_images"):
            st.success(f"✅ {len(st.session_state['generated_images'])}개 이미지 완료!")

            cols = st.columns(len(st.session_state["generated_images"]))
            for idx, img_data in enumerate(st.session_state["generated_images"]):
                with cols[idx]:
                    # BytesIO 객체를 st.image에 직접 전달
                    img_data["bytes"].seek(0)
                    st.image(img_data["bytes"], caption=f"버전 {idx+1}", use_container_width=True)
                    img_data["bytes"].seek(0)
                    st.download_button(
                        f"⬇️ 다운로드",
                        img_data["bytes"].read(), # read()로 바이트 데이터 다시 읽기
                        f"image_v{idx+1}.png",
                        "image/png",
                        key=f"dl_{idx}"
                    )
                    img_data["bytes"].seek(0) # 다음 사용을 위해 포인터 재설정

        else:
            st.error("❌ 이미지 생성에 실패했습니다. 백엔드 로그를 확인하세요.")


# ============================================================
# 페이지 3: I2I 이미지 편집 (개선)
# ============================================================
def render_i2i_page(config: ConfigLoader, api: APIClient, connect_mode: bool):
    st.title("🖼️ 이미지 편집 (Image-to-Image)")
    st.info("💡 업로드된 이미지를 AI로 편집하거나, T2I 결과를 편집합니다 (배경 변경, 스타일 변경 등)")
    
    # ------------------------------------------------------------
    # 1. 이미지 소스 선택 및 표시 
    # ------------------------------------------------------------
    uploaded_file = None
    preloaded = st.session_state.get("generated_images", [])
    
    image_bytes = None
    target_image_name = "미선택"
    
    col_upload, col_select = st.columns([1, 2])

    # A. 업로드
    with col_upload:
        uploaded_file = st.file_uploader("새 이미지 업로드", type=["png", "jpg", "jpeg"])
        
    # B. 페이지 2 결과 선택
    can_use_preloaded = connect_mode and preloaded
    
    selected_idx = None
    if can_use_preloaded:
        with col_select:
            st.markdown("##### 또는 페이지 2 결과 사용")
            image_indices = list(range(len(preloaded)))
            
            # T2I 결과 목록 중 선택
            idx = st.selectbox(
                "편집 대상 선택",
                image_indices,
                format_func=lambda x: f"T2I 결과 버전 {x+1}",
                key="i2i_image_selector",
                index=0
            )
            
            if idx is not None and preloaded:
                selected_idx = idx

    # 최종 이미지 바이트 결정 (업로드가 우선)
    if uploaded_file:
        image_bytes = uploaded_file.getvalue()
        target_image_name = uploaded_file.name
    elif selected_idx is not None:
        # BytesIO 객체를 바이트로 변환하는 헬퍼 함수
        def get_image_bytes(bytes_io_obj):
             # 포인터를 처음으로 되돌리고 읽기
             bytes_io_obj.seek(0)
             return bytes_io_obj.read()
             
        image_bytes = get_image_bytes(preloaded[selected_idx]["bytes"])
        target_image_name = f"T2I 결과 버전 {selected_idx+1}"

    st.markdown("---")
    if image_bytes:
        st.image(image_bytes, caption=f"🔍 현재 편집 대상: {target_image_name}", width=350)
    else:
        st.warning("⚠️ 이미지를 업로드하거나 페이지 2에서 생성 및 선택하세요")

    if not image_bytes:
        return # 이미지가 없으면 나머지 설정 및 버튼 비활성화

    # ------------------------------------------------------------
    # 2. 편집 프롬프트 입력 및 연결 모드 설정
    # ------------------------------------------------------------
    st.subheader("📝 편집 지시 및 프롬프트 구성")

    selected_caption = st.session_state.get("selected_caption", "")
    
    # 연결 모드 (페이지 1 문구 활용)
    if connect_mode and selected_caption:
        st.info(f"🔗 연결 모드 활성화 — 페이지 1 문구가 편집 컨셉으로 활용됩니다.\n\n**선택 문구:** {selected_caption}")
    elif connect_mode:
        st.warning("⚠️ 페이지 1에서 문구를 선택하지 않았습니다. 편집 지시만 사용됩니다.")

    # 사용자가 직접 입력하는 메인 편집 프롬프트
    edit_prompt = st.text_area(
        "메인 편집 지시 (배경, 사물, 색상 등)",
        placeholder="예: 배경을 푸른색 해변으로 바꾸고, 모델에게 선글라스를 씌워줘",
        value=st.session_state.get("edit_prompt_i2i", ""),
        key="edit_prompt_area_i2i"
    )
    st.session_state["edit_prompt_i2i"] = edit_prompt

    # ------------------------------------------------------------
    # 3. 세부 조정 옵션
    # ------------------------------------------------------------
    st.markdown("### 🎚️ 세부 조정 및 옵션")
    
    i2i_config = config.get("image.i2i", {})
    
    col_strength, col_steps, col_size = st.columns(3)
    
    # 변화 강도 (Strength)
    with col_strength:
        strength = st.slider(
            "✨ 변화 강도 (Strength)",
            min_value=i2i_config.get("strength", {}).get("min", 0.0),
            max_value=i2i_config.get("strength", {}).get("max", 1.0),
            value=st.session_state.get("strength_i2i", i2i_config.get("strength", {}).get("default", 0.75)),
            step=i2i_config.get("strength", {}).get("step", 0.05),
            help="0.0: 원본 유지, 1.0: 완전히 새로운 이미지",
            key="strength_slider_i2i"
        )
        st.session_state["strength_i2i"] = strength

    # 추론 단계 (Steps) - T2I와 동일한 범위 사용
    with col_steps:
        steps = st.slider(
            "추론 단계 (Steps)",
            min_value=config.get("image.steps.min", 1),
            max_value=config.get("image.steps.max", 50),
            value=st.session_state.get("steps_i2i", 30),
            step=1,
            help="생성 반복 횟수 (높을수록 정교하지만 느림)",
            key="steps_slider_i2i"
        )
        st.session_state["steps_i2i"] = steps
        
    # 출력 크기 (T2I와 동일하게 구성)
    with col_size:
        # 현재 모델 정보 가져오기 (크기 권장을 위해)
        model_info = api.get_model_info()
        current_model_name = model_info.get("current") if model_info else None
        is_flux = current_model_name and "flux" in current_model_name.lower()

        # 이미지 크기 (설정 기반)
        preset_sizes = config.get("image.preset_sizes", [])

        # FLUX 모델 사용 시 권장 크기 표시
        size_options = []
        for s in preset_sizes:
            label = f"{s['name']} ({s['width']}x{s['height']})"
            if is_flux and s['width'] == 1024 and s['height'] == 1024:
                label += " ⭐ 권장"
            size_options.append(label)

        default_size_idx_i2i = 0
        if "selected_size_i2i" in st.session_state and st.session_state["selected_size_i2i"] in size_options:
            default_size_idx_i2i = size_options.index(st.session_state["selected_size_i2i"])
            
        selected_size = st.selectbox(
            "출력 크기",
            size_options,
            index=default_size_idx_i2i,
            help="입력 이미지가 이 크기로 리사이즈된 후 편집됩니다",
            key="size_selector_i2i"
        )
        st.session_state["selected_size_i2i"] = selected_size

        size_idx = size_options.index(selected_size)
        width = preset_sizes[size_idx]["width"]
        height = preset_sizes[size_idx]["height"]


    # Negative Prompt (T2I와 동일하게 구성)
    negative_prompt = st.text_area(
        "NEGATIVE 프롬프트",
        placeholder="예: blur, low quality, artifacts, extra fingers",
        value=st.session_state.get("negative_prompt_i2i", "distorted, lowres, bad hands, watermark"),
        key="negative_prompt_area_i2i"
    )
    st.session_state["negative_prompt_i2i"] = negative_prompt
    
    # ------------------------------------------------------------
    # 4. 최종 프롬프트 구성 및 실행
    # ------------------------------------------------------------
    
    # 최종 프롬프트 구성 (페이지 1 문구 활용)
    final_prompt = edit_prompt
    if connect_mode and selected_caption:
        # T2I 페이지와 통일성을 위해 caption_to_prompt 사용
        support_prompt = caption_to_prompt(selected_caption)
        final_prompt = f"{edit_prompt}, {support_prompt}".strip(", ")
    
    # 디버깅/정보용
    if final_prompt:
        st.caption(f"**최종 PROMPT:** {final_prompt[:150]}...")

    submitted = st.button("✨ 이미지 편집 실행", type="primary")

    if submitted:
        if not final_prompt.strip():
            st.error("❌ 편집 지시(프롬프트)를 입력하세요")
            return
        
        aligned_w = align_to_64(width)
        aligned_h = align_to_64(height)
        
        # BytesIO 객체를 base64 인코딩 전에 다시 읽기
        
        payload = {
            "input_image_base64": base64.b64encode(image_bytes).decode(),
            "prompt": final_prompt,
            "negative_prompt": negative_prompt if negative_prompt.strip() else None,
            "strength": strength,
            "width": aligned_w,
            "height": aligned_h,
            "steps": steps # Steps 변수 사용
        }
        
        try:
            with st.spinner("편집 중..."):
                edited_io = api.call_i2i(payload)
            
            if edited_io:
                edited_io.seek(0)
                edited_bytes = edited_io.read()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("원본")
                    st.image(image_bytes, caption=target_image_name, use_container_width=True)
                with col2:
                    st.subheader("편집됨")
                    st.image(edited_bytes, caption="편집 결과", use_container_width=True)
                
                st.success("✅ 완료!")
                st.download_button("⬇️ 편집 이미지 다운로드", edited_bytes, "edited.png", "image/png")
            else:
                st.error("❌ 편집된 이미지를 받지 못했습니다.")
        except Exception as e:
            st.error(f"❌ 편집 실패: {e}")

# ============================================================
# 실행
# ============================================================
if __name__ == "__main__":
    main()