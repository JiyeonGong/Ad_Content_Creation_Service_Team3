# C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\healthcare\frontend.py

#========================================
# 프론트엔드/벡엔드 분리 버전
#========================================

# import streamlit as st
# import requests
# from io import BytesIO
# from PIL import Image

# BACKEND_URL = "http://localhost:8000"

# st.set_page_config(page_title="💪 헬스케어 AI 콘텐츠 제작", layout="wide")
# st.sidebar.title("메뉴")
# menu = st.sidebar.radio("페이지 선택", ["📝 문구 생성", "🖼 이미지 생성", "🖼️ 이미지 편집"])

# # 연결 모드 토글
# connect_mode = st.sidebar.checkbox("🔗 페이지 연결 모드", value=True)
# st.sidebar.info("연결 모드 ON: 페이지1에서 생성된 문구/페이지2 이미지 사용\nOFF: 각 페이지 독립 사용")

# # ========================
# # 페이지 1: 문구 생성
# # ========================
# if menu == "📝 문구 생성":
#     st.title("📝 홍보 문구 & 해시태그 생성")
#     service_name = st.text_input("제품/클래스 이름")
#     features = st.text_area("핵심 특징")
#     tone = st.selectbox("톤", ["친근하고 동기부여","전문적이고 신뢰감","재미있고 트렌디","차분하고 감성적"])
    
#     if st.button("생성"):
#         resp = requests.post(f"{BACKEND_URL}/generate_captions", data={
#             "service_name": service_name,
#             "features": features,
#             "tone": tone
#         }).json()
#         if "error" in resp:
#             st.error(resp["error"])
#         else:
#             st.session_state["captions"] = resp["captions"]
#             st.session_state["hashtags"] = resp["hashtags"]
#             st.write("💬 생성된 문구:")
#             for c in resp["captions"]:
#                 st.write(c)
#             st.write("🔖 해시태그:")
#             st.code(resp["hashtags"])

# # ========================
# # 페이지 2: 이미지 생성
# # ========================
# elif menu == "🖼 이미지 생성":
#     st.title("🖼 문구 기반 이미지 생성")
    
#     if connect_mode and "captions" in st.session_state:
#         selected_caption = st.selectbox("문구 선택", st.session_state["captions"])
#     else:
#         selected_caption = st.text_area("문구 입력", placeholder="문구를 입력하세요")
    
#     size = st.selectbox("이미지 크기", ["1024x1024","1792x1024"])
    
#     if st.button("3버전 생성") and selected_caption:
#         width, height = map(int, size.split("x"))
#         st.session_state["generated_images"] = []
#         for i in range(3):
#             prompt = f"{selected_caption} (variation {i+1}), Instagram banner, vibrant, professional"
#             resp = requests.post(f"{BACKEND_URL}/generate_image", data={
#                 "prompt": prompt,
#                 "width": width,
#                 "height": height
#             }).json()
#             image_bytes = resp["image_bytes"]
#             st.session_state["generated_images"].append(image_bytes)
#             st.image(BytesIO(image_bytes), caption=f"버전 {i+1}")

# # ========================
# # 페이지 3: 이미지 편집
# # ========================
# elif menu == "🖼️ 이미지 편집":
#     st.title("🖼️ 이미지 편집 / 합성")
    
#     uploaded_file = st.file_uploader("이미지 업로드", type=["png","jpg","jpeg"])
    
#     if connect_mode and "generated_images" in st.session_state and not uploaded_file:
#         img_options = [f"버전 {i+1}" for i in range(len(st.session_state["generated_images"]))]
#         selected_idx = st.selectbox("페이지2 이미지 선택", range(len(img_options)), format_func=lambda x: img_options[x])
#         selected_image_bytes = st.session_state["generated_images"][selected_idx]
#         st.image(BytesIO(selected_image_bytes), caption=f"선택된 이미지: {img_options[selected_idx]}")
#     else:
#         selected_image_bytes = uploaded_file.read() if uploaded_file else None
    
#     prompt = st.text_area("편집 문구")
#     strength = st.slider("변화 강도", 0.0, 1.0, 0.75, 0.05)
#     size = st.selectbox("이미지 크기", ["1024x1024","1792x1024"])
    
#     if st.button("편집 이미지 생성") and selected_image_bytes and prompt:
#         width, height = map(int, size.split("x"))
#         files = {"image": ("image.png", selected_image_bytes, "image/png")}
#         data = {"prompt": prompt, "strength": strength, "width": width, "height": height}
#         resp = requests.post(f"{BACKEND_URL}/edit_image", files=files, data=data).json()
#         st.image(BytesIO(resp["image_bytes"]), caption="편집 이미지 결과")









# C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\healthcare\frontend.py

#========================================
# 프론트엔드/벡엔드 분리 버전 + streamlit.py 개선 사항 반영
#========================================

import streamlit as st
from backend import (
    openai_client, MODEL_GPT_MINI,
    generate_caption_and_hashtags, caption_to_image_prompt,
    init_local_sdxl_t2i, init_local_sdxl_i2i,
    generate_image_local, generate_image_i2i_local
)

st.set_page_config(page_title="💪 헬스케어 AI 콘텐츠 제작", layout="wide")

# ------------------- 사이드바 메뉴 -------------------
menu = st.sidebar.radio(
    "페이지 선택",
    ["📝 홍보 문구+해시태그 생성", "🖼 인스타그램 이미지 생성", "🖼️ 이미지 편집/합성"]
)
connect_mode = st.sidebar.checkbox("🔗 페이지 연결 모드", value=True)

# ------------------- 페이지 1: 문구 + 해시태그 -------------------
if menu == "📝 홍보 문구+해시태그 생성":
    st.title("📝 홍보 문구 & 해시태그 생성")

    if not openai_client:
        st.error("❌ OpenAI API 키가 설정되지 않아 이 기능을 사용할 수 없습니다.")
    else:
        with st.form("content_form"):
            service_type = st.selectbox("서비스 종류", ["헬스장","PT","요가/필라테스","건강식품/보조제","기타"])
            location = st.text_input("지역", placeholder="예: 강남, 마포구, 온라인")
            service_name = st.text_input("제품/클래스 이름", placeholder="예: 30일 다이어트 챌린지")
            features = st.text_area("핵심 특징 및 장점", placeholder="예: 전문 PT와 함께하는 맞춤형 운동, 영양 관리 포함")
            tone = st.selectbox("톤 선택", ["친근하고 동기부여","전문적이고 신뢰감","재미있고 트렌디","차분하고 감성적"])
            submitted = st.form_submit_button("✨ 문구+해시태그 생성")

        if submitted and service_name and features and location:
            info = {
                "service_type": service_type,
                "service_name": service_name,
                "features": features,
                "location": location,
                "event_info": "없음"
            }
            output = generate_caption_and_hashtags(openai_client, MODEL_GPT_MINI, tone, info, 15)
            st.text_area("생성된 문구 & 해시태그", value=output, height=300)
        else:
            st.warning("서비스 종류, 이름, 특징, 지역을 모두 입력해주세요.")

# ------------------- 페이지 2: 이미지 생성 -------------------
elif menu == "🖼 인스타그램 이미지 생성":
    st.title("🖼 문구 기반 이미지 생성 (3가지 버전)")
    pipe_t2i = init_local_sdxl_t2i()

    if connect_mode and "selected_caption" in st.session_state:
        selected_caption = st.session_state["selected_caption"]
        st.info(f"🔗 연결 모드: 페이지1 문구 사용\n**선택된 문구:** {selected_caption}")
    else:
        selected_caption = st.text_area("문구 입력", placeholder="예: 💪 새해 목표, 이번엔 꼭 이루자!")

    image_size = st.selectbox("이미지 크기", ["1024x1024","1792x1024","1024x1792"])
    submitted = st.button("🖼 3가지 버전 생성")

    if submitted and selected_caption:
        width, height = map(int, image_size.split("x"))
        st.session_state["generated_images"] = []
        for i in range(3):
            prompt = caption_to_image_prompt(f"{selected_caption} (style variation {i+1})")
            img_bytes = generate_image_local(pipe_t2i, prompt, width, height)
            st.session_state["generated_images"].append(img_bytes)
            st.image(img_bytes, caption=f"버전 {i+1}")

# ------------------- 페이지 3: 이미지 편집/합성 -------------------
elif menu == "🖼️ 이미지 편집/합성":
    st.title("🖼️ 이미지 편집 / 합성")
    pipe_i2i = init_local_sdxl_i2i()

    uploaded_file = st.file_uploader("업로드 이미지", type=["png","jpg","jpeg"])
    if uploaded_file:
        image_bytes = uploaded_file.getvalue()
        st.image(image_bytes, caption="업로드 이미지", width=300)
    elif connect_mode and "generated_images" in st.session_state:
        image_idx = st.selectbox("사용할 이미지 선택", range(len(st.session_state["generated_images"])), format_func=lambda x: f"버전 {x+1}")
        image_bytes = st.session_state["generated_images"][image_idx]
        st.image(image_bytes, caption=f"선택된 이미지: 버전 {image_idx+1}", width=300)
    else:
        st.warning("이미지를 업로드하거나 페이지2에서 생성하세요.")
        image_bytes = None

    selected_caption = st.text_input("편집에 반영할 문구 입력", placeholder="예: 💪 새해 목표, 이번엔 꼭 이루자!")
    denoising_strength = st.slider("변화 강도", 0.0, 1.0, 0.75, 0.05)
    output_size = st.selectbox("출력 이미지 크기", ["1024x1024","1792x1024","1024x1792"])
    edit_prompt = st.text_area("추가 편집 지시 (선택)", placeholder="예: 밝고 활기찬 분위기, 파란 배경")

    submitted = st.button("✨ 합성/편집 이미지 생성")
    if submitted and image_bytes and selected_caption:
        width, height = map(int, output_size.split("x"))
        final_prompt = caption_to_image_prompt(selected_caption)
        if edit_prompt:
            final_prompt += f", {edit_prompt}"
        edited_bytes = generate_image_i2i_local(pipe_i2i, image_bytes, final_prompt, denoising_strength, width, height)
        col1, col2 = st.columns(2)
        with col1: st.image(image_bytes, caption="원본 이미지")
        with col2: st.image(edited_bytes, caption="편집된 이미지")
        st.download_button("⬇️ 다운로드", edited_bytes, "edited_image.png", "image/png")