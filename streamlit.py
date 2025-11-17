# C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\healthcare\streamlit.py
# ============================================================
# 💪 헬스케어 AI 콘텐츠 제작 앱 (Streamlit + GPT-5 Mini / SDXL 로컬)
# 연결 모드 ON/OFF 지원
# 캐시 경로 통합 적용 (Streamlit + Hugging Face)
# ============================================================

import os
import re
import streamlit as st
from openai import OpenAI
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline
import torch
from io import BytesIO
from PIL import Image

# ============================================================
# 🌐 프로젝트 기반 캐시 경로 설정
# ============================================================

# 프로젝트 루트 (src 폴더 기준)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
cache_root = os.path.join(project_root, "cache")
os.makedirs(cache_root, exist_ok=True)

# Streamlit 캐시 (🚫 'global.cacheDir' 옵션은 지원되지 않으므로 제거)
# st.set_option("global.cacheDir", streamlit_cache_dir)
# Streamlit 캐시 파일은 기본 경로 (~/.streamlit/cache)에 저장됨.

# Hugging Face 모델 캐시
hf_cache_dir = os.path.join(cache_root, "hf_models")
os.makedirs(hf_cache_dir, exist_ok=True)

# Streamlit 캐시 경로를 지정하는 코드를 제거
# st.sidebar.info(f"Streamlit 캐시: 기본 경로 사용\n HF 모델 캐시: {hf_cache_dir}")


# ============================================================
# 🌱 .env 자동 로딩
# ============================================================
from dotenv import load_dotenv

# 프로젝트 루트 기준으로 .env 경로 지정
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
dotenv_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path)

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

connect_mode = st.sidebar.checkbox("🔗 페이지 연결 모드", value=True)
st.sidebar.info("연결 모드 ON: 페이지1에서 생성된 문구를 자동으로 페이지2/3에 사용\n"
                "OFF: 각 페이지 독립 입력 사용")

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
        m = re.search(r"문구:(.*?)해시태그:(.*)", output, re.S)
        if m:
            caption_text = m.group(1).strip()
            hashtags = m.group(2).strip()
            captions = [line.split(".",1)[1].strip() if "." in line else line.strip()
                         for line in caption_text.split("\n") if line.strip()]
        else:
            captions = [output]
    except Exception:
        captions = [output]
    return captions, hashtags

@st.cache_data(show_spinner="AI가 홍보 문구를 생성하는 중... ⏳")
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
        response = client.responses.create(
            model=model,
            input=prompt,
            reasoning={"effort":"minimal"},
            max_output_tokens=512, 
        )
        return response.output_text.strip()
    except Exception as e:
        st.error(f"GPT-5 Mini 호출 오류: {e}")
        return f"문구:\n1. [API 오류]\n해시태그:\n#[API오류]"

# ============================================================
# 🖼 SDXL 초기화 및 이미지 생성
# ============================================================

@st.cache_resource(show_spinner="SDXL T2I 모델 로딩 중...")
def init_local_sdxl_t2i(model_id="stabilityai/stable-diffusion-xl-base-1.0"):
    if not torch.cuda.is_available():
        st.warning("⚠️ GPU가 감지되지 않았습니다. 이미지 생성이 매우 느릴 수 있습니다.")
    pipe = StableDiffusionXLPipeline.from_pretrained(
        model_id,
        cache_dir=hf_cache_dir,  # HF 모델 캐시 경로 지정
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return pipe.to(device)

@st.cache_resource(show_spinner="SDXL I2I 모델 로딩 중...")
def init_local_sdxl_i2i(model_id="stabilityai/stable-diffusion-xl-base-1.0"):
    if not torch.cuda.is_available():
        st.warning("⚠️ GPU가 감지되지 않았습니다. 이미지 생성이 매우 느릴 수 있습니다.")
    pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
        model_id,
        cache_dir=hf_cache_dir,  # HF 모델 캐시 경로 지정
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return pipe.to(device)

@st.cache_data(show_spinner=False)
def generate_image_local(prompt, width=1024, height=1024, steps=30):
    pipe = init_local_sdxl_t2i()
    negative_prompt = "low quality, blurry, text, watermark, distorted"
    result = pipe(prompt=prompt, negative_prompt=negative_prompt, width=width, height=height, num_inference_steps=steps)
    image = result.images[0]
    buf = BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf

@st.cache_data(show_spinner=False)
def generate_image_i2i_local(input_image_bytes, prompt, strength=0.75, width=1024, height=1024, steps=30):
    pipe = init_local_sdxl_i2i()
    negative_prompt = "low quality, blurry, text, watermark, distorted"
    input_image = Image.open(BytesIO(input_image_bytes)).convert("RGB").resize((width, height))
    result = pipe(
        prompt=prompt, 
        image=input_image,
        strength=strength,
        negative_prompt=negative_prompt, 
        num_inference_steps=steps
    )
    image = result.images[0]
    buf = BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf

def caption_to_image_prompt(caption, style="Instagram banner"):
    return f"{caption}, {style}, vibrant, professional, motivational"

# ============================================================
# 🔄 세션 상태 초기화
# ============================================================

if not connect_mode:
    st.cache_data.clear() 
    for key in ["captions","hashtags","generated_images","selected_caption"]:
        if key in st.session_state:
            del st.session_state[key]

# ============================================================
# 📝 페이지 1: 홍보 문구 + 해시태그
# ============================================================

if menu == "📝 홍보 문구+해시태그 생성":
    st.title("📝 홍보 문구 & 해시태그 생성")
    
    if not openai_client:
        st.error("❌ OpenAI API 키가 설정되지 않아 이 기능을 사용할 수 없습니다.")
    else:
        with st.form("content_form"):
            
            # 👇 사용자 요청에 따라 추가된 입력 필드
            service_type = st.selectbox(
                "서비스 종류",
                ["헬스장", "PT (개인 트레이닝)", "요가/필라테스", "건강 식품/보조제", "기타"],
            )
            location = st.text_input("지역", placeholder="예: 강남, 마포구, 온라인")
            # 👆 추가된 입력 필드

            service_name = st.text_input("제품/클래스 이름", placeholder="예: 30일 다이어트 챌린지")
            features = st.text_area("핵심 특징 및 장점", placeholder="예: 전문 PT와 함께하는 맞춤형 운동, 영양 관리 포함")
            tone = st.selectbox("톤 선택", ["친근하고 동기부여","전문적이고 신뢰감","재미있고 트렌디","차분하고 감성적"])
            submitted = st.form_submit_button("✨ 문구+해시태그 생성")

        if submitted:
            # `location`과 `service_name`, `features`는 GPT 프롬프트에 필수적이므로, 
            # `location`의 빈 값 체크를 `validate_inputs`에 포함하는 것이 좋습니다.
            if validate_inputs(service_name, features) and location.strip(): # 지역 정보가 추가됨
                
                info = {
                    "service_type": service_type, # 👈 새로운 정보 포함
                    "service_name": service_name,
                    "features": features,
                    "location": location,       # 👈 새로운 정보 포함
                    "event_info":"없음"
                }
                
                output = generate_caption_and_hashtags(openai_client, MODEL_GPT_MINI, tone, info, 15)
                captions, hashtags = parse_output(output)
                st.session_state["captions"] = captions
                st.session_state["hashtags"] = hashtags
            else:
                 st.warning("⚠️ 서비스 이름, 핵심 특징, **지역**을 모두 입력해주세요.")


        # 생성된 문구 표시 및 선택 (이하 동일)
        if "captions" in st.session_state and st.session_state["captions"]:
            # ... (이하 기존 코드와 동일)
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

# ============================================================
# 🖼 페이지 2: 문구 기반 이미지 3버전 생성
# ============================================================

elif menu == "🖼 인스타그램 이미지 생성":
    st.title("🖼 문구 기반 이미지 생성 (3가지 버전)")
    
    # 연결 모드일 때 페이지1 문구 사용 가능
    if connect_mode and "selected_caption" in st.session_state:
        st.info(f"🔗 연결 모드: 페이지1에서 선택한 문구 사용\n\n**선택된 문구:** {st.session_state['selected_caption']}")
        selected_caption = st.session_state["selected_caption"]
    else:
        if connect_mode:
            st.warning("⚠️ 페이지1에서 문구를 먼저 생성하고 선택하세요.")
        selected_caption = st.text_area("문구 입력 (연결 모드 OFF 또는 페이지1 문구 없음)", 
                                         placeholder="예: 💪 새해 목표, 이번엔 꼭 이루자! 전문 PT와 함께하는 30일 다이어트 챌린지 🔥")
    
    image_size = st.selectbox("이미지 크기", ["1024x1024","1792x1024","1024x1792"])
    submitted = st.button("🖼 3가지 버전 생성", type="primary")

    if submitted and selected_caption:
        width, height = map(int, image_size.split("x"))
        st.session_state["generated_images"] = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i in range(3):
            status_text.text(f"⏳ 버전 {i+1}/3 생성 중... (캐싱되지 않은 경우 시간이 걸립니다)")
            
            # 각 버전마다 약간 다른 프롬프트
            version_prompt = caption_to_image_prompt(
                f"{selected_caption} (style variation {i+1})"
            )
            
            try:
                # 🟢 generate_image_local 함수가 cache_data를 사용하므로, 
                # 같은 프롬프트로 재시도 시 매우 빠르게 이미지를 반환합니다.
                image_bytes = generate_image_local(version_prompt, width=width, height=height)
                st.session_state["generated_images"].append({
                    "prompt": version_prompt, 
                    "bytes": image_bytes
                })
                progress_bar.progress((i+1)/3)
            except Exception as e:
                st.error(f"이미지 생성 오류 (버전 {i+1}): {e}")
                break

        status_text.empty()
        progress_bar.empty()
        
        if st.session_state["generated_images"]:
            st.success(f"✅ {len(st.session_state['generated_images'])}개 이미지 생성 완료!")
            
            cols = st.columns(len(st.session_state["generated_images"]))
            for idx, img_data in enumerate(st.session_state["generated_images"]):
                with cols[idx]:
                    st.image(img_data["bytes"], caption=f"버전 {idx+1}", use_container_width=True)
                    st.download_button(
                        f"⬇️ 버전 {idx+1} 다운로드", 
                        img_data["bytes"], 
                        f"instagram_banner_v{idx+1}.png",
                        "image/png",
                        key=f"download_{idx}"
                    )

# ============================================================
# 🖼 페이지 3: 이미지 편집/합성 (I2I 기능으로 수정됨)
# ============================================================

elif menu == "🖼️ 이미지 편집/합성":
    st.title("🖼️ 이미지 편집 / 합성 (Image-to-Image)")
    
    st.info("💡 이 기능은 **업로드된 이미지를 기반**으로 문구와 추가 지시를 반영하여 새로운 스타일의 이미지를 생성합니다.")
    
    # 이미지 소스 선택
    uploaded_file = st.file_uploader("업로드 이미지", type=["png","jpg","jpeg"])
    
    # 페이지2에서 생성된 이미지 확인
    preloaded_images = st.session_state.get("generated_images", [])
    
    image_bytes = None
    if uploaded_file:
        image_bytes = uploaded_file.getvalue()
        st.image(image_bytes, caption="업로드된 이미지", width=300)
    elif preloaded_images and connect_mode:
        st.info("🔗 연결 모드: 페이지2에서 생성된 이미지 사용")
        image_idx = st.selectbox("사용할 이미지 선택", 
                                 range(len(preloaded_images)),
                                 format_func=lambda x: f"버전 {x+1}")
        image_bytes = preloaded_images[image_idx]["bytes"].getvalue() # BytesIO에서 실제 바이트 가져오기
        st.image(image_bytes, caption=f"선택된 이미지: 버전 {image_idx+1}", width=300)
    else:
        st.warning("⚠️ 이미지를 업로드하거나 페이지2에서 이미지를 먼저 생성하세요.")
    
    # 문구 소스 선택
    if connect_mode and "selected_caption" in st.session_state:
        st.info(f"🔗 사용할 문구: {st.session_state['selected_caption']}")
        selected_caption = st.session_state["selected_caption"]
    else:
        selected_caption = st.text_input("편집에 반영할 문구 입력", 
                                         placeholder="예: 💪 새해 목표, 이번엔 꼭 이루자!")
    
    # I2I에 필수적인 변화 강도 슬라이더 추가
    denoising_strength = st.slider(
        "✨ 변화 강도 (Strength)", 
        min_value=0.0, 
        max_value=1.0, 
        value=0.75, 
        step=0.05,
        help="0.0에 가까울수록 원본 이미지 유지, 1.0에 가까울수록 프롬프트에 따른 새로운 이미지 생성"
    )

    edit_prompt = st.text_area("추가 편집 지시 (선택)", 
                                 placeholder="예: 더 밝고 활기찬 분위기로, 파란색 배경 추가")
    output_size = st.selectbox("출력 이미지 크기", ["1024x1024","1792x1024","1024x1792"])
    
    submitted = st.button("✨ 합성/편집 이미지 생성", type="primary")

    if submitted:
        if not image_bytes:
            st.error("❌ 이미지를 먼저 업로드하거나 페이지2에서 생성하세요.")
        elif not selected_caption:
            st.error("❌ 문구를 입력하세요.")
        else:
            width, height = map(int, output_size.split('x'))
            
            # 최종 프롬프트 생성
            final_prompt = caption_to_image_prompt(selected_caption)
            if edit_prompt:
                final_prompt += f", {edit_prompt}"
            
            with st.spinner("합성/편집 중... ⏳ (캐싱되지 않은 경우 시간이 걸립니다)"):
                try:
                    # 🚀 I2I 전용 함수 호출 (원본 이미지와 변화 강도 전달)
                    edited_image_bytes = generate_image_i2i_local(
                        image_bytes, # 원본 이미지 바이트 전달
                        final_prompt, 
                        denoising_strength, # 변화 강도 전달
                        width=width, 
                        height=height
                    )
                    
                    col1, col2 = st.columns(2)
                    
                    # Original Image Display 
                    with col1:
                        st.subheader("원본 이미지")
                        st.image(image_bytes, use_container_width=True) 

                    # Edited Image Display
                    with col2:
                        st.subheader("편집된 이미지")
                        st.image(edited_image_bytes, caption="I2I 결과", use_container_width=True)
                    
                    st.success("✅ 이미지 생성 완료!")
                    st.download_button("⬇️ 편집 이미지 다운로드", 
                                       edited_image_bytes, 
                                       "edited_image.png",
                                       "image/png")
                except Exception as e:
                    st.error(f"이미지 생성 오류: {e}")