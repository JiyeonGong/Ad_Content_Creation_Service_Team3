# Streamlit App 실행 (메인 화면)

import streamlit as st
# 같은 src/frontend 폴더 내에 있으므로 바로 import 가능하지만,
# 실행 위치에 따라 달라질 수 있어 절대 경로 방식이나 sys.path 추가가 필요할 수 있음.
# 가장 안전한 방법:
try:
    from api_client import request_ad_generation
except ImportError:
    from src.frontend.api_client import request_ad_generation

# 페이지 설정
st.set_page_config(page_title="트레이너 광고 제작소", layout="wide")

st.title("💪 트레이너를 위한 AI 광고 제작소")
st.markdown("사진 한 장만 올리세요. **분석부터 카피라이팅까지** AI가 해결해 드립니다.")

# --- Sidebar: 입력 폼 ---
with st.sidebar:
    st.header("Step 1. 정보 입력")
    uploaded_file = st.file_uploader("트레이너/회원 사진 업로드", type=["jpg", "png", "jpeg"])
    
    target_input = st.text_input("타겟 고객", value="30대 판교 직장인")
    purpose_input = st.text_input("광고 목적", value="여름 대비 PT 할인 이벤트")
    
    generate_btn = st.button("광고 생성하기 ✨", type="primary")

# --- Main: 결과 화면 ---
if generate_btn:
    if uploaded_file is None:
        st.error("사진을 업로드해주세요!")
    else:
        with st.spinner("AI가 사진을 분석하고 배경을 생성 중입니다... (약 30초 소요)"):
            # 백엔드 호출
            result = request_ad_generation(uploaded_file, target_input, purpose_input)
        
        if "error" in result:
            st.error(result["error"])
        else:
            # 결과 세션에 저장 (새로고침 시 유지용)
            st.session_state['result'] = result

# 저장된 결과가 있으면 표시
if 'result' in st.session_state:
    res = st.session_state['result']
    
    st.divider()
    
    # Step 2: 분석 결과
    st.subheader("Step 2. AI 전문가 분석")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(uploaded_file, caption="원본 사진", use_container_width=True)
    with col2:
        st.info(f"🔍 **자세 분석:** {res['analysis']['pose_analysis']}")
        st.success(f"💡 **마케팅 소구점:** {res['analysis']['expert_comment']}")

    st.divider()
    
    # Step 3: 생성된 콘텐츠
    st.subheader("Step 3. 맞춤형 콘텐츠 제안")
    
    tabs = st.tabs([c['option_name'] for c in res['contents']])
    
    for i, tab in enumerate(tabs):
        content = res['contents'][i]
        with tab:
            c1, c2 = st.columns([1, 1])
            with c1:
                # 실제 구현 시에는 생성된 이미지 URL이 들어갑니다.
                st.image(content['image_url'], caption="생성된 이미지 예시")
            with c2:
                st.text_area("광고 카피", value=content['copy_text'], height=150)
                st.button(f"다운로드 ({content['option_name']})", key=f"btn_{i}")

    st.divider()
   
    # Step 4: 가이드
    st.subheader("Step 4. 업로드 꿀팁")
    st.write(f"**추천 해시태그:** {' '.join(res['hashtags'])}")
    st.write(f"**추천 시간:** {res['upload_guide']}")