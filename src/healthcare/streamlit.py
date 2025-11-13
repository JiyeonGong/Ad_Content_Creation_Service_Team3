# ============================================================
# 🏋️ 헬스케어 AI 콘텐츠 제작 앱 (Streamlit + GPT-5 Mini/SDXL(huggingface api))
# ============================================================

import os
import streamlit as st
from openai import OpenAI
import time
import requests
import base64
from io import BytesIO

# ============================================================
# 🌍 환경 변수 로드 및 AI 클라이언트 초기화
# ============================================================

# ★ 실제 사용 시 .env 파일에서 API 키를 로드해야 합니다.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_API_TOKEN = os.getenv("HF_API_TOKEN") # Hugging Face API 키 추가

# 텍스트 생성 (GPT-5 Mini)
openai_client = None
MODEL_GPT_MINI = "gpt-5-mini" 

if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        st.error(f"❌ OpenAI 클라이언트 초기화 오류: API 키를 확인해주세요. ({e})")
else:
    st.warning("⚠️ OPENAI_API_KEY가 설정되지 않았습니다. 텍스트 생성 기능을 사용할 수 없습니다.")

# 이미지 생성 (Hugging Face Stable Diffusion XL)
MODEL_HF_IMAGE = "stabilityai/stable-diffusion-xl-base-1.0"
HF_API_URL = f"https://api-inference.huggingface.co/models/{MODEL_HF_IMAGE}"

if not HF_API_TOKEN:
    st.warning("⚠️ HF_API_TOKEN이 설정되지 않았습니다. 이미지 생성 기능을 사용할 수 없습니다.")

# ============================================================
# 🖥 Streamlit 페이지 설정
# ============================================================

st.set_page_config(page_title="💪 헬스케어 AI 콘텐츠 제작", layout="wide")
st.sidebar.title("메뉴")
menu = st.sidebar.radio(
    "페이지 선택",
    ["📝 홍보 문구+해시태그 통합 생성", "🖼 인스타그램 이미지 생성"],
)

# ============================================================
# 🧩 유틸리티 함수
# ============================================================

def validate_inputs(service_name, features):
    """필수 입력값이 비어있는지 확인"""
    if not service_name or not features:
        st.warning("⚠️ 서비스 이름과 핵심 특징은 반드시 입력해주세요.")
        return False
    return True

def parse_output(output):
    """GPT-5 Mini의 응답을 문구와 해시태그로 안전하게 분리"""
    captions = []
    hashtags = ""
    
    try:
        if "문구:" in output and "해시태그:" in output:
            parts = output.split("해시태그:")
            caption_part = parts[0].replace("문구:", "").strip()
            hashtags = parts[1].strip()

            # 문구 파싱 (번호가 매겨진 리스트 형식으로 가정)
            for line in caption_part.split('\n'):
                if line.strip() and line[0].isdigit() and '.' in line:
                    # '1. [문구]' 형태에서 번호 제거
                    captions.append(line.split('.', 1)[1].strip())
                elif line.strip() and not line.startswith('문구:'):
                     captions.append(line.strip())
            
    except Exception:
        # 파싱 실패 시 원본 텍스트를 하나의 문구로 간주
        st.error("⚠️ 결과 파싱에 실패했습니다. 원본 텍스트를 확인해주세요.")
        return [output], ""
        
    return captions, hashtags

def generate_caption_and_hashtags(client, model, tone, info, hashtag_count=15):
    """
    한 번의 API 호출로 인스타그램 홍보 문구 3개와 해시태그를 동시에 생성
    (GPT-5 Mini 사용)
    """
    prompt = f"""
당신은 헬스케어 소상공인을 위한 전문 인스타그램 콘텐츠 크리에이터입니다.
아래 정보를 바탕으로 인스타그램 게시물에 최적화된 콘텐츠를 생성해 주세요.

요청:
1. 인스타그램 홍보 문구 3개를 작성
    - 각 문구는 후킹 → 핵심 메시지 → 명확한 CTA 구조
    - 이모티콘을 적절히 사용
    - 문체 스타일: {tone}
2. 위 문구를 기반으로 해시태그 {hashtag_count}개를 추천
    - 대형/중형/틈새 태그의 균형 유지
    - 모든 태그는 #태그 형식, 공백 없이, 중복 제거

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
#[태그1] #[태그2] #[태그3] ... #[태그N]
"""
    try:
        response = client.responses.create(
            model=model,
            input=prompt,
            reasoning={"effort": "minimal"} # GPT-5 Mini의 속도 최적화 파라미터 활용
        )
        return response.output_text.strip()
    except Exception as e:
        st.error(f"API 호출 중 오류가 발생했습니다: {e}")
        return f"문구:\n1. [API 오류 발생]\n해시태그:\n#[API오류] #[점검중]"

def generate_image_asset(api_token, prompt, size="1024x1024"):
    """
    Stable Diffusion XL (Hugging Face Inference API)를 사용하여 이미지 생성
    """
    if not api_token:
        st.error("❌ Hugging Face API Token이 설정되지 않아 이미지 생성을 할 수 없습니다.")
        return None

    # SDXL은 텍스트를 이미지로 변환할 때 긍정 프롬프트와 부정 프롬프트를 사용하는 것이 일반적입니다.
    # DALL-E와 달리 API 호출 구조가 다릅니다.
    
    # 긍정 프롬프트 생성 (사용자 입력 + 품질 보강)
    full_prompt = (
        f"A photorealistic, highly detailed Instagram banner of a healthcare/fitness center. {prompt}. "
        f"Vibrant colors, modern and motivational style. No text or font on the image."
    )
    
    # 부정 프롬프트 (생성 품질 저하 요소 제거)
    negative_prompt = (
        "low quality, blurry, ugly, distorted, deformed, text, watermark, logo, bad anatomy, "
        "disfigured, extra limbs, grainy, monochrome, oversaturated"
    )

    # 이미지 크기에 따른 SDXL 해상도 조정 (1024x1024, 1792x1024, 1024x1792 중 선택)
    if size == "1792x1024":
        width, height = 1792, 1024
    elif size == "1024x1792":
        width, height = 1024, 1792
    else:
        width, height = 1024, 1024

    headers = {"Authorization": f"Bearer {api_token}"}
    payload = {
        "inputs": full_prompt,
        "parameters": {
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "num_inference_steps": 30, # 추론 단계 설정 (품질과 속도 타협점)
        },
        "options": {
            "wait_for_model": True # 모델 로딩 대기
        }
    }
    
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            st.error(f"Hugging Face API 호출 오류 ({response.status_code}): {response.text}")
            return None
        
        # 응답은 이미지 바이너리 데이터입니다.
        image_bytes = response.content
        
        # Streamlit에서 표시하기 위해 BytesIO를 사용하거나 Base64 인코딩을 사용할 수 있습니다.
        # 여기서는 BytesIO를 사용하여 Streamlit image()에 직접 전달할 수 있도록 준비합니다.
        return image_bytes

    except requests.exceptions.RequestException as e:
        st.error(f"네트워크 통신 중 오류가 발생했습니다: {e}")
        return None

# ============================================================
# 📣 페이지 1: 홍보 문구 + 해시태그 통합 생성
# ============================================================

if menu == "📝 홍보 문구+해시태그 통합 생성":
    st.title("📝 인스타그램 맞춤 홍보 문구 & 해시태그 통합 생성")
    st.markdown(f"**AI 모델**: `{MODEL_GPT_MINI}` (OpenAI, 빠른 응답 및 비용 최적화)")
    st.divider()

    if openai_client:
        with st.form("content_generation_form"):
            st.subheader("💡 서비스 정보 입력")
            
            col1, col2 = st.columns(2)
            with col1:
                service_type = st.selectbox(
                    "서비스 종류", 
                    ["헬스장", "PT (개인 트레이닝)", "요가/필라테스", "건강 식품/보조제", "기타"]
                )
            with col2:
                location = st.text_input("지역 (예: 강남, 마포구, 온라인)")

            service_name = st.text_input("제품/클래스 이름", key="service_name_input")
            features = st.text_area(
                "핵심 특징 및 장점 (줄바꿈 또는 콤마로 구분)",
                height=100,
                placeholder="예: 최신 머신 완비, 1:1 맞춤 식단 관리, 20년 경력 트레이너",
                key="features_input"
            )

            col3, col4 = st.columns(2)
            with col3:
                event_info = st.text_input("이벤트/할인 내용", placeholder="예: 선착순 10명 30% 할인")
            with col4:
                tone = st.selectbox(
                    "톤 선택",
                    ["친근하고 동기부여", "전문적이고 신뢰감", "재미있고 트렌디", "차분하고 감성적"]
                )

            # 톤 예시 안내
            tone_examples = {
                "친근하고 동기부여": "🔥 오늘부터 진짜 몸 만들기 시작!",
                "전문적이고 신뢰감": "체계적인 분석과 과학적 운동법으로 몸을 설계합니다.",
                "재미있고 트렌디": "운동은 지루하다는 편견? 우리랑 하면 NO!",
                "차분하고 감성적": "몸과 마음이 함께 회복되는 시간."
            }
            st.caption(f"💬 **선택 톤 예시**: {tone_examples[tone]}")

            # 폼 제출 버튼
            submitted = st.form_submit_button("✨ 문구+해시태그 생성", type="primary")

        if submitted:
            if validate_inputs(service_name, features):
                with st.spinner("문구와 해시태그를 생성 중입니다. GPT-5 Mini는 빠릅니다! 🚀"):
                    info = {
                        "service_type": service_type,
                        "service_name": service_name,
                        "features": features,
                        "location": location if location else "전국/온라인",
                        "event_info": event_info if event_info else "없음"
                    }
                    output = generate_caption_and_hashtags(openai_client, MODEL_GPT_MINI, tone, info, hashtag_count=15)
                
                # 결과 출력 및 파싱
                st.success("✅ 문구 및 해시태그 생성 완료!")
                captions, hashtags = parse_output(output)

                st.markdown("### 💬 인스타그램 홍보 문구 (3가지 버전)")
                for i, caption in enumerate(captions):
                    st.markdown(f"**📌 {i+1}.**")
                    st.markdown(f"```markdown\n{caption}\n```")
                
                st.markdown("### 🔖 추천 해시태그")
                st.code(hashtags.strip(), language="text")
                
                st.info("💡 Tip: 문구와 해시태그를 복사하여 인스타그램에 바로 사용해 보세요.")
    else:
        st.error("❌ API 클라이언트가 초기화되지 않아 기능을 사용할 수 없습니다.")


# # ============================================================
# # 🖼 페이지 2: 이미지 생성
# # ============================================================

# elif menu == "🖼 인스타그램 이미지 생성":
#     st.title("🖼 인스타그램 이미지/배너 생성")
#     st.markdown(f"**AI 모델**: `{MODEL_HF_IMAGE}` (Hugging Face Inference API)")
#     st.markdown("💡 **참고**: DALL-E 3에서 SDXL 1.0으로 대체되었습니다. Hugging Face API Token이 필요합니다.")
#     st.divider()

#     if HF_API_TOKEN:
#         with st.form("image_generation_form"):
#             st.subheader("🎨 배너 이미지 요청")
#             image_prompt = st.text_area(
#                 "이미지에 대한 상세 묘사 (한국어로 자세히 설명할수록 좋습니다)",
#                 height=150,
#                 placeholder="예: 근육질의 남자가 땀 흘리며 데드리프트를 하는 모습, 역동적이고 강렬한 느낌, 붉은색 조명, 인스타그램 피드에 맞게 정사각형 구도"
#             )
#             image_size = st.selectbox(
#                 "이미지 크기 (인스타그램 최적화)",
#                 ["1024x1024 (정사각형)", "1792x1024 (스토리/릴스 세로)", "1024x1792 (피드 가로)"]
#             )
            
#             # 크기 문자열만 추출
#             size_value = image_size.split(' ')[0] 

#             image_submitted = st.form_submit_button("🖼 이미지 생성 요청", type="primary")

#         if image_submitted and image_prompt:
#             if "image_bytes" in st.session_state:
#                 del st.session_state["image_bytes"] # 이전 결과 제거
            
#             with st.spinner("이미지를 생성 중입니다. SDXL 모델 로딩에 시간이 걸릴 수 있습니다. ⏳"):
#                 # 이미지 생성을 위해 HF_API_TOKEN과 프롬프트를 전달
#                 image_bytes = generate_image_asset(HF_API_TOKEN, image_prompt, size=size_value)
            
#             if image_bytes:
#                 st.session_state["image_bytes"] = image_bytes
#                 st.session_state["image_prompt"] = image_prompt
#                 st.success("✅ 이미지 생성 완료!")

#         if "image_bytes" in st.session_state:
#             st.markdown("### 🖼 생성된 이미지")
#             # Bytes 데이터를 Streamlit에 표시
#             st.image(st.session_state["image_bytes"], caption=st.session_state["image_prompt"], use_column_width=True)
            
#             # 이미지 다운로드 버튼
#             st.download_button(
#                 label="이미지 다운로드 (PNG)",
#                 data=st.session_state["image_bytes"],
#                 file_name="instagram_sdxl_banner.png",
#                 mime="image/png"
#             )
#             st.info("💡 생성된 이미지는 Stable Diffusion XL 모델로 제작되었으며, Hugging Face의 이용 약관을 따릅니다.")

#     else:
#         st.error("❌ Hugging Face API Token이 설정되지 않아 기능을 사용할 수 없습니다. `HF_API_TOKEN` 환경 변수를 확인하세요.")

# # ============================================================
# # 🖼 페이지 3: 이미지 합성/편집
# # ============================================================

# elif menu == "🖼️ 맞춤형 이미지 합성/편집":
#     st.title("🖼️ 맞춤형 이미지 합성/편집")
#     st.markdown(f"**AI 모델**: `Hugging Face Inference API (SDXL Inpainting 등)`")
#     st.markdown("💡 **참고**: 원본 이미지를 기반으로 새로운 요소를 추가하거나 스타일을 변경합니다. (Hugging Face API Token 필요)")
#     st.divider()

#     if HF_API_TOKEN:
#         with st.form("image_composition_form"):
#             st.subheader("🖼️ 원본 이미지 업로드")
#             uploaded_file = st.file_uploader(
#                 "합성할 이미지를 업로드하세요 (PNG, JPG)", 
#                 type=["png", "jpg", "jpeg"]
#             )

#             st.subheader("📝 합성/편집 지시")
#             composition_prompt = st.text_area(
#                 "어떻게 합성/편집하고 싶은지 자세히 설명해주세요 (한국어 권장)",
#                 height=150,
#                 placeholder="예: 이미지 속 인물에게 운동복을 입혀줘, 배경을 숲속으로 바꿔줘, 로고를 추가해 줘, 빛의 방향을 바꿔줘"
#             )
            
#             st.subheader("⚙️ 추가 설정 (선택 사항)")
#             col1, col2 = st.columns(2)
#             with col1:
#                 edit_mode = st.selectbox(
#                     "주요 합성 모드 선택",
#                     ["객체 추가/변경", "배경 변경", "스타일 변경", "객체 제거", "기타"],
#                     help="AI가 어떤 유형의 편집을 수행할지 이해하는 데 도움이 됩니다."
#                 )
#             with col2:
#                 output_size = st.selectbox(
#                     "결과물 이미지 크기",
#                     ["1024x1024 (정사각형)", "1792x1024 (스토리/릴스 세로)", "1024x1792 (피드 가로)"],
#                     help="인스타그램에 최적화된 크기를 선택하세요."
#                 )
            
#             negative_prompt_composition = st.text_area(
#                 "합성 결과물에서 제외하고 싶은 요소 (부정 프롬프트)",
#                 height=70,
#                 placeholder="예: 흐릿함, 왜곡된 글자, 이상한 신체, 저화질, 워터마크"
#             )

#             composition_submitted = st.form_submit_button("✨ 합성 이미지 생성", type="primary")

#         if composition_submitted and uploaded_file and composition_prompt:
#             # 파일을 바이트로 읽기
#             image_bytes = uploaded_file.getvalue()
            
#             # TODO: 선택된 `edit_mode`에 따라 적절한 Hugging Face 모델 및 API 호출 로직 분기
#             # 예를 들어, "객체 추가/변경"이면 Inpainting 모델 사용, "스타일 변경"이면 InstructPix2Pix 사용 등.
#             # 이 부분은 Hugging Face 모델에 대한 추가 연구 및 구현이 필요합니다.
#             st.info("💡 선택하신 모드에 따라 적합한 AI 모델을 호출하여 이미지를 합성합니다.")

#             with st.spinner("이미지를 합성 중입니다. 시간이 다소 소요될 수 있습니다. 🎨"):
#                 # 예시: Inpainting 모델 호출 (실제 API 엔드포인트는 모델마다 다름)
#                 # 이 예시에서는 SDXL base 모델을 사용하지만, Inpainting 전용 모델이 더 적합합니다.
#                 # 편의상 기존 generate_image_asset 함수를 재활용 (원본 이미지를 인코딩하여 함께 보내야 함)
#                 # 실제 Inpainting API는 원본 이미지, 마스크 이미지, 프롬프트를 받습니다.
#                 # 현재는 원본 이미지를 입력으로 받는 SDXL Inpainting 모델 API 호출 코드를 여기에 작성해야 합니다.
                
#                 # --- 임시 코드 (실제 Inpainting 모델 API 호출로 대체 필요) ---
#                 # 이 부분은 Hugging Face에 inpainting 모델 Inference API로 요청을 보내는 코드로 대체되어야 합니다.
#                 # SDXL Inpainting 모델의 Inference API는 input (원본 이미지), mask_image (마스크), prompt를 받습니다.
                
#                 # 현재는 uploaded_file을 input으로 받는 예시
#                 try:
#                     # 마스크가 없으므로 전체 이미지를 대상으로 프롬프트 적용 (Text-to-Image with Image)
#                     # 실제 Inpainting 모델 API는 마스크 이미지를 Base64로 받습니다.
#                     # 여기서는 간단히 Text-to-Image 모델에 프롬프트와 함께 이미지를 전달하는 형태로 가정합니다.
#                     # 이는 SDXL-Inpainting과는 다른 방식이므로 실제 사용 시 모델에 맞는 API 호출을 해야 합니다.

#                     # 임시로 SDXL Base 모델에 이미지 정보 + 프롬프트 전달 시도 (완벽한 합성은 아님)
#                     # 실제로는 inpainting 모델을 호출하고, mask를 생성해서 보내야 합니다.
#                     # https://huggingface.co/docs/api-inference/detailed_parameters#text-to-image-inpainting
                    
#                     # Hugging Face Inference API를 위한 headers 설정
#                     headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
                    
#                     # 이미지 파일을 Base64로 인코딩하여 payload에 포함
#                     encoded_image = base64.b64encode(image_bytes).decode("utf-8")
                    
#                     # 임시로 SDXL Text-to-Image 모델에 image_data를 inputs로 보냄 (합성 전용 아님)
#                     # 이 부분은 실제 Inpainting 또는 Image-to-Image 모델의 API 호출 구조에 맞춰 수정되어야 함
                    
#                     # ★★★ 실제 Inpainting 모델 API 호출 예시 (모델에 따라 파라미터 다름) ★★★
#                     # 예: "stabilityai/stable-diffusion-xl-base-1.0" 모델의 Inpainting 버전 사용 가정
#                     # 모델 엔드포인트 변경이 필요할 수 있습니다. (예: stabilityai/stable-diffusion-xl-inpainting-0.9)
#                     hf_image_api_url_for_composition = f"https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0" # Inpainting 모델로 변경 필요!

#                     # SDXL Inpainting API의 예상 payload (마스크가 없으면 작동 방식이 다를 수 있음)
#                     # 여기서는 일단 원본 이미지에 프롬프트를 적용하는 Image-to-Image 형태로 가정
#                     payload_img2img = {
#                         "inputs": encoded_image, # 원본 이미지 (Base64)
#                         "parameters": {
#                             "prompt": f"Based on the input image, {composition_prompt}",
#                             "negative_prompt": negative_prompt_composition if negative_prompt_composition else "low quality, blurry, text, watermark",
#                             "width": int(output_size.split('x')[0]),
#                             "height": int(output_size.split('x')[1]),
#                             "num_inference_steps": 30,
#                             "guidance_scale": 7.5 # 가이던스 스케일 (프롬프트 준수도)
#                         },
#                         "options": {
#                             "wait_for_model": True
#                         }
#                     }

#                     response = requests.post(hf_image_api_url_for_composition, headers=headers, json=payload_img2img)

#                     if response.status_code != 200:
#                         st.error(f"Hugging Face API 호출 오류 ({response.status_code}): {response.text}")
#                         composite_image_bytes = None
#                     else:
#                         composite_image_bytes = response.content

#                 except requests.exceptions.RequestException as e:
#                     st.error(f"네트워크 통신 중 오류가 발생했습니다: {e}")
#                     composite_image_bytes = None
#                 # --- 임시 코드 끝 ---


#             if composite_image_bytes:
#                 st.session_state["composite_image_bytes"] = composite_image_bytes
#                 st.session_state["composite_prompt"] = composition_prompt
#                 st.success("✅ 합성 이미지 생성 완료!")
                
#         if "composite_image_bytes" in st.session_state:
#             st.markdown("### 🖼️ 합성된 이미지")
#             st.image(st.session_state["composite_image_bytes"], caption=st.session_state["composite_prompt"], use_column_width=True)
            
#             st.download_button(
#                 label="합성 이미지 다운로드 (PNG)",
#                 data=st.session_state["composite_image_bytes"],
#                 file_name="composite_image.png",
#                 mime="image/png"
#             )
#             st.info("💡 Hugging Face Inference API를 통해 합성된 이미지입니다. 모델별 라이선스를 확인하세요.")
#     else:
#         st.error("❌ Hugging Face API Token이 설정되지 않아 이미지 합성 기능을 사용할 수 없습니다. `HF_API_TOKEN` 환경 변수를 확인하세요.")
