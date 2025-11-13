# C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\healthcare\backend.py

# ========================================
# 프론트엔드/벡엔드 분리 버전
# ========================================

import os
import re
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline
import torch
from io import BytesIO
from PIL import Image

# ===============================
# 🌍 환경 변수 및 클라이언트 초기화
# ===============================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_GPT_MINI = "gpt-5-mini"
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ===============================
# FastAPI 앱 & CORS
# ===============================
app = FastAPI(title="Healthcare AI Content API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시 도메인 제한 가능
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# GPT-5 Mini 문구 생성
# ===============================
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

@app.post("/generate_captions")
def generate_captions(
    service_name: str = Form(...),
    features: str = Form(...),
    tone: str = Form("친근하고 동기부여")
):
    if not openai_client:
        return {"error": "OpenAI API 키가 설정되지 않았습니다."}

    prompt = f"""
당신은 헬스케어 소상공인을 위한 전문 인스타그램 콘텐츠 크리에이터입니다.
아래 정보를 바탕으로 인스타그램 게시물에 최적화된 콘텐츠를 생성해 주세요.

요청:
1. 인스타그램 홍보 문구 3개 작성
    - 각 문구: 후킹 → 핵심 메시지 → CTA
    - 이모티콘 사용
    - 문체 스타일: {tone}

[정보]
서비스 종류: 헬스/피트니스
서비스명: {service_name}
핵심 특징: {features}
지역: 전국/온라인
이벤트: 없음

출력 형식:
문구:
1. [문구1]
2. [문구2]
3. [문구3]

해시태그:
#[태그1] #[태그2] ... #[태그N]
"""
    response = openai_client.responses.create(
        model=MODEL_GPT_MINI,
        input=prompt,
        reasoning={"effort":"minimal"},
        max_output_tokens=512
    )
    captions, hashtags = parse_output(response.output_text.strip())
    return {"captions": captions, "hashtags": hashtags}

# ===============================
# SDXL T2I
# ===============================
pipe_t2i = None
def init_sdxl_t2i():
    global pipe_t2i
    if pipe_t2i is None:
        pipe_t2i = StableDiffusionXLPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        ).to("cuda" if torch.cuda.is_available() else "cpu")
    return pipe_t2i

@app.post("/generate_image")
def generate_image(prompt: str = Form(...), width: int = Form(1024), height: int = Form(1024), steps: int = Form(30)):
    pipe = init_sdxl_t2i()
    negative_prompt = "low quality, blurry, text, watermark, distorted"
    result = pipe(prompt=prompt, negative_prompt=negative_prompt, width=width, height=height, num_inference_steps=steps)
    buf = BytesIO()
    result.images[0].save(buf, format="PNG")
    buf.seek(0)
    return {"image_bytes": buf.getvalue()}

# ===============================
# SDXL I2I
# ===============================
pipe_i2i = None
def init_sdxl_i2i():
    global pipe_i2i
    if pipe_i2i is None:
        pipe_i2i = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        ).to("cuda" if torch.cuda.is_available() else "cpu")
    return pipe_i2i

@app.post("/edit_image")
def edit_image(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    strength: float = Form(0.75),
    width: int = Form(1024),
    height: int = Form(1024),
    steps: int = Form(30)
):
    pipe = init_sdxl_i2i()
    input_image = Image.open(BytesIO(image.file.read())).convert("RGB").resize((width, height))
    negative_prompt = "low quality, blurry, text, watermark, distorted"
    
    result = pipe(prompt=prompt, image=input_image, strength=strength, negative_prompt=negative_prompt, num_inference_steps=steps)
    buf = BytesIO()
    result.images[0].save(buf, format="PNG")
    buf.seek(0)
    return {"image_bytes": buf.getvalue()}