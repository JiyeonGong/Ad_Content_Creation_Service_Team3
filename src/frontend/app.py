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
        self.timeout = config.get("api.timeout", 600)  # 10분으로 증가
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

    if page_id == "image_editing_experiment":
        # 4페이지: 이미지 편집 모델 선택
        st.sidebar.subheader("🎨 이미지 편집 모델")

        # 현재 로드된 ComfyUI 모델 상태 확인
        current_comfyui_model = api.get_current_comfyui_model()

        # 편집 모델 목록을 세션에 저장 (페이지 함수에서 사용)
        experiments_data = api.get_image_editing_experiments()
        if experiments_data and experiments_data.get("success"):
            st.session_state["editing_experiments"] = experiments_data.get("experiments", [])
            experiments = st.session_state["editing_experiments"]

            if experiments:
                # 편집 모델만 필터링 (생성 모델 제외: FLUX.1-dev-Q8, FLUX.1-dev-Q4)
                editing_models = [
                    exp for exp in experiments
                    if "bnb" not in exp["id"] and not exp["id"].startswith("FLUX.1-dev")
                ]

                # 실험 ID와 이름을 매핑
                exp_map = {exp["id"]: exp for exp in editing_models}
                exp_ids = ["none"] + [exp["id"] for exp in editing_models]
                exp_names = ["모델 없음"] + [f"{exp['name']}" for exp in editing_models]

                # 기본값 설정
                default_idx = 0
                if current_comfyui_model:
                    if current_comfyui_model in exp_ids:
                        default_idx = exp_ids.index(current_comfyui_model)

                selected_exp_name = st.sidebar.selectbox(
                    "편집 모델 선택",
                    exp_names,
                    index=default_idx,
                    help="배경 제거 후 사용할 이미지 편집 모델을 선택하세요. '모델 없음'을 선택하면 메모리를 비웁니다.",
                    key="editing_model_selector"
                )

                # 선택된 실험 객체 찾기
                selected_idx = exp_names.index(selected_exp_name)
                selected_exp_id = exp_ids[selected_idx]

                # "모델 없음" 선택 시 처리
                if selected_exp_id == "none":
                    st.session_state["selected_editing_experiment"] = None
                    if current_comfyui_model:
                        # 언로드 필요
                        with st.spinner("모델 언로드 중..."):
                            try:
                                res = api.unload_model_comfyui()
                                if res.get("success"):
                                    st.sidebar.success("모델이 꺼졌습니다.")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.sidebar.error(f"언로드 실패: {res.get('message')}")
                            except Exception as e:
                                st.sidebar.error(f"❌ {e}")
                    else:
                        st.sidebar.markdown(f"⚫ **OFF** (Unloaded)")
                else:
                    # 일반 모델 선택
                    selected_experiment = editing_models[selected_idx - 1]  # "모델 없음" 제외
                    st.session_state["selected_editing_experiment"] = selected_experiment

                    # 상태 표시 (선택한 모델이 실제로 로드되었는지 확인)
                    if current_comfyui_model == selected_exp_id:
                        st.sidebar.success(f"💡 **ON** (Loaded: {selected_experiment['name']})")
                    else:
                        st.sidebar.markdown(f"⚫ **OFF** (Unloaded)")

                    # 모델 정보 표시 (편집 모델인 경우에만)
                    if "background_removal_model" in selected_experiment:
                        st.sidebar.caption(f"📝 배경 제거: {selected_experiment['background_removal_model']}")
                    if "editing_model" in selected_experiment:
                        st.sidebar.caption(f"📝 편집: {selected_experiment['editing_model']}")

            else:
                st.sidebar.warning("사용 가능한 편집 모델이 없습니다.")
        else:
            st.sidebar.error("편집 모델 목록을 불러올 수 없습니다.")

    else:
        # 1,2,3 페이지: 이미지 생성 모델 선택
        st.sidebar.subheader("🤖 이미지 생성 모델")

        # 현재 로드된 ComfyUI 모델 상태 확인
        current_comfyui_model = api.get_current_comfyui_model()

        # ComfyUI experiments에서 생성 모델만 필터링
        experiments_data = api.get_image_editing_experiments()
        if experiments_data and experiments_data.get("success"):
            experiments = experiments_data.get("experiments", [])

            # 생성 모델만 필터링 (FLUX.1-dev-Q8, FLUX.1-dev-Q4)
            generation_models = [exp for exp in experiments if "FLUX.1-dev-Q" in exp["id"]]

            if generation_models:
                exp_map = {exp["id"]: exp for exp in generation_models}
                exp_ids = ["none"] + [exp["id"] for exp in generation_models]
                exp_names = ["모델 없음"] + [f"{exp['name']}" for exp in generation_models]

                # 기본값 설정
                default_idx = 0
                if current_comfyui_model and current_comfyui_model in exp_ids:
                    default_idx = exp_ids.index(current_comfyui_model)

                selected_exp_name = st.sidebar.selectbox(
                    "모델 선택",
                    exp_names,
                    index=default_idx,
                    help="이미지 생성에 사용할 모델을 선택하세요. '모델 없음'을 선택하면 메모리를 비웁니다.",
                    key="generation_model_selector"
                )

                # 선택된 실험 객체 찾기
                selected_idx = exp_names.index(selected_exp_name)
                selected_exp_id = exp_ids[selected_idx]

                # 세션에 선택된 모델 ID 저장 (페이지에서 사용)
                st.session_state["selected_generation_model_id"] = selected_exp_id

                # "모델 없음" 선택 시 처리
                if selected_exp_id == "none":
                    if current_comfyui_model:
                        # 언로드 필요
                        with st.spinner("모델 언로드 중..."):
                            try:
                                res = api.unload_model_comfyui()
                                if res.get("success"):
                                    st.sidebar.success("모델이 꺼졌습니다.")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.sidebar.error(f"언로드 실패: {res.get('message')}")
                            except Exception as e:
                                st.sidebar.error(f"❌ {e}")
                    else:
                        st.sidebar.markdown(f"⚫ **OFF** (Unloaded)")
                else:
                    # 일반 모델 선택
                    selected_experiment = generation_models[selected_idx - 1]  # "모델 없음" 제외

                    # 상태 표시 (선택한 모델이 실제로 로드되었는지 확인)
                    if current_comfyui_model == selected_exp_id:
                        st.sidebar.success(f"💡 **ON** (Loaded: {selected_experiment['name']})")
                    else:
                        st.sidebar.markdown(f"⚫ **OFF** (Unloaded)")

                    # 모델 정보 표시
                    st.sidebar.caption(f"📝 {selected_experiment.get('description', '')}")

            else:
                st.sidebar.warning("사용 가능한 생성 모델이 없습니다.")
        else:
            st.sidebar.error("모델 목록을 불러올 수 없습니다.")

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
    
    # 선택된 모델 ID 가져오기 (사이드바에서 선택한 모델)
    selected_model_id = st.session_state.get("selected_generation_model_id")

    # 현재 로드된 모델 확인
    current_model_name = api.get_current_comfyui_model()
    is_flux = (selected_model_id and "flux" in selected_model_id.lower()) or (current_model_name and "flux" in current_model_name.lower())

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

    # Steps & Guidance Scale (기본값 사용)
    default_steps = config.get("image.steps.default", 28)
    default_guidance = 3.5

    # 모델 선택 상태 표시
    if not selected_model_id or selected_model_id == "none":
        st.warning("⚠️ 사이드바에서 생성 모델을 먼저 선택하세요")
    else:
        display_model = current_model_name if current_model_name else selected_model_id
        st.info(f"ℹ️ 선택된 모델: **{display_model}** (권장 steps: {default_steps}, guidance: {default_guidance})")

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

    # 후처리 방식 선택
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
        help="후처리 없음: 가장 빠름\nImpact Pack: ComfyUI 기반 얼굴/손 보정"
    )

    # ADetailer 제거됨 (ComfyUI 사용으로 인해 비활성화)
    enable_adetailer = False
    adetailer_targets = None

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
                "guidance_scale": guidance_scale,
                "post_process_method": post_process_method,
                "enable_adetailer": enable_adetailer,
                "adetailer_targets": adetailer_targets,
                "model_name": selected_model_id  # 선택된 모델 전달
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

    # 선택된 모델 ID 가져오기 (사이드바에서 선택한 모델)
    selected_model_id = st.session_state.get("selected_generation_model_id")

    # 현재 로드된 모델 확인
    current_model_name = api.get_current_comfyui_model()
    is_flux = (selected_model_id and "flux" in selected_model_id.lower()) or (current_model_name and "flux" in current_model_name.lower())

    # 출력 크기 (입력 이미지가 이 크기로 리사이즈됨)
    preset_sizes = config.get("image.preset_sizes", [])

    # FLUX 모델 사용 시 권장 크기 표시
    size_options = []
    for s in preset_sizes:
        label = f"{s['name']} ({s['width']}x{s['height']})"
        if is_flux and s['width'] == 1024 and s['height'] == 1024:
            label += " ⭐ 권장"
        size_options.append(label)

    # 모델 선택 상태 표시
    if not selected_model_id or selected_model_id == "none":
        st.warning("⚠️ 사이드바에서 생성 모델을 먼저 선택하세요")

    selected_size = st.selectbox(
        "출력 크기",
        size_options,
        help="입력 이미지가 이 크기로 리사이즈된 후 편집됩니다"
    )

    size_idx = size_options.index(selected_size)
    width = preset_sizes[size_idx]["width"]
    height = preset_sizes[size_idx]["height"]

    # 후처리 방식 선택
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
        help="후처리 없음: 가장 빠름\nImpact Pack: ComfyUI 기반 얼굴/손 보정",
        key="i2i_post_process"
    )

    # ADetailer 제거됨 (ComfyUI 사용으로 인해 비활성화)
    enable_adetailer = False
    adetailer_targets = None

    # 처리 중 상태 확인
    is_processing = st.session_state.get("is_processing_i2i", False)

    # 버튼 표시 (처리 중이면 비활성화)
    if is_processing:
        st.warning("⏳ 이미지 편집 중입니다... 잠시만 기다려주세요.")
        submitted = False
    else:
        submitted = st.button("✨ 이미지 편집", type="primary", disabled=is_processing)
    
    if submitted:
        if not image_bytes:
            st.error("❌ 이미지를 먼저 업로드하세요")
            return
        if not selected_caption:
            st.error("❌ 문구를 입력하세요")
            return
        
        # 처리 시작 상태 설정
        st.session_state["is_processing_i2i"] = True
        st.rerun()

    # 실제 처리 로직 (rerun 후 실행됨)
    if is_processing and image_bytes and selected_caption:
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
            "steps": 30,
            "post_process_method": post_process_method,
            "enable_adetailer": enable_adetailer,
            "adetailer_targets": adetailer_targets,
            "model_name": selected_model_id  # 선택된 모델 전달
        }
        
        try:
            with st.spinner("편집 중..."):
                edited = api.call_i2i(payload)

            # 처리 완료 - 상태 해제
            st.session_state["is_processing_i2i"] = False

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
            # 에러 발생 시에도 상태 해제
            st.session_state["is_processing_i2i"] = False
            st.error(f"❌ 편집 실패: {e}")

# ============================================================
# 🆕 페이지 4: 이미지 편집
# ============================================================
def render_image_editing_experiment_page(config: ConfigLoader, api: APIClient):
    st.title("✂️ 이미지 편집")
    st.markdown("**배경 제거 및 이미지 편집**")

    # 세션에서 선택된 편집 모델 가져오기 (메인 함수의 사이드바에서 선택)
    if "selected_editing_experiment" not in st.session_state:
        st.warning("⚠️ 편집 모델을 선택해주세요.")
        return

    selected_experiment = st.session_state["selected_editing_experiment"]

    # None 체크 ("모델 없음" 선택 시)
    if selected_experiment is None:
        st.warning("⚠️ 편집 모델을 선택해주세요. 사이드바에서 '모델 없음'이 아닌 편집 모델을 선택하세요.")
        return

    # 모델 정보 표시
    st.info(f"**선택된 모델**: {selected_experiment['name']}\n\n{selected_experiment['description']}")

    # 1. 이미지 업로드
    st.subheader("1️⃣ 이미지 업로드")
    uploaded_file = st.file_uploader(
        "편집할 이미지 업로드",
        type=["png", "jpg", "jpeg", "webp"],
        help="배경을 제거하고 편집할 이미지를 업로드하세요"
    )

    if not uploaded_file:
        st.info("👆 이미지를 업로드하세요")
        return

    # 업로드된 이미지 표시
    image_bytes = uploaded_file.read()
    image = Image.open(BytesIO(image_bytes))

    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(image, caption="원본 이미지", use_container_width=True)
    with col2:
        st.markdown("**이미지 정보**")
        st.write(f"- 크기: {image.size[0]} x {image.size[1]}")
        st.write(f"- 포맷: {image.format}")
        st.write(f"- 모드: {image.mode}")

    # 2. 편집 프롬프트 및 설정
    st.subheader("2️⃣ 편집 설정")

    # 모델별 기능 선택 (YAML의 features 활용)
    features = selected_experiment.get("features", [])
    if features:
        st.markdown("**편집 유형 선택**")
        feature_names = [f"{f['name']} - {f['description']}" for f in features]
        selected_feature_idx = st.selectbox(
            "기능",
            range(len(features)),
            format_func=lambda x: feature_names[x],
            help="모델이 지원하는 편집 기능을 선택하세요"
        )
        selected_feature = features[selected_feature_idx]

        # 기능별 동적 UI 렌더링
        st.markdown(f"**{selected_feature['name']}**")
        st.caption(selected_feature['description'])

        # UI 요소 렌더링
        ui_elements = selected_feature.get("ui_elements", [])
        additional_params = {}

        for idx, ui_elem in enumerate(ui_elements):
            elem_type = ui_elem.get("type")
            label = ui_elem.get("label")

            if elem_type == "text_input":
                placeholder = ui_elem.get("placeholder", "")
                help_text = ""

                # 특정 레이블에 대한 설명 추가
                if "채울 내용" in label:
                    help_text = "배경 제거 후 채워질 내용을 설명하세요 (예: 현대적인 사무실, 자연 배경 등)"
                elif "확장 영역" in label:
                    help_text = "확장된 영역에 추가로 그려질 내용을 설명하세요 (예: 산 풍경 계속, 바다 배경 등)"

                additional_params[label] = st.text_input(
                    label,
                    placeholder=placeholder,
                    help=help_text,
                    key=f"ui_elem_{idx}"
                )

            elif elem_type == "select":
                options = ui_elem.get("options", [])
                additional_params[label] = st.selectbox(label, options, key=f"ui_elem_{idx}")

            elif elem_type == "mask_tool":
                st.info(f"💡 {label}: 배경이 자동으로 제거됩니다")

            elif elem_type == "expansion_direction":
                options = ui_elem.get("options", [])
                help_text = "이미지를 확장할 방향을 선택하세요 (여러 개 선택 가능)"
                additional_params[label] = st.multiselect(
                    label,
                    options,
                    help=help_text,
                    key=f"ui_elem_{idx}"
                )

    prompt = st.text_area(
        "메인 편집 프롬프트 (전체적인 스타일/분위기)",
        placeholder="예: modern office background, bright lighting, professional atmosphere, high quality",
        help="이미지 전체의 스타일, 분위기, 품질을 설명하세요. 위의 '채울 내용'과 함께 사용됩니다.",
        height=100,
        key="edit_prompt"
    )

    # 고급 설정
    with st.expander("⚙️ 고급 설정"):
        # 네거티브 프롬프트
        negative_prompt = st.text_area(
            "네거티브 프롬프트 (선택)",
            placeholder="예: blurry, low quality, distorted, ugly, bad anatomy",
            help="생성하지 않을 요소를 설명하세요. 비워두면 자동으로 positive 프롬프트와 동일하게 처리됩니다. FLUX 모델은 네거티브 프롬프트 효과가 제한적입니다.",
            height=80,
            key="negative_prompt"
        )

        st.divider()

        col1, col2, col3 = st.columns(3)

        exp_config = config.get("image.editing_experiment", {})

        with col1:
            steps_config = exp_config.get("steps", {})
            steps = st.slider(
                "추론 단계 (Steps)",
                min_value=steps_config.get("min", 10),
                max_value=steps_config.get("max", 50),
                value=steps_config.get("default", 28),
                help="높을수록 품질 향상, 시간 증가"
            )

        with col2:
            guidance_config = exp_config.get("guidance_scale", {})
            guidance_scale = st.slider(
                "Guidance Scale",
                min_value=guidance_config.get("min", 1.0),
                max_value=guidance_config.get("max", 15.0),
                value=guidance_config.get("default", 3.5),
                step=guidance_config.get("step", 0.5),
                help="프롬프트 준수 강도"
            )

        with col3:
            strength_config = exp_config.get("strength", {})
            strength = st.slider(
                "변화 강도 (Strength)",
                min_value=strength_config.get("min", 0.0),
                max_value=strength_config.get("max", 1.0),
                value=strength_config.get("default", 0.8),
                step=strength_config.get("step", 0.05),
                help="원본 대비 변화 정도"
            )

    # 3. 실행
    st.subheader("3️⃣ 편집 실행")

    # 버튼 비활성화 처리를 위한 세션 상태
    if "editing_in_progress" not in st.session_state:
        st.session_state["editing_in_progress"] = False

    if "editing_request" not in st.session_state:
        st.session_state["editing_request"] = None

    # 편집 버튼 (진행 중일 때 비활성화)
    button_disabled = st.session_state["editing_in_progress"]

    if st.button("🎨 편집 시작", type="primary", use_container_width=True, disabled=button_disabled):
        # 프롬프트 체크
        if not prompt.strip():
            st.warning("⚠️ 메인 편집 프롬프트를 입력하세요")
            st.stop()

        # 편집 요청 저장
        st.session_state["editing_request"] = {
            "experiment_id": selected_experiment["id"],
            "input_image_base64": base64.b64encode(image_bytes).decode("utf-8"),
            "prompt": prompt,
            "negative_prompt": negative_prompt if negative_prompt.strip() else "",
            "steps": steps,
            "guidance_scale": guidance_scale,
            "strength": strength
        }
        st.session_state["editing_in_progress"] = True
        st.rerun()

    # 편집 요청이 있으면 실행
    if st.session_state["editing_in_progress"] and st.session_state["editing_request"]:
        payload = st.session_state["editing_request"]

        try:
            with st.spinner("이미지 편집 중... (배경 제거 + 편집 적용)"):
                result = api.edit_with_comfyui(payload)

            # 편집 완료 - 버튼 다시 활성화 및 요청 초기화
            st.session_state["editing_in_progress"] = False
            st.session_state["editing_request"] = None

            if result and result.get("success"):
                st.success(f"✅ 편집 완료! (소요 시간: {result.get('elapsed_time', 0):.1f}초)")

                # 4. 결과 표시
                st.subheader("4️⃣ 결과")

                # 배경 제거 이미지 (있는 경우)
                if result.get("background_removed_image_base64"):
                    bg_removed_bytes = base64.b64decode(result["background_removed_image_base64"])
                    bg_removed_image = Image.open(BytesIO(bg_removed_bytes))

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("**원본**")
                        st.image(image, use_container_width=True)
                    with col2:
                        st.markdown("**배경 제거**")
                        st.image(bg_removed_image, use_container_width=True)
                    with col3:
                        st.markdown("**편집 결과**")
                        output_bytes = base64.b64decode(result["output_image_base64"])
                        output_image = Image.open(BytesIO(output_bytes))
                        st.image(output_image, use_container_width=True)

                    # 다운로드 버튼
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            "⬇️ 배경 제거 이미지 다운로드",
                            BytesIO(bg_removed_bytes).getvalue(),
                            f"background_removed_{selected_experiment['id']}.png",
                            "image/png",
                            use_container_width=True
                        )
                    with col2:
                        st.download_button(
                            "⬇️ 편집 결과 다운로드",
                            BytesIO(output_bytes).getvalue(),
                            f"edited_{selected_experiment['id']}.png",
                            "image/png",
                            use_container_width=True
                        )

                else:
                    # 배경 제거 이미지 없이 최종 결과만
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**원본**")
                        st.image(image, use_container_width=True)
                    with col2:
                        st.markdown("**편집 결과**")
                        output_bytes = base64.b64decode(result["output_image_base64"])
                        output_image = Image.open(BytesIO(output_bytes))
                        st.image(output_image, use_container_width=True)

                    # 다운로드 버튼
                    st.download_button(
                        "⬇️ 편집 결과 다운로드",
                        BytesIO(output_bytes).getvalue(),
                        f"edited_{selected_experiment['id']}.png",
                        "image/png",
                        use_container_width=True
                    )

            else:
                # 편집 실패 - 버튼 다시 활성화 및 요청 초기화
                st.session_state["editing_in_progress"] = False
                st.session_state["editing_request"] = None
                error_msg = result.get("error", "알 수 없는 오류") if result else "응답 없음"
                st.error(f"❌ 편집 실패: {error_msg}")

        except Exception as e:
            # 예외 발생 시에도 버튼 다시 활성화 및 요청 초기화
            st.session_state["editing_in_progress"] = False
            st.session_state["editing_request"] = None
            st.error(f"❌ 오류 발생: {e}")

# ============================================================
# 실행
# ============================================================
if __name__ == "__main__":
    main()
