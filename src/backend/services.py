# # src/backend/services.py
# # ============================================================
# # ⚙️ AI 핵심 추론 엔진 (Web-Independent)
# # - GPT-5 Mini 호출 (OpenAI API)
# # - SDXL T2I/I2I 로컬 추론 (Diffusers)
# # - 이 파일은 FastAPI에 의존하지 않습니다.
# # ============================================================

# import os
# import io
# import base64
# from typing import Dict, Any, List

# # AI 모델 및 이미지 처리를 위한 라이브러리
# from openai import OpenAI
# from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline
# import torch
# from PIL import Image
# from dotenv import load_dotenv

# # ============================================================
# # 🌐 환경 설정 및 클라이언트 초기화
# # ============================================================

# # .env 파일 로딩 (프로젝트 루트 기준)
# load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# MODEL_GPT_MINI = "gpt-5-mini"

# # Hugging Face 모델 캐시 경로 설정
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# hf_cache_dir = os.path.join(project_root, "cache", "hf_models")
# os.makedirs(hf_cache_dir, exist_ok=True)

# # OpenAI 클라이언트 초기화
# openai_client = None
# if OPENAI_API_KEY:
#     try:
#         openai_client = OpenAI(api_key=OPENAI_API_KEY)
#     except Exception as e:
#         print(f"OpenAI 클라이언트 초기화 오류: {e}")
# else:
#     print("⚠️ OPENAI_API_KEY가 설정되지 않아 GPT 기능을 사용할 수 없습니다.")

# # SDXL 모델 변수 (초기화는 init 함수에서 수행)
# T2I_PIPE = None
# I2I_PIPE = None
# DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

# def init_sdxl_pipelines():
#     """SDXL T2I 및 I2I 파이프라인을 초기화하고 전역 변수에 저장합니다."""
#     global T2I_PIPE, I2I_PIPE
#     try:
#         print(f"SDXL 모델 로딩 중... (Device: {DEVICE}, Cache: {hf_cache_dir})")
#         dtype = torch.float16 if torch.cuda.is_available() else torch.float32

#         # T2I (Text-to-Image) 파이프라인
#         T2I_PIPE = StableDiffusionXLPipeline.from_pretrained(
#             MODEL_ID,
#             cache_dir=hf_cache_dir,
#             torch_dtype=dtype
#         ).to(DEVICE)
        
#         # I2I (Image-to-Image) 파이프라인
#         I2I_PIPE = StableDiffusionXLImg2ImgPipeline.from_pretrained(
#             MODEL_ID,
#             cache_dir=hf_cache_dir,
#             torch_dtype=dtype
#         ).to(DEVICE)
        
#         print("SDXL 모델 로딩 완료.")
#     except Exception as e:
#         print(f"SDXL 모델 로딩 실패: {e}")
#         T2I_PIPE = None
#         I2I_PIPE = None

# # ============================================================
# # 🎯 AI 추론 함수 (핵심 로직)
# # ============================================================

# def generate_caption_core(info: dict, tone: str) -> str:
#     """GPT-5 Mini를 사용하여 문구 및 해시태그를 생성합니다."""
#     if not openai_client:
#         raise ValueError("OpenAI 클라이언트가 초기화되지 않았습니다.")
        
#     prompt = f"""
# 당신은 헬스케어 소상공인을 위한 전문 인스타그램 콘텐츠 크리에이터입니다.
# 아래 정보를 바탕으로 인스타그램 게시물에 최적화된 콘텐츠를 생성해 주세요.

# 요청:
# 1. 인스타그램 홍보 문구 3개 작성
#     - 각 문구: 후킹 → 핵심 메시지 → CTA
#     - 이모티콘 사용
#     - 문체 스타일: {tone}
# 2. 해시태그 15개 추천 (중복 제거)

# [정보]
# 서비스 종류: {info['service_type']}
# 서비스명: {info['service_name']}
# 핵심 특징: {info['features']}
# 지역: {info['location']}
# 이벤트: 없음

# 출력 형식:
# 문구:
# 1. [문구1]
# 2. [문구2]
# 3. [문구3]

# 해시태그:
# #[태그1] #[태그2] ... #[태그N]
# """
#     try:
#         response = openai_client.responses.create(
#             model=MODEL_GPT_MINI,
#             input=prompt,
#             reasoning={"effort":"minimal"},
#             max_output_tokens=512, 
#         )
#         return response.output_text.strip()
#     except Exception as e:
#         print(f"GPT-5 Mini 호출 오류: {e}")
#         raise

# def generate_t2i_core(prompt: str, width: int, height: int, steps: int) -> bytes:
#     """SDXL T2I를 사용하여 이미지를 생성하고 PNG 바이트를 반환합니다."""
#     if not T2I_PIPE:
#         raise ValueError("T2I 파이프라인이 초기화되지 않았습니다.")

#     negative_prompt = "low quality, blurry, text, watermark, distorted, ugly, tiling, poorly drawn"
    
#     result = T2I_PIPE(
#         prompt=prompt, 
#         negative_prompt=negative_prompt, 
#         width=width, 
#         height=height, 
#         num_inference_steps=steps,
#         guidance_scale=7.5 # 기본값 사용
#     )
#     image = result.images[0]
    
#     # BytesIO로 변환 후 반환
#     buf = io.BytesIO()
#     image.save(buf, format="PNG")
#     return buf.getvalue()

# def generate_i2i_core(input_image_bytes: bytes, prompt: str, strength: float, width: int, height: int, steps: int) -> bytes:
#     """SDXL I2I를 사용하여 이미지를 편집/합성하고 PNG 바이트를 반환합니다."""
#     if not I2I_PIPE:
#         raise ValueError("I2I 파이프라인이 초기화되지 않았습니다.")

#     negative_prompt = "low quality, blurry, text, watermark, distorted, ugly, tiling, poorly drawn"
    
#     # 1. 원본 이미지 로드 및 리사이즈
#     input_image = Image.open(io.BytesIO(input_image_bytes)).convert("RGB").resize((width, height))
    
#     # 2. I2I 파이프라인 실행
#     result = I2I_PIPE(
#         prompt=prompt, 
#         image=input_image,
#         strength=strength,
#         negative_prompt=negative_prompt, 
#         num_inference_steps=steps,
#         guidance_scale=7.5
#     )
#     image = result.images[0]
    
#     # 3. BytesIO로 변환 후 반환
#     buf = io.BytesIO()
#     image.save(buf, format="PNG")
#     return buf.getvalue()


















# services.py (안정화 버전 - SDXL 폴백 포함)
import os
import io
import traceback
import base64
from typing import Optional

from openai import OpenAI
from diffusers import (
    StableDiffusionXLPipeline, 
    StableDiffusionXLImg2ImgPipeline,
    DiffusionPipeline,
    AutoPipelineForText2Image,
    AutoPipelineForImage2Image
)
import torch
from PIL import Image
from dotenv import load_dotenv

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_GPT_MINI = "gpt-5-mini"

# 🆕 모델 우선순위 설정 (환경변수로 제어 가능)
PRIMARY_MODEL = os.getenv("IMAGE_MODEL_ID", "black-forest-labs/FLUX.1-schnell")
FALLBACK_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
USE_FALLBACK = os.getenv("USE_SDXL_FALLBACK", "true").lower() == "true"

# HF cache location
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
hf_cache_dir = os.path.join(project_root, "cache", "hf_models")
os.makedirs(hf_cache_dir, exist_ok=True)

# Globals
openai_client: Optional[OpenAI] = None
T2I_PIPE = None
I2I_PIPE = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CURRENT_MODEL = None  # 실제 로드된 모델 추적

# Initialize OpenAI client
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"⚠️ OpenAI 초기화 실패: {e}")
        openai_client = None
else:
    print("⚠️ OPENAI_API_KEY 미설정 — GPT 기능 불가")

# ===========================
# Utility helpers
# ===========================
def align_to_64(x: int) -> int:
    """64의 배수로 정렬 (최소 64)"""
    try:
        xi = int(x)
    except Exception:
        xi = 64
    return max(64, (xi // 64) * 64)

def ensure_steps(steps: int) -> int:
    try:
        s = int(steps)
    except Exception:
        s = 1
    return max(1, s)

# ===========================
# 모델별 추론 파라미터
# ===========================
def get_model_params(model_id: str):
    """모델별 최적 파라미터 반환"""
    if "FLUX" in model_id.upper():
        return {
            "default_steps": 4,
            "use_negative_prompt": False,
            "guidance_scale": None,
            "supports_i2i": True
        }
    else:  # SDXL
        return {
            "default_steps": 30,
            "use_negative_prompt": True,
            "guidance_scale": 7.5,
            "supports_i2i": True
        }

# ===========================
# 🆕 모델 초기화 (안정화 + 폴백)
# ===========================
def init_image_pipelines():
    """
    이미지 생성 모델을 로드합니다.
    1. FLUX 시도 (성공 시 종료)
    2. 실패 시 SDXL로 폴백
    3. 이미 로드된 경우 스킵
    """
    global T2I_PIPE, I2I_PIPE, DEVICE, CURRENT_MODEL

    # 이미 로드되었으면 스킵
    if T2I_PIPE is not None:
        print(f"ℹ️ 이미지 파이프라인 이미 로드됨 (모델: {CURRENT_MODEL}) — 스킵")
        return

    print(f"📦 이미지 모델 로딩 시작 (Device={DEVICE})")
    dtype = torch.float16 if DEVICE == "cuda" else torch.float32

    # 1단계: PRIMARY 모델 시도 (FLUX)
    try:
        print(f"🔄 1차 시도: {PRIMARY_MODEL} 로딩 중...")
        
        T2I_PIPE = DiffusionPipeline.from_pretrained(
            PRIMARY_MODEL,
            cache_dir=hf_cache_dir,
            torch_dtype=dtype,
        ).to(DEVICE)
        
        # I2I 파이프라인 생성
        try:
            I2I_PIPE = AutoPipelineForImage2Image.from_pipe(T2I_PIPE)
        except:
            I2I_PIPE = T2I_PIPE  # 폴백
        
        CURRENT_MODEL = PRIMARY_MODEL
        print(f"✅ {PRIMARY_MODEL} 로딩 성공!")
        return  # 성공 시 종료
        
    except Exception as e:
        error_msg = str(e).lower()
        print(f"⚠️ {PRIMARY_MODEL} 로딩 실패: {e}")
        
        # HF 인증 필요 에러인지 확인
        if "401" in error_msg or "authentication" in error_msg or "gated" in error_msg:
            print("❗ Hugging Face 인증이 필요한 모델입니다.")
            print("해결 방법:")
            print("1. https://huggingface.co/black-forest-labs/FLUX.1-schnell 방문")
            print("2. 'Agree and access repository' 클릭")
            print("3. HF 토큰 생성: https://huggingface.co/settings/tokens")
            print("4. 터미널에서: huggingface-cli login")
        
        # 폴백 시도
        if not USE_FALLBACK:
            print("❌ 폴백이 비활성화되어 있습니다. USE_SDXL_FALLBACK=true 설정 필요")
            T2I_PIPE = None
            I2I_PIPE = None
            return

    # 2단계: FALLBACK 모델 시도 (SDXL)
    try:
        print(f"🔄 2차 시도: {FALLBACK_MODEL} (SDXL) 로딩 중...")
        
        T2I_PIPE = StableDiffusionXLPipeline.from_pretrained(
            FALLBACK_MODEL,
            cache_dir=hf_cache_dir,
            torch_dtype=dtype,
        ).to(DEVICE)

        I2I_PIPE = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            FALLBACK_MODEL,
            cache_dir=hf_cache_dir,
            torch_dtype=dtype,
        ).to(DEVICE)
        
        CURRENT_MODEL = FALLBACK_MODEL
        print(f"✅ {FALLBACK_MODEL} (폴백) 로딩 성공!")
        return
        
    except Exception as e2:
        print(f"❌ SDXL 폴백도 실패: {e2}")
        print(traceback.format_exc())
        
        # GPU OOM 시 CPU 폴백
        if DEVICE == "cuda" and "out of memory" in str(e2).lower():
            print("⚠️ GPU OOM 발생 — CPU 폴백 시도")
            try:
                DEVICE = "cpu"
                T2I_PIPE = StableDiffusionXLPipeline.from_pretrained(
                    FALLBACK_MODEL,
                    cache_dir=hf_cache_dir,
                    torch_dtype=torch.float32,
                ).to("cpu")
                
                I2I_PIPE = StableDiffusionXLImg2ImgPipeline.from_pretrained(
                    FALLBACK_MODEL,
                    cache_dir=hf_cache_dir,
                    torch_dtype=torch.float32,
                ).to("cpu")
                
                CURRENT_MODEL = FALLBACK_MODEL
                print("✅ SDXL CPU 로딩 완료 (느립니다)")
                return
                
            except Exception as e3:
                print(f"❌ CPU 폴백 최종 실패: {e3}")
        
        T2I_PIPE = None
        I2I_PIPE = None
        CURRENT_MODEL = None

# ===========================
# GPT로 한국어 프롬프트 번역/최적화
# ===========================
def optimize_prompt(text: str) -> str:
    """
    한국어 프롬프트를 영어로 번역 및 이미지 생성에 최적화
    SDXL의 경우 77 토큰 제한 고려
    """
    if not openai_client:
        return text
    
    # 이미 영어인 경우 스킵
    if all(ord(char) < 128 for char in text[:20]):
        return text
    
    try:
        # SDXL인 경우 짧게 요청
        if CURRENT_MODEL and "stable-diffusion" in CURRENT_MODEL.lower():
            constraint = "Keep it under 60 words (SDXL has 77 token limit)."
        else:
            constraint = "Keep it concise but descriptive (under 150 words)."
        
        system_prompt = f"""You are a professional prompt engineer for image generation AI.
Translate Korean marketing text to optimized English prompts.
Focus on visual elements, style, mood, and composition.
{constraint}
Output ONLY the English prompt, no explanations."""

        resp = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            input=f"Convert to image prompt:\n{text}",
            reasoning={"effort": "minimal"},
            max_output_tokens=200,
        )
        
        result = getattr(resp, "output_text", None) or str(resp)
        optimized = result.strip()
        print(f"🔄 프롬프트 최적화:\n  원본: {text[:80]}...\n  최적화: {optimized[:80]}...")
        return optimized
        
    except Exception as e:
        print(f"⚠️ 프롬프트 최적화 실패, 원본 사용: {e}")
        return text

# ===========================
# GPT-5 Mini: 문구 생성
# ===========================
def generate_caption_core(info: dict, tone: str) -> str:
    if not openai_client:
        raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다.")

    prompt = f"""
당신은 헬스케어 소상공인을 위한 전문 인스타그램 콘텐츠 크리에이터입니다.
아래 정보를 바탕으로 인스타그램 게시물에 최적화된 콘텐츠를 생성해 주세요.

요청:
1. 인스타그램 홍보 문구 3개 작성
    - 각 문구: 후킹 → 핵심 메시지 → CTA
    - 이모티콘 사용
    - 문체 스타일: {tone}
2. 해시태그 15개 추천 (중복 제거)

[정보]
서비스 종류: {info.get('service_type')}
서비스명: {info.get('service_name')}
핵심 특징: {info.get('features')}
지역: {info.get('location')}

출력 형식:
문구:
1. [문구1]
2. [문구2]
3. [문구3]

해시태그:
#[태그1] #[태그2] ... #[태그N]
"""
    try:
        resp = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            input=prompt,
            reasoning={"effort": "minimal"},
            max_output_tokens=512,
        )
        text = getattr(resp, "output_text", None) or str(resp)
        return text.strip()
    except Exception as e:
        print(f"🚨 GPT 호출 실패: {e}")
        raise

# ===========================
# 이미지 생성 (T2I)
# ===========================
def generate_t2i_core(prompt: str, width: int, height: int, steps: int) -> bytes:
    global T2I_PIPE, CURRENT_MODEL
    
    if T2I_PIPE is None:
        raise RuntimeError("이미지 파이프라인이 초기화되지 않았습니다.")
    
    # 프롬프트 최적화
    optimized_prompt = optimize_prompt(prompt)
    
    # 모델별 파라미터
    params = get_model_params(CURRENT_MODEL)
    
    # 공통 파라미터
    gen_params = {
        "prompt": optimized_prompt,
        "width": width,
        "height": height,
        "num_inference_steps": steps if steps > 1 else params["default_steps"],
    }
    
    # 조건부 파라미터 추가
    if params["use_negative_prompt"]:
        gen_params["negative_prompt"] = "low quality, blurry, text, watermark, distorted"
    
    if params["guidance_scale"] is not None:
        gen_params["guidance_scale"] = params["guidance_scale"]
    
    print(f"🎨 이미지 생성 중 (모델: {CURRENT_MODEL}, steps: {gen_params['num_inference_steps']})")
    
    result = T2I_PIPE(**gen_params)
    image = result.images[0]
    
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

# ===========================
# 이미지 편집 (I2I)
# ===========================
def generate_i2i_core(input_image_bytes: bytes, prompt: str, strength: float, 
                      width: int, height: int, steps: int) -> bytes:
    global I2I_PIPE, CURRENT_MODEL
    
    if I2I_PIPE is None:
        raise RuntimeError("이미지 파이프라인이 초기화되지 않았습니다.")
    
    # 프롬프트 최적화
    optimized_prompt = optimize_prompt(prompt)
    
    # 입력 이미지 준비
    input_image = Image.open(io.BytesIO(input_image_bytes)).convert("RGB").resize((width, height))
    
    # 모델별 파라미터
    params = get_model_params(CURRENT_MODEL)
    
    gen_params = {
        "prompt": optimized_prompt,
        "image": input_image,
        "strength": float(strength),
        "num_inference_steps": steps if steps > 1 else params["default_steps"],
    }
    
    if params["use_negative_prompt"]:
        gen_params["negative_prompt"] = "low quality, blurry, text, watermark, distorted"
    
    if params["guidance_scale"] is not None:
        gen_params["guidance_scale"] = params["guidance_scale"]
    
    print(f"✏️ 이미지 편집 중 (모델: {CURRENT_MODEL}, strength: {strength})")
    
    result = I2I_PIPE(**gen_params)
    image = result.images[0]
    
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()