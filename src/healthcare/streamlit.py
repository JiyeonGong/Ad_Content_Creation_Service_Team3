# ============================================================
# 헬스케어 AI 콘텐츠 제작 앱 (Streamlit + GPT-5 Mini/SDXL API 기능 확장)
# ============================================================

import os
import streamlit as st
from openai import OpenAI
import requests
import base64

# ============================================================
# 🌍 환경 변수 및 AI 클라이언트 초기화
# ============================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

MODEL_GPT_MINI = "gpt-5-mini"
MODEL_HF_IMAGE = "stabilityai/stable-diffusion-xl-base-1.0"
HF_API_URL = f"https://api-inference.huggingface.co/models/{MODEL_HF_IMAGE}"

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
    if not service_name or not features:
        st.warning("⚠️ 서비스 이름과 핵심 특징은 반드시 입력해주세요.")
        return False
    return True

def parse_output(output):
    captions = []
    hashtags = ""
    try:
        if "문구:" in output and "해시태그:" in output:
            parts = output.split("해시태그:")
            caption_part = parts[0].replace("문구:", "").strip()
            hashtags = parts[1].strip()
            for line in caption_part.split('\n'):
                if line.strip() and (line[0].isdigit() and '.' in line):
                    captions.append(line.split('.', 1)[1].strip())
                elif line.strip() and not line.startswith('문구:'):
                    captions.append(line.strip())
    except Exception:
        return [output], ""
    return captions, hashtags

def generate_caption_and_hashtags(client, model, tone, info, hashtag_count=15):
    prompt = f"""
당신은 헬스케어 소상공인을 위한 전문 인스타그램 콘텐츠 크리에이터입니다.
아래 정보를 바탕으로 인스타그램 게시물에 최적화된 콘텐츠를 생성해 주세요.

요청:
1. 인스타그램 홍보 문구 3개를 작성
    - 각 문구는 후킹 → 핵심 메시지 → 명확한 CTA 구조
    - 이모티콘을 적절히 사용
    - 문체 스타일: {tone}
2. 위 문구를 기반으로 해시태그 {hashtag_count}개를 추천
    - 모든 태그는 #태그 형식, 중복 제거

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
        response = client.responses.create(
            model=model,
            input=prompt,
            reasoning={"effort": "minimal"}
        )
        return response.output_text.strip()
    except Exception as e:
        st.error(f"API 호출 오류: {e}")
        return f"문구:\n1. [API 오류]\n해시태그:\n#[API오류]"

def generate_image_asset(api_token, prompt, size="1024x1024"):
    if not api_token:
        st.error("HF_API_TOKEN이 설정되지 않아 이미지 생성 불가.")
        return None
    if size == "1792x1024":
        width, height = 1792, 1024
    elif size == "1024x1792":
        width, height = 1024, 1792
    else:
        width, height = 1024, 1024

    full_prompt = f"{prompt}, vibrant colors, modern and motivational style, photorealistic, Instagram banner, no text or watermark"
    negative_prompt = "low quality, blurry, distorted, text, watermark"

    headers = {"Authorization": f"Bearer {api_token}"}
    payload = {
        "inputs": full_prompt,
        "parameters": {"negative_prompt": negative_prompt, "width": width, "height": height, "num_inference_steps": 30},
        "options": {"wait_for_model": True}
    }
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        if response.status_code != 200:
            st.error(f"Hugging Face API 오류 ({response.status_code}): {response.text}")
            return None
        return response.content
    except Exception as e:
        st.error(f"네트워크 오류: {e}")
        return None

def caption_to_image_prompt(caption, style="Instagram banner"):
    return f"{caption}, {style}"

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
# 🖼 페이지 2: 3가지 이미지 버전 생성 + 선택 전달
# ============================================================
elif menu == "🖼 인스타그램 이미지 생성":
    st.title("🖼 문구 기반 이미지 생성 (3가지 버전)")
    if HF_API_TOKEN:
        if "captions" not in st.session_state:
            st.warning("⚠️ 페이지1에서 문구를 먼저 생성해주세요.")
        else:
            selected_caption = st.selectbox("이미지에 반영할 문구 선택", st.session_state["captions"])
            image_size = st.selectbox("이미지 크기", ["1024x1024","1792x1024","1024x1792"])
            submitted = st.button("🖼 3가지 버전 생성")

            if submitted:
                size_value = image_size
                st.session_state["generated_images"] = []
                st.info("⏳ 3가지 버전 생성 중...")

                for i in range(3):
                    version_prompt = caption_to_image_prompt(f"{selected_caption} (version {i+1})")
                    image_bytes = generate_image_asset(HF_API_TOKEN, version_prompt, size=size_value)
                    if image_bytes:
                        st.session_state["generated_images"].append({"prompt": version_prompt, "bytes": image_bytes})

                if st.session_state["generated_images"]:
                    st.success("✅ 3가지 이미지 생성 완료!")
                    st.markdown("### 🖼 미리보기 & 페이지3 전달용 선택")
                    for idx, img_data in enumerate(st.session_state["generated_images"]):
                        st.image(img_data["bytes"], caption=f"버전 {idx+1}: {img_data['prompt']}", use_column_width=True)
                        st.download_button(f"버전 {idx+1} 다운로드", img_data["bytes"], f"instagram_banner_v{idx+1}.png","image/png")

                    version_choices = [f"버전 {i+1}" for i in range(len(st.session_state["generated_images"]))]
                    selected_version = st.selectbox("페이지3 편집용 이미지 선택", version_choices)
                    st.session_state["selected_for_edit"] = st.session_state["generated_images"][version_choices.index(selected_version)]["bytes"]
                    st.success(f"✅ {selected_version} 선택 완료. 페이지3에서 편집 가능합니다.")
    else:
        st.error("❌ HF_API_TOKEN이 설정되지 않았습니다.")

# ============================================================
# 🖼 페이지 3: 이미지 편집/합성
# ============================================================
elif menu == "🖼️ 이미지 편집/합성":
    st.title("🖼️ 이미지 편집 / 합성")
    if HF_API_TOKEN:
        uploaded_file = st.file_uploader("업로드 이미지 (없으면 페이지2 선택 이미지 사용)", type=["png","jpg","jpeg"])
        preloaded_image = st.session_state.get("selected_for_edit", None)

        if uploaded_file:
            image_bytes = uploaded_file.getvalue()
        elif preloaded_image:
            image_bytes = preloaded_image
        else:
            image_bytes = None
            st.warning("⚠️ 이미지가 없습니다.")

        if image_bytes and "captions" in st.session_state:
            selected_caption = st.selectbox("편집에 반영할 문구 선택", st.session_state["captions"])
            edit_prompt = st.text_area("추가 편집 지시 (선택)")
            output_size = st.selectbox("출력 이미지 크기", ["1024x1024","1792x1024","1024x1792"])
            negative_prompt = st.text_area("제외 요소 (선택)")
            submitted = st.button("✨ 합성 이미지 생성")

            if submitted:
                width, height = map(int, output_size.split('x'))
                full_prompt = caption_to_image_prompt(selected_caption)
                if edit_prompt:
                    full_prompt += f", {edit_prompt}"

                with st.spinner("합성/편집 중... ⏳"):
                    try:
                        headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
                        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
                        payload = {
                            "inputs": encoded_image,
                            "parameters": {
                                "prompt": f"Based on the input image, {full_prompt}",
                                "negative_prompt": negative_prompt if negative_prompt else "low quality, blurry, text, watermark",
                                "width": width, "height": height, "num_inference_steps": 30, "guidance_scale": 7.5
                            },
                            "options": {"wait_for_model": True}
                        }
                        hf_url = f"https://api-inference.huggingface.co/models/{MODEL_HF_IMAGE}"
                        response = requests.post(hf_url, headers=headers, json=payload)
                        if response.status_code == 200:
                            edited_image_bytes = response.content
                            st.image(edited_image_bytes, caption=full_prompt, use_column_width=True)
                            st.download_button("합성 이미지 다운로드", edited_image_bytes, "edited_image.png","image/png")
                        else:
                            st.error(f"Hugging Face API 오류 ({response.status_code}): {response.text}")
                    except Exception as e:
                        st.error(f"네트워크 오류: {e}")
    else:
        st.error("❌ HF_API_TOKEN이 설정되지 않았습니다.")
