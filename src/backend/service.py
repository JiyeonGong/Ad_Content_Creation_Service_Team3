# src/backend/services.py
# ============================================================
# ⚙️ AI 핵심 추론 엔진 (Web-Independent)
# - GPT-5 Mini 호출 (OpenAI API)
# - SDXL T2I/I2I 로컬 추론 (Diffusers)
# - 이 파일은 FastAPI에 의존하지 않습니다.
# ============================================================

import os
import io
import base64
from typing import Dict, Any, List

# AI 모델 및 이미지 처리를 위한 라이브러리
from openai import OpenAI
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline
import torch
from PIL import Image
from dotenv import load_dotenv

# ============================================================
# 🌐 환경 설정 및 클라이언트 초기화
# ============================================================

# .env 파일 로딩 (프로젝트 루트 기준)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_GPT_MINI = "gpt-5-mini"

# Hugging Face 모델 캐시 경로 설정
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
hf_cache_dir = os.path.join(project_root, "cache", "hf_models")
os.makedirs(hf_cache_dir, exist_ok=True)

# OpenAI 클라이언트 초기화
openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"OpenAI 클라이언트 초기화 오류: {e}")
else:
    print("⚠️ OPENAI_API_KEY가 설정되지 않아 GPT 기능을 사용할 수 없습니다.")

# SDXL 모델 변수 (초기화는 init 함수에서 수행)
T2I_PIPE = None
I2I_PIPE = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

def init_sdxl_pipelines():
    """SDXL T2I 및 I2I 파이프라인을 초기화하고 전역 변수에 저장합니다."""
    global T2I_PIPE, I2I_PIPE
    try:
        print(f"SDXL 모델 로딩 중... (Device: {DEVICE}, Cache: {hf_cache_dir})")
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        # T2I (Text-to-Image) 파이프라인
        T2I_PIPE = StableDiffusionXLPipeline.from_pretrained(
            MODEL_ID,
            cache_dir=hf_cache_dir,
            torch_dtype=dtype
        ).to(DEVICE)
        
        # I2I (Image-to-Image) 파이프라인
        I2I_PIPE = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            MODEL_ID,
            cache_dir=hf_cache_dir,
            torch_dtype=dtype
        ).to(DEVICE)
        
        print("SDXL 모델 로딩 완료.")
    except Exception as e:
        print(f"SDXL 모델 로딩 실패: {e}")
        T2I_PIPE = None
        I2I_PIPE = None

# ============================================================
# 🎯 AI 추론 함수 (핵심 로직)
# ============================================================

def generate_caption_core(info: dict, tone: str) -> str:
    """GPT-5 Mini를 사용하여 문구 및 해시태그를 생성합니다."""
    if not openai_client:
        raise ValueError("OpenAI 클라이언트가 초기화되지 않았습니다.")
        
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
서비스 종류: {info['service_type']}
서비스명: {info['service_name']}
핵심 특징: {info['features']}
지역: {info['location']}
이벤트: 없음

출력 형식:
문구:
1. [문구1]
2. [문구2]
3. [문구3]

해시태그:
#[태그1] #[태그2] ... #[태그N]
"""
    try:
        response = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            input=prompt,
            reasoning={"effort":"minimal"},
            max_output_tokens=512, 
        )
        return response.output_text.strip()
    except Exception as e:
        print(f"GPT-5 Mini 호출 오류: {e}")
        raise

def generate_t2i_core(prompt: str, width: int, height: int, steps: int) -> bytes:
    """SDXL T2I를 사용하여 이미지를 생성하고 PNG 바이트를 반환합니다."""
    if not T2I_PIPE:
        raise ValueError("T2I 파이프라인이 초기화되지 않았습니다.")

    negative_prompt = "low quality, blurry, text, watermark, distorted, ugly, tiling, poorly drawn"
    
    result = T2I_PIPE(
        prompt=prompt, 
        negative_prompt=negative_prompt, 
        width=width, 
        height=height, 
        num_inference_steps=steps,
        guidance_scale=7.5 # 기본값 사용
    )
    image = result.images[0]
    
    # BytesIO로 변환 후 반환
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

def generate_i2i_core(input_image_bytes: bytes, prompt: str, strength: float, width: int, height: int, steps: int) -> bytes:
    """SDXL I2I를 사용하여 이미지를 편집/합성하고 PNG 바이트를 반환합니다."""
    if not I2I_PIPE:
        raise ValueError("I2I 파이프라인이 초기화되지 않았습니다.")

    negative_prompt = "low quality, blurry, text, watermark, distorted, ugly, tiling, poorly drawn"
    
    # 1. 원본 이미지 로드 및 리사이즈
    input_image = Image.open(io.BytesIO(input_image_bytes)).convert("RGB").resize((width, height))
    
    # 2. I2I 파이프라인 실행
    result = I2I_PIPE(
        prompt=prompt, 
        image=input_image,
        strength=strength,
        negative_prompt=negative_prompt, 
        num_inference_steps=steps,
        guidance_scale=7.5
    )
    image = result.images[0]
    
    # 3. BytesIO로 변환 후 반환
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()