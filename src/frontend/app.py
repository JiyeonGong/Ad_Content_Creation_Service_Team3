# app.py (리팩토링 버전)
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
    st.title("🖼 문구 기반 이미지 생성 (3가지 버전)")
    
    # 문구 입력
    selected_caption = ""
    if connect_mode and "selected_caption" in st.session_state:
        st.info(f"🔗 연결 모드: 페이지1 문구 사용\n\n**선택된 문구:** {st.session_state['selected_caption']}")
        selected_caption = st.session_state["selected_caption"]
    else:
        if connect_mode:
            st.warning("⚠️ 페이지1에서 문구를 먼저 생성하세요")
        selected_caption = st.text_area(
            "문구 입력",
            placeholder=config.get("ui.placeholders.caption", "")
        )
    
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
        # FLUX 모델이고 1024x1024인 경우 권장 표시
        if is_flux and s['width'] == 1024 and s['height'] == 1024:
            label += " ⭐ 권장"
        size_options.append(label)

    selected_size = st.selectbox("이미지 크기", size_options)

    # 선택된 크기 파싱
    size_idx = size_options.index(selected_size)
    width = preset_sizes[size_idx]["width"]
    height = preset_sizes[size_idx]["height"]
    
    # Steps & Guidance Scale (모델 정보 기반)
    model_info = api.get_model_info()
    if model_info and model_info.get("current"):
        current_model_name = model_info["current"]
        current_model = model_info["models"].get(current_model_name, {})
        default_steps = current_model.get("default_steps", 10)
        default_guidance = current_model.get("guidance_scale")

        st.info(f"ℹ️ 현재 모델: **{current_model_name}** (권장 steps: {default_steps}, guidance: {default_guidance if default_guidance else 'N/A'})")
    else:
        default_steps = config.get("image.steps.default", 10)
        default_guidance = None

    col1, col2 = st.columns(2)

    with col1:
        steps = st.slider(
            "추론 단계 (Steps)",
            min_value=config.get("image.steps.min", 1),
            max_value=config.get("image.steps.max", 50),
            value=default_steps,
            step=1,
            help="생성 반복 횟수 (높을수록 정교하지만 느림)"
        )

    with col2:
        # Guidance Scale (모델이 지원하는 경우만)
        if default_guidance is not None:
            guidance_scale = st.slider(
                "Guidance Scale",
                min_value=1.0,
                max_value=10.0,
                value=float(default_guidance),
                step=0.5,
                help="프롬프트 준수 강도 (높을수록 프롬프트를 더 따름)"
            )
        else:
            guidance_scale = None
            st.caption("(현재 모델은 Guidance Scale 미사용)")

    # 생성 개수 선택
    num_images = st.slider(
        "생성할 이미지 개수",
        min_value=1,
        max_value=5,
        value=1,
        step=1,
        help="여러 개 생성 시 각각 다른 랜덤 seed 사용 (시간: 약 30-60초/이미지)"
    )

    # 생성 중 상태 확인
    is_generating = st.session_state.get("is_generating_t2i", False)

    if is_generating:
        st.warning("⏳ 이미지 생성 중입니다... 페이지를 이동하지 마세요!")
        submitted = False
    else:
        submitted = st.button(f"🖼 이미지 생성 ({num_images}개)", type="primary")

    if submitted and selected_caption:
        # 생성 시작 - 상태 설정
        st.session_state["is_generating_t2i"] = True

        # 해상도 정렬
        aligned_w = align_to_64(width)
        aligned_h = align_to_64(height)
        if aligned_w != width or aligned_h != height:
            st.info(f"해상도 정렬: {width}x{height} → {aligned_w}x{aligned_h}")

        st.session_state["generated_images"] = []
        progress = st.progress(0)

        for i in range(num_images):
            # 1개만 생성할 때는 variation 표시 안함
            if num_images == 1:
                prompt = caption_to_prompt(selected_caption)
            else:
                prompt = caption_to_prompt(f"{selected_caption} (variation {i+1})")

            payload = {
                "prompt": prompt,
                "width": aligned_w,
                "height": aligned_h,
                "steps": steps,
                "guidance_scale": guidance_scale
            }

            try:
                with st.spinner(f"이미지 {i+1}/{num_images} 생성 중..."):
                    img_bytes = api.call_t2i(payload)
                    if img_bytes:
                        st.session_state["generated_images"].append({
                            "prompt": prompt,
                            "bytes": img_bytes
                        })
                progress.progress((i+1)/num_images)
            except Exception as e:
                st.error(f"이미지 {i+1} 생성 실패: {e}")
                break
        
        progress.empty()

        # 생성 완료 - 상태 해제
        st.session_state["is_generating_t2i"] = False

        if st.session_state.get("generated_images"):
            st.success(f"✅ {len(st.session_state['generated_images'])}개 이미지 완료!")

            cols = st.columns(len(st.session_state["generated_images"]))
            for idx, img_data in enumerate(st.session_state["generated_images"]):
                with cols[idx]:
                    st.image(img_data["bytes"], caption=f"버전 {idx+1}", use_container_width=True)
                    st.download_button(
                        f"⬇️ 다운로드",
                        img_data["bytes"],
                        f"image_v{idx+1}.png",
                        "image/png",
                        key=f"dl_{idx}"
                    )
        else:
            st.error("❌ 이미지 생성에 실패했습니다. 백엔드 로그를 확인하세요.")

# ============================================================
# 페이지 3: I2I 이미지 편집
# ============================================================
def render_i2i_page(config: ConfigLoader, api: APIClient, connect_mode: bool):
    st.title("🖼️ 이미지 편집 (Image-to-Image)")
    st.info("💡 업로드된 이미지를 AI로 편집합니다 (배경 변경, 스타일 변경 등)")
    
    # 이미지 소스
    uploaded = st.file_uploader("이미지 업로드", type=["png", "jpg", "jpeg"])
    preloaded = st.session_state.get("generated_images", [])
    
    image_bytes = None
    display_image = None
    
    if uploaded:
        image_bytes = uploaded.getvalue()
        display_image = image_bytes
    elif preloaded and connect_mode:
        st.info("🔗 연결 모드: 페이지2 이미지 사용")
        idx = st.selectbox("이미지 선택", range(len(preloaded)), format_func=lambda x: f"버전 {x+1}")
        image_bytes = preloaded[idx]["bytes"].getvalue()
        display_image = image_bytes
    
    if display_image:
        st.image(display_image, caption="선택된 이미지", width=300)
    else:
        st.warning("⚠️ 이미지를 업로드하거나 페이지2에서 생성하세요")
    
    # 문구
    selected_caption = ""
    if connect_mode and "selected_caption" in st.session_state:
        st.info(f"🔗 사용할 문구: {st.session_state['selected_caption']}")
        selected_caption = st.session_state["selected_caption"]
    else:
        selected_caption = st.text_input("편집 문구", placeholder=config.get("ui.placeholders.caption", ""))
    
    # I2I 설정
    i2i_config = config.get("image.i2i", {})
    strength = st.slider(
        "✨ 변화 강도 (Strength)",
        min_value=i2i_config.get("strength", {}).get("min", 0.0),
        max_value=i2i_config.get("strength", {}).get("max", 1.0),
        value=i2i_config.get("strength", {}).get("default", 0.75),
        step=i2i_config.get("strength", {}).get("step", 0.05),
        help="0.0: 원본 유지, 1.0: 완전히 새로운 이미지"
    )
    
    edit_prompt = st.text_area(
        "추가 지시 (선택)",
        placeholder=config.get("ui.placeholders.edit_prompt", "")
    )

    # 현재 모델 정보 가져오기 (크기 권장을 위해)
    model_info = api.get_model_info()
    current_model_name = model_info.get("current") if model_info else None
    is_flux = current_model_name and "flux" in current_model_name.lower()

    # 출력 크기 (입력 이미지가 이 크기로 리사이즈됨)
    preset_sizes = config.get("image.preset_sizes", [])

    # FLUX 모델 사용 시 권장 크기 표시
    size_options = []
    for s in preset_sizes:
        label = f"{s['name']} ({s['width']}x{s['height']})"
        if is_flux and s['width'] == 1024 and s['height'] == 1024:
            label += " ⭐ 권장"
        size_options.append(label)

    selected_size = st.selectbox(
        "출력 크기",
        size_options,
        help="입력 이미지가 이 크기로 리사이즈된 후 편집됩니다"
    )

    size_idx = size_options.index(selected_size)
    width = preset_sizes[size_idx]["width"]
    height = preset_sizes[size_idx]["height"]

    submitted = st.button("✨ 이미지 편집", type="primary")
    
    if submitted:
        if not image_bytes:
            st.error("❌ 이미지를 먼저 업로드하세요")
            return
        if not selected_caption:
            st.error("❌ 문구를 입력하세요")
            return
        
        aligned_w = align_to_64(width)
        aligned_h = align_to_64(height)
        
        final_prompt = caption_to_prompt(selected_caption)
        if edit_prompt:
            final_prompt += f", {edit_prompt}"
        
        payload = {
            "input_image_base64": base64.b64encode(image_bytes).decode(),
            "prompt": final_prompt,
            "strength": strength,
            "width": aligned_w,
            "height": aligned_h,
            "steps": 30
        }
        
        try:
            with st.spinner("편집 중..."):
                edited = api.call_i2i(payload)
            
            if edited:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("원본")
                    st.image(image_bytes, use_container_width=True)
                with col2:
                    st.subheader("편집됨")
                    st.image(edited, use_container_width=True)
                
                st.success("✅ 완료!")
                st.download_button("⬇️ 편집 이미지 다운로드", edited, "edited.png", "image/png")
        except Exception as e:
            st.error(f"❌ 편집 실패: {e}")

# ============================================================
# 실행
# ============================================================
if __name__ == "__main__":
    main()
