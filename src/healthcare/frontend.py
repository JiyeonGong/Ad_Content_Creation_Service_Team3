# C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\healthcare\frontend.py

#========================================
# 프론트엔드/벡엔드 분리 버전
#========================================

import streamlit as st
import requests
from io import BytesIO
from PIL import Image

BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="💪 헬스케어 AI 콘텐츠 제작", layout="wide")
st.sidebar.title("메뉴")
menu = st.sidebar.radio("페이지 선택", ["📝 문구 생성", "🖼 이미지 생성", "🖼️ 이미지 편집"])

# 연결 모드 토글
connect_mode = st.sidebar.checkbox("🔗 페이지 연결 모드", value=True)
st.sidebar.info("연결 모드 ON: 페이지1에서 생성된 문구/페이지2 이미지 사용\nOFF: 각 페이지 독립 사용")

# ========================
# 페이지 1: 문구 생성
# ========================
if menu == "📝 문구 생성":
    st.title("📝 홍보 문구 & 해시태그 생성")
    service_name = st.text_input("제품/클래스 이름")
    features = st.text_area("핵심 특징")
    tone = st.selectbox("톤", ["친근하고 동기부여","전문적이고 신뢰감","재미있고 트렌디","차분하고 감성적"])
    
    if st.button("생성"):
        resp = requests.post(f"{BACKEND_URL}/generate_captions", data={
            "service_name": service_name,
            "features": features,
            "tone": tone
        }).json()
        if "error" in resp:
            st.error(resp["error"])
        else:
            st.session_state["captions"] = resp["captions"]
            st.session_state["hashtags"] = resp["hashtags"]
            st.write("💬 생성된 문구:")
            for c in resp["captions"]:
                st.write(c)
            st.write("🔖 해시태그:")
            st.code(resp["hashtags"])

# ========================
# 페이지 2: 이미지 생성
# ========================
elif menu == "🖼 이미지 생성":
    st.title("🖼 문구 기반 이미지 생성")
    
    if connect_mode and "captions" in st.session_state:
        selected_caption = st.selectbox("문구 선택", st.session_state["captions"])
    else:
        selected_caption = st.text_area("문구 입력", placeholder="문구를 입력하세요")
    
    size = st.selectbox("이미지 크기", ["1024x1024","1792x1024"])
    
    if st.button("3버전 생성") and selected_caption:
        width, height = map(int, size.split("x"))
        st.session_state["generated_images"] = []
        for i in range(3):
            prompt = f"{selected_caption} (variation {i+1}), Instagram banner, vibrant, professional"
            resp = requests.post(f"{BACKEND_URL}/generate_image", data={
                "prompt": prompt,
                "width": width,
                "height": height
            }).json()
            image_bytes = resp["image_bytes"]
            st.session_state["generated_images"].append(image_bytes)
            st.image(BytesIO(image_bytes), caption=f"버전 {i+1}")

# ========================
# 페이지 3: 이미지 편집
# ========================
elif menu == "🖼️ 이미지 편집":
    st.title("🖼️ 이미지 편집 / 합성")
    
    uploaded_file = st.file_uploader("이미지 업로드", type=["png","jpg","jpeg"])
    
    if connect_mode and "generated_images" in st.session_state and not uploaded_file:
        img_options = [f"버전 {i+1}" for i in range(len(st.session_state["generated_images"]))]
        selected_idx = st.selectbox("페이지2 이미지 선택", range(len(img_options)), format_func=lambda x: img_options[x])
        selected_image_bytes = st.session_state["generated_images"][selected_idx]
        st.image(BytesIO(selected_image_bytes), caption=f"선택된 이미지: {img_options[selected_idx]}")
    else:
        selected_image_bytes = uploaded_file.read() if uploaded_file else None
    
    prompt = st.text_area("편집 문구")
    strength = st.slider("변화 강도", 0.0, 1.0, 0.75, 0.05)
    size = st.selectbox("이미지 크기", ["1024x1024","1792x1024"])
    
    if st.button("편집 이미지 생성") and selected_image_bytes and prompt:
        width, height = map(int, size.split("x"))
        files = {"image": ("image.png", selected_image_bytes, "image/png")}
        data = {"prompt": prompt, "strength": strength, "width": width, "height": height}
        resp = requests.post(f"{BACKEND_URL}/edit_image", files=files, data=data).json()
        st.image(BytesIO(resp["image_bytes"]), caption="편집 이미지 결과")