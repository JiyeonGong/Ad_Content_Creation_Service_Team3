# frontend/pages/page_i2i.py
import streamlit as st
import base64
from services.api_client import call_i2i_api
from services.utils import caption_to_image_prompt, align64

def render(connect_mode: bool):
    st.title("🖼️ 이미지 편집 / 합성 (Image-to-Image)")

    uploaded_file = st.file_uploader("업로드 이미지", type=["png","jpg","jpeg"])
    preloaded_images = st.session_state.get("generated_images", [])

    image_bytes = None
    if uploaded_file:
        image_bytes = uploaded_file.getvalue()
    elif preloaded_images and connect_mode:
        st.info("🔗 연결 모드: 페이지2에서 생성된 이미지 사용")
        idx = st.selectbox("사용할 이미지 선택", range(len(preloaded_images)), format_func=lambda x: f"버전 {x+1}")
        image_bytes = preloaded_images[idx]["bytes"].getvalue() 

    if image_bytes:
        st.image(image_bytes, caption="선택된 이미지", width=300)
    else:
        st.warning("⚠️ 이미지를 업로드하거나 페이지2에서 생성하세요.")

    selected_caption = ""
    if connect_mode and "selected_caption" in st.session_state:
        st.info(f"🔗 사용할 문구: {st.session_state['selected_caption']}")
        selected_caption = st.session_state["selected_caption"]
    else:
        selected_caption = st.text_input("편집에 반영할 문구 입력", placeholder="예: 💪 새해 목표!")

    denoising_strength = st.slider("✨ 변화 강도 (Strength)", 0.0, 1.0, 0.75, 0.05)
    edit_prompt = st.text_area("추가 편집 지시 (선택)", placeholder="예: 더 밝고 활기찬 분위기로, 파란색 배경 추가")
    output_size = st.selectbox("출력 이미지 크기", ["1080x1350","1080x1080","1080x556","1024x1024"])
    submitted = st.button("✨ 합성/편집 이미지 생성", type="primary")

    if submitted:
        if not image_bytes or not selected_caption:
            st.error("❌ 이미지와 문구를 모두 선택/입력하세요.")
            return

        width, height = map(int, output_size.split('x'))
        aligned_w, aligned_h = align64(width), align64(height)
        final_prompt = caption_to_image_prompt(selected_caption)
        if edit_prompt:
            final_prompt += f", {edit_prompt}"

        payload = {
            "input_image_base64": base64.b64encode(image_bytes).decode('utf-8'),
            "prompt": final_prompt,
            "strength": denoising_strength,
            "width": aligned_w,
            "height": aligned_h,
            "steps": 30
        }

        try:
            result_img = call_i2i_api(payload)
            if result_img:
                col1, col2 = st.columns(2)
                with col1: st.subheader("원본 이미지"); st.image(image_bytes, use_container_width=True)
                with col2: st.subheader("편집된 이미지"); st.image(result_img, caption="I2I 결과", use_container_width=True)
                st.download_button("⬇️ 편집 이미지 다운로드", result_img, "edited_image.png", "image/png")
                st.success("✅ 이미지 생성 완료!")
            else:
                st.error("❌ 편집/합성 실패: API에서 이미지가 반환되지 않음")
        except Exception as e:
            st.error(f"❌ 편집/합성 실패: {str(e)}")