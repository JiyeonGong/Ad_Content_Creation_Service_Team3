# frontend/pages/page_caption.py
import streamlit as st
from services.api_client import call_caption_api
from services.utils import validate_inputs, parse_output

def render(connect_mode: bool):
    st.title("📝 홍보 문구 & 해시태그 생성")
    
    with st.form("content_form"):
        service_type = st.selectbox(
            "서비스 종류",
            ["헬스장", "PT (개인 트레이닝)", "요가/필라테스", "건강 식품/보조제", "기타"]
        )
        location = st.text_input("지역", placeholder="예: 강남, 마포구, 온라인")
        service_name = st.text_input("제품/클래스 이름", placeholder="예: 30일 다이어트 챌린지")
        features = st.text_area("핵심 특징 및 장점", placeholder="예: 전문 PT와 함께하는 맞춤형 운동, 영양 관리 포함")
        tone = st.selectbox("톤 선택", ["친근하고 동기부여","전문적이고 신뢰감","재미있고 트렌디","차분하고 감성적"])
        submitted = st.form_submit_button("✨ 문구+해시태그 생성")

    if submitted:
        if validate_inputs(service_name, features, location):
            payload = {
                "service_type": service_type,
                "service_name": service_name,
                "features": features,
                "location": location,
                "tone": tone
            }
            with st.spinner("AI가 홍보 문구를 생성하는 중... ⏳"):
                output = call_caption_api(payload)
                captions, hashtags = parse_output(output)
                st.session_state["captions"] = captions
                st.session_state["hashtags"] = hashtags

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
        st.success(f"✅ 선택된 문구: {st.session_state['selected_caption'][:50]}...")
        st.markdown("### 🔖 추천 해시태그")
        st.code(st.session_state["hashtags"], language="")