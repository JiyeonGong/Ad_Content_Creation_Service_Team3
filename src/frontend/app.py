# app.py (리팩토링 버전)
"""
헬스케어 AI 콘텐츠 제작 앱 - Streamlit 프론트엔드
설정 기반 아키텍처로 하드코딩 최소화
"""
import os
import re
import time
import logging
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
                "steps": {"min": 1, "max": 50, "default": 28}
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
        self.timeout = config.get("api.timeout", 3600)  # 기본값을 3600초(60분)로 증가
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

    def get_image_editing_experiments(self) -> Optional[Dict]:
        """이미지 편집 실험 목록 조회"""
        try:
            resp = requests.get(
                f"{self.base_url}/api/image_editing/experiments",
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logging.error(f"실험 목록 조회 실패: {e}")
            return None

    # 프리로드 기능 제거됨 - 사용하지 않음

    def unload_model_comfyui(self) -> Dict:
        """ComfyUI 모델 언로드 요청"""
        try:
            resp = requests.post(
                f"{self.base_url}/api/unload",
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise Exception(f"모델 언로드 실패: {e}")

    def get_current_comfyui_model(self) -> Optional[str]:
        """현재 로드된 ComfyUI 모델 조회"""
        try:
            resp = requests.get(
                f"{self.base_url}/api/current_model",
                timeout=5
            )
            resp.raise_for_status()
            return resp.json().get("current_model")
        except Exception:
            return None

    def check_comfyui_status(self) -> Optional[Dict]:
        """ComfyUI 서버 상태 확인"""
        try:
            resp = requests.get(
                f"{self.base_url}/api/comfyui/status",
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def edit_with_comfyui(self, payload: Dict) -> Optional[Dict]:
        """ComfyUI를 사용한 이미지 편집"""
        try:
            resp = requests.post(
                f"{self.base_url}/api/edit_with_comfyui",
                json=payload,
                timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.json().get("detail", str(e))
            raise Exception(f"이미지 편집 실패: {error_detail}")
        except Exception as e:
            raise Exception(f"요청 실패: {e}")










    # ============================================================
    # 🆕 이미지 편집 실험 (페이지4)
    # ============================================================
    def call_image_editing_experiment(self, payload: dict):
        """페이지4: 고급 이미지 편집 API 호출"""

        try:
            url = f"{self.base_url}/api/edit_with_comfyui"
            response = requests.post(url, json=payload, timeout=self.timeout)  # 타임아웃 설정 추가

            if response.status_code != 200:
                raise RuntimeError(f"이미지 편집 실패: {response.text}")

            data = response.json()

            if not data.get("success"):
                raise RuntimeError(data.get("error", "편집 실패 (알 수 없는 오류)"))

            # 메인 결과 이미지
            output_b64 = data.get("output_image_base64")
            if not output_b64:
                raise RuntimeError("출력 이미지 Base64가 없습니다.")

            return base64.b64decode(output_b64)

        except Exception as e:
            raise RuntimeError(f"call_image_editing_experiment 오류: {e}")

    # ============================================================
    # 🆕 3D 캘리그라피 생성 (페이지5)
    # ============================================================
    def call_calligraphy(self, payload: dict) -> Optional[BytesIO]:
        """페이지5: 3D 캘리그라피 생성 API 호출"""
        try:
            url = f"{self.base_url}/api/generate_calligraphy"
            response = requests.post(url, json=payload, timeout=self.timeout)
            
            if response.status_code != 200:
                raise RuntimeError(f"캘리그라피 생성 실패: {response.text}")
            
            # PNG 이미지 바이트 직접 반환
            return BytesIO(response.content)
            
        except Exception as e:
            raise RuntimeError(f"call_calligraphy 오류: {e}")










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

    # 모델 선택 (ModelSelector 사용)
    st.sidebar.markdown("---")
    
    from model_selector import ModelSelector
    selector = ModelSelector(api)
    
    if page_id == "image_editing_experiment":
        # 4페이지: 편집 모드 선택
        selected_mode_id = selector.render_editing_mode_selector()
    else:
        # 1,2,3 페이지: 이미지 생성 모델 선택
        selected_model_id = selector.render_generation_model_selector()

    # ComfyUI 상태 표시 (사이드바 바로 보이게)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔧 ComfyUI 상태")
    comfyui_status = api.check_comfyui_status()
    if comfyui_status and comfyui_status.get("connected"):
        st.sidebar.success("✅ 연결됨")
        st.sidebar.caption(f"URL: {comfyui_status.get('base_url', 'N/A')}")
    else:
        st.sidebar.error("❌ 연결 안됨")
        st.sidebar.caption("ComfyUI 서버를 실행하세요")

    # 연결 모드
    st.sidebar.markdown("---")
    connect_mode = st.sidebar.checkbox(
        "🔗 페이지 연결 모드",
        value=config.get("connection_mode.enabled_by_default", True)
    )
    st.sidebar.info(config.get("connection_mode.description", ""))

    # 백엔드 상태 표시 (expander 안에)
    with st.sidebar.expander("📊 시스템 상태 상세"):
        status = api.get_backend_status(force_refresh=True)
        if status:
            # 서버 재시작 감지 시 자동 새로고침
            if status.get("server_restarted"):
                st.warning("🔄 서버가 재시작되었습니다. 상태를 새로고침합니다...")
                st.rerun()

            st.json(status)
        else:
            st.error("⚠️ 백엔드 연결 안됨")
    
    # 연결 모드 OFF 시 세션 초기화
    if not connect_mode:
        for key in ["captions", "hashtags", "generated_images", "selected_caption"]:
            if key in st.session_state:
                del st.session_state[key]
    
    # 페이지 라우팅
    if page_id == "caption":
        render_caption_page(config, api)
    elif page_id == "t2i":
        render_t2i_page(config, api, connect_mode)
    elif page_id == "i2i":
        render_i2i_page(config, api, connect_mode)
    elif page_id == "image_editing_experiment":
        render_image_editing_experiment_page(config, api)
    elif page_id == "text_overlay":
        render_text_overlay_page(config, api)

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
# 페이지 2: T2I 이미지 생성
# ============================================================
def render_t2i_page(config: ConfigLoader, api: APIClient, connect_mode: bool):
    st.title("🖼 문구 기반 이미지 생성 (FLUX + ComfyUI)")

    # ─────────────────────────────────────────
    # 1) 페이지1 문구 + 페이지2 사용자 프롬프트
    # ─────────────────────────────────────────
    selected_caption = st.session_state.get("selected_caption", "")
    hashtags = st.session_state.get("hashtags", "")

    if connect_mode and selected_caption:
        st.info(
            "🔗 **연결 모드 ON**\n\n"
            "페이지 1에서 선택한 문구가 **보조 컨텍스트**로 같이 들어갑니다.\n\n"
            f"**선택 문구:** {selected_caption}\n\n"
            f"**해시태그:** {hashtags}"
        )
        base_prompt = st.text_area(
            "메인 프롬프트 (사용자 입력)",
            placeholder="예: 밝고 에너지 넘치는 필라테스 스튜디오, 건강하고 활기찬 느낌",
            key="base_prompt_t2i",
            value=st.session_state.get("base_prompt_t2i", "")
        )
    else:
        if connect_mode and not selected_caption:
            st.warning("⚠️ 연결 모드 ON이지만, 페이지1에서 문구가 선택되지 않았습니다.")
        base_prompt = st.text_area(
            "메인 프롬프트",
            placeholder=config.get("ui.placeholders.caption", "예: 따뜻한 조명, 편안한 분위기의 요가 공간"),
            key="base_prompt_t2i",
            value=st.session_state.get("base_prompt_t2i", "")
        )

    # 페이지1 문구를 보조 컨텍스트로 붙이기 (PromptHelper 사용)
    from utils import PromptHelper
    
    raw_prompt = PromptHelper.combine_caption_and_prompt(
        base_prompt, selected_caption, hashtags, connect_mode
    )

    if raw_prompt:
        st.caption(f"**전달될 PROMPT (백엔드에서 최적화 처리됨):** {raw_prompt[:150]}...")

    # ─────────────────────────────────────────
    # 2) 모델 / 해상도 / steps / guidance 설정
    # ─────────────────────────────────────────
    from utils import PromptHelper
    
    # 사이드바에서 선택된 생성 모델 ID
    selected_model_id = st.session_state.get("selected_generation_model_id")
    current_model_name = api.get_current_comfyui_model()

    # FLUX 여부 판단 (권장 해상도 표시용)
    is_flux = (
        (selected_model_id and "flux" in selected_model_id.lower()) or
        (current_model_name and "flux" in current_model_name.lower())
    )

    # 이미지 크기 (설정 기반)
    preset_sizes = config.get("image.preset_sizes", [])
    size_options = []
    for s in preset_sizes:
        label = f"{s['name']} ({s['width']}x{s['height']})"
        if is_flux and s["width"] == 1024 and s["height"] == 1024:
            label += " ⭐ 권장"
        size_options.append(label)

    if not size_options:
        st.error("❌ frontend_config.yaml 에 image.preset_sizes 설정이 없습니다.")
        return

    selected_size = st.selectbox("이미지 크기", size_options, key="t2i_size_selector")
    size_idx = size_options.index(selected_size)
    width = preset_sizes[size_idx]["width"]
    height = preset_sizes[size_idx]["height"]

    # Steps & Guidance
    default_steps = config.get("image.steps.default", 28)
    steps_min = config.get("image.steps.min", 1)
    steps_max = config.get("image.steps.max", 50)
    default_guidance = 3.5

    col1, col2 = st.columns(2)
    with col1:
        steps = st.slider(
            "추론 단계 (Steps)",
            min_value=steps_min,
            max_value=steps_max,
            value=default_steps,
            step=1,
            help="생성 반복 횟수 (높을수록 정교하지만 느립니다)"
        )
    with col2:
        guidance_scale = st.slider(
            "Guidance Scale",
            min_value=1.0,
            max_value=10.0,
            value=float(default_guidance),
            step=0.5,
            help="프롬프트를 얼마나 강하게 따를지 (높을수록 강하게 반영)"
        )

    # 생성 개수
    num_images = st.slider(
        "생성할 이미지 개수",
        min_value=1,
        max_value=5,
        value=1,
        step=1,
        help="여러 개 생성 시 각각 다른 seed로 생성"
    )

    # 후처리 설정
    st.divider()
    st.subheader("🔧 후처리 옵션")

    post_process_method = st.radio(
        "후처리 방식",
        options=["none", "impact_pack"],
        format_func=lambda x: {
            "none": "없음 (빠름)",
            "impact_pack": "ComfyUI Impact Pack (YOLO+SAM, 얼굴/손 보정)"
        }[x],
        index=0,
        help="후처리 없음: 가장 빠름 / Impact Pack: ComfyUI 기반 얼굴/손 보정",
        key="t2i_post_process"
    )

    enable_adetailer = False
    adetailer_targets = None

    # 모델 선택 상태 안내
    if not selected_model_id or selected_model_id == "none":
        st.warning("⚠️ 사이드바에서 **생성 모델을 먼저 선택**하세요.")
    else:
        display_model = current_model_name if current_model_name else selected_model_id
        st.info(f"ℹ️ 선택된 모델: **{display_model}** (권장 steps: {default_steps}, guidance: {default_guidance})")

    # ─────────────────────────────────────────
    # 3) 이미지 생성 버튼 (rerun 사용 X, 한 번에 처리)
    # ─────────────────────────────────────────
    generate_disabled = not raw_prompt or not selected_model_id or selected_model_id == "none"

    if st.button(f"🖼 이미지 생성 ({num_images}개)", type="primary", disabled=generate_disabled):
        if not raw_prompt:
            st.error("❌ 프롬프트를 입력하세요.")
            return
        if not selected_model_id or selected_model_id == "none":
            st.error("❌ 사이드바에서 생성 모델을 선택하세요.")
            return

        aligned_w = align_to_64(width)
        aligned_h = align_to_64(height)
        if aligned_w != width or aligned_h != height:
            st.info(f"해상도 정렬: {width}x{height} → {aligned_w}x{aligned_h}")

        st.session_state["generated_images"] = []
        progress = st.progress(0.0)

        for i in range(num_images):
            # 여러 장 생성 시 약간의 텍스트 variation만 추가 (seed는 백엔드/ComfyUI가 관리)
            if num_images == 1:
                prompt_for_this = raw_prompt
            else:
                prompt_for_this = f"{raw_prompt}, variation {i+1}"

            payload = {
                "prompt": prompt_for_this,
                "width": aligned_w,
                "height": aligned_h,
                "steps": steps,
                "guidance_scale": guidance_scale,
                "post_process_method": post_process_method,
                "enable_adetailer": enable_adetailer,
                "adetailer_targets": adetailer_targets,
                "model_name": selected_model_id,
            }

            try:
                with st.spinner(f"이미지 {i+1}/{num_images} 생성 중..."):
                    img_bytes = api.call_t2i(payload)
                if img_bytes:
                    st.session_state["generated_images"].append(
                        {"prompt": prompt_for_this, "bytes": img_bytes}
                    )
                progress.progress((i + 1) / num_images)
            except Exception as e:
                # ❗ 여기서 에러를 바로 보여주기 때문에 rerun으로 날아가지 않음
                st.error(f"이미지 {i+1} 생성 실패: {e}")
                break

        progress.empty()

    # ─────────────────────────────────────────
    # 4) 결과 표시
    # ─────────────────────────────────────────
    if st.session_state.get("generated_images"):
        imgs = st.session_state["generated_images"]
        st.success(f"✅ {len(imgs)}개 이미지 생성 완료!")

        cols = st.columns(len(imgs))
        for idx, img_data in enumerate(imgs):
            with cols[idx]:
                img_bytes = img_data["bytes"]
                img_bytes.seek(0)
                st.image(img_bytes, caption=f"버전 {idx+1}", use_container_width=True)
                img_bytes.seek(0)
                st.download_button(
                    "⬇️ 다운로드",
                    img_bytes.read(),
                    file_name=f"t2i_flux_v{idx+1}.png",
                    mime="image/png",
                    key=f"t2i_dl_{idx}"
                )
                img_bytes.seek(0)



























# def render_t2i_page(config: ConfigLoader, api: APIClient, connect_mode: bool):
#     st.title("🖼 문구 기반 이미지 생성 (3가지 버전)")
    
#     # 문구 입력
#     selected_caption = ""
#     if connect_mode and "selected_caption" in st.session_state:
#         st.info(f"🔗 연결 모드: 페이지1 문구 사용\n\n**선택된 문구:** {st.session_state['selected_caption']}")
#         selected_caption = st.session_state["selected_caption"]
#     else:
#         if connect_mode:
#             st.warning("⚠️ 페이지1에서 문구를 먼저 생성하세요")
#         selected_caption = st.text_area(
#             "문구 입력",
#             placeholder=config.get("ui.placeholders.caption", "")
#         )
    
#     # 선택된 모델 ID 가져오기 (사이드바에서 선택한 모델)
#     selected_model_id = st.session_state.get("selected_generation_model_id")

#     # 현재 로드된 모델 확인
#     current_model_name = api.get_current_comfyui_model()
#     is_flux = (selected_model_id and "flux" in selected_model_id.lower()) or (current_model_name and "flux" in current_model_name.lower())

#     # 이미지 크기 (설정 기반)
#     preset_sizes = config.get("image.preset_sizes", [])

#     # FLUX 모델 사용 시 권장 크기 표시
#     size_options = []
#     for s in preset_sizes:
#         label = f"{s['name']} ({s['width']}x{s['height']})"
#         # FLUX 모델이고 1024x1024인 경우 권장 표시
#         if is_flux and s['width'] == 1024 and s['height'] == 1024:
#             label += " ⭐ 권장"
#         size_options.append(label)

#     selected_size = st.selectbox("이미지 크기", size_options)

#     # 선택된 크기 파싱
#     size_idx = size_options.index(selected_size)
#     width = preset_sizes[size_idx]["width"]
#     height = preset_sizes[size_idx]["height"]

#     # Steps & Guidance Scale (기본값 사용)
#     default_steps = config.get("image.steps.default", 28)
#     default_guidance = 3.5

#     # 모델 선택 상태 표시
#     if not selected_model_id or selected_model_id == "none":
#         st.warning("⚠️ 사이드바에서 생성 모델을 먼저 선택하세요")
#     else:
#         display_model = current_model_name if current_model_name else selected_model_id
#         st.info(f"ℹ️ 선택된 모델: **{display_model}** (권장 steps: {default_steps}, guidance: {default_guidance})")

#     col1, col2 = st.columns(2)

#     with col1:
#         steps = st.slider(
#             "추론 단계 (Steps)",
#             min_value=config.get("image.steps.min", 1),
#             max_value=config.get("image.steps.max", 50),
#             value=default_steps,
#             step=1,
#             help="생성 반복 횟수 (높을수록 정교하지만 느림)"
#         )

#     with col2:
#         # Guidance Scale (모델이 지원하는 경우만)
#         if default_guidance is not None:
#             guidance_scale = st.slider(
#                 "Guidance Scale",
#                 min_value=1.0,
#                 max_value=10.0,
#                 value=float(default_guidance),
#                 step=0.5,
#                 help="프롬프트 준수 강도 (높을수록 프롬프트를 더 따름)"
#             )
#         else:
#             guidance_scale = None
#             st.caption("(현재 모델은 Guidance Scale 미사용)")

#     # 생성 개수 선택
#     num_images = st.slider(
#         "생성할 이미지 개수",
#         min_value=1,
#         max_value=5,
#         value=1,
#         step=1,
#         help="여러 개 생성 시 각각 다른 랜덤 seed 사용 (시간: 약 30-60초/이미지)"
#     )

#     # 후처리 방식 선택
#     st.divider()
#     st.subheader("🔧 후처리 옵션")

#     post_process_method = st.radio(
#         "후처리 방식",
#         options=["none", "impact_pack"],
#         format_func=lambda x: {
#             "none": "없음 (빠름)",
#             "impact_pack": "ComfyUI Impact Pack (YOLO+SAM, 얼굴/손 보정)"
#         }[x],
#         index=0,
#         help="후처리 없음: 가장 빠름\nImpact Pack: ComfyUI 기반 얼굴/손 보정"
#     )

#     # ADetailer 제거됨 (ComfyUI 사용으로 인해 비활성화)
#     enable_adetailer = False
#     adetailer_targets = None

#     # 생성 중 상태 확인
#     is_generating = st.session_state.get("is_generating_t2i", False)

#     if is_generating:
#         st.warning("⏳ 이미지 생성 중입니다... 페이지를 이동하지 마세요!")
#         submitted = False
#     else:
#         submitted = st.button(f"🖼 이미지 생성 ({num_images}개)", type="primary")

#     if submitted and selected_caption:
#         # 생성 시작 - 상태 설정
#         st.session_state["is_generating_t2i"] = True

#         # 해상도 정렬
#         aligned_w = align_to_64(width)
#         aligned_h = align_to_64(height)
#         if aligned_w != width or aligned_h != height:
#             st.info(f"해상도 정렬: {width}x{height} → {aligned_w}x{aligned_h}")

#         st.session_state["generated_images"] = []
#         progress = st.progress(0)

#         for i in range(num_images):
#             # 1개만 생성할 때는 variation 표시 안함
#             if num_images == 1:
#                 prompt = caption_to_prompt(selected_caption)
#             else:
#                 prompt = caption_to_prompt(f"{selected_caption} (variation {i+1})")

#             payload = {
#                 "prompt": prompt,
#                 "width": aligned_w,
#                 "height": aligned_h,
#                 "steps": steps,
#                 "guidance_scale": guidance_scale,
#                 "post_process_method": post_process_method,
#                 "enable_adetailer": enable_adetailer,
#                 "adetailer_targets": adetailer_targets,
#                 "model_name": selected_model_id  # 선택된 모델 전달
#             }

#             try:
#                 with st.spinner(f"이미지 {i+1}/{num_images} 생성 중..."):
#                     img_bytes = api.call_t2i(payload)
#                     if img_bytes:
#                         st.session_state["generated_images"].append({
#                             "prompt": prompt,
#                             "bytes": img_bytes
#                         })
#                 progress.progress((i+1)/num_images)
#             except Exception as e:
#                 st.error(f"이미지 {i+1} 생성 실패: {e}")
#                 break
        
#         progress.empty()

#         # 생성 완료 - 상태 해제
#         st.session_state["is_generating_t2i"] = False

#         if st.session_state.get("generated_images"):
#             st.success(f"✅ {len(st.session_state['generated_images'])}개 이미지 완료!")

#             cols = st.columns(len(st.session_state["generated_images"]))
#             for idx, img_data in enumerate(st.session_state["generated_images"]):
#                 with cols[idx]:
#                     st.image(img_data["bytes"], caption=f"버전 {idx+1}", use_container_width=True)
#                     st.download_button(
#                         f"⬇️ 다운로드",
#                         img_data["bytes"],
#                         f"image_v{idx+1}.png",
#                         "image/png",
#                         key=f"dl_{idx}"
#                     )
#         else:
#             st.error("❌ 이미지 생성에 실패했습니다. 백엔드 로그를 확인하세요.")

# ============================================================
# 페이지 3: I2I 이미지 편집
# ============================================================
def render_i2i_page(config: ConfigLoader, api: APIClient, connect_mode: bool):
    st.title("🖼️ 이미지 편집 (Image-to-Image)")
    st.info("💡 업로드된 이미지나 페이지2에서 생성된 이미지를 기반으로 스타일/분위기를 바꿉니다.\n"
            "프롬프트는 백엔드에서 FLUX 전용 3단계 변환을 그대로 공유합니다.")

    # ─────────────────────────────────────────
    # 1) 편집 대상 이미지 선택 (업로드 or 페이지2 결과)
    # ─────────────────────────────────────────
    col_upload, col_select = st.columns([1, 2])

    with col_upload:
        uploaded_file = st.file_uploader(
            "새 이미지 업로드",
            type=["png", "jpg", "jpeg"],
            key="i2i_uploaded_file"
        )

    preloaded = st.session_state.get("generated_images", [])
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
    source_name = "미선택"

    if uploaded_file:
        image_bytes = uploaded_file.getvalue()
        source_name = uploaded_file.name
    elif selected_preloaded_index is not None:
        img_io = preloaded[selected_preloaded_index]["bytes"]
        img_io.seek(0)
        image_bytes = img_io.read()
        source_name = f"T2I 결과 {selected_preloaded_index+1}번"

    st.markdown("---")

    if not image_bytes:
        edited = st.session_state.get("edited_image_data")
        if edited:
            st.info("이전에 편집한 결과가 있습니다. 아래에서 다시 확인할 수 있습니다.")
        else:
            st.warning("⚠ 이미지를 업로드하거나 페이지 2에서 생성한 이미지를 선택하세요.")
            return
    else:
        st.image(image_bytes, caption=f"편집 대상: {source_name}", width=350)
        # 편집 대상이 바뀌면 이전 결과 초기화
        edited = st.session_state.get("edited_image_data")
        if edited and edited.get("source_name") != source_name:
            st.session_state["edited_image_data"] = None

    # ─────────────────────────────────────────
    # 2) 편집 프롬프트 (항상 사용자 입력 가능) + 연결 모드 보조 프롬프트
    # ─────────────────────────────────────────
    st.subheader("📝 편집 프롬프트")

    selected_caption = st.session_state.get("selected_caption", "")
    hashtags = st.session_state.get("hashtags", "")

    if connect_mode and selected_caption:
        st.info(f"🔗 연결 모드 — 페이지1 문구가 보조 프롬프트로 사용됩니다.\n\n"
                f"**선택 문구:** {selected_caption}\n\n"
                f"**해시태그:** {hashtags}")
    elif connect_mode:
        st.warning("⚠ 연결 모드 ON이지만 페이지1에서 문구가 선택되지 않았습니다.")

    edit_prompt = st.text_area(
        "메인 편집 지시 (사용자 입력)",
        placeholder=config.get("ui.placeholders.edit_prompt", "예: 더 밝고 활기찬 분위기로, 파란색 배경 추가"),
        key="edit_prompt_i2i",
        value=st.session_state.get("edit_prompt_i2i", "")
    )

    captions_for_support = f"{selected_caption} {hashtags}".strip()

    # ─────────────────────────────────────────
    # 3) 보조 프롬프트 옵션 (페이지2와 유사한 UX)
    # ─────────────────────────────────────────
    st.markdown("---")
    st.subheader("🎚 보조 프롬프트 옵션")

    support_strength = st.select_slider(
        "보조 프롬프트 강도",
        options=["약하게", "중간", "강하게"],
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
        st.info("💡 페이지1 문구에서 핵심 키워드만 추출해 단순하게 스타일을 반영합니다.")
    elif support_method == "GPT 기반 자연스럽게":
        st.info("💡 페이지1 문구를 바탕으로 자연스러운 스타일·조명·무드를 자동 확장합니다.")
    else:
        st.info("💡 기본 문구에 균형 잡힌 분위기 키워드를 섞어 안정적으로 조절된 이미지를 생성합니다.")

    # PromptHelper 사용 (중복 제거)
    from utils import PromptHelper
    
    support_prompt = ""
    if connect_mode and selected_caption:
        support_prompt = PromptHelper.build_support_prompt(
            captions_for_support, support_method, support_strength
        )

    # 최종 프롬프트 조합 (나머지 변환은 백엔드에서)
    final_prompt = edit_prompt.strip()
    if connect_mode and selected_caption and support_prompt:
        final_prompt = f"{edit_prompt.strip()}, {support_prompt}".strip(", ")

    if final_prompt:
        st.caption(f"최종 PROMPT (백엔드에서 최적화 처리): {final_prompt[:120]}...")

    # ─────────────────────────────────────────
    # 4) I2I 세부 옵션 (strength / steps / size / guidance / 후처리)
    # ─────────────────────────────────────────
    st.markdown("---")
    st.subheader("⚙ 편집 세부 조정")

    i2i_cfg = config.get("image.i2i", {})
    strength_cfg = i2i_cfg.get("strength", {})

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        strength = st.slider(
            "변화 강도 (strength)",
            float(strength_cfg.get("min", 0.0)),
            float(strength_cfg.get("max", 1.0)),
            value=float(st.session_state.get("strength_i2i", strength_cfg.get("default", 0.7))),
            step=float(strength_cfg.get("step", 0.05)),
            key="strength_i2i",
        )
    with col_b:
        steps = st.slider(
            "Steps",
            1, 50,
            value=st.session_state.get("steps_i2i", 30),
            key="steps_i2i",
        )
    with col_c:
        guidance_scale = st.slider(
            "Guidance",
            1.0, 10.0,
            value=st.session_state.get("guidance_i2i", 5.0),
            step=0.5,
            key="guidance_i2i",
        )
    with col_d:
        preset_sizes = config.get("image.preset_sizes", [])
        size_labels = [f"{s['name']} ({s['width']}x{s['height']})" for s in preset_sizes]
        selected_size = st.selectbox(
            "출력 크기",
            size_labels,
            key="size_selector_i2i",
            index=size_labels.index(st.session_state.get("size_selector_i2i", size_labels[0]))
            if st.session_state.get("size_selector_i2i") in size_labels else 0
        )
        idx = size_labels.index(selected_size)
        width = preset_sizes[idx]["width"]
        height = preset_sizes[idx]["height"]

    st.divider()
    st.subheader("🔧 후처리 옵션")

    post_process_method = st.radio(
        "후처리 방식",
        options=["none", "impact_pack"],
        format_func=lambda x: {
            "none": "없음 (빠름)",
            "impact_pack": "ComfyUI Impact Pack (YOLO+SAM, 얼굴/손 보정)"
        }[x],
        index=0,
        key="i2i_post_process"
    )

    enable_adetailer = False
    adetailer_targets = None

    # ─────────────────────────────────────────
    # 5) 실행 버튼
    # ─────────────────────────────────────────
    submitted = st.button("✨ 이미지 편집 실행", type="primary",
                          disabled=not (final_prompt.strip() and image_bytes))

    if submitted:
        if not image_bytes:
            st.error("❌ 이미지를 먼저 업로드하거나 선택하세요.")
            return
        if not final_prompt.strip():
            st.error("❌ 편집 프롬프트를 입력하세요.")
            return

        aligned_w = align_to_64(width)
        aligned_h = align_to_64(height)

        payload = {
            "input_image_base64": base64.b64encode(image_bytes).decode(),
            "prompt": final_prompt,
            "strength": float(strength),
            "width": aligned_w,
            "height": aligned_h,
            "steps": int(steps),
            "guidance_scale": float(guidance_scale),
            "post_process_method": post_process_method,
            "enable_adetailer": enable_adetailer,
            "adetailer_targets": adetailer_targets,
            # model_name은 생략 시 백엔드에서 현재 로드된 모델 사용
        }

        try:
            with st.spinner("이미지 편집 중..."):
                edited_io = api.call_i2i(payload)

            if edited_io:
                edited_bytes = edited_io.read()
                st.session_state["edited_image_data"] = {
                    "source_name": source_name,
                    "original_bytes": image_bytes,
                    "edited_bytes": edited_bytes,
                    "prompt": final_prompt
                }
        except Exception as e:
            st.error(f"편집 실패: {e}")

    # ─────────────────────────────────────────
    # 6) 결과 표시
    # ─────────────────────────────────────────
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
# 🆕 페이지 4: 이미지 편집 (v3.0 - FLUX 보조 프롬프팅 적용)
# ============================================================
def render_image_editing_experiment_page(config: ConfigLoader, api: APIClient):
    st.title("✨ AI 이미지 편집 (3가지 모드 + FLUX 프롬프팅 지원)")
    st.markdown("원본 이미지를 분석하고, 선택한 모드에 따라 AI로 자연스럽게 편집합니다.")

    # ---------------------------------------------------------------------
    # 0) 유틸 - 보조 프롬프트 생성 (페이지2/3와 동일)
    # ---------------------------------------------------------------------
    # PromptHelper 사용 (중복 제거)
    from utils import PromptHelper

    # ---------------------------------------------------------------------
    # 1) 사이드바에서 선택된 편집 모드 가져오기
    # ---------------------------------------------------------------------
    # 사이드바에서 이미 ModelSelector를 통해 편집 모드를 선택했으므로
    # 세션 스테이트에서 가져와 사용
    selected_mode_id = st.session_state.get("selected_editing_mode", "portrait_mode")
    
    # 모드 이름 표시를 위한 매핑
    mode_display_names = {
        "portrait_mode": "👤 인물 모드",
        "product_mode": "📦 제품 모드",
        "hybrid_mode": "✨ 고급(하이브리드) 모드"
    }
    
    # 선택된 모드의 이름 가져오기
    selected_mode_name = mode_display_names.get(selected_mode_id, selected_mode_id)
    
    st.info(f"**선택된 모드**: {selected_mode_name}")

    # ---------------------------------------------------------------------
    # 2) 이미지 입력
    # ---------------------------------------------------------------------
    uploaded_file = st.file_uploader("편집할 이미지 업로드", type=["png", "jpg", "jpeg"])
    generated_images = st.session_state.get("generated_images", [])

    image_bytes = None
    display_image = None

    col_upload, col_preloaded = st.columns([1, 1])
    with col_upload:
        if uploaded_file:
            image_bytes = uploaded_file.getvalue()
            display_image = image_bytes

    with col_preloaded:
        if generated_images:
            idx = st.selectbox(
                "또는 페이지2 생성 이미지를 편집하기",
                range(len(generated_images)),
                format_func=lambda x: f"T2I 이미지 {x+1}",
                key="page4_preloaded_selector"
            )
            img_io = generated_images[idx]["bytes"]
            img_io.seek(0)
            image_bytes = img_io.read()
            display_image = image_bytes

    if display_image:
        st.image(display_image, caption="원본 이미지", width=350)
    else:
        st.warning("⚠️ 이미지를 업로드하거나 페이지2에서 생성하세요.")
        return

    st.markdown("---")

    # ---------------------------------------------------------------------
    # 3) 페이지1 문구 기반 보조 프롬프트 설정
    # ---------------------------------------------------------------------
    selected_caption = st.session_state.get("selected_caption", "")
    selected_hashtags = st.session_state.get("hashtags", "")

    captions_for_support = f"{selected_caption} {selected_hashtags}".strip()

    st.subheader("🎚 보조 프롬프트 옵션")

    support_strength = st.select_slider(
        "보조 프롬프트 강도",
        ["약하게", "중간", "강하게"],
        key="page4_support_strength",
        value=st.session_state.get("page4_support_strength", "중간")
    )

    support_method = st.selectbox(
        "보조 프롬프트 방식",
        ["단순 키워드 변환", "GPT 기반 자연스럽게", "사용자 조절형 혼합"],
        key="page4_support_method",
        index=["단순 키워드 변환", "GPT 기반 자연스럽게", "사용자 조절형 혼합"]
            .index(st.session_state.get("page4_support_method", "단순 키워드 변환"))
    )

    support_prompt = ""
    if selected_caption:
        support_prompt = PromptHelper.build_support_prompt(
            captions_for_support,
            support_method,
            support_strength
        )

    # ---------------------------------------------------------------------
    # 4) 실제 편집 프롬프트 입력
    # ---------------------------------------------------------------------
    st.subheader("✏️ 메인 편집 프롬프트")

    base_prompt = st.text_area(
        "편집 지시 문구 (필수)",
        placeholder=config.get("ui.placeholders.edit_prompt", "예: 배경을 밝고 화사하게 변경"),
        key="page4_base_prompt"
    )

    # 최종 프롬프트 구성
    final_prompt = base_prompt
    if support_prompt:
        final_prompt = f"{base_prompt}, {support_prompt}"

    if final_prompt.strip():
        st.caption(f"**최종 PROMPT (백엔드에서 최적화 처리):** {final_prompt[:150]}...")

    # ---------------------------------------------------------------------
    # 5) 모델/파라미터 설정
    # ---------------------------------------------------------------------
    st.subheader("⚙ 편집 파라미터 설정")

    edit_cfg = config.get("image.editing_experiment", {})
    steps = st.slider(
        "Steps",
        edit_cfg.get("steps", {}).get("min", 10),
        edit_cfg.get("steps", {}).get("max", 50),
        value=edit_cfg.get("steps", {}).get("default", 28),
        step=1,
        key="page4_steps"
    )

    guidance_scale = st.slider(
        "Guidance Scale",
        edit_cfg.get("guidance_scale", {}).get("min", 1.0),
        edit_cfg.get("guidance_scale", {}).get("max", 15.0),
        value=edit_cfg.get("guidance_scale", {}).get("default", 3.5),
        step=0.5,
        key="page4_guidance"
    )

    # ControlNet 옵션 (portrait/hybrid)
    if selected_mode_id in ["portrait_mode", "hybrid_mode"]:
        controlnet_type = st.selectbox(
            "ControlNet 타입",
            ["canny", "depth"],
            key="page4_controlnet_type"
        )
        controlnet_strength = st.slider(
            "ControlNet 강도",
            0.0, 1.0,
            value=0.7,
            step=0.05,
            key="page4_controlnet_strength"
        )
        denoise_strength = st.slider(
            "Denoise 강도",
            0.0, 1.0,
            value=1.0,
            step=0.05,
            key="page4_denoise_strength"
        )
    else:
        controlnet_type = "depth"
        controlnet_strength = 0.0
        denoise_strength = 1.0

    # Product 모드 전용 옵션
    blending_strength = None
    if selected_mode_id == "product_mode":
        blending_strength = st.slider(
            "배경-제품 블렌딩 강도",
            0.0, 1.0,
            value=0.35,
            step=0.05,
            key="page4_blending_strength"
        )

    st.markdown("---")

    # ---------------------------------------------------------------------
    # 6) 편집 실행
    # ---------------------------------------------------------------------
    if "page4_processing" not in st.session_state:
        st.session_state["page4_processing"] = False

    button_disabled = st.session_state["page4_processing"]

    if st.button("🚀 이미지 편집 실행", type="primary", disabled=button_disabled):
        if not final_prompt.strip():
            st.error("❌ 편집 프롬프트를 입력하세요")
            return

        st.session_state["page4_processing"] = True

        # API 요청 payload
        payload = {
            "experiment_id": selected_mode_id,
            "input_image_base64": base64.b64encode(image_bytes).decode("utf-8"),
            "prompt": final_prompt,
            "negative_prompt": "",
            "steps": steps,
            "guidance_scale": guidance_scale,
            "strength": 0.8,  # deprecated (유지)
            "controlnet_type": controlnet_type,
            "controlnet_strength": controlnet_strength,
            "denoise_strength": denoise_strength,
            "blending_strength": blending_strength,
            "background_prompt": final_prompt if selected_mode_id == "product_mode" else None,
        }

        st.session_state["page4_payload"] = payload
        st.rerun()

    # ---------------------------------------------------------------------
    # 7) 실제 처리
    # ---------------------------------------------------------------------
    if st.session_state.get("page4_processing") and st.session_state.get("page4_payload"):
        payload = st.session_state["page4_payload"]

        with st.spinner("⏳ AI 이미지 편집 중..."):
            try:
                # call_image_editing_experiment는 이미지 bytes를 직접 반환
                edited_bytes = api.call_image_editing_experiment(payload)
                st.session_state["page4_processing"] = False

                if edited_bytes:
                    # 편집 결과를 세션 상태에 저장 (다운로드 후에도 유지)
                    st.session_state["page4_edited_result"] = {
                        "image_bytes": edited_bytes,
                        "mode_name": selected_mode_name,
                        "prompt": final_prompt
                    }
                    st.rerun()
                else:
                    st.error("⚠️ 출력 이미지가 없습니다.")
            except Exception as e:
                st.session_state["page4_processing"] = False
                st.error(f"❌ 편집 실패: {e}")

    # ---------------------------------------------------------------------
    # 8) 편집 결과 표시 (세션 상태에서 가져오기)
    # ---------------------------------------------------------------------
    if st.session_state.get("page4_edited_result"):
        result = st.session_state["page4_edited_result"]
        
        st.markdown("---")
        st.subheader("🎉 편집 완료!")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(display_image, caption="📸 원본 이미지", use_container_width=True)
        with col2:
            st.image(result["image_bytes"], caption=f"✨ {result['mode_name']} 결과", use_container_width=True)
        
        st.download_button(
            "⬇️ 편집 이미지 다운로드",
            result["image_bytes"],
            file_name=f"edited_{selected_mode_id}.png",
            mime="image/png",
            use_container_width=True,
            key="download_edited_result"
        )
        
        st.caption(f"💡 사용된 프롬프트: {result['prompt']}")
        
        # 새로운 편집 시작 버튼
        if st.button("🔄 새로운 이미지로 다시 편집", use_container_width=True):
            st.session_state["page4_edited_result"] = None
            st.rerun()































# ============================================================
# 🆕 페이지 4: 이미지 편집 (v3.0 - 3가지 모드)
# ============================================================
# def render_image_editing_experiment_page(config: ConfigLoader, api: APIClient):
#     st.title("✨ AI 이미지 편집")
#     st.markdown("**3가지 편집 모드로 원하는 부분만 정밀하게 변경하세요**")

#     # 편집 모드 정보 (image_editing_config.yaml에서 로드)
#     EDITING_MODES = {
#         "portrait_mode": {
#             "id": "portrait_mode",
#             "name": "👤 인물 모드",
#             "icon": "👤",
#             "description": "얼굴은 100% 보존하고, 의상과 배경만 자연스럽게 변경",
#             "detail": "Face Detector로 얼굴을 자동 보호하고, ControlNet(Depth/Canny)으로 체형을 유지하면서 옷과 배경만 변경합니다.",
#             "use_cases": ["프로필 사진 배경 변경", "의상 스타일 변경", "촬영 장소 변경"]
#         },
#         "product_mode": {
#             "id": "product_mode",
#             "name": "📦 제품 모드",
#             "icon": "📦",
#             "description": "제품은 그대로 유지하고, 배경을 창의적으로 변경",
#             "detail": "BEN2로 제품을 정밀하게 분리한 뒤, FLUX T2I로 새로운 배경을 생성하고 자연스럽게 합성합니다.",
#             "use_cases": ["제품 사진 배경 교체", "광고 이미지 제작", "스튜디오 배경 연출"]
#         },
#         "hybrid_mode": {
#             "id": "hybrid_mode",
#             "name": "✨ 고급 모드",
#             "icon": "✨",
#             "description": "얼굴과 제품을 동시에 보존하고, 나머지만 변경",
#             "detail": "얼굴(Face Detector)과 제품(BEN2)을 동시에 보호하면서, ControlNet Canny로 손가락 디테일까지 유지합니다.",
#             "use_cases": ["인물+제품 광고", "손에 든 제품 촬영", "모델+제품 합성"]
#         }
#     }

#     # 1️⃣ 이미지 업로드
#     st.subheader("1️⃣ 이미지 업로드")
#     uploaded_file = st.file_uploader(
#         "편집할 이미지를 업로드하세요",
#         type=["png", "jpg", "jpeg", "webp"],
#         help="인물 사진, 제품 사진, 또는 인물+제품 사진 모두 가능합니다"
#     )

#     if not uploaded_file:
#         st.info("👆 이미지를 먼저 업로드하세요")

#         # 샘플 사용 예시 표시 (항상 보이게)
#         st.markdown("### 💡 각 모드 사용 예시")
#         col1, col2, col3 = st.columns(3)
#         with col1:
#             st.markdown("**👤 인물 모드**")
#             for use_case in EDITING_MODES["portrait_mode"]["use_cases"]:
#                 st.markdown(f"• {use_case}")
#         with col2:
#             st.markdown("**📦 제품 모드**")
#             for use_case in EDITING_MODES["product_mode"]["use_cases"]:
#                 st.markdown(f"• {use_case}")
#         with col3:
#             st.markdown("**✨ 고급 모드**")
#             for use_case in EDITING_MODES["hybrid_mode"]["use_cases"]:
#                 st.markdown(f"• {use_case}")
#         return

#     # 업로드된 이미지 표시
#     image_bytes = uploaded_file.read()
#     image = Image.open(BytesIO(image_bytes))

#     col1, col2 = st.columns([1, 1])
#     with col1:
#         st.image(image, caption="원본 이미지", use_container_width=True)
#     with col2:
#         st.markdown("**이미지 정보**")
#         st.write(f"• 크기: {image.size[0]} x {image.size[1]} 픽셀")
#         st.write(f"• 포맷: {image.format}")
#         st.write(f"• 파일 크기: {len(image_bytes) / 1024:.1f} KB")

#     # 2️⃣ 선택된 편집 모드 확인
#     if "selected_editing_mode" not in st.session_state:
#         st.warning("⚠️ 사이드바에서 편집 모드를 선택해주세요.")
#         return

#     selected_mode_id = st.session_state["selected_editing_mode"]
#     selected_mode = EDITING_MODES[selected_mode_id]

#     st.subheader(f"2️⃣ 선택된 모드: {selected_mode['name']}")
#     st.info(f"**{selected_mode['description']}**\n\n{selected_mode['detail']}")
#     st.divider()

#     # 3️⃣ 프롬프트 입력
#     st.subheader("3️⃣ 편집 내용 입력")

#     # 모드별 프롬프트 입력
#     if selected_mode_id == "portrait_mode":
#         prompt = st.text_area(
#             "의상과 배경 설명",
#             placeholder="예: Wearing a professional navy blue suit, modern office background with glass windows, natural daylight, high quality",
#             help="변경하고 싶은 의상과 배경을 영어로 상세히 설명하세요. 얼굴은 자동으로 보호됩니다.",
#             height=100,
#             key="prompt"
#         )

#     elif selected_mode_id == "product_mode":
#         background_prompt = st.text_area(
#             "배경 설명",
#             placeholder="예: Cyberpunk city at night, neon lights, futuristic atmosphere, bokeh effect, high quality",
#             help="생성하고 싶은 배경을 영어로 상세히 설명하세요. 제품은 자동으로 분리되어 보존됩니다.",
#             height=100,
#             key="background_prompt"
#         )
#         prompt = background_prompt  # API 호출 시 사용

#     elif selected_mode_id == "hybrid_mode":
#         prompt = st.text_area(
#             "의상과 배경 설명",
#             placeholder="예: Woman in elegant red dress holding champagne bottle, luxury hotel lobby background, golden lighting, professional photography",
#             help="변경하고 싶은 의상과 배경을 영어로 설명하세요. 얼굴과 손에 든 제품은 자동으로 보호됩니다.",
#             height=100,
#             key="prompt"
#         )

#     # 4️⃣ 파라미터 설정
#     st.subheader("4️⃣ 파라미터 조정")

#     # 모드별 파라미터 설정
#     col1, col2 = st.columns(2)

#     with col1:
#         steps = st.slider(
#             "생성 품질 (Steps)",
#             min_value=10,
#             max_value=50,
#             value=28,
#             help="높을수록 품질이 향상되지만 시간이 오래 걸립니다"
#         )

#     with col2:
#         if selected_mode_id == "portrait_mode":
#             guidance_scale = st.slider(
#                 "프롬프트 반영 강도",
#                 min_value=1.0,
#                 max_value=10.0,
#                 value=3.5,
#                 step=0.5,
#                 help="높을수록 프롬프트를 강하게 반영합니다"
#             )
#         elif selected_mode_id == "product_mode":
#             guidance_scale = st.slider(
#                 "배경 디테일 강도",
#                 min_value=3.0,
#                 max_value=10.0,
#                 value=5.0,
#                 step=0.5,
#                 help="높을수록 배경 프롬프트를 강하게 반영합니다"
#             )
#         elif selected_mode_id == "hybrid_mode":
#             guidance_scale = st.slider(
#                 "프롬프트 반영 강도",
#                 min_value=1.0,
#                 max_value=10.0,
#                 value=3.5,
#                 step=0.5,
#                 help="높을수록 프롬프트를 강하게 반영합니다"
#             )

#     # 모드별 추가 파라미터
#     if selected_mode_id == "portrait_mode" or selected_mode_id == "hybrid_mode":
#         col1, col2, col3 = st.columns(3)

#         with col1:
#             controlnet_type = st.selectbox(
#                 "체형 유지 방식",
#                 ["depth", "canny"],
#                 index=0 if selected_mode_id == "portrait_mode" else 1,
#                 help="Depth: 체형/포즈 유지 | Canny: 손가락 디테일 유지"
#             )

#         with col2:
#             controlnet_strength = st.slider(
#                 "체형 유지 강도",
#                 min_value=0.0,
#                 max_value=1.0,
#                 value=0.7 if selected_mode_id == "portrait_mode" else 0.8,
#                 step=0.05,
#                 help="높을수록 원본 체형/포즈를 강하게 유지합니다"
#             )

#         with col3:
#             denoise_strength = st.slider(
#                 "변경 강도",
#                 min_value=0.7 if selected_mode_id == "hybrid_mode" else 0.0,
#                 max_value=1.0,
#                 value=1.0 if selected_mode_id == "portrait_mode" else 0.9,
#                 step=0.05,
#                 help="1.0 = 완전히 새로 그림, 낮을수록 원본 보존"
#             )

#     elif selected_mode_id == "product_mode":
#         blending_strength = st.slider(
#             "합성 자연스러움",
#             min_value=0.2,
#             max_value=0.6,
#             value=0.35,
#             step=0.05,
#             help="낮을수록 원본 제품 보존, 높을수록 배경과 자연스럽게 융합"
#         )

#     # 네거티브 프롬프트 (선택 사항)
#     with st.expander("⚙️ 추가 설정 (선택)"):
#         negative_prompt = st.text_area(
#             "네거티브 프롬프트",
#             value="blurry, low quality, distorted, bad anatomy",
#             help="생성하지 않을 요소를 설명하세요 (FLUX 모델은 효과가 제한적)",
#             height=60,
#             key="negative_prompt"
#         )

#     # 5️⃣ 편집 실행
#     st.subheader("5️⃣ 편집 실행")

#     # 버튼 비활성화 처리를 위한 세션 상태
#     if "editing_in_progress" not in st.session_state:
#         st.session_state["editing_in_progress"] = False

#     if "editing_request" not in st.session_state:
#         st.session_state["editing_request"] = None

#     # 편집 버튼 (진행 중일 때 비활성화)
#     button_disabled = st.session_state["editing_in_progress"]

#     if st.button(f"{selected_mode['icon']} 편집 시작", type="primary", use_container_width=True, disabled=button_disabled):
#         # 프롬프트 체크
#         if not prompt or not prompt.strip():
#             st.warning("⚠️ 프롬프트를 입력하세요")
#             st.stop()

#         # 편집 요청 저장 (모드별 파라미터 포함)
#         payload = {
#             "experiment_id": selected_mode_id,
#             "input_image_base64": base64.b64encode(image_bytes).decode("utf-8"),
#             "prompt": prompt,
#             "negative_prompt": negative_prompt,
#             "steps": steps,
#             "guidance_scale": guidance_scale,
#             "strength": 0.8,  # 하위 호환성 (deprecated)
#         }

#         # 모드별 추가 파라미터
#         if selected_mode_id == "portrait_mode" or selected_mode_id == "hybrid_mode":
#             payload["controlnet_type"] = controlnet_type
#             payload["controlnet_strength"] = controlnet_strength
#             payload["denoise_strength"] = denoise_strength

#         if selected_mode_id == "product_mode":
#             payload["blending_strength"] = blending_strength
#             payload["background_prompt"] = prompt  # 배경 프롬프트를 background_prompt로도 전달

#         st.session_state["editing_request"] = payload
#         st.session_state["editing_in_progress"] = True
#         st.rerun()

#     # 편집 요청이 있으면 실행
#     if st.session_state["editing_in_progress"] and st.session_state["editing_request"]:
#         payload = st.session_state["editing_request"]

#         # 진행상황 표시
#         selected_mode = EDITING_MODES.get(payload["experiment_id"], {})
#         mode_name = selected_mode.get("name", "이미지 편집")

#         # 파이프라인 단계 정의
#         pipeline_steps = {
#             "portrait_mode": [
#                 "📥 이미지 업로드 및 전처리",
#                 "🔍 얼굴 영역 자동 감지",
#                 "🎭 얼굴 마스크 생성 및 반전",
#                 "📊 체형 가이드 추출 (Depth/Canny)",
#                 "🎨 ControlNet 적용",
#                 "🚀 이미지 생성 (의상/배경 변경)",
#                 "💾 결과 저장 및 후처리"
#             ],
#             "product_mode": [
#                 "📥 이미지 업로드 및 전처리",
#                 "✂️ BEN2 배경 제거 (제품 분리)",
#                 "🎨 AI 배경 생성 (T2I)",
#                 "🔗 제품+배경 레이어 합성",
#                 "🖼️ FLUX Fill 자연스러운 블렌딩",
#                 "💾 결과 저장 및 후처리"
#             ],
#             "hybrid_mode": [
#                 "📥 이미지 업로드 및 전처리",
#                 "🔍 얼굴 + 제품 영역 감지",
#                 "🎭 멀티 마스크 생성 및 합성",
#                 "📊 윤곽선 가이드 추출 (Canny)",
#                 "🎨 ControlNet 적용",
#                 "🚀 이미지 생성 (의상/배경 변경)",
#                 "💾 결과 저장 및 후처리"
#             ]
#         }

#         steps = pipeline_steps.get(payload["experiment_id"], [])

#         try:
#             # 진행상황 안내 표시
#             st.info(f"🎨 **{mode_name} 파이프라인 실행 중...**\n\n" +
#                    "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)]) +
#                    "\n\n💡 백엔드 로그를 모니터링하여 실시간 진행상황을 확인하세요!")

#             with st.spinner(f"{mode_name} 실행 중... 잠시만 기다려주세요 (평균 30-60초 소요)"):
#                 result = api.edit_with_comfyui(payload)

#             # 편집 완료 - 버튼 다시 활성화 및 요청 초기화
#             st.session_state["editing_in_progress"] = False
#             st.session_state["editing_request"] = None

#             if result and result.get("success"):
#                 st.success(f"✅ 편집 완료! ({selected_mode['name']} | 소요 시간: {result.get('elapsed_time', 0):.1f}초)")

#                 # 6️⃣ 결과 표시
#                 st.subheader("6️⃣ 편집 결과")

#                 # 배경 제거 이미지 (있는 경우)
#                 if result.get("background_removed_image_base64"):
#                     bg_removed_bytes = base64.b64decode(result["background_removed_image_base64"])
#                     bg_removed_image = Image.open(BytesIO(bg_removed_bytes))

#                     col1, col2, col3 = st.columns(3)
#                     with col1:
#                         st.markdown("**📸 원본 이미지**")
#                         st.image(image, use_container_width=True)
#                     with col2:
#                         st.markdown("**✂️ 배경 제거 (중간 단계)**")
#                         st.image(bg_removed_image, use_container_width=True)
#                     with col3:
#                         st.markdown(f"**{selected_mode['icon']} 최종 결과**")
#                         output_bytes = base64.b64decode(result["output_image_base64"])
#                         output_image = Image.open(BytesIO(output_bytes))
#                         st.image(output_image, use_container_width=True)

#                     # 다운로드 버튼
#                     col1, col2 = st.columns(2)
#                     with col1:
#                         st.download_button(
#                             "⬇️ 배경 제거 이미지 다운로드",
#                             BytesIO(bg_removed_bytes).getvalue(),
#                             f"background_removed_{selected_mode_id}.png",
#                             "image/png",
#                             use_container_width=True
#                         )
#                     with col2:
#                         st.download_button(
#                             "⬇️ 최종 결과 다운로드",
#                             BytesIO(output_bytes).getvalue(),
#                             f"edited_{selected_mode_id}.png",
#                             "image/png",
#                             use_container_width=True
#                         )

#                 else:
#                     # 배경 제거 이미지 없이 최종 결과만
#                     col1, col2 = st.columns(2)
#                     with col1:
#                         st.markdown("**📸 원본 이미지**")
#                         st.image(image, use_container_width=True)
#                     with col2:
#                         st.markdown(f"**{selected_mode['icon']} 편집 결과**")
#                         output_bytes = base64.b64decode(result["output_image_base64"])
#                         output_image = Image.open(BytesIO(output_bytes))
#                         st.image(output_image, use_container_width=True)

#                     # 다운로드 버튼
#                     st.download_button(
#                         "⬇️ 편집 결과 다운로드",
#                         BytesIO(output_bytes).getvalue(),
#                         f"edited_{selected_mode_id}.png",
#                         "image/png",
#                         use_container_width=True
#                     )

#             else:
#                 # 편집 실패 - 버튼 다시 활성화 및 요청 초기화
#                 st.session_state["editing_in_progress"] = False
#                 st.session_state["editing_request"] = None
#                 error_msg = result.get("error", "알 수 없는 오류") if result else "응답 없음"
#                 st.error(f"❌ 편집 실패: {error_msg}")

#         except Exception as e:
#             # 예외 발생 시에도 버튼 다시 활성화 및 요청 초기화
#             st.session_state["editing_in_progress"] = False
#             st.session_state["editing_request"] = None
#             st.error(f"❌ 오류 발생: {e}")

# ============================================================
# 페이지 5: 3D 캘리그라피 생성 (텍스트 오버레이)
# ============================================================
def render_text_overlay_page(config: ConfigLoader, api: APIClient):
    """텍스트 오버레이 페이지 - 3D 캘리그라피 생성 (ControlNet Depth SDXL 활용)"""
    st.title("🔤 3D 캘리그라피 생성")
    
    st.info("""
    💡 **ControlNet Depth SDXL**을 활용하여 입체적인 3D 텍스트를 생성합니다.
    - Depth Map 기반으로 자연스러운 입체감 구현
    - 배경이 투명한 PNG로 생성되어 다른 이미지와 합성 가능
    - 다양한 3D 스타일 지원 (엠보싱, 조각, 플로팅 등)
    """)
    
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("⚙️ 텍스트 설정")
        
        # 텍스트 입력
        text_input = st.text_input(
            "생성할 텍스트",
            placeholder="예: 새해 대박!",
            help="한글, 영문 모두 가능합니다",
            key="calligraphy_text"
        )
        
        # 색상 선택
        color_hex = st.color_picker(
            "텍스트 색상",
            value="#FFFFFF",
            help="생성 후 색상 적용 (흰색 권장)",
            key="calligraphy_color"
        )
        
        # 3D 스타일 선택 (ControlNet Depth 활용)
        style_options = {
            "default": "기본 (Default) - 자연스러운 3D 입체감",
            "emboss": "엠보싱 (Emboss) - 돌출된 금속 효과",
            "carved": "조각 (Carved) - 돌에 새긴 듯한 효과",
            "floating": "플로팅 (Floating) - 공중에 떠 있는 효과"
        }
        
        style_display = st.selectbox(
            "3D 스타일",
            list(style_options.values()),
            help="ControlNet Depth를 사용한 다양한 입체감 표현",
            key="calligraphy_style"
        )
        
        # 역매핑: 표시명 -> 실제 style 값
        style = [k for k, v in style_options.items() if v == style_display][0]
        
        # 폰트 경로 (고급 옵션)
        with st.expander("🔧 고급 설정"):
            font_path = st.text_input(
                "폰트 파일 경로 (선택)",
                placeholder="/home/shared/RiaSans-Bold.ttf",
                help="비워두면 기본 폰트 사용. 서버에 있는 폰트 경로를 입력하세요",
                key="calligraphy_font_path"
            )
            
            st.caption("""
            **ℹ️ 사용 모델:**
            - ControlNet Depth SDXL (Depth Map 추출)
            - Stable Diffusion XL Base (3D 효과 생성)
            - Rembg (배경 제거)
            """)
        
        # 생성 버튼
        st.markdown("---")
        generate_btn = st.button(
            "🎨 3D 캘리그라피 생성",
            type="primary",
            use_container_width=True,
            disabled=not text_input or not text_input.strip()
        )
    
    with col2:
        st.subheader("📋 미리보기 및 결과")
        
        # 생성 버튼 클릭 시
        if generate_btn:
            if not text_input or not text_input.strip():
                st.warning("⚠️ 텍스트를 입력하세요")
            else:
                # API 호출 준비
                payload = {
                    "text": text_input,
                    "color_hex": color_hex,
                    "style": style,  # default, emboss, carved, floating
                    "font_path": font_path.strip() if font_path else ""
                }
                
                try:
                    with st.spinner(f"⏳ ControlNet Depth로 3D 효과 생성 중... (스타일: {style})"):
                        # API 호출
                        result_image = api.call_calligraphy(payload)
                    
                    if result_image:
                        st.success("✅ 3D 캘리그라피 생성 완료!")
                        
                        # 결과 이미지 표시
                        result_image.seek(0)
                        st.image(
                            result_image,
                            caption=f"생성된 캘리그라피: {text_input}",
                            use_container_width=True
                        )
                        
                        # 다운로드 버튼
                        result_image.seek(0)
                        st.download_button(
                            "⬇️ PNG 다운로드 (배경 투명)",
                            result_image.read(),
                            f"calligraphy_{text_input[:10]}.png",
                            "image/png",
                            use_container_width=True,
                            key="download_calligraphy"
                        )
                        
                        # 세션 상태에 저장 (재사용 가능)
                        result_image.seek(0)
                        st.session_state["last_calligraphy"] = {
                            "text": text_input,
                            "image": result_image.read()
                        }
                    else:
                        st.error("❌ 이미지 생성 실패")
                        
                except Exception as e:
                    st.error(f"❌ 생성 실패: {e}")
        
        # 이전 결과 표시
        elif "last_calligraphy" in st.session_state:
            st.info("이전 생성 결과:")
            last_result = st.session_state["last_calligraphy"]
            st.image(
                last_result["image"],
                caption=f"이전 결과: {last_result['text']}",
                use_container_width=True
            )
            st.download_button(
                "⬇️ PNG 다운로드",
                last_result["image"],
                f"calligraphy_{last_result['text'][:10]}.png",
                "image/png",
                use_container_width=True,
                key="download_last_calligraphy"
            )
        else:
            st.markdown("텍스트를 입력하고 생성 버튼을 눌러주세요.")
    
    # 사용 예시
    st.markdown("---")
    st.markdown("### 💡 사용 예시")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**광고 문구**")
        st.caption("• 신년 특가\n• 오픈 기념\n• 할인 중")
    
    with col2:
        st.markdown("**이벤트 제목**")
        st.caption("• 새해 대박\n• PT 무료 체험\n• 회원 모집")
    
    with col3:
        st.markdown("**강조 텍스트**")
        st.caption("• SALE\n• NEW\n• HOT")

# ============================================================
# 실행
# ============================================================
if __name__ == "__main__":
    main()
