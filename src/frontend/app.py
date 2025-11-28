# app.py
"""
헬스케어 AI 콘텐츠 제작 앱 - Streamlit 프론트엔드
프롬프트는 최대한 심플하게 모으고,
FLUX 전용 3단계 프롬프트 변환은 전부 백엔드(services.py)에서 처리.
"""
import os
import re
import streamlit as st
import requests
from io import BytesIO
from PIL import Image
import base64
import yaml
from typing import Optional, Dict, Any
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
                "steps": {"min": 1, "max": 50, "default": 10},
                "i2i": {
                    "strength": {"min": 0.0, "max": 1.0, "default": 0.75, "step": 0.05}
                }
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

        self._model_info = None
        self._backend_status = None
        self._server_start_time = None
    
    def get_backend_status(self, force_refresh: bool = False) -> Optional[Dict]:
        """백엔드 상태 조회 (캐싱)"""
        if self._backend_status and not force_refresh:
            return self._backend_status

        try:
            resp = requests.get(f"{self.base_url}/status", timeout=5)
            resp.raise_for_status()
            self._backend_status = resp.json()

            new_start_time = self._backend_status.get("server_start_time")
            if new_start_time and self._server_start_time:
                if new_start_time != self._server_start_time:
                    # 서버 재시작 → 캐시 무효화
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
        """모델 전환 (비동기 폴링)"""
        import time

        try:
            resp = requests.post(
                f"{self.base_url}/api/switch_model_async",
                json={"model_name": model_name},
                timeout=10
            )
            resp.raise_for_status()
        except Exception as e:
            raise Exception(f"모델 전환 시작 실패: {e}")

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

                if not status.get("in_progress", True):
                    if status.get("success"):
                        self._model_info = None
                        self._backend_status = None
                        return {
                            "success": True,
                            "message": status.get("message", "모델 전환 완료")
                        }
                    else:
                        raise Exception(status.get("error", "모델 전환 실패"))
            except requests.exceptions.RequestException:
                pass

        raise Exception("모델 전환 타임아웃 (5분 초과)")
    
    def load_model(self, model_name: str) -> Dict:
        """모델 로드"""
        try:
            resp = requests.post(
                f"{self.base_url}/api/load_model",
                json={"model_name": model_name},
                timeout=300
            )
            resp.raise_for_status()
            self._model_info = None
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
            self._model_info = None
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
# 유틸
# ============================================================
def align_to_64(val: int) -> int:
    v = max(64, int(val))
    return (v // 64) * 64


def parse_caption_output(output: str) -> tuple:
    """GPT 출력 파싱 (문구/해시태그)"""
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


# ============================================================
# 메인 앱
# ============================================================
def main():
    config = ConfigLoader()
    api = APIClient(config)
    
    st.set_page_config(
        page_title=config.get("app.title"),
        layout=config.get("app.layout", "wide")
    )
    
    # 사이드바 메뉴
    st.sidebar.title("메뉴")
    pages_config = config.get("pages", [])
    page_options = [f"{p['icon']} {p['title']}" for p in pages_config]
    menu = st.sidebar.radio("페이지 선택", page_options)
    selected_idx = page_options.index(menu)
    page_id = pages_config[selected_idx]["id"]
    
    # 모델 선택
    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 이미지 생성 모델")

    model_info = api.get_model_info()
    if model_info:
        current_model = model_info.get("current")
        available_models = list(model_info.get("models", {}).keys())
        
        if current_model:
            st.sidebar.success(f"💡 **ON** (Loaded: {current_model})")
        else:
            st.sidebar.markdown(f"⚫ **OFF** (Unloaded)")

        default_idx = 0
        if current_model and current_model in available_models:
            default_idx = available_models.index(current_model)
            
        selected_model = st.sidebar.selectbox(
            "모델 선택",
            available_models,
            index=default_idx,
            key="model_selector"
        )

        if selected_model in model_info["models"]:
            model_desc = model_info["models"][selected_model].get("description", "")
            if model_desc:
                st.sidebar.caption(f"📝 {model_desc}")

        if current_model:
            if st.sidebar.button("🔌 모델 끄기 (Unload)", type="secondary"):
                with st.spinner("모델 언로드 중..."):
                    try:
                        api.unload_model()
                        st.sidebar.success("모델이 꺼졌습니다.")
                        api.get_model_info(force_refresh=True)
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"❌ {e}")
            
            if selected_model != current_model:
                if st.sidebar.button("🔄 모델 전환", type="primary"):
                    with st.spinner(f"'{selected_model}' 로 전환 중..."):
                        try:
                            result = api.switch_model(selected_model)
                            st.sidebar.success(result["message"])
                            api.get_model_info(force_refresh=True)
                            st.rerun()
                        except Exception as e:
                            st.sidebar.error(f"❌ {e}")
        else:
            if st.sidebar.button("⚡ 모델 켜기 (Load)", type="primary"):
                with st.spinner(f"'{selected_model}' 로딩 중..."):
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

    # 백엔드 상태
    with st.sidebar.expander("🔧 시스템 상태"):
        status = api.get_backend_status(force_refresh=True)
        if status:
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
    
    # 연결 모드 OFF 시 세션 일부 초기화
    if not connect_mode:
        for key in [
            "captions", "hashtags", "generated_images", "selected_caption",
            "edit_prompt_i2i", "strength_i2i", "steps_i2i",
            "selected_size_i2i"
        ]:
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

    with st.form("content_form", clear_on_submit=False):
        service_types = config.get("caption.service_types", [])
        default_service_type = st.session_state.get("service_type_input", service_types[0] if service_types else "")
        service_type = st.selectbox(
            "서비스 종류",
            service_types,
            key="service_type_input",
            index=service_types.index(default_service_type) if default_service_type in service_types else 0
        )

        location = st.text_input(
            "지역",
            placeholder=config.get("ui.placeholders.location", "예: 강남"),
            key="location_input",
            value=st.session_state.get("location_input", "")
        )

        service_name = st.text_input(
            "제품/클래스 이름",
            placeholder=config.get("ui.placeholders.service_name", "예: 프리미엄 PT 10회"),
            key="service_name_input",
            value=st.session_state.get("service_name_input", "")
        )

        features = st.text_area(
            "핵심 특징 및 장점",
            placeholder=config.get("ui.placeholders.features", "예: 1:1 맞춤 PT, 체형 교정 전문"),
            key="features_input",
            value=st.session_state.get("features_input", "")
        )

        tones = config.get("caption.tones", [])
        default_tone = st.session_state.get("tone_input", tones[0] if tones else "")
        tone = st.selectbox(
            "톤 선택",
            tones,
            key="tone_input",
            index=tones.index(default_tone) if default_tone in tones else 0
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
# 페이지 2: T2I 이미지 생성 (Flux 최적화 구조)
# ============================================================
def render_t2i_page(config: ConfigLoader, api: APIClient, connect_mode: bool):
    st.title("🖼 문구 기반 이미지 생성 (FLUX 최적화 프롬프트)")

    # 1) 페이지1 문구 + 사용자 프롬프트
    selected_caption = st.session_state.get("selected_caption", "")

    if connect_mode and selected_caption:
        st.info(f"🔗 연결 모드 — 페이지1 문구가 보조 요소로 사용됩니다.\n\n**선택 문구:** {selected_caption}")
        base_prompt = st.text_area(
            "메인 프롬프트 (사용자 입력)",
            placeholder="예: 밝고 에너지 넘치는 필라테스 스튜디오, 건강하고 활기찬 느낌",
            key="base_prompt_t2i",
            value=st.session_state.get("base_prompt_t2i", "")
        )
    else:
        if connect_mode:
            st.warning("⚠️ 페이지1에서 문구를 먼저 생성하세요")
        base_prompt = st.text_area(
            "메인 프롬프트",
            placeholder=config.get("ui.placeholders.caption", "예: 따뜻한 조명, 편안한 분위기의 요가 공간"),
            key="base_prompt_t2i",
            value=st.session_state.get("base_prompt_t2i", "")
        )

    captions_for_support = f"{selected_caption} {st.session_state.get('hashtags', '')}".strip()

    # 2) 모델 정보 (Flux 여부 확인 및 권장 해상도 표시)
    model_info = api.get_model_info()
    current_model_name = model_info.get("current") if model_info else None
    current_model_type = ""
    is_flux = False
    if model_info and current_model_name and current_model_name in model_info["models"]:
        current_model_type = model_info["models"][current_model_name].get("type", "")
        is_flux = "flux" in current_model_type.lower()

    # 3) 보조 프롬프트 UI
    st.markdown("---")
    st.markdown("### 🎚 보조 프롬프트 설정 (페이지1 문구 사용 시)")

    support_strength = st.select_slider(
        "보조 프롬프트 강도",
        options=["약하게", "중간", "강하게"],
        key="support_strength_t2i",
        value=st.session_state.get("support_strength_t2i", "중간"),
    )

    support_method = st.selectbox(
        "보조 프롬프트 생성 방식",
        ["단순 키워드 변환", "GPT 기반 자연스러운 스타일 변환", "사용자 조절형 혼합"],
        key="support_method_t2i",
        index=["단순 키워드 변환", "GPT 기반 자연스러운 스타일 변환", "사용자 조절형 혼합"].index(
            st.session_state.get("support_method_t2i", "단순 키워드 변환")
        )
    )

    if support_method == "단순 키워드 변환":
        support_description = (
            "💡 **단순 키워드 변환 모드입니다.**\n"
            "페이지1 문구에서 **핵심 단어만 추출**해 간결한 보조 프롬프트를 구성합니다.\n"
            "문장의 구조를 무시하고, 순수한 컨셉 키워드 중심으로 동작합니다."
        )
    elif support_method == "GPT 기반 자연스러운 스타일 변환":
        support_description = (
            "💡 **GPT 기반 자연스러운 스타일 변환 모드입니다.**\n"
            "원본 문구에 *'cinematic soft light', 'premium studio mood'* 같은 **고품질 스타일 키워드를 자동 추가**합니다.\n"
            "이미지의 **예술적인 분위기·조명·품질 개선**에 최적화된 방식입니다."
        )
    else:
        support_description = (
            "💡 **사용자 조절형 혼합 모드입니다.**\n"
            "원본 문구에 *'warm tone', 'clean aesthetic'* 등 **예측 가능한 분위기 키워드**를 추가합니다.\n"
            "과한 스타일링 없이 **일관된 분위기 유지 + 강도 조절**에 적합합니다."
        )

    st.info(support_description)

    def build_support_prompt(text, method, strength):
        if not text:
            return ""
        if method == "단순 키워드 변환":
            prompt = ", ".join(re.split(r"[ ,.\n]+", text)[:30])
        elif method == "GPT 기반 자연스러운 스타일 변환":
            prompt = f"{text}, cinematic soft light, refined composition, premium studio mood"
        else:
            prompt = f"{text}, warm tone, clean aesthetic, balanced framing"

        weight = {"약하게": "0.3", "중간": "0.6", "강하게": "1.0"}[strength]
        return f"({prompt}:{weight})"

    support_prompt = build_support_prompt(captions_for_support, support_method, support_strength)

    # 4) 최종 프롬프트 (백엔드에서 FLUX 3단계 변환)
    final_prompt = base_prompt
    if connect_mode and selected_caption and support_prompt:
        final_prompt = f"{base_prompt}, {support_prompt}".strip(", ")

    if final_prompt:
        st.caption(f"**최종 PROMPT (백엔드에서 FLUX 전용 변환 적용):** {final_prompt[:150]}...")

    # 5) 이미지 생성 옵션
    st.markdown("---")

    preset_sizes = config.get("image.preset_sizes", [])
    size_options = []
    for s in preset_sizes:
        label = f"{s['name']} ({s['width']}x{s['height']})"
        if is_flux and s['width'] == 1024:
            label += " ⭐ FLUX 권장"
        size_options.append(label)

    selected_size = st.selectbox(
        "이미지 크기",
        size_options,
        key="selected_size_t2i",
        index=size_options.index(st.session_state.get("selected_size_t2i", size_options[0]))
        if st.session_state.get("selected_size_t2i") in size_options else 0
    )

    size_idx = size_options.index(selected_size)
    width = preset_sizes[size_idx]["width"]
    height = preset_sizes[size_idx]["height"]

    col1, col2 = st.columns(2)
    with col1:
        steps_cfg = config.get("image.steps", {})
        steps = st.slider(
            "추론 단계 (Steps)",
            steps_cfg.get("min", 1),
            steps_cfg.get("max", 50),
            key="steps_t2i",
            value=st.session_state.get("steps_t2i", steps_cfg.get("default", 20))
        )
    with col2:
        guidance_scale = st.slider(
            "Guidance Scale",
            1.0, 10.0,
            key="guidance_t2i",
            value=st.session_state.get("guidance_t2i", 5.0)
        )

    num_images = st.slider(
        "생성할 이미지 개수",
        1, 5,
        key="num_images_t2i",
        value=st.session_state.get("num_images_t2i", 1)
    )

    # 6) 생성 버튼 / 루프
    is_generating = st.session_state.get("is_generating_t2i", False)

    if not is_generating:
        submitted = st.button("🖼 이미지 생성", type="primary", disabled=not final_prompt.strip())
    else:
        st.warning("⏳ 이미지 생성 중입니다. 페이지를 이동하지 마세요.")
        submitted = False

    if submitted:
        st.session_state["is_generating_t2i"] = True
        st.rerun()

    if st.session_state.get("is_generating_t2i"):
        aligned_w = align_to_64(width)
        aligned_h = align_to_64(height)

        st.session_state["generated_images"] = []
        progress_bar = st.progress(0)

        for i in range(num_images):
            payload = {
                "prompt": final_prompt,
                "width": aligned_w,
                "height": aligned_h,
                "steps": steps,
                "guidance_scale": guidance_scale,
            }

            progress_bar.progress(i / num_images, f"{i+1}/{num_images} 생성 중…")

            img_bytes = api.call_t2i(payload)
            if img_bytes:
                st.session_state["generated_images"].append({
                    "bytes": img_bytes,
                    "prompt": final_prompt,
                    "index": i + 1
                })

        st.session_state["is_generating_t2i"] = False
        st.rerun()

    # 7) 결과 표시
    if st.session_state.get("generated_images"):
        st.success(f"완료! 총 {len(st.session_state['generated_images'])}개 생성됨.")

        cols = st.columns(len(st.session_state["generated_images"]))
        for idx, img in enumerate(st.session_state["generated_images"]):
            with cols[idx]:
                img["bytes"].seek(0)
                st.image(img["bytes"], caption=f"버전 {idx+1}")
                img["bytes"].seek(0)
                st.download_button(
                    f"⬇️ 다운로드",
                    img["bytes"].read(),
                    file_name=f"t2i_image_{idx+1}.png",
                    mime="image/png",
                    key=f"download_btn_{idx}"
                )
                img["bytes"].seek(0)


# ============================================================
# 페이지 3: I2I 이미지 편집 (Flux 3단계 파이프라인 공유)
# ============================================================
def render_i2i_page(config: ConfigLoader, api: APIClient, connect_mode: bool):
    st.title("🖼️ 이미지 편집 (Image-to-Image)")
    st.info("💡 업로드된 이미지를 AI로 편집하거나, 페이지2 결과를 바탕으로 스타일을 바꿉니다.\n"
            "프롬프트는 백엔드에서 FLUX 전용 3단계 변환을 동일하게 사용합니다.")

    preloaded = st.session_state.get("generated_images", [])

    col_upload, col_select = st.columns([1, 2])
    with col_upload:
        uploaded_file = st.file_uploader(
            "새 이미지 업로드",
            type=["png", "jpg", "jpeg"],
            key="i2i_uploaded_file"
        )

    can_use_preloaded = connect_mode and preloaded
    selected_preloaded_index = None

    if can_use_preloaded:
        with col_select:
            selected_preloaded_index = st.selectbox(
                "또는 페이지2에서 생성한 이미지 선택",
                list(range(len(preloaded))),
                format_func=lambda x: f"T2I 결과 {x+1}번",
                key="i2i_preloaded_selector"
            )

    image_bytes = None
    target_image_name = "미선택"

    if uploaded_file:
        image_bytes = uploaded_file.getvalue()
        target_image_name = uploaded_file.name
    elif selected_preloaded_index is not None:
        img_io = preloaded[selected_preloaded_index]["bytes"]
        img_io.seek(0)
        image_bytes = img_io.read()
        target_image_name = f"T2I 결과 {selected_preloaded_index+1}번"

    st.markdown("---")
    if not image_bytes:
        if not st.session_state.get("edited_image_data"):
            st.warning("⚠ 이미지를 업로드하거나 페이지 2에서 생성한 이미지를 선택하세요.")
            return
    else:
        st.image(image_bytes, caption=f"편집 대상: {target_image_name}", width=350)
        if (
            st.session_state.get("edited_image_data") and
            st.session_state["edited_image_data"].get("source_name") != target_image_name
        ):
            del st.session_state["edited_image_data"]

    # 편집 프롬프트
    st.subheader("📝 편집 프롬프트")

    selected_caption = st.session_state.get("selected_caption", "")
    if connect_mode and selected_caption:
        st.info(f"🔗 연결 모드 — 페이지1 문구 활용됨\n\n**선택 문구:** {selected_caption}")
    elif connect_mode:
        st.warning("⚠ 연결 모드 ON이지만 페이지1에서 문구가 선택되지 않았습니다.")

    edit_prompt = st.text_area(
        "메인 편집 지시",
        placeholder=config.get("ui.placeholders.edit_prompt", "예: 더 밝고 활기찬 분위기로, 파란색 배경 추가"),
        key="edit_prompt_i2i",
        value=st.session_state.get("edit_prompt_i2i", "")
    )

    captions_for_support = f"{selected_caption} {st.session_state.get('hashtags','')}".strip()

    # 보조 프롬프트 옵션 (페이지2와 동일 컨셉)
    st.markdown("---")
    st.markdown("### 🎚 보조 프롬프트 옵션")

    support_strength = st.select_slider(
        "보조 프롬프트 강도",
        ["약하게", "중간", "강하게"],
        key="support_strength_i2i",
        value=st.session_state.get("support_strength_i2i", "중간"),
    )

    support_method = st.selectbox(
        "보조 프롬프트 방식",
        ["단순 키워드 변환", "GPT 기반 자연스럽게", "사용자 조절형 혼합"],
        key="support_method_i2i",
        index=["단순 키워드 변환", "GPT 기반 자연스럽게", "사용자 조절형 혼합"]
        .index(st.session_state.get("support_method_i2i", "단순 키워드 변환"))
    )

    if support_method == "단순 키워드 변환":
        st.info("💡 페이지1 문구에서 핵심 키워드만 추출해 단순 스타일로 반영합니다.")
    elif support_method == "GPT 기반 자연스럽게":
        st.info("💡 페이지1 문구를 바탕으로 자연스러운 스타일·조명·무드를 자동 확장합니다.")
    else:
        st.info("💡 기본 문구에 균형 잡힌 분위기 키워드를 섞어 안정적으로 조절된 이미지를 생성합니다.")

    # 세부 옵션 (strength/steps/size)
    st.markdown("### ⚙ 편집 세부 조정")
    i2i_cfg = config.get("image.i2i", {})

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        strength = st.slider(
            "변화 강도 (strength)",
            float(i2i_cfg.get("strength", {}).get("min", 0.0)),
            float(i2i_cfg.get("strength", {}).get("max", 1.0)),
            key="strength_i2i",
            value=st.session_state.get("strength_i2i", i2i_cfg.get("strength", {}).get("default", 0.7)),
            step=float(i2i_cfg.get("strength", {}).get("step", 0.05)),
        )
    with col_b:
        steps = st.slider(
            "Steps",
            1, 50,
            key="steps_i2i",
            value=st.session_state.get("steps_i2i", 30)
        )
    with col_c:
        preset_sizes = config.get("image.preset_sizes", [])
        size_labels = [f"{s['name']} ({s['width']}x{s['height']})" for s in preset_sizes]
        selected_size = st.selectbox(
            "출력 크기",
            size_labels,
            key="size_selector_i2i",
            index=size_labels.index(st.session_state.get("size_selector_i2i", size_labels[0]))
            if st.session_state.get("size_selector_i2i") in size_labels else 0
        )
        # st.session_state["size_selector_i2i"] = selected_size
        idx = size_labels.index(selected_size)
        width = preset_sizes[idx]["width"]
        height = preset_sizes[idx]["height"]

    # 보조 프롬프트 생성
    def build_support(text, method, strength):
        if not text:
            return ""
        if method == "단순 키워드 변환":
            base = ", ".join(re.split(r"[ ,.\n]+", text)[:20])
        elif method == "GPT 기반 자연스럽게":
            base = f"{text}, cinematic soft light, premium mood, refined rendering"
        else:
            base = f"{text}, balanced framing, clean aesthetic"

        ratio = {"약하게": "0.3", "중간": "0.6", "강하게": "1.0"}[strength]
        return f"({base}:{ratio})"

    support_prompt_final = build_support(captions_for_support, support_method, support_strength)

    final_prompt = edit_prompt
    if connect_mode and selected_caption and support_prompt_final:
        final_prompt = f"{edit_prompt}, {support_prompt_final}"

    if final_prompt:
        st.caption(f"최종 PROMPT (백엔드에서 FLUX 전용 변환 적용): {final_prompt[:120]}...")

    # 실행 버튼
    submitted = st.button("✨ 이미지 편집 실행", type="primary", disabled=not (final_prompt.strip() and image_bytes))

    if submitted:
        st.session_state["edited_image_data"] = None

        aligned_w = align_to_64(width)
        aligned_h = align_to_64(height)

        payload = {
            "input_image_base64": base64.b64encode(image_bytes).decode(),
            "prompt": final_prompt,
            "strength": float(strength),
            "width": aligned_w,
            "height": aligned_h,
            "steps": steps
        }

        try:
            with st.spinner("이미지 편집 중..."):
                edited_io = api.call_i2i(payload)

            if edited_io:
                st.session_state["edited_image_data"] = {
                    "source_name": target_image_name,
                    "original_bytes": image_bytes,
                    "edited_bytes": edited_io.read(),
                    "prompt": final_prompt
                }
                st.rerun()

        except Exception as e:
            st.error(f"편집 실패: {e}")

    # 결과 표시
    edited = st.session_state.get("edited_image_data")
    if edited:
        st.markdown("---")
        st.subheader("🎉 편집 결과")

        c1, c2 = st.columns(2)
        with c1:
            st.caption(f"원본 이미지: {edited['source_name']}")
            st.image(edited["original_bytes"])
        with c2:
            st.caption("편집된 이미지")
            st.image(edited["edited_bytes"])
            st.download_button(
                "⬇ 편집본 다운로드",
                edited["edited_bytes"],
                "edited_image.png",
                "image/png",
                key="download_i2i"
            )

        st.caption(f"사용된 프롬프트: {edited['prompt']}")


# ============================================================
# 실행
# ============================================================
if __name__ == "__main__":
    main()
































































# # app.py (입력/생성 값 유지 개선)
# """
# 헬스케어 AI 콘텐츠 제작 앱 - Streamlit 프론트엔드
# 설정 기반 아키텍처로 하드코딩 최소화
# """
# import os
# import re
# import streamlit as st
# import requests
# from io import BytesIO
# from PIL import Image
# import base64
# import yaml
# from typing import Optional, Dict, Any, List
# from pathlib import Path

# # ============================================================
# # 설정 로더
# # ============================================================
# class ConfigLoader:
#     """설정 파일 로더"""
    
#     def __init__(self, config_path: Optional[str] = None):
#         if config_path is None:
#             config_path = os.path.join(os.path.dirname(__file__), "frontend_config.yaml")
        
#         self.config_path = config_path
#         self.config = self._load_config()
    
#     def _load_config(self) -> Dict[str, Any]:
#         """YAML 설정 파일 로드"""
#         try:
#             with open(self.config_path, 'r', encoding='utf-8') as f:
#                 return yaml.safe_load(f)
#         except FileNotFoundError:
#             st.warning(f"⚠️ 설정 파일이 없습니다: {self.config_path}")
#             return self._default_config()
#         except Exception as e:
#             st.error(f"❌ 설정 파일 로드 실패: {e}")
#             return self._default_config()
    
#     def _default_config(self) -> Dict[str, Any]:
#         """기본 설정 반환"""
#         return {
#             "app": {"title": "AI 콘텐츠 제작", "layout": "wide"},
#             "api": {"base_url": "http://localhost:8000", "timeout": 180, "retry_attempts": 2},
#             "caption": {
#                 "service_types": ["헬스장", "PT", "요가/필라테스", "기타"],
#                 "tones": ["친근하고 동기부여", "전문적이고 신뢰감"]
#             },
#             "image": {
#                 "preset_sizes": [
#                     {"name": "1024x1024", "width": 1024, "height": 1024}
#                 ],
#                 "steps": {"min": 1, "max": 50, "default": 10}
#             }
#         }
    
#     def get(self, path: str, default=None):
#         """점 표기법으로 설정 값 가져오기 (예: 'api.base_url')"""
#         keys = path.split('.')
#         value = self.config
#         for key in keys:
#             if isinstance(value, dict):
#                 value = value.get(key)
#             else:
#                 return default
#         return value if value is not None else default

# # ============================================================
# # API 클라이언트
# # ============================================================
# class APIClient:
#     """백엔드 API 클라이언트"""

#     def __init__(self, config: ConfigLoader):
#         self.base_url = os.getenv("API_BASE_URL") or config.get("api.base_url")
#         self.timeout = config.get("api.timeout", 180)
#         self.retry_attempts = config.get("api.retry_attempts", 2)

#         # 백엔드 모델 정보 캐싱
#         self._model_info = None
#         self._backend_status = None

#         # 서버 시작 시간 (재시작 감지용)
#         self._server_start_time = None
    
#     def get_backend_status(self, force_refresh: bool = False) -> Optional[Dict]:
#         """백엔드 상태 조회 (캐싱)"""
#         if self._backend_status and not force_refresh:
#             return self._backend_status

#         try:
#             resp = requests.get(f"{self.base_url}/status", timeout=5)
#             resp.raise_for_status()
#             self._backend_status = resp.json()

#             # 서버 재시작 감지
#             new_start_time = self._backend_status.get("server_start_time")
#             if new_start_time and self._server_start_time:
#                 if new_start_time != self._server_start_time:
#                     # 서버가 재시작됨 - 캐시 무효화
#                     self._model_info = None
#                     self._server_start_time = new_start_time
#                     return {"server_restarted": True, **self._backend_status}
#             self._server_start_time = new_start_time

#             return self._backend_status
#         except Exception as e:
#             st.error(f"❌ 백엔드 연결 실패: {e}")
#             return None
    
#     def get_model_info(self, force_refresh: bool = False) -> Optional[Dict]:
#         """모델 정보 조회 (캐싱)"""
#         if self._model_info and not force_refresh:
#             return self._model_info

#         try:
#             resp = requests.get(f"{self.base_url}/models", timeout=5)
#             resp.raise_for_status()
#             self._model_info = resp.json()
#             return self._model_info
#         except Exception as e:
#             st.warning(f"⚠️ 모델 정보 조회 실패: {e}")
#             return None

#     def switch_model(self, model_name: str) -> Dict:
#         """모델 전환 (비동기 방식)"""
#         import time

#         # 1. 비동기 전환 시작
#         try:
#             resp = requests.post(
#                 f"{self.base_url}/api/switch_model_async",
#                 json={"model_name": model_name},
#                 timeout=10
#             )
#             resp.raise_for_status()
#         except Exception as e:
#             raise Exception(f"모델 전환 시작 실패: {e}")

#         # 2. 폴링으로 완료 대기 (최대 5분)
#         max_wait = 300
#         poll_interval = 2
#         elapsed = 0

#         while elapsed < max_wait:
#             time.sleep(poll_interval)
#             elapsed += poll_interval

#             try:
#                 status_resp = requests.get(
#                     f"{self.base_url}/api/switch_model_status",
#                     timeout=5
#                 )
#                 status_resp.raise_for_status()
#                 status = status_resp.json()

#                 # 전환 완료 확인
#                 if not status.get("in_progress", True):
#                     if status.get("success"):
#                         # 캐시 무효화
#                         self._model_info = None
#                         self._backend_status = None
#                         return {
#                             "success": True,
#                             "message": status.get("message", "모델 전환 완료")
#                         }
#                     else:
#                         raise Exception(status.get("error", "모델 전환 실패"))
#             except requests.exceptions.RequestException:
#                 # 네트워크 오류는 무시하고 재시도
#                 pass

#         raise Exception("모델 전환 타임아웃 (5분 초과)")
    
#     def load_model(self, model_name: str) -> Dict:
#         """모델 로드"""
#         try:
#             # 로딩은 시간이 걸릴 수 있으므로 타임아웃 넉넉히
#             resp = requests.post(
#                 f"{self.base_url}/api/load_model",
#                 json={"model_name": model_name},
#                 timeout=300
#             )
#             resp.raise_for_status()
#             self._model_info = None # 캐시 초기화
#             return resp.json()
#         except Exception as e:
#             raise Exception(f"모델 로드 실패: {e}")

#     def unload_model(self) -> Dict:
#         """모델 언로드"""
#         try:
#             resp = requests.post(
#                 f"{self.base_url}/api/unload_model",
#                 timeout=60
#             )
#             resp.raise_for_status()
#             self._model_info = None # 캐시 초기화
#             return resp.json()
#         except Exception as e:
#             raise Exception(f"모델 언로드 실패: {e}")
    
#     def call_caption(self, payload: Dict) -> str:
#         """문구 생성 API 호출"""
#         try:
#             resp = requests.post(
#                 f"{self.base_url}/api/caption",
#                 json=payload,
#                 timeout=self.timeout
#             )
#             resp.raise_for_status()
#             return resp.json()["output_text"]
#         except Exception as e:
#             raise Exception(f"문구 생성 실패: {e}")
    
#     def call_t2i(self, payload: Dict) -> Optional[BytesIO]:
#         """T2I 이미지 생성 (자동 재시도 포함)"""
#         current_payload = payload.copy()
        
#         for attempt in range(self.retry_attempts + 1):
#             try:
#                 resp = requests.post(
#                     f"{self.base_url}/api/generate_t2i",
#                     json=current_payload,
#                     timeout=self.timeout
#                 )
#                 resp.raise_for_status()
#                 b64 = resp.json()["image_base64"]
#                 return BytesIO(base64.b64decode(b64))
            
#             except requests.exceptions.HTTPError as e:
#                 if e.response.status_code == 503 and attempt < self.retry_attempts:
#                     # GPU OOM 시 해상도 줄여서 재시도
#                     detail = e.response.json().get("detail", "")
#                     if "메모리" in detail or "GPU" in detail:
#                         w = current_payload["width"]
#                         h = current_payload["height"]
#                         new_w = max(64, align_to_64(w // 2))
#                         new_h = max(64, align_to_64(h // 2))
#                         st.info(f"⚠️ 메모리 부족 - 해상도 낮춤: {w}x{h} → {new_w}x{new_h}")
#                         current_payload["width"] = new_w
#                         current_payload["height"] = new_h
#                         continue
#                 raise Exception(f"T2I 생성 실패: {e.response.json().get('detail', str(e))}")
#             except Exception as e:
#                 raise Exception(f"T2I 요청 실패: {e}")
        
#         return None
    
#     def call_i2i(self, payload: Dict) -> Optional[BytesIO]:
#         """I2I 이미지 편집 (자동 재시도 포함)"""
#         current_payload = payload.copy()
        
#         for attempt in range(self.retry_attempts + 1):
#             try:
#                 resp = requests.post(
#                     f"{self.base_url}/api/generate_i2i",
#                     json=current_payload,
#                     timeout=self.timeout
#                 )
#                 resp.raise_for_status()
#                 b64 = resp.json()["image_base64"]
#                 return BytesIO(base64.b64decode(b64))
            
#             except requests.exceptions.HTTPError as e:
#                 if e.response.status_code == 503 and attempt < self.retry_attempts:
#                     detail = e.response.json().get("detail", "")
#                     if "메모리" in detail or "GPU" in detail:
#                         w = current_payload["width"]
#                         h = current_payload["height"]
#                         new_w = max(64, align_to_64(w // 2))
#                         new_h = max(64, align_to_64(h // 2))
#                         st.info(f"⚠️ 메모리 부족 - 해상도 낮춤: {w}x{h} → {new_w}x{new_h}")
#                         current_payload["width"] = new_w
#                         current_payload["height"] = new_h
#                         continue
#                 raise Exception(f"I2I 편집 실패: {e.response.json().get('detail', str(e))}")
#             except Exception as e:
#                 raise Exception(f"I2I 요청 실패: {e}")
        
#         return None

# # ============================================================
# # 유틸리티 함수
# # ============================================================
# def align_to_64(val: int) -> int:
#     """64의 배수로 정렬"""
#     v = max(64, int(val))
#     return (v // 64) * 64

# def parse_caption_output(output: str) -> tuple:
#     """GPT 출력 파싱"""
#     captions, hashtags = [], ""
#     try:
#         m = re.search(r"문구:(.*?)해시태그:(.*)", output, re.S)
#         if m:
#             caption_text = m.group(1).strip()
#             hashtags = m.group(2).strip()
#             captions = [
#                 line.split(".", 1)[1].strip() if "." in line else line.strip()
#                 for line in caption_text.split("\n") if line.strip()
#             ]
#         else:
#             captions = [output]
#     except:
#         captions = [output]
#     return captions, hashtags

# def caption_to_prompt(caption: str, style: str = "Instagram banner") -> str:
#     """문구를 이미지 프롬프트로 변환"""
#     return f"{caption}, {style}, vibrant, professional, motivational"

# # ============================================================
# # 메인 앱
# # ============================================================
# def main():
#     # 설정 로드
#     config = ConfigLoader()
#     api = APIClient(config)
    
#     # 앱 설정
#     st.set_page_config(
#         page_title=config.get("app.title"),
#         layout=config.get("app.layout", "wide")
#     )
    
#     # 사이드바
#     st.sidebar.title("메뉴")
    
#     # 페이지 목록 (설정 파일 기반)
#     pages_config = config.get("pages", [])
#     page_options = [f"{p['icon']} {p['title']}" for p in pages_config]
#     menu = st.sidebar.radio("페이지 선택", page_options)
    
#     # 선택된 페이지 ID 찾기
#     selected_idx = page_options.index(menu)
#     page_id = pages_config[selected_idx]["id"]
    
#     # 모델 선택
#     st.sidebar.markdown("---")
#     st.sidebar.subheader("🤖 이미지 생성 모델")

#     model_info = api.get_model_info()
#     if model_info:
#         current_model = model_info.get("current") # None이면 언로드 상태
#         available_models = list(model_info.get("models", {}).keys())
        
#         # 상태 아이콘 및 텍스트
#         if current_model:
#             st.sidebar.success(f"💡 **ON** (Loaded: {current_model})")
#         else:
#             st.sidebar.markdown(f"⚫ **OFF** (Unloaded)")

#         # 모델 선택 드롭다운 (로드할 모델 또는 전환할 모델 선택)
#         # 현재 로드된 모델이 있으면 그걸 기본값으로, 없으면 첫 번째 모델
#         default_idx = 0
#         if current_model and current_model in available_models:
#             default_idx = available_models.index(current_model)
            
#         selected_model = st.sidebar.selectbox(
#             "모델 선택",
#             available_models,
#             index=default_idx,
#             key="model_selector"
#         )

#         # 선택한 모델 설명
#         if selected_model in model_info["models"]:
#             model_desc = model_info["models"][selected_model].get("description", "")
#             if model_desc:
#                 st.sidebar.caption(f"📝 {model_desc}")

#         # 제어 버튼 영역
#         col_btn1, col_btn2 = st.sidebar.columns(2)
        
#         if current_model:
#             # 로드된 상태: 언로드 버튼 + (다른 모델 선택 시) 전환 버튼
#             if st.sidebar.button("🔌 모델 끄기 (Unload)", type="secondary"):
#                 with st.spinner("모델 언로드 중..."):
#                     try:
#                         api.unload_model()
#                         st.sidebar.success("모델이 꺼졌습니다.")
#                         api.get_model_info(force_refresh=True)
#                         st.rerun()
#                     except Exception as e:
#                         st.sidebar.error(f"❌ {e}")
            
#             # 모델이 다르면 전환 버튼 표시
#             if selected_model != current_model:
#                 if st.sidebar.button("🔄 모델 전환", type="primary"):
#                     with st.spinner(f"'{selected_model}' 로 전환 중..."):
#                         try:
#                             # 전환은 기존 switch_model 사용 (비동기)
#                             result = api.switch_model(selected_model)
#                             st.sidebar.success(result["message"])
#                             api.get_model_info(force_refresh=True)
#                             st.rerun()
#                         except Exception as e:
#                             st.sidebar.error(f"❌ {e}")
#         else:
#             # 언로드 상태: 로드 버튼
#             if st.sidebar.button("⚡ 모델 켜기 (Load)", type="primary"):
#                 with st.spinner(f"'{selected_model}' 로딩 중... (잠시만 기다려주세요)"):
#                     try:
#                         api.load_model(selected_model)
#                         st.sidebar.success(f"'{selected_model}' 로드 완료!")
#                         api.get_model_info(force_refresh=True)
#                         st.rerun()
#                     except Exception as e:
#                         st.sidebar.error(f"❌ {e}")
#     else:
#         st.sidebar.warning("⚠️ 모델 정보를 가져올 수 없습니다")

#     # 연결 모드
#     st.sidebar.markdown("---")
#     connect_mode = st.sidebar.checkbox(
#         "🔗 페이지 연결 모드",
#         value=config.get("connection_mode.enabled_by_default", True)
#     )
#     st.sidebar.info(config.get("connection_mode.description", ""))

#     # 백엔드 상태 표시
#     with st.sidebar.expander("🔧 시스템 상태"):
#         status = api.get_backend_status(force_refresh=True)
#         if status:
#             # 서버 재시작 감지 시 자동 새로고침
#             if status.get("server_restarted"):
#                 st.warning("🔄 서버가 재시작되었습니다. 상태를 새로고침합니다...")
#                 api.get_model_info(force_refresh=True)
#                 st.rerun()

#             st.json(status)
#             if st.button("🔄 새로고침"):
#                 api.get_backend_status(force_refresh=True)
#                 api.get_model_info(force_refresh=True)
#                 st.rerun()
#         else:
#             st.error("백엔드 연결 안됨")
    
#     # 연결 모드 OFF 시 세션 초기화
#     if not connect_mode:
#         for key in ["captions", "hashtags", "generated_images", "selected_caption", "edit_prompt_i2i", "strength_i2i", "steps_i2i", "negative_prompt_i2i", "selected_size_i2i"]:
#             if key in st.session_state:
#                 del st.session_state[key]
    
#     # 페이지 라우팅
#     if page_id == "caption":
#         render_caption_page(config, api)
#     elif page_id == "t2i":
#         render_t2i_page(config, api, connect_mode)
#     elif page_id == "i2i":
#         render_i2i_page(config, api, connect_mode)




# # ============================================================
# # 페이지 1: 문구 생성 (입력값 유지 패치 완료)
# # ============================================================
# def render_caption_page(config: ConfigLoader, api: APIClient):
#     st.title("📝 홍보 문구 & 해시태그 생성")

#     # --- 입력 폼 ---
#     with st.form("content_form", clear_on_submit=False):

#         # 서비스 종류
#         service_types = config.get("caption.service_types", [])
#         default_service_type = st.session_state.get("service_type_input", service_types[0] if service_types else "")
#         service_type = st.selectbox(
#             "서비스 종류",
#             service_types,
#             key="service_type_input",
#             index=service_types.index(default_service_type) if default_service_type in service_types else 0
#         )

#         # 지역
#         location = st.text_input(
#             "지역",
#             placeholder=config.get("ui.placeholders.location", "예: 강남"),
#             key="location_input",
#             value=st.session_state.get("location_input", "")
#         )

#         # 서비스명
#         service_name = st.text_input(
#             "제품/클래스 이름",
#             placeholder=config.get("ui.placeholders.service_name", "예: 프리미엄 PT 10회"),
#             key="service_name_input",
#             value=st.session_state.get("service_name_input", "")
#         )

#         # 특징
#         features = st.text_area(
#             "핵심 특징 및 장점",
#             placeholder=config.get("ui.placeholders.features", "예: 1:1 맞춤 PT, 체형 교정 전문"),
#             key="features_input",
#             value=st.session_state.get("features_input", "")
#         )

#         # 톤
#         tones = config.get("caption.tones", [])
#         default_tone = st.session_state.get("tone_input", tones[0] if tones else "")
#         tone = st.selectbox(
#             "톤 선택",
#             tones,
#             key="tone_input",
#             index=tones.index(default_tone) if default_tone in tones else 0
#         )

#         submitted = st.form_submit_button("✨ 문구+해시태그 생성")

#     # --- 제출 처리 ---
#     if submitted:
#         if not service_name.strip() or not features.strip() or not location.strip():
#             st.warning(config.get("ui.messages.no_input"))
#             return

#         payload = {
#             "service_type": service_type,
#             "service_name": service_name,
#             "features": features,
#             "location": location,
#             "tone": tone
#         }

#         with st.spinner(config.get("ui.messages.loading")):
#             try:
#                 output = api.call_caption(payload)
#                 captions, hashtags = parse_caption_output(output)

#                 st.session_state["captions"] = captions
#                 st.session_state["hashtags"] = hashtags

#             except Exception as e:
#                 st.error(f"{config.get('ui.messages.error')}: {e}")
#                 return

#     # --- 생성된 문구 표시 ---
#     if "captions" in st.session_state and st.session_state["captions"]:
#         st.markdown("### 💬 생성된 문구")

#         for i, caption in enumerate(st.session_state["captions"], 1):
#             st.write(f"**{i}.** {caption}")

#         st.markdown("---")

#         selected_idx = st.radio(
#             "다음 페이지에서 사용할 문구 선택:",
#             range(len(st.session_state["captions"])),
#             format_func=lambda x: f"문구 {x+1}",
#             key="caption_selector"
#         )

#         st.session_state["selected_caption"] = st.session_state["captions"][selected_idx]
#         st.success(f"✅ 선택: {st.session_state['selected_caption'][:50]}...")

#         st.markdown("### 🔖 추천 해시태그")
#         st.code(st.session_state["hashtags"], language="")




# # ============================================================
# # 페이지 2: T2I 이미지 생성 (입력값 유지 + 연결 모드 변경에도 상태 유지)
# # ============================================================
# def render_t2i_page(config: ConfigLoader, api: APIClient, connect_mode: bool):
#     st.title("🖼 문구 기반 이미지 생성 (향상된 프롬프트 제어 포함)")

#     # ======================================================================
#     # 1) 페이지1 문구 + 사용자 입력 프롬프트 (값 유지 패치 완료)
#     # ======================================================================
#     selected_caption = st.session_state.get("selected_caption", "")

#     if connect_mode and selected_caption:
#         st.info(f"🔗 연결 모드 활성화 — 페이지1 문구가 보조 요소로 사용됩니다.\n\n**선택 문구:** {selected_caption}")
#         base_prompt = st.text_area(
#             "메인 프롬프트 (사용자 입력)",
#             placeholder="예: 밝고 에너지 넘치는 필라테스 스튜디오, 건강하고 활기찬 느낌",
#             key="base_prompt_t2i",
#             value=st.session_state.get("base_prompt_t2i", "")
#         )
#     else:
#         if connect_mode:
#             st.warning("⚠️ 페이지1에서 문구를 먼저 생성하세요")

#         base_prompt = st.text_area(
#             "메인 프롬프트",
#             placeholder=config.get("ui.placeholders.caption", "예: 따뜻한 조명, 편안한 분위기의 요가 공간"),
#             key="base_prompt_t2i",
#             value=st.session_state.get("base_prompt_t2i", "")
#         )

#     # 페이지1 보조 프롬프트 원본
#     captions_for_support = f"{selected_caption} {st.session_state.get('hashtags', '')}".strip()

#     # ======================================================================
#     # 2) 보조 프롬프트 UI (완전 상태 유지)
#     # ======================================================================
#     st.markdown("---")
#     st.markdown("### 🎚 보조 프롬프트 설정 (페이지1 문구 사용 시)")

#     support_strength = st.select_slider(
#         "보조 프롬프트 강도",
#         options=["약하게", "중간", "강하게"],
#         key="support_strength_t2i",
#         value=st.session_state.get("support_strength_t2i", "중간"),
#     )

#     support_method = st.selectbox(
#         "보조 프롬프트 생성 방식",
#         ["단순 키워드 변환", "GPT 기반 자연스러운 스타일 변환", "사용자 조절형 혼합"],
#         key="support_method_t2i",
#         index=["단순 키워드 변환", "GPT 기반 자연스러운 스타일 변환", "사용자 조절형 혼합"].index(
#             st.session_state.get("support_method_t2i", "단순 키워드 변환")
#         )
#     )

#     enable_negative = st.checkbox(
#         "NEGATIVE 프롬프트 자동 생성",
#         key="enable_negative_t2i",
#         value=st.session_state.get("enable_negative_t2i", True)
#     )

#     # 프롬프트 방식 설명 로직
#     support_description = ""
#     if support_method == "단순 키워드 변환":
#         support_description = (
#             "💡 **단순 키워드 변환 모드입니다.**\n"
#             "페이지1 문구에서 **핵심 단어만 추출**해 간결한 보조 프롬프트를 구성합니다.\n"
#             "문장의 구조를 무시하고, 순수한 컨셉 키워드 중심으로 동작합니다."
#         )
#     elif support_method == "GPT 기반 자연스러운 스타일 변환":
#         support_description = (
#             "💡 **GPT 기반 자연스러운 스타일 변환 모드입니다.**\n"
#             "원본 문구에 *'cinematic soft light', 'premium studio mood'* 같은 **고품질 스타일 키워드를 자동 추가**합니다.\n"
#             "이미지의 **예술적인 분위기·조명·품질 개선**에 최적화된 방식입니다."
#         )
#     elif support_method == "사용자 조절형 혼합":
#         support_description = (
#             "💡 **사용자 조절형 혼합 모드입니다.**\n"
#             "원본 문구에 *'warm tone', 'clean aesthetic'* 등 **예측 가능한 분위기 키워드**를 추가합니다.\n"
#             "과한 스타일링 없이 **일관된 분위기 유지 + 강도 조절**에 적합합니다."
#         )

#     st.info(support_description) # 출력 코드



#     # ======================================================================
#     # 3) 보조 프롬프트 생성
#     # ======================================================================
#     def build_support_prompt(text, method, strength):
#         if not text:
#             return ""

#         if method == "단순 키워드 변환":
#             prompt = ", ".join(re.split(r"[ ,.\n]+", text)[:30])
#         elif method == "GPT 기반 자연스러운 스타일 변환":
#             prompt = f"{text}, cinematic soft light, refined composition, premium studio mood"
#         else:
#             prompt = f"{text}, warm tone, clean aesthetic, balanced framing"

#         weight = {"약하게": "0.3", "중간": "0.6", "강하게": "1.0"}[strength]
#         return f"({prompt}:{weight})"

#     support_prompt = build_support_prompt(captions_for_support, support_method, support_strength)

#     # ======================================================================
#     # 4) NEGATIVE 프롬프트
#     # ======================================================================
#     auto_negative_prompt = (
#         "distorted body, extra limbs, blur, noise, low quality, artifacts, "
#         "mutated hands, unrealistic anatomy, text, watermark, bad hands, lowres, worse quality"
#     ) if enable_negative else ""

#     # ======================================================================
#     # 5) 최종 프롬프트 구성
#     # ======================================================================
#     final_prompt = base_prompt
#     if connect_mode and selected_caption:
#         final_prompt = f"{base_prompt}, {support_prompt}".strip(", ")

#     if final_prompt:
#         st.caption(f"**최종 PROMPT:** {final_prompt[:150]}...")

#     if auto_negative_prompt:
#         st.caption(f"**NEGATIVE PROMPT:** {auto_negative_prompt}")

#     # ======================================================================
#     # 6) 이미지 생성 옵션 (모두 session_state로 유지)
#     # ======================================================================
#     st.markdown("---")

#     # 모델 정보
#     model_info = api.get_model_info()
#     current_model_name = model_info.get("current") if model_info else None
#     is_flux = current_model_name and "flux" in current_model_name.lower()

#     # 크기 선택
#     preset_sizes = config.get("image.preset_sizes", [])
#     size_options = []
#     for s in preset_sizes:
#         label = f"{s['name']} ({s['width']}x{s['height']})"
#         if is_flux and s['width'] == 1024:
#             label += " ⭐ 권장"
#         size_options.append(label)

#     selected_size = st.selectbox(
#         "이미지 크기",
#         size_options,
#         key="selected_size_t2i",
#         index=size_options.index(st.session_state.get("selected_size_t2i", size_options[0]))
#         if st.session_state.get("selected_size_t2i") in size_options else 0
#     )

#     size_idx = size_options.index(selected_size)
#     width = preset_sizes[size_idx]["width"]
#     height = preset_sizes[size_idx]["height"]

#     # steps, guidance
#     col1, col2 = st.columns(2)

#     with col1:
#         steps = st.slider(
#             "추론 단계 (Steps)",
#             1, 50,
#             key="steps_t2i",
#             value=st.session_state.get("steps_t2i", 20)
#         )

#     with col2:
#         guidance_scale = st.slider(
#             "Guidance Scale",
#             1.0, 10.0,
#             key="guidance_t2i",
#             value=st.session_state.get("guidance_t2i", 5.0)
#         )

#     num_images = st.slider(
#         "생성할 이미지 개수",
#         1, 5,
#         key="num_images_t2i",
#         value=st.session_state.get("num_images_t2i", 1)
#     )

#     # ======================================================================
#     # 7) 생성 버튼
#     # ======================================================================
#     is_generating = st.session_state.get("is_generating_t2i", False)

#     if not is_generating:
#         submitted = st.button("🖼 이미지 생성", type="primary", disabled=not final_prompt.strip())
#     else:
#         st.warning("⏳ 이미지 생성 중입니다. 페이지를 이동하지 마세요.")
#         submitted = False

#     # ---- BTN → 생성 시작 ----
#     if submitted:
#         st.session_state["is_generating_t2i"] = True
#         st.rerun()

#     # ---- 실제 생성 ----
#     if st.session_state.get("is_generating_t2i"):
#         aligned_w = align_to_64(width)
#         aligned_h = align_to_64(height)

#         st.session_state["generated_images"] = []
#         progress_bar = st.progress(0)

#         for i in range(num_images):
#             payload = {
#                 "prompt": final_prompt,
#                 "negative_prompt": auto_negative_prompt if enable_negative else None,
#                 "width": aligned_w,
#                 "height": aligned_h,
#                 "steps": steps,
#                 "guidance_scale": guidance_scale,
#             }

#             progress_bar.progress(i / num_images, f"{i+1}/{num_images} 생성 중…")

#             img_bytes = api.call_t2i(payload)
#             if img_bytes:
#                 st.session_state["generated_images"].append({
#                     "bytes": img_bytes,
#                     "prompt": final_prompt,
#                     "index": i + 1
#                 })

#         st.session_state["is_generating_t2i"] = False
#         st.rerun()

#     # ======================================================================
#     # 8) 생성 후 이미지 표시 (다운로드해도 값 유지!)
#     # ======================================================================
#     if st.session_state.get("generated_images"):
#         st.success(f"완료! 총 {len(st.session_state['generated_images'])}개 생성됨.")

#         cols = st.columns(len(st.session_state["generated_images"]))

#         for idx, img in enumerate(st.session_state["generated_images"]):
#             with cols[idx]:
#                 img["bytes"].seek(0)
#                 st.image(img["bytes"], caption=f"버전 {idx+1}")

#                 img["bytes"].seek(0)
#                 st.download_button(
#                     f"⬇️ 다운로드",
#                     img["bytes"].read(),
#                     file_name=f"t2i_image_{idx+1}.png",
#                     mime="image/png",
#                     key=f"download_btn_{idx}"
#                 )
#                 img["bytes"].seek(0)



# # ============================================================
# # 페이지 3: I2I 이미지 편집 (입력값 유지 + 연결 모드 변경에도 안정화)
# # ============================================================
# def render_i2i_page(config: ConfigLoader, api: APIClient, connect_mode: bool):
#     st.title("🖼️ 이미지 편집 (Image-to-Image)")
#     st.info("💡 업로드된 이미지를 AI로 편집하거나, T2I 결과를 바탕으로 편집합니다.")

#     # ============================================================
#     # 1. 이미지 소스 선택 (입력 유지 기능 포함)
#     # ============================================================
#     preloaded = st.session_state.get("generated_images", [])

#     col_upload, col_select = st.columns([1, 2])

#     # 이미지 업로드 (key 추가)
#     with col_upload:
#         uploaded_file = st.file_uploader(
#             "새 이미지 업로드", 
#             type=["png", "jpg", "jpeg"],
#             key="i2i_uploaded_file"
#         )

#     # 페이지2 이미지 선택
#     can_use_preloaded = connect_mode and preloaded
#     selected_preloaded_index = None

#     if can_use_preloaded:
#         with col_select:
#             selected_preloaded_index = st.selectbox(
#                 "또는 페이지2에서 생성한 이미지 선택",
#                 list(range(len(preloaded))),
#                 format_func=lambda x: f"T2I 결과 {x+1}번",
#                 key="i2i_preloaded_selector"
#             )

#     # 최종 입력 이미지 결정
#     image_bytes = None
#     target_image_name = "미선택"

#     # 업로드 우선
#     if uploaded_file:
#         image_bytes = uploaded_file.getvalue()
#         target_image_name = uploaded_file.name

#     elif selected_preloaded_index is not None:
#         # BytesIO → bytes 변환
#         img_io = preloaded[selected_preloaded_index]["bytes"]
#         img_io.seek(0)
#         image_bytes = img_io.read()
#         target_image_name = f"T2I 결과 {selected_preloaded_index+1}번"

#     # 이미지 없을 때
#     st.markdown("---")
#     if not image_bytes:
#         if not st.session_state.get("edited_image_data"):
#             st.warning("⚠ 이미지를 업로드하거나 페이지 2에서 생성한 이미지를 선택하세요.")
#             return
#     else:
#         st.image(image_bytes, caption=f"편집 대상: {target_image_name}", width=350)

#         # 새 이미지 선택 시 기존 결과 삭제
#         if (
#             st.session_state.get("edited_image_data") 
#             and st.session_state["edited_image_data"].get("source_name") != target_image_name
#         ):
#             del st.session_state["edited_image_data"]

#     # ============================================================
#     # 2. 편집 프롬프트 (입력 유지 OK)
#     # ============================================================
#     st.subheader("📝 편집 프롬프트")

#     selected_caption = st.session_state.get("selected_caption", "")

#     if connect_mode and selected_caption:
#         st.info(f"🔗 연결 모드 — 페이지1 문구 활용됨\n\n**선택 문구:** {selected_caption}")
#     elif connect_mode:
#         st.warning("⚠ 연결 모드 ON이지만 페이지1에서 문구가 선택되지 않았습니다.")

#     edit_prompt = st.text_area(
#         "메인 편집 지시",
#         placeholder="예: 배경을 해변으로 바꾸고 캐릭터에 선글라스 추가",
#         key="edit_prompt_i2i",
#         value=st.session_state.get("edit_prompt_i2i", "")
#     )

#     captions_for_support = f"{selected_caption} {st.session_state.get('hashtags','')}".strip()

#     # ============================================================
#     # 3. 보조 프롬프트 옵션 (페이지2와 동일 유지)
#     # ============================================================
#     st.markdown("---")
#     st.markdown("### 🎚 보조 프롬프트 옵션")

#     support_strength = st.select_slider(
#         "보조 프롬프트 강도",
#         ["약하게", "중간", "강하게"],
#         key="support_strength_i2i",
#         value=st.session_state.get("support_strength_i2i", "중간"),
#     )

#     support_method = st.selectbox(
#         "보조 프롬프트 방식",
#         ["단순 키워드 변환", "GPT 기반 자연스럽게", "사용자 조절형 혼합"],
#         key="support_method_i2i",
#         index=["단순 키워드 변환", "GPT 기반 자연스럽게", "사용자 조절형 혼합"]
#         .index(st.session_state.get("support_method_i2i", "단순 키워드 변환"))
#     )

#     # support_description 유지
#     if support_method == "단순 키워드 변환":
#         st.info("💡 페이지1 문구에서 핵심 키워드만 추출해 단순 스타일로 반영합니다.")
#     elif support_method == "GPT 기반 자연스럽게":
#         st.info("💡 페이지1 문구를 바탕으로 자연스러운 스타일·조명·무드를 자동 확장합니다.")
#     else:
#         st.info("💡 기본 문구에 균형 잡힌 분위기 키워드를 섞어 안정적으로 조절된 이미지를 생성합니다.")

#     enable_negative = st.checkbox(
#         "NEGATIVE 프롬프트 자동 생성",
#         key="enable_negative_i2i",
#         value=st.session_state.get("enable_negative_i2i", True)
#     )

#     # ============================================================
#     # 4. 세부 옵션 (strength/steps/size)
#     # ============================================================
#     st.markdown("### ⚙ 편집 세부 조정")

#     i2i_cfg = config.get("image.i2i", {})

#     col_a, col_b, col_c = st.columns(3)

#     with col_a:
#         strength = st.slider(
#             "변화 강도 (strength)",
#             float(i2i_cfg.get("strength", {}).get("min", 0.0)),
#             float(i2i_cfg.get("strength", {}).get("max", 1.0)),
#             key="strength_i2i",
#             value=st.session_state.get("strength_i2i", i2i_cfg.get("strength", {}).get("default", 0.7)),
#             step=float(i2i_cfg.get("strength", {}).get("step", 0.05)),
#         )

#     with col_b:
#         steps = st.slider(
#             "Steps",
#             1, 50,
#             key="steps_i2i",
#             value=st.session_state.get("steps_i2i", 30)
#         )

#     with col_c:
#         preset_sizes = config.get("image.preset_sizes", [])
#         size_labels = [f"{s['name']} ({s['width']}x{s['height']})" for s in preset_sizes]

#         selected_size = st.selectbox(
#             "출력 크기",
#             size_labels,
#             key="size_selector_i2i",
#             index=size_labels.index(st.session_state.get("size_selector_i2i", size_labels[0]))
#             if st.session_state.get("size_selector_i2i") in size_labels else 0
#         )
#         st.session_state["size_selector_i2i"] = selected_size

#         idx = size_labels.index(selected_size)
#         width = preset_sizes[idx]["width"]
#         height = preset_sizes[idx]["height"]

#     negative_prompt_user = st.text_area(
#         "NEGATIVE 프롬프트 (직접 입력)",
#         key="negative_prompt_i2i",
#         value=st.session_state.get("negative_prompt_i2i", "low quality, blurry, distorted")
#     )

#     # ============================================================
#     # 5. 최종 프롬프트 구성
#     # ============================================================
#     def build_support(text, method, strength):
#         if not text:
#             return ""
#         if method == "단순 키워드 변환":
#             base = ", ".join(re.split(r"[ ,.\n]+", text)[:20])
#         elif method == "GPT 기반 자연스럽게":
#             base = f"{text}, cinematic soft light, premium mood, refined rendering"
#         else:
#             base = f"{text}, balanced framing, clean aesthetic"

#         ratio = {"약하게": "0.3", "중간": "0.6", "강하게": "1.0"}[strength]
#         return f"({base}:{ratio})"

#     support_prompt_final = build_support(captions_for_support, support_method, support_strength)

#     final_prompt = edit_prompt
#     if connect_mode and selected_caption:
#         final_prompt = f"{edit_prompt}, {support_prompt_final}"

#     # negative prompt 구성
#     if enable_negative:
#         negative_prompt_final = (
#             "distorted, extra limbs, bad hands, watermark, lowres, noise, artifacts, "
#             + negative_prompt_user
#         )
#     else:
#         negative_prompt_final = negative_prompt_user

#     if final_prompt:
#         st.caption(f"최종 PROMPT: {final_prompt[:120]}...")

#     # ============================================================
#     # 6. 실행 버튼
#     # ============================================================
#     submitted = st.button("✨ 이미지 편집 실행", type="primary", disabled=not final_prompt.strip())

#     if submitted:
#         st.session_state["edited_image_data"] = None

#         aligned_w = align_to_64(width)
#         aligned_h = align_to_64(height)

#         payload = {
#             "input_image_base64": base64.b64encode(image_bytes).decode(),
#             "prompt": final_prompt,
#             "negative_prompt": negative_prompt_final,
#             "strength": float(strength),
#             "width": aligned_w,
#             "height": aligned_h,
#             "steps": steps
#         }

#         try:
#             with st.spinner("이미지 편집 중..."):
#                 edited_io = api.call_i2i(payload)

#             if edited_io:
#                 st.session_state["edited_image_data"] = {
#                     "source_name": target_image_name,
#                     "original_bytes": image_bytes,
#                     "edited_bytes": edited_io.read(),
#                     "prompt": final_prompt
#                 }
#                 st.rerun()

#         except Exception as e:
#             st.error(f"편집 실패: {e}")

#     # ============================================================
#     # 7. 결과 표시
#     # ============================================================
#     edited = st.session_state.get("edited_image_data")
#     if edited:
#         st.markdown("---")
#         st.subheader("🎉 편집 결과")

#         c1, c2 = st.columns(2)

#         with c1:
#             st.caption(f"원본 이미지: {edited['source_name']}")
#             st.image(edited["original_bytes"])

#         with c2:
#             st.caption("편집된 이미지")
#             st.image(edited["edited_bytes"])

#             st.download_button(
#                 "⬇ 편집본 다운로드",
#                 edited["edited_bytes"],
#                 "edited_image.png",
#                 "image/png",
#                 key="download_i2i"
#             )

#         st.caption(f"사용된 프롬프트: {edited['prompt']}")




# # ============================================================
# # 실행
# # ============================================================
# if __name__ == "__main__":
#     main()