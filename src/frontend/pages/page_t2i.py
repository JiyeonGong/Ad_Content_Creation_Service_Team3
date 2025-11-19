# frontend/pages/page_t2i.py
import streamlit as st
from services.api_client import call_t2i_api
from services.utils import caption_to_image_prompt, align64

def render(connect_mode: bool):
    st.title("🖼 문구 기반 이미지 생성 (3가지 버전)")
    
    selected_caption = ""
    if connect_mode and "selected_caption" in st.session_state:
        st.info(f"🔗 연결 모드: 페이지1 문구 사용\n\n**선택된 문구:** {st.session_state['selected_caption']}")
        selected_caption = st.session_state["selected_caption"]
    else:
        if connect_mode:
            st.warning("⚠️ 페이지1에서 문구를 먼저 생성하고 선택하세요.")
        selected_caption = st.text_area("문구 입력", placeholder="예: 💪 새해 목표!")

    image_size = st.selectbox("이미지 크기", ["1080x1350","1080x1080","1080x556","1024x1024"])
    inference_steps = st.slider("추론 단계 (Steps)", 1, 50, 10)

    submitted = st.button("🖼 3가지 버전 생성", type="primary")

    if submitted and selected_caption:
        width, height = map(int, image_size.split("x"))
        aligned_w, aligned_h = align64(width), align64(height)
        st.session_state["generated_images"] = []
        progress_bar = st.progress(0)

        for i in range(3):
            prompt = caption_to_image_prompt(f"{selected_caption} (style variation {i+1})")
            payload = {"prompt": prompt, "width": aligned_w, "height": aligned_h, "steps": inference_steps}
            
            try:
                img_bytes = call_t2i_api(payload)
                if img_bytes:
                    st.session_state["generated_images"].append({"prompt": prompt, "bytes": img_bytes})
                    progress_bar.progress((i+1)/3)
                else:
                    st.error(f"❌ 이미지 생성 실패: API에서 이미지가 반환되지 않음 (버전 {i+1})")
                    st.stop()  # 더 이상 진행하지 않음
            except Exception as e:
                st.error(f"❌ 이미지 생성 실패: {str(e)} (버전 {i+1})")
                st.stop()  # 예외 발생 시 중단

        progress_bar.empty()
        if st.session_state.get("generated_images"):
            st.success(f"✅ {len(st.session_state['generated_images'])}개 이미지 생성 완료!")
            cols = st.columns(len(st.session_state["generated_images"]))
            for idx, img in enumerate(st.session_state["generated_images"]):
                with cols[idx]:
                    st.image(img["bytes"], caption=f"버전 {idx+1}", use_container_width=True)
                    st.download_button(f"⬇️ 버전 {idx+1} 다운로드", img["bytes"], f"instagram_banner_v{idx+1}.png", "image/png")