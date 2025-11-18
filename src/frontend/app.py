# # C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\healthcare\frontend.py
# # ============================================================
# # 💪 헬스케어 AI 콘텐츠 제작 앱 (Streamlit 프론트엔드)
# # - 모든 AI 로직은 FastAPI 백엔드(http://localhost:8000)로 위임
# # ============================================================

# import os
# import re
# import streamlit as st
# import requests
# from io import BytesIO
# from PIL import Image
# import base64
# import json

# # ============================================================
# # 🌐 환경 설정 및 클라이언트 설정
# # ============================================================

# # 백엔드 API 기본 URL (FastAPI 서버가 실행 중인 주소)
# API_BASE_URL = "http://localhost:8000"

# st.set_page_config(page_title="💪 헬스케어 AI 콘텐츠 제작", layout="wide")
# st.sidebar.title("메뉴")

# # 페이지 선택
# menu = st.sidebar.radio(
#     "페이지 선택",
#     ["📝 홍보 문구+해시태그 생성", "🖼 인스타그램 이미지 생성", "🖼️ 이미지 편집/합성"],
# )

# # 연결 모드 토글
# st.sidebar.markdown("---")
# connect_mode = st.sidebar.checkbox("🔗 페이지 연결 모드", value=True)
# st.sidebar.info("연결 모드 ON: 페이지1에서 생성된 문구를 자동으로 페이지2/3에 사용\n"
#                 "OFF: 각 페이지 독립 입력 사용")

# # ============================================================
# # 🧩 유틸리티 함수
# # ============================================================

# def validate_inputs(service_name, features, location):
#     """입력 필드 유효성 검사"""
#     if not service_name.strip() or not features.strip() or not location.strip():
#         st.warning("⚠️ 서비스 이름, 핵심 특징, 지역을 모두 입력해주세요.")
#         return False
#     return True

# def parse_output(output):
#     """GPT API 응답을 문구와 해시태그로 파싱 (기존 로직 유지)"""
#     captions, hashtags = [], ""
#     try:
#         m = re.search(r"문구:(.*?)해시태그:(.*)", output, re.S)
#         if m:
#             caption_text = m.group(1).strip()
#             hashtags = m.group(2).strip()
#             # 1. [문구] 형식에서 [문구]만 추출
#             captions = [line.split(".",1)[1].strip() if "." in line else line.strip()
#                          for line in caption_text.split("\n") if line.strip()]
#         else:
#             captions = [output]
#     except Exception:
#         captions = [output]
#     return captions, hashtags

# def caption_to_image_prompt(caption, style="Instagram banner"):
#     """문구를 이미지 생성 프롬프트로 변환"""
#     return f"{caption}, {style}, vibrant, professional, motivational"

# def base64_to_bytesio(base64_str: str) -> BytesIO:
#     """Base64 문자열을 BytesIO 객체로 디코딩합니다."""
#     image_bytes = base64.b64decode(base64_str)
#     return BytesIO(image_bytes)


# # ============================================================
# # 📞 API 호출 함수 (AI 로직은 백엔드로 위임)
# # ============================================================

# def call_caption_api(payload: dict[str, str]) -> str:
#     """FastAPI를 호출하여 문구를 생성합니다."""
#     url = f"{API_BASE_URL}/api/caption"
#     try:
#         # POST 요청을 보내고 JSON 응답을 받습니다.
#         response = requests.post(url, json=payload, timeout=60)
#         response.raise_for_status() # HTTP 오류가 발생하면 예외 발생
#         return response.json()["output_text"]
#     except requests.exceptions.RequestException as e:
#         st.error(f"❌ API 호출 오류 (문구 생성): 백엔드 서버가 실행 중인지 확인하세요. {e}")
#         return f"문구:\n1. [API 연결 오류]\n해시태그:\n#[API오류]"

# def call_t2i_api(payload: dict[str, any]) -> BytesIO:
#     """FastAPI를 호출하여 T2I 이미지를 생성하고 BytesIO 객체를 반환합니다."""
#     url = f"{API_BASE_URL}/api/generate_t2i"
#     try:
#         with st.spinner("이미지 생성 중... ⏳"):
#             response = requests.post(url, json=payload, timeout=120)
#             response.raise_for_status() 
#             # Base64 문자열을 받아 BytesIO로 디코딩
#             base64_str = response.json()["image_base64"]
#             return base64_to_bytesio(base64_str)
#     except requests.exceptions.RequestException as e:
#         st.error(f"❌ API 호출 오류 (T2I): 백엔드 서버가 실행 중인지 확인하세요. {e}")
#         return None
#     except Exception as e:
#         st.error(f"❌ 이미지 디코딩/처리 오류: {e}")
#         return None

# def call_i2i_api(payload: dict[str, any]) -> BytesIO:
#     """FastAPI를 호출하여 I2I 이미지를 생성하고 BytesIO 객체를 반환합니다."""
#     url = f"{API_BASE_URL}/api/generate_i2i"
#     try:
#         with st.spinner("합성/편집 중... ⏳"):
#             response = requests.post(url, json=payload, timeout=120)
#             response.raise_for_status() 
#             base64_str = response.json()["image_base64"]
#             return base64_to_bytesio(base64_str)
#     except requests.exceptions.RequestException as e:
#         st.error(f"❌ API 호출 오류 (I2I): 백엔드 서버가 실행 중인지 확인하세요. {e}")
#         return None
#     except Exception as e:
#         st.error(f"❌ 이미지 디코딩/처리 오류: {e}")
#         return None

# # ============================================================
# # 🔄 세션 상태 초기화
# # ============================================================

# if not connect_mode:
#     # 연결 모드 OFF 시 세션 상태 초기화
#     for key in ["captions","hashtags","generated_images","selected_caption"]:
#         if key in st.session_state:
#             del st.session_state[key]

# # ============================================================
# # 📝 페이지 1: 홍보 문구 + 해시태그
# # ============================================================

# if menu == "📝 홍보 문구+해시태그 생성":
#     st.title("📝 홍보 문구 & 해시태그 생성")
    
#     with st.form("content_form"):
#         # GPT API 호출에 필요한 입력 필드
#         service_type = st.selectbox(
#             "서비스 종류",
#             ["헬스장", "PT (개인 트레이닝)", "요가/필라테스", "건강 식품/보조제", "기타"],
#         )
#         location = st.text_input("지역", placeholder="예: 강남, 마포구, 온라인")
#         service_name = st.text_input("제품/클래스 이름", placeholder="예: 30일 다이어트 챌린지")
#         features = st.text_area("핵심 특징 및 장점", placeholder="예: 전문 PT와 함께하는 맞춤형 운동, 영양 관리 포함")
#         tone = st.selectbox("톤 선택", ["친근하고 동기부여","전문적이고 신뢰감","재미있고 트렌디","차분하고 감성적"])
#         submitted = st.form_submit_button("✨ 문구+해시태그 생성")

#     if submitted:
#         if validate_inputs(service_name, features, location):
#             # 💡 GPT-5 Mini 호출을 FastAPI 백엔드로 위임
#             payload = {
#                 "service_type": service_type,
#                 "service_name": service_name,
#                 "features": features,
#                 "location": location,
#                 "tone": tone
#             }
            
#             with st.spinner("AI가 홍보 문구를 생성하는 중... ⏳"):
#                 output = call_caption_api(payload)
#                 captions, hashtags = parse_output(output)
                
#                 st.session_state["captions"] = captions
#                 st.session_state["hashtags"] = hashtags

#     # 생성된 문구 표시 및 선택 (이하 동일)
#     if "captions" in st.session_state and st.session_state["captions"]:
#         st.markdown("### 💬 생성된 문구")
#         for i, caption in enumerate(st.session_state["captions"], 1):
#             st.write(f"**{i}.** {caption}")
        
#         st.markdown("---")
#         selected_idx = st.radio(
#             "다음 페이지에서 사용할 문구 선택:", 
#             range(len(st.session_state["captions"])),
#             format_func=lambda x: f"문구 {x+1}",
#             key="caption_selector"
#         )
#         st.session_state["selected_caption"] = st.session_state["captions"][selected_idx]
        
#         st.success(f"✅ 선택된 문구: {st.session_state['selected_caption'][:50]}...")
        
#         st.markdown("### 🔖 추천 해시태그")
#         st.code(st.session_state["hashtags"], language="")

# # ============================================================
# # 🖼 페이지 2: 문구 기반 이미지 3버전 생성 (T2I)
# # ============================================================

# elif menu == "🖼 인스타그램 이미지 생성":
#     st.title("🖼 문구 기반 이미지 생성 (3가지 버전)")
    
#     # 문구 입력/선택
#     selected_caption = ""
#     if connect_mode and "selected_caption" in st.session_state:
#         st.info(f"🔗 연결 모드: 페이지1에서 선택한 문구 사용\n\n**선택된 문구:** {st.session_state['selected_caption']}")
#         selected_caption = st.session_state["selected_caption"]
#     else:
#         if connect_mode:
#             st.warning("⚠️ 페이지1에서 문구를 먼저 생성하고 선택하세요.")
#         selected_caption = st.text_area("문구 입력 (연결 모드 OFF 또는 페이지1 문구 없음)", 
#                                          placeholder="예: 💪 새해 목표, 이번엔 꼭 이루자! 전문 PT와 함께하는 30일 다이어트 챌린지 🔥")
    
#     image_size = st.selectbox("이미지 크기", [
#         "1080x1350", # 4:5 사이즈
#         "1080x1080", # 1:1 사이즈
#         "1080x556", # 16:9 사이즈
#         ])
    
#     # 설정: 추론 단계 (steps)를 UI에서 제어할 수 있도록 추가
#     inference_steps = st.slider("추론 단계 (Steps)", min_value=0, max_value=50, value=10, step=5)

#     submitted = st.button("🖼 3가지 버전 생성", type="primary")

#     if submitted and selected_caption:
#         width, height = map(int, image_size.split("x"))
#         st.session_state["generated_images"] = []
        
#         progress_bar = st.progress(0)
        
#         for i in range(3):
#             # 각 버전마다 약간 다른 프롬프트
#             version_prompt = caption_to_image_prompt(
#                 f"{selected_caption} (style variation {i+1})"
#             )
            
#             # 💡 T2I 호출을 FastAPI 백엔드로 위임
#             payload = {
#                 "prompt": version_prompt, 
#                 "width": width, 
#                 "height": height, 
#                 "steps": inference_steps
#             }
            
#             image_bytes_io = call_t2i_api(payload)
            
#             if image_bytes_io:
#                 st.session_state["generated_images"].append({
#                     "prompt": version_prompt, 
#                     "bytes": image_bytes_io # BytesIO 객체 저장
#                 })
#                 progress_bar.progress((i+1)/3)
#             else:
#                 break

#         progress_bar.empty()
        
#         if st.session_state["generated_images"]:
#             st.success(f"✅ {len(st.session_state['generated_images'])}개 이미지 생성 완료!")
            
#             cols = st.columns(len(st.session_state["generated_images"]))
#             for idx, img_data in enumerate(st.session_state["generated_images"]):
#                 with cols[idx]:
#                     # BytesIO 객체를 Streamlit 이미지 위젯에 전달
#                     st.image(img_data["bytes"], caption=f"버전 {idx+1}", use_container_width=True)
#                     st.download_button(
#                         f"⬇️ 버전 {idx+1} 다운로드", 
#                         img_data["bytes"], 
#                         f"instagram_banner_v{idx+1}.png",
#                         "image/png",
#                         key=f"download_{idx}"
#                     )

# # ============================================================
# # 🖼 페이지 3: 이미지 편집/합성 (I2I)
# # ============================================================

# elif menu == "🖼️ 이미지 편집/합성":
#     st.title("🖼️ 이미지 편집 / 합성 (Image-to-Image)")
    
#     st.info("💡 이 기능은 **업로드된 이미지를 기반**으로 문구와 추가 지시를 반영하여 새로운 스타일의 이미지를 생성합니다.")
    
#     # 1. 이미지 소스 선택
#     uploaded_file = st.file_uploader("업로드 이미지", type=["png","jpg","jpeg"])
#     preloaded_images = st.session_state.get("generated_images", [])
    
#     image_bytes = None
#     input_image_display = None

#     if uploaded_file:
#         image_bytes = uploaded_file.getvalue()
#         input_image_display = image_bytes
#     elif preloaded_images and connect_mode:
#         st.info("🔗 연결 모드: 페이지2에서 생성된 이미지 사용")
#         image_idx = st.selectbox("사용할 이미지 선택", 
#                                  range(len(preloaded_images)),
#                                  format_func=lambda x: f"버전 {x+1}")
#         # BytesIO 객체에서 실제 바이트를 가져옵니다.
#         image_bytes = preloaded_images[image_idx]["bytes"].getvalue() 
#         input_image_display = image_bytes
    
#     if input_image_display:
#          st.image(input_image_display, caption="선택된 이미지", width=300)
#     else:
#         st.warning("⚠️ 이미지를 업로드하거나 페이지2에서 이미지를 먼저 생성하세요.")
    
#     # 2. 문구 소스 선택
#     selected_caption = ""
#     if connect_mode and "selected_caption" in st.session_state:
#         st.info(f"🔗 사용할 문구: {st.session_state['selected_caption']}")
#         selected_caption = st.session_state["selected_caption"]
#     else:
#         selected_caption = st.text_input("편집에 반영할 문구 입력", 
#                                          placeholder="예: 💪 새해 목표, 이번엔 꼭 이루자!")
    
#     # 3. I2I 파라미터 및 프롬프트
#     denoising_strength = st.slider(
#         "✨ 변화 강도 (Strength)", 
#         min_value=0.0, max_value=1.0, value=0.75, step=0.05,
#         help="0.0에 가까울수록 원본 이미지 유지, 1.0에 가까울수록 프롬프트에 따른 새로운 이미지 생성"
#     )
#     edit_prompt = st.text_area("추가 편집 지시 (선택)", 
#                                  placeholder="예: 더 밝고 활기찬 분위기로, 파란색 배경 추가")
#     output_size = st.selectbox("출력 이미지 크기", [
#         "1080x1350", # 4:5 사이즈
#         "1080x1080", # 1:1 사이즈
#         "1080x556", # 16:9 사이즈
#         ])
    
#     submitted = st.button("✨ 합성/편집 이미지 생성", type="primary")

#     if submitted:
#         if not image_bytes:
#             st.error("❌ 이미지를 먼저 업로드하거나 페이지2에서 생성하세요.")
#         elif not selected_caption:
#             st.error("❌ 문구를 입력하세요.")
#         else:
#             width, height = map(int, output_size.split('x'))
            
#             # 최종 프롬프트 생성
#             final_prompt = caption_to_image_prompt(selected_caption)
#             if edit_prompt:
#                 final_prompt += f", {edit_prompt}"
            
#             # 💡 I2I 호출을 FastAPI 백엔드로 위임
#             # 1. 입력 이미지 바이트를 Base64로 인코딩
#             input_image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
#             # 2. API Payload 생성
#             payload = {
#                 "input_image_base64": input_image_base64,
#                 "prompt": final_prompt, 
#                 "strength": denoising_strength,
#                 "width": width, 
#                 "height": height,
#                 "steps": 30
#             }
            
#             edited_image_bytes_io = call_i2i_api(payload)
            
#             if edited_image_bytes_io:
#                 col1, col2 = st.columns(2)
                
#                 # Original Image Display 
#                 with col1:
#                     st.subheader("원본 이미지")
#                     st.image(image_bytes, use_container_width=True) 

#                 # Edited Image Display
#                 with col2:
#                     st.subheader("편집된 이미지")
#                     # BytesIO 객체를 Streamlit 이미지 위젯에 전달
#                     st.image(edited_image_bytes_io, caption="I2I 결과", use_container_width=True)
                
#                 st.success("✅ 이미지 생성 완료!")
#                 st.download_button("⬇️ 편집 이미지 다운로드", 
#                                    edited_image_bytes_io, # BytesIO 객체 전달
#                                    "edited_image.png",
#                                    "image/png")
























# /home/spai0323/Ad_Content_Creation_Service_Team3/src/frontend/app.py
# ============================================================
# 💪 헬스케어 AI 콘텐츠 제작 앱 (Streamlit 프론트엔드)
# - 모든 AI 로직은 FastAPI 백엔드(http://localhost:8000)로 위임
# - 개선: steps 최소값 1, 64-pixel 정렬, GPU OOM 시 폴백(retry)
# ============================================================

import os
import re
import streamlit as st
import requests
from io import BytesIO
from PIL import Image
import base64
import json
import math
from typing import Optional

# ============================================================
# 🌐 환경 설정 및 클라이언트 설정
# ============================================================
API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="💪 헬스케어 AI 콘텐츠 제작", layout="wide")
st.sidebar.title("메뉴")

# 페이지 선택
menu = st.sidebar.radio(
    "페이지 선택",
    ["📝 홍보 문구+해시태그 생성", "🖼 인스타그램 이미지 생성", "🖼️ 이미지 편집/합성"],
)

# 연결 모드 토글
st.sidebar.markdown("---")
connect_mode = st.sidebar.checkbox("🔗 페이지 연결 모드", value=True)
st.sidebar.info("연결 모드 ON: 페이지1에서 생성된 문구를 자동으로 페이지2/3에 사용\n"
                "OFF: 각 페이지 독립 입력 사용")

# ============================================================
# 🧩 유틸리티 함수
# ============================================================
def validate_inputs(service_name, features, location):
    """입력 필드 유효성 검사"""
    if not service_name.strip() or not features.strip() or not location.strip():
        st.warning("⚠️ 서비스 이름, 핵심 특징, 지역을 모두 입력해주세요.")
        return False
    return True

def parse_output(output):
    """GPT API 응답을 문구와 해시태그로 파싱 (기존 로직 유지)"""
    captions, hashtags = [], ""
    try:
        m = re.search(r"문구:(.*?)해시태그:(.*)", output, re.S)
        if m:
            caption_text = m.group(1).strip()
            hashtags = m.group(2).strip()
            # 1. [문구] 형식에서 [문구]만 추출
            captions = [line.split(".",1)[1].strip() if "." in line else line.strip()
                         for line in caption_text.split("\n") if line.strip()]
        else:
            captions = [output]
    except Exception:
        captions = [output]
    return captions, hashtags

def caption_to_image_prompt(caption, style="Instagram banner"):
    """문구를 이미지 생성 프롬프트로 변환"""
    return f"{caption}, {style}, vibrant, professional, motivational"

def base64_to_bytesio(base64_str: str) -> BytesIO:
    """Base64 문자열을 BytesIO 객체로 디코딩합니다."""
    image_bytes = base64.b64decode(base64_str)
    return BytesIO(image_bytes)

def align64(val: int) -> int:
    """값을 64의 배수로 정렬. 최소 64는 보장."""
    try:
        v = int(val)
    except Exception:
        v = 64
    aligned = max(64, (v // 64) * 64)
    # If v < 64 then returns 64; if v not multiple it floors to multiple
    return aligned

def human_readable_size(w: int, h: int) -> str:
    return f"{w}x{h}"

# ============================================================
# 📞 API 호출 함수 (AI 로직은 백엔드로 위임)
#    - T2I/I2I 호출 실패 시 폴백(retry) 로직 포함
# ============================================================
def call_caption_api(payload: dict) -> str:
    """FastAPI를 호출하여 문구를 생성합니다."""
    url = f"{API_BASE_URL}/api/caption"
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["output_text"]
    except requests.exceptions.RequestException as e:
        st.error(f"❌ API 호출 오류 (문구 생성): 백엔드 서버가 실행 중인지 확인하세요. {e}")
        return f"문구:\n1. [API 연결 오류]\n해시태그:\n#[API오류]"

def _post_json(url: str, payload: dict, timeout: int = 300) -> requests.Response:
    """보조: POST JSON 요청 (예외는 그대로 던짐)"""
    return requests.post(url, json=payload, timeout=timeout)

def call_t2i_api(payload: dict, fallback_attempts: int = 2) -> Optional[BytesIO]:
    """
    FastAPI를 호출하여 T2I 이미지를 생성하고 BytesIO 객체를 반환합니다.
    실패(특히 GPU OOM)에 대해서는 해상도를 절반으로 줄여 재시도합니다.
    """
    url = f"{API_BASE_URL}/api/generate_t2i"
    current_payload = payload.copy()

    for attempt in range(fallback_attempts + 1):
        try:
            with st.spinner(f"이미지 생성 중... (시도 {attempt+1}/{fallback_attempts+1}) ⏳"):
                response = _post_json(url, current_payload)
                response.raise_for_status()
                base64_str = response.json()["image_base64"]
                return base64_to_bytesio(base64_str)
        except requests.exceptions.HTTPError as he:
            code = he.response.status_code if he.response is not None else None
            detail = ""
            try:
                detail = he.response.json().get("detail", "") if he.response is not None else ""
            except Exception:
                detail = he.response.text if he.response is not None else str(he)
            st.warning(f"API 오류 (HTTP {code}): {detail}")
            # GPU OOM 또는 메모리 관련 503이면 해상도 폴백 시도
            if code == 503 and ("메모리" in str(detail) or "GPU" in str(detail) or "cuda" in str(detail).lower()):
                if attempt < fallback_attempts:
                    # 절반 해상도로 줄이기
                    w = current_payload.get("width", 1024)
                    h = current_payload.get("height", 1024)
                    new_w = max(64, w // 2)
                    new_h = max(64, h // 2)
                    new_w = align64(new_w)
                    new_h = align64(new_h)
                    st.info(f"⚠️ GPU 메모리 부족으로 해상도를 낮춰 재시도합니다: {w}x{h} → {new_w}x{new_h}")
                    current_payload["width"] = new_w
                    current_payload["height"] = new_h
                    # continue to next attempt
                    continue
            # 다른 HTTP 에러면 중단
            st.error(f"❌ 이미지 생성 실패: HTTP {code} - {detail}")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"❌ API 호출 오류 (T2I): 백엔드 서버가 실행 중인지 확인하세요. {e}")
            return None
        except Exception as e:
            st.error(f"❌ 이미지 디코딩/처리 오류: {e}")
            return None
    # 모든 재시도 실패
    st.error("❌ 이미지 생성에 실패했습니다 (모든 재시도 소진).")
    return None

def call_i2i_api(payload: dict, fallback_attempts: int = 2) -> Optional[BytesIO]:
    """
    FastAPI를 호출하여 I2I 이미지를 생성하고 BytesIO 객체를 반환합니다.
    실패시 해상도 폴백(retry) 로직 포함.
    """
    url = f"{API_BASE_URL}/api/generate_i2i"
    current_payload = payload.copy()

    for attempt in range(fallback_attempts + 1):
        try:
            with st.spinner(f"합성/편집 중... (시도 {attempt+1}/{fallback_attempts+1}) ⏳"):
                response = _post_json(url, current_payload)
                response.raise_for_status()
                base64_str = response.json()["image_base64"]
                return base64_to_bytesio(base64_str)
        except requests.exceptions.HTTPError as he:
            code = he.response.status_code if he.response is not None else None
            detail = ""
            try:
                detail = he.response.json().get("detail", "") if he.response is not None else ""
            except Exception:
                detail = he.response.text if he.response is not None else str(he)
            st.warning(f"API 오류 (HTTP {code}): {detail}")
            if code == 503 and ("메모리" in str(detail) or "GPU" in str(detail) or "cuda" in str(detail).lower()):
                if attempt < fallback_attempts:
                    w = current_payload.get("width", 1024)
                    h = current_payload.get("height", 1024)
                    new_w = max(64, w // 2)
                    new_h = max(64, h // 2)
                    new_w = align64(new_w)
                    new_h = align64(new_h)
                    st.info(f"⚠️ GPU 메모리 부족으로 해상도를 낮춰 재시도합니다: {w}x{h} → {new_w}x{new_h}")
                    current_payload["width"] = new_w
                    current_payload["height"] = new_h
                    continue
            st.error(f"❌ 합성/편집 실패: HTTP {code} - {detail}")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"❌ API 호출 오류 (I2I): 백엔드 서버가 실행 중인지 확인하세요. {e}")
            return None
        except Exception as e:
            st.error(f"❌ 이미지 디코딩/처리 오류: {e}")
            return None
    st.error("❌ 합성/편집에 실패했습니다 (모든 재시도 소진).")
    return None

# ============================================================
# 🔄 세션 상태 초기화
# ============================================================
if not connect_mode:
    # 연결 모드 OFF 시 세션 상태 초기화
    for key in ["captions","hashtags","generated_images","selected_caption"]:
        if key in st.session_state:
            del st.session_state[key]

# ============================================================
# 📝 페이지 1: 홍보 문구 + 해시태그
# ============================================================
if menu == "📝 홍보 문구+해시태그 생성":
    st.title("📝 홍보 문구 & 해시태그 생성")
    
    with st.form("content_form"):
        # GPT API 호출에 필요한 입력 필드
        service_type = st.selectbox(
            "서비스 종류",
            ["헬스장", "PT (개인 트레이닝)", "요가/필라테스", "건강 식품/보조제", "기타"],
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

    # 생성된 문구 표시 및 선택
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

# ============================================================
# 🖼 페이지 2: 문구 기반 이미지 3버전 생성 (T2I)
# ============================================================
elif menu == "🖼 인스타그램 이미지 생성":
    st.title("🖼 문구 기반 이미지 생성 (3가지 버전)")
    
    # 문구 입력/선택
    selected_caption = ""
    if connect_mode and "selected_caption" in st.session_state:
        st.info(f"🔗 연결 모드: 페이지1에서 선택한 문구 사용\n\n**선택된 문구:** {st.session_state['selected_caption']}")
        selected_caption = st.session_state["selected_caption"]
    else:
        if connect_mode:
            st.warning("⚠️ 페이지1에서 문구를 먼저 생성하고 선택하세요.")
        selected_caption = st.text_area("문구 입력 (연결 모드 OFF 또는 페이지1 문구 없음)", 
                                         placeholder="예: 💪 새해 목표, 이번엔 꼭 이루자! 전문 PT와 함께하는 30일 다이어트 챌린지 🔥")
    
    image_size = st.selectbox("이미지 크기 (원본값 — 내부적으로 64배수로 정렬됩니다)", [
        "1080x1350", # 4:5 사이즈
        "1080x1080", # 1:1 사이즈
        "1080x556",  # 16:9-ish
        "1024x1024", # 권장 SDXL 기본
    ])
    
    # 추론 단계 (steps) 최소값 1로 변경
    inference_steps = st.slider("추론 단계 (Steps)", min_value=1, max_value=50, value=10, step=1)

    submitted = st.button("🖼 3가지 버전 생성", type="primary")

    if submitted and selected_caption:
        # parse selected size and align to 64
        width, height = map(int, image_size.split("x"))
        aligned_w = align64(width)
        aligned_h = align64(height)
        if aligned_w != width or aligned_h != height:
            st.info(f"입력 해상도 {width}x{height} → 64배수로 정렬: {aligned_w}x{aligned_h}")

        st.session_state["generated_images"] = []
        progress_bar = st.progress(0)

        for i in range(3):
            version_prompt = caption_to_image_prompt(
                f"{selected_caption} (style variation {i+1})"
            )
            payload = {
                "prompt": version_prompt, 
                "width": aligned_w, 
                "height": aligned_h, 
                "steps": inference_steps
            }
            
            image_bytes_io = call_t2i_api(payload)
            
            if image_bytes_io:
                st.session_state["generated_images"].append({
                    "prompt": version_prompt, 
                    "bytes": image_bytes_io
                })
                progress_bar.progress((i+1)/3)
            else:
                # 실패 시 루프 중단 (이미지 생성 실패)
                break

        progress_bar.empty()
        
        if st.session_state.get("generated_images"):
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
        else:
            st.error("❌ 이미지 생성에 실패했습니다. 백엔드 로그를 확인하세요.")

# ============================================================
# 🖼 페이지 3: 이미지 편집/합성 (I2I)
# ============================================================
elif menu == "🖼️ 이미지 편집/합성":
    st.title("🖼️ 이미지 편집 / 합성 (Image-to-Image)")
    
    st.info("💡 업로드된 이미지를 기반으로 문구와 추가 지시를 반영하여 새로운 스타일의 이미지를 생성합니다.")
    
    # 이미지 소스 선택
    uploaded_file = st.file_uploader("업로드 이미지", type=["png","jpg","jpeg"])
    preloaded_images = st.session_state.get("generated_images", [])
    
    image_bytes = None
    input_image_display = None

    if uploaded_file:
        image_bytes = uploaded_file.getvalue()
        input_image_display = image_bytes
    elif preloaded_images and connect_mode:
        st.info("🔗 연결 모드: 페이지2에서 생성된 이미지 사용")
        image_idx = st.selectbox("사용할 이미지 선택", 
                                 range(len(preloaded_images)),
                                 format_func=lambda x: f"버전 {x+1}")
        image_bytes = preloaded_images[image_idx]["bytes"].getvalue() 
        input_image_display = image_bytes
    
    if input_image_display:
         st.image(input_image_display, caption="선택된 이미지", width=300)
    else:
        st.warning("⚠️ 이미지를 업로드하거나 페이지2에서 이미지를 먼저 생성하세요.")
    
    # 문구 소스 선택
    selected_caption = ""
    if connect_mode and "selected_caption" in st.session_state:
        st.info(f"🔗 사용할 문구: {st.session_state['selected_caption']}")
        selected_caption = st.session_state["selected_caption"]
    else:
        selected_caption = st.text_input("편집에 반영할 문구 입력", 
                                         placeholder="예: 💪 새해 목표, 이번엔 꼭 이루자!")
    
    denoising_strength = st.slider(
        "✨ 변화 강도 (Strength)", 
        min_value=0.0, max_value=1.0, value=0.75, step=0.05,
        help="0.0에 가까울수록 원본 이미지 유지, 1.0에 가까울수록 프롬프트에 따른 새로운 이미지 생성"
    )
    edit_prompt = st.text_area("추가 편집 지시 (선택)", 
                                 placeholder="예: 더 밝고 활기찬 분위기로, 파란색 배경 추가")
    output_size = st.selectbox("출력 이미지 크기 (원본값 — 내부적으로 64배수로 정렬됩니다)", [
        "1080x1350", "1080x1080", "1080x556", "1024x1024"
    ])
    
    submitted = st.button("✨ 합성/편집 이미지 생성", type="primary")

    if submitted:
        if not image_bytes:
            st.error("❌ 이미지를 먼저 업로드하거나 페이지2에서 생성하세요.")
        elif not selected_caption:
            st.error("❌ 문구를 입력하세요.")
        else:
            width, height = map(int, output_size.split('x'))
            aligned_w = align64(width)
            aligned_h = align64(height)
            if aligned_w != width or aligned_h != height:
                st.info(f"입력 해상도 {width}x{height} → 64배수로 정렬: {aligned_w}x{aligned_h}")

            final_prompt = caption_to_image_prompt(selected_caption)
            if edit_prompt:
                final_prompt += f", {edit_prompt}"
            
            input_image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            payload = {
                "input_image_base64": input_image_base64,
                "prompt": final_prompt, 
                "strength": denoising_strength,
                "width": aligned_w, 
                "height": aligned_h,
                "steps": 30
            }
            
            edited_image_bytes_io = call_i2i_api(payload)
            
            if edited_image_bytes_io:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("원본 이미지")
                    st.image(image_bytes, use_container_width=True) 
                with col2:
                    st.subheader("편집된 이미지")
                    st.image(edited_image_bytes_io, caption="I2I 결과", use_container_width=True)
                
                st.success("✅ 이미지 생성 완료!")
                st.download_button("⬇️ 편집 이미지 다운로드", 
                                   edited_image_bytes_io,
                                   "edited_image.png",
                                   "image/png")
            else:
                st.error("❌ 편집/합성에 실패했습니다. 백엔드 로그를 확인하세요.")