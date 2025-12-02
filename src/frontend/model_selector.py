"""
모델 선택 UI 컴포넌트
"""
import streamlit as st
import time
from typing import Optional, Dict, List


class ModelSelector:
    """모델 선택 UI 컴포넌트 - 복잡한 모델 선택 로직을 캡슐화"""
    
    def __init__(self, api_client):
        """
        Args:
            api_client: APIClient 인스턴스
        """
        self.api = api_client
    
    def render_editing_mode_selector(self) -> str:
        """편집 모드 선택 UI 렌더링
        
        Returns:
            선택된 모드 ID (예: "portrait_mode")
        """
        st.sidebar.subheader("✨ 편집 모드 선택")
        
        # 편집 모드 정의
        EDITING_MODES = {
            "portrait_mode": {"id": "portrait_mode", "name": "👤 인물 모드", "icon": "👤"},
            "product_mode": {"id": "product_mode", "name": "📦 제품 모드", "icon": "📦"},
            "hybrid_mode": {"id": "hybrid_mode", "name": "✨ 고급 모드", "icon": "✨"},
            "flux_fill_mode": {"id": "flux_fill_mode", "name": "🖌️ 인페인팅 모드", "icon": "🖌️"},
            "qwen_edit_mode": {"id": "qwen_edit_mode", "name": "🎯 정밀 편집 모드", "icon": "🎯"}
        }
        
        mode_ids = list(EDITING_MODES.keys())
        mode_names = [EDITING_MODES[m]["name"] for m in mode_ids]
        
        # 기본값 결정
        default_idx = self._get_default_editing_mode_index(mode_ids)
        
        # UI 렌더링
        selected_mode_name = st.sidebar.selectbox(
            "편집 모드",
            mode_names,
            index=default_idx,
            help="원하는 편집 모드를 선택하세요",
            key="editing_mode_selector"
        )
        
        selected_idx = mode_names.index(selected_mode_name)
        selected_mode_id = mode_ids[selected_idx]
        
        # 세션에 저장
        st.session_state["selected_editing_mode"] = selected_mode_id
        
        # 모드 설명
        mode_descriptions = {
            "portrait_mode": "얼굴은 보존하고, 의상과 배경만 변경",
            "product_mode": "제품은 보존하고, 배경을 창의적으로 변경",
            "hybrid_mode": "얼굴과 제품을 동시에 보존",
            "flux_fill_mode": "마스크 영역을 새로운 내용으로 채우거나 이미지 확장 (FLUX.1-Fill)",
            "qwen_edit_mode": "자연어 명령으로 정밀하게 이미지 편집 (Qwen-Image-Edit)"
        }
        st.sidebar.info(mode_descriptions[selected_mode_id])
        
        return selected_mode_id
    
    def render_generation_model_selector(self) -> Optional[str]:
        """이미지 생성 모델 선택 UI 렌더링
        
        Returns:
            선택된 모델 ID (예: "FLUX.1-dev-Q8") 또는 None
        """
        st.sidebar.subheader("🤖 이미지 생성 모델")
        
        # 현재 로드된 모델 확인
        current_model = self.api.get_current_comfyui_model()
        
        # 사용 가능한 모델 목록 가져오기
        generation_models = self._get_available_generation_models()
        
        if not generation_models:
            st.sidebar.warning("사용 가능한 생성 모델이 없습니다.")
            return None
        
        # 모델 선택 UI
        exp_ids = ["none"] + [exp["id"] for exp in generation_models]
        exp_names = ["모델 없음"] + [exp["name"] for exp in generation_models]
        
        # 기본값 결정
        default_idx = self._get_default_model_index(exp_ids, current_model)
        
        # UI 렌더링
        selected_exp_name = st.sidebar.selectbox(
            "모델 선택",
            exp_names,
            index=default_idx,
            help="이미지 생성에 사용할 모델을 선택하세요. '모델 없음'을 선택하면 메모리를 비웁니다.",
            key="generation_model_selector"
        )
        
        selected_idx = exp_names.index(selected_exp_name)
        selected_exp_id = exp_ids[selected_idx]
        
        # 세션에 저장
        st.session_state["selected_generation_model_id"] = selected_exp_id
        
        # 모델 상태 처리
        self._handle_model_selection(
            selected_exp_id, 
            current_model, 
            generation_models[selected_idx - 1] if selected_idx > 0 else None
        )
        
        return selected_exp_id if selected_exp_id != "none" else None
    
    def _get_available_generation_models(self) -> List[Dict]:
        """사용 가능한 생성 모델 목록 가져오기
        
        Returns:
            생성 모델 리스트
        """
        try:
            experiments_data = self.api.get_image_editing_experiments()
            if not experiments_data or not experiments_data.get("success"):
                return []
            
            experiments = experiments_data.get("experiments", [])
            # FLUX 생성 모델만 필터링
            return [exp for exp in experiments if "FLUX.1-dev-Q" in exp["id"]]
        except Exception as e:
            st.sidebar.error(f"모델 목록 조회 실패: {e}")
            return []
    
    def _get_default_editing_mode_index(self, mode_ids: List[str]) -> int:
        """편집 모드 기본 인덱스 결정
        
        Args:
            mode_ids: 모드 ID 리스트
            
        Returns:
            기본 인덱스
        """
        if "selected_editing_mode" in st.session_state:
            saved_mode = st.session_state["selected_editing_mode"]
            if saved_mode in mode_ids:
                return mode_ids.index(saved_mode)
        return 0
    
    def _get_default_model_index(self, exp_ids: List[str], current_model: Optional[str]) -> int:
        """생성 모델 기본 인덱스 결정
        
        Args:
            exp_ids: 모델 ID 리스트 (["none"] 포함)
            current_model: 현재 로드된 모델
            
        Returns:
            기본 인덱스
        """
        # 세션에 저장된 값 우선
        if "selected_generation_model_id" in st.session_state:
            saved_model = st.session_state["selected_generation_model_id"]
            if saved_model in exp_ids:
                return exp_ids.index(saved_model)
        
        # 현재 로드된 모델이 있으면 해당 모델 선택
        if current_model and current_model in exp_ids:
            return exp_ids.index(current_model)
        
        return 0
    
    def _handle_model_selection(
        self, 
        selected_id: str, 
        current_model: Optional[str],
        selected_experiment: Optional[Dict]
    ):
        """모델 선택에 따른 처리 및 상태 표시
        
        Args:
            selected_id: 선택된 모델 ID
            current_model: 현재 로드된 모델
            selected_experiment: 선택된 실험 객체
        """
        if selected_id == "none":
            # "모델 없음" 선택 시
            if current_model:
                with st.spinner("모델 언로드 중..."):
                    try:
                        res = self.api.unload_model_comfyui()
                        if res.get("success"):
                            st.sidebar.success("모델이 꺼졌습니다.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.sidebar.error(f"언로드 실패: {res.get('message')}")
                    except Exception as e:
                        st.sidebar.error(f"❌ {e}")
            else:
                st.sidebar.markdown("⚫ **OFF** (Unloaded)")
        else:
            # 일반 모델 선택
            if selected_experiment:
                # 상태 표시
                if current_model == selected_id:
                    st.sidebar.success(f"💡 **ON** (Loaded: {selected_experiment['name']})")
                else:
                    st.sidebar.markdown("⚫ **OFF** (Unloaded)")
                
                # 모델 정보 표시
                description = selected_experiment.get('description', '')
                if description:
                    st.sidebar.caption(f"📝 {description}")
