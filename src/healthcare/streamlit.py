# ============================================================
# 헬스케어 AI 콘텐츠 제작 앱 (Streamlit + GPT-5 Mini / SDXL 로컬)
# ============================================================

import os
import streamlit as st
from openai import OpenAI
from diffusers import StableDiffusionXLPipeline
import torch
from io import BytesIO

# ============================================================
# 🌍 환경 변수 및 AI 클라이언트 초기화
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_GPT_MINI = "gpt-5-mini"

openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        st.error(f"OpenAI 클라이언트 초기화 오류: {e}")
else:
    st.warning("⚠️ OPENAI_API_KEY가 설정되지 않았습니다.")

# ============================================================
# 🖥 Streamlit 페이지 설정
# ============================================================

st.set_page_config(page_title="💪 헬스케어 AI 콘텐츠 제작", layout="wide")
st.sidebar.title("메뉴")
menu = st.sidebar.radio(
    "페이지 선택",
    ["📝 홍보 문구+해시태그 생성", "🖼 인스타그램 이미지 생성", "🖼️ 이미지 편집/합성"],
)

# ============================================================
# 🧩 유틸리티 함수
# ============================================================

def validate_inputs(service_name, features):
    if not service_name.strip() or not features.strip():
        st.warning("⚠️ 서비스 이름과 핵심 특징을 입력해주세요.")
        return False
    return True

def parse_output(output):
    captions, hashtags = [], ""
    try:
        if "문구:" in output and "해시태그:" in output:
            parts = output.split("해시태그:")
            caption_part = parts[0].replace("문구:", "").strip()
            hashtags = parts[1].strip()
            for line in caption_part.split("\n"):
                if line.strip() and (line[0].isdigit() and "." in line):
                    captions.append(line.split(".", 1)[1].strip())
                elif line.strip() and not line.startswith("문구:"):
                    captions.append(line.strip())
    except Exception:
        return [output], ""
    return captions, hashtags

def generate_caption_and_hashtags(client, model, tone, info, hashtag_count=15):
    prompt = f"""
당신은 헬스케어 소상공인을 위한 전문 인스타그램 콘텐츠 크리에이터입니다.
아래 정보를 바탕으로 인스타그램 게시물에 최적화된 콘텐츠를 생성해 주세요.

요청:
1. 인스타그램 홍보 문구 3개 작성
    - 각 문구: 후킹 → 핵심 메시지 → CTA
    - 이모티콘 사용
    - 문체 스타일: {tone}
2. 해시태그 {hashtag_count}개 추천 (중복 제거)

[정보]
서비스 종류: {info['service_type']}
서비스명: {info['service_name']}
핵심 특징: {info['features']}
지역: {info['location']}
이벤트: {info['event_info']}

출력 형식:
문구:
1. [문구1]
2. [문구2]
3. [문구3]

해시태그:
#[태그1] #[태그2] ... #[태그N]
"""
    try:
        response = client.responses.create(model=model, input=prompt, reasoning={"effort":"minimal"})
        return response.output_text.strip()
    except Exception as e:
        st.error(f"GPT-5 Mini 호출 오류: {e}")
        return f"문구:\n1. [API 오류]\n해시태그:\n#[API오류]"

# ============================================================
# 🖼 로컬 SDXL 초기화 & 이미지 생성
# ============================================================

pipe = None
def init_local_sdxl(model_id="stabilityai/stable-diffusion-xl-base-1.0"):
    global pipe
    if pipe is None:
        pipe = StableDiffusionXLPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
        pipe = pipe.to("cuda")  # GPU 없으면 "cpu"
    return pipe

def generate_image_local(prompt, width=1024, height=1024, steps=30):
    global pipe
    if pipe is None:
        pipe = init_local_sdxl()
    negative_prompt = "low quality, blurry, text, watermark, distorted"
    result = pipe(prompt=prompt, negative_prompt=negative_prompt, width=width, height=height, num_inference_steps=steps)
    image = result.images[0]
    buf = BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf

def caption_to_image_prompt(caption, style="Instagram banner"):
    return f"{caption}, {style}, vibrant, professional, motivational"

# ============================================================
# 📝 페이지 1: 홍보 문구 + 해시태그
# ============================================================

if menu == "📝 홍보 문구+해시태그 생성":
    st.title("📝 홍보 문구 & 해시태그 생성")
    if openai_client:
        with st.form("content_form"):
            service_name = st.text_input("제품/클래스 이름")
            features = st.text_area("핵심 특징 및 장점")
            tone = st.selectbox("톤 선택", ["친근하고 동기부여","전문적이고 신뢰감","재미있고 트렌디","차분하고 감성적"])
            submitted = st.form_submit_button("✨ 문구+해시태그 생성")

        if submitted and validate_inputs(service_name, features):
            info = {"service_type":"헬스/피트니스","service_name":service_name,"features":features,"location":"전국/온라인","event_info":"없음"}
            output = generate_caption_and_hashtags(openai_client, MODEL_GPT_MINI, tone, info, 15)
            captions, hashtags = parse_output(output)
            st.session_state["captions"] = captions
            st.session_state["hashtags"] = hashtags

        if "captions" in st.session_state:
            st.markdown("### 💬 생성된 문구")
            for i, caption in enumerate(st.session_state["captions"]):
                st.radio(f"문구 선택 {i+1}", st.session_state["captions"], key=f"selected_caption_{i}")
            st.markdown("### 🔖 추천 해시태그")
            st.code(st.session_state["hashtags"])

# ============================================================
# 🖼 페이지 2: 문구 기반 이미지 3버전 생성
# ============================================================

elif menu == "🖼 인스타그램 이미지 생성":
    st.title("🖼 문구 기반 이미지 생성 (3가지 버전)")
    if "captions" not in st.session_state:
        st.warning("⚠️ 페이지1에서 문구를 먼저 생성해주세요.")
    else:
        selected_caption = st.selectbox("이미지에 반영할 문구 선택", st.session_state["captions"])
        image_size = st.selectbox("이미지 크기", ["1024x1024","1792x1024","1024x1792"])
        submitted = st.button("🖼 3가지 버전 생성")

        if submitted:
            width, height = map(int, image_size.split("x"))
            st.session_state["generated_images"] = []
            st.info("⏳ 3가지 버전 생성 중...")
            for i in range(3):
                version_prompt = caption_to_image_prompt(f"{selected_caption} (version {i+1})")
                image_bytes = generate_image_local(version_prompt, width=width, height=height)
                st.session_state["generated_images"].append({"prompt": version_prompt, "bytes": image_bytes})

            st.success("✅ 3가지 이미지 생성 완료!")
            for idx, img_data in enumerate(st.session_state["generated_images"]):
                st.image(img_data["bytes"], caption=f"버전 {idx+1}: {img_data['prompt']}", use_column_width=True)
                st.download_button(f"버전 {idx+1} 다운로드", img_data["bytes"], f"instagram_banner_v{idx+1}.png","image/png")

# ============================================================
# 🖼 페이지 3: 이미지 편집/합성 (로컬 SDXL)
# ============================================================

elif menu == "🖼️ 이미지 편집/합성":
    st.title("🖼️ 이미지 편집 / 합성")
    uploaded_file = st.file_uploader("업로드 이미지 (없으면 페이지2 선택 이미지 사용)", type=["png","jpg","jpeg"])
    preloaded_image = st.session_state.get("generated_images", [None])[0]
    image_bytes = uploaded_file.getvalue() if uploaded_file else preloaded_image

    if image_bytes and "captions" in st.session_state:
        selected_caption = st.selectbox("편집에 반영할 문구 선택", st.session_state["captions"])
        edit_prompt = st.text_area("추가 편집 지시 (선택)")
        output_size = st.selectbox("출력 이미지 크기", ["1024x1024","1792x1024","1024x1792"])
        submitted = st.button("✨ 합성 이미지 생성")

        if submitted:
            width, height = map(int, output_size.split('x'))
            final_prompt = caption_to_image_prompt(selected_caption)
            if edit_prompt:
                final_prompt += f", {edit_prompt}"
            with st.spinner("합성/편집 중... ⏳"):
                edited_image_bytes = generate_image_local(final_prompt, width=width, height=height)
                st.image(edited_image_bytes, caption=final_prompt, use_column_width=True)
                st.download_button("합성 이미지 다운로드", edited_image_bytes, "edited_image.png","image/png")

