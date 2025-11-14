# C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\healthcare\backend.py
# ============================================================
# ⚙️ FastAPI 백엔드 API 서버 (AI 추론 로직 담당)
# - GPT-5 Mini 호출 (OpenAI API)
# - SDXL T2I/I2I 로컬 추론 (Diffusers)
# - 이미지 데이터는 Base64로 인코딩/디코딩하여 전송
# ============================================================

import os
import io
import base64
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field

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

# SDXL 모델 초기화 (FastAPI 시작 시 한 번만 실행)
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

# FastAPI 앱 생성 및 모델 로딩
app = FastAPI(title="헬스케어 AI 콘텐츠 API")

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 SDXL 모델을 로드합니다."""
    init_sdxl_pipelines()

# ============================================================
# 📜 Pydantic 스키마 정의 (Request/Response 데이터 구조)
# ============================================================

class CaptionRequest(BaseModel):
    """문구 생성 요청 데이터 모델"""
    service_type: str = Field(..., description="서비스 종류 (예: 헬스장)")
    service_name: str = Field(..., description="제품/클래스 이름")
    features: str = Field(..., description="핵심 특징 및 장점")
    location: str = Field(..., description="지역")
    tone: str = Field(..., description="문체 스타일")

class CaptionResponse(BaseModel):
    """문구 생성 응답 데이터 모델"""
    output_text: str = Field(..., description="GPT-5 Mini가 생성한 원본 텍스트")

class T2IRequest(BaseModel):
    """T2I 이미지 생성 요청 데이터 모델"""
    prompt: str = Field(..., description="이미지 생성 프롬프트")
    width: int = 1024
    height: int = 1024
    steps: int = 30

class T2IResponse(BaseModel):
    """T2I 이미지 생성 응답 데이터 모델"""
    image_base64: str = Field(..., description="생성된 이미지의 Base64 인코딩 문자열 (PNG 형식)")

class I2IRequest(BaseModel):
    """I2I 이미지 편집/합성 요청 데이터 모델"""
    input_image_base64: str = Field(..., description="원본 이미지의 Base64 인코딩 문자열 (PNG/JPG)")
    prompt: str = Field(..., description="이미지 편집 프롬프트")
    strength: float = 0.75
    width: int = 1024
    height: int = 1024
    steps: int = 30

# ============================================================
# 🎯 AI 추론 함수 (기존 Streamlit 로직을 API 함수로 변환)
# ============================================================

def generate_caption_core(client, model, tone, info, hashtag_count=15) -> str:
    """GPT-5 Mini를 사용하여 문구 및 해시태그를 생성합니다."""
    if not client:
        raise ValueError("OpenAI 클라이언트가 초기화되지 않았습니다.")
        
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
        response = client.responses.create(
            model=model,
            input=prompt,
            reasoning={"effort":"minimal"},
            max_output_tokens=512, 
        )
        return response.output_text.strip()
    except Exception as e:
        print(f"GPT-5 Mini 호출 오류: {e}")
        raise

def generate_t2i_core(pipe: StableDiffusionXLPipeline, prompt: str, width: int, height: int, steps: int) -> bytes:
    """SDXL T2I를 사용하여 이미지를 생성하고 PNG 바이트를 반환합니다."""
    negative_prompt = "low quality, blurry, text, watermark, distorted, ugly, tiling, poorly drawn"
    
    result = pipe(
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

def generate_i2i_core(pipe: StableDiffusionXLImg2ImgPipeline, input_image_bytes: bytes, prompt: str, strength: float, width: int, height: int, steps: int) -> bytes:
    """SDXL I2I를 사용하여 이미지를 편집/합성하고 PNG 바이트를 반환합니다."""
    negative_prompt = "low quality, blurry, text, watermark, distorted, ugly, tiling, poorly drawn"
    
    # 1. 원본 이미지 로드 및 리사이즈 (I2I는 입력 이미지 크기에 영향을 받음)
    input_image = Image.open(io.BytesIO(input_image_bytes)).convert("RGB").resize((width, height))
    
    # 2. I2I 파이프라인 실행
    result = pipe(
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


# ============================================================
# 🚀 API 엔드포인트 정의
# ============================================================

@app.post("/api/caption", response_model=CaptionResponse)
async def create_caption(request: CaptionRequest):
    """
    GPT-5 Mini를 사용하여 홍보 문구와 해시태그를 생성합니다.
    """
    if not openai_client:
        raise HTTPException(status_code=503, detail="GPT-5 Mini 서비스가 준비되지 않았습니다.")
        
    info = {
        "service_type": request.service_type,
        "service_name": request.service_name,
        "features": request.features,
        "location": request.location,
        "event_info": "없음"
    }

    try:
        output_text = generate_caption_core(openai_client, MODEL_GPT_MINI, request.tone, info)
        return CaptionResponse(output_text=output_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문구 생성 중 오류 발생: {e}")


@app.post("/api/generate_t2i", response_model=T2IResponse)
async def generate_t2i_image(request: T2IRequest):
    """
    SDXL T2I를 사용하여 텍스트 프롬프트 기반으로 이미지를 생성합니다.
    """
    if not T2I_PIPE:
        raise HTTPException(status_code=503, detail="SDXL T2I 모델이 로드되지 않았습니다.")

    try:
        # 비동기적으로 GPU 작업을 실행하는 경우 (FastAPI의 기본 동작)
        image_bytes = await app.loop.run_in_executor(
            None, # 기본 Executor (쓰레드 풀)
            generate_t2i_core,
            T2I_PIPE,
            request.prompt,
            request.width,
            request.height,
            request.steps
        )
        
        # Base64로 인코딩하여 JSON 응답으로 반환
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        return T2IResponse(image_base64=image_base64)
    except Exception as e:
        # GPU 메모리 부족 등의 오류 처리
        raise HTTPException(status_code=500, detail=f"T2I 이미지 생성 중 오류 발생: {e}")


@app.post("/api/generate_i2i", response_model=T2IResponse) # I2I도 T2I와 동일하게 Base64 응답
async def generate_i2i_image(request: I2IRequest):
    """
    SDXL I2I를 사용하여 원본 이미지를 기반으로 편집/합성 이미지를 생성합니다.
    """
    if not I2I_PIPE:
        raise HTTPException(status_code=503, detail="SDXL I2I 모델이 로드되지 않았습니다.")
        
    try:
        # Base64 디코딩 (입력 이미지 바이트)
        input_image_bytes = base64.b64decode(request.input_image_base64)
        
        # 비동기적으로 GPU 작업을 실행하는 경우
        image_bytes = await app.loop.run_in_executor(
            None,
            generate_i2i_core,
            I2I_PIPE,
            input_image_bytes,
            request.prompt,
            request.strength,
            request.width,
            request.height,
            request.steps
        )
        
        # Base64로 인코딩하여 JSON 응답으로 반환
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        return T2IResponse(image_base64=image_base64)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"I2I 이미지 생성 중 오류 발생: {e}")

# 상태 확인용 엔드포인트
@app.get("/status")
def get_status():
    return {
        "gpt_ready": openai_client is not None,
        "sdxl_t2i_ready": T2I_PIPE is not None,
        "sdxl_i2i_ready": I2I_PIPE is not None,
        "device": DEVICE
    }