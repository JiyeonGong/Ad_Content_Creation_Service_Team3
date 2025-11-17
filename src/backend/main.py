# /home/spai0323/Ad_Content_Creation_Service_Team3/src/backend/main.py
# ============================================================
# 🚀 FastAPI 백엔드 API 서버 (게이트웨이 역할)
# - AI 추론 로직은 'services.py'로 위임
# - Pydantic 스키마 정의
# ============================================================

import base64
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field

# ⭐️ 1. AI 핵심 로직을 services 모듈에서 import
from . import services

# ============================================================
# 📜 Pydantic 스키마 정의 (데이터 구조)
# (이 부분은 변경 없음)
# ============================================================

class CaptionRequest(BaseModel):
    service_type: str = Field(..., description="서비스 종류 (예: 헬스장)")
    service_name: str = Field(..., description="제품/클래스 이름")
    features: str = Field(..., description="핵심 특징 및 장점")
    location: str = Field(..., description="지역")
    tone: str = Field(..., description="문체 스타일")

class CaptionResponse(BaseModel):
    output_text: str = Field(..., description="GPT-5 Mini가 생성한 원본 텍스트")

class T2IRequest(BaseModel):
    prompt: str = Field(..., description="이미지 생성 프롬프트")
    width: int = 1024
    height: int = 1024
    steps: int = 30

class T2IResponse(BaseModel):
    image_base64: str = Field(..., description="생성된 이미지의 Base64 인코딩 문자열 (PNG 형식)")

class I2IRequest(BaseModel):
    input_image_base64: str = Field(..., description="원본 이미지의 Base64 인코딩 문자열 (PNG/JPG)")
    prompt: str = Field(..., description="이미지 편집 프롬프트")
    strength: float = 0.75
    width: int = 1024
    height: int = 1024
    steps: int = 30

# ============================================================
# 🚀 FastAPI 앱 생성 및 이벤트 핸들러
# ============================================================

app = FastAPI(title="헬스케어 AI 콘텐츠 API")

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 SDXL 모델을 로드합니다. (services 모듈의 함수 호출)"""
    # ⭐️ 2. services의 초기화 함수 호출
    services.init_sdxl_pipelines()

# ============================================================
# 🚀 API 엔드포인트 정의 (핵심 로직은 'services'로 위임)
# ============================================================

@app.post("/api/caption", response_model=CaptionResponse)
async def create_caption(request: CaptionRequest):
    """
    GPT-5 Mini를 사용하여 홍보 문구와 해시태그를 생성합니다.
    """
    if not services.openai_client:
        raise HTTPException(status_code=503, detail="GPT-5 Mini 서비스가 준비되지 않았습니다.")
        
    info = {
        "service_type": request.service_type,
        "service_name": request.service_name,
        "features": request.features,
        "location": request.location,
    }

    try:
        # ⭐️ 3. services의 핵심 함수 호출
        output_text = services.generate_caption_core(info, request.tone)
        return CaptionResponse(output_text=output_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문구 생성 중 오류 발생: {e}")


@app.post("/api/generate_t2i", response_model=T2IResponse)
async def generate_t2i_image(request: T2IRequest):
    """
    SDXL T2I를 사용하여 텍스트 프롬프트 기반으로 이미지를 생성합니다.
    """
    if not services.T2I_PIPE:
        raise HTTPException(status_code=503, detail="SDXL T2I 모델이 로드되지 않았습니다.")

    try:
        # ⭐️ 3. services의 핵심 함수 호출
        image_bytes = await app.loop.run_in_executor(
            None, 
            services.generate_t2i_core,
            request.prompt,
            request.width,
            request.height,
            request.steps
        )
        
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        return T2IResponse(image_base64=image_base64)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"T2I 이미지 생성 중 오류 발생: {e}")


@app.post("/api/generate_i2i", response_model=T2IResponse) 
async def generate_i2i_image(request: I2IRequest):
    """
    SDXL I2I를 사용하여 원본 이미지를 기반으로 편집/합성 이미지를 생성합니다.
    """
    if not services.I2I_PIPE:
        raise HTTPException(status_code=503, detail="SDXL I2I 모델이 로드되지 않았습니다.")
        
    try:
        input_image_bytes = base64.b64decode(request.input_image_base64)
        
        # ⭐️ 3. services의 핵심 함수 호출
        image_bytes = await app.loop.run_in_executor(
            None,
            services.generate_i2i_core,
            input_image_bytes,
            request.prompt,
            request.strength,
            request.width,
            request.height,
            request.steps
        )
        
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        return T2IResponse(image_base64=image_base64)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"I2I 이미지 생성 중 오류 발생: {e}")

# 상태 확인용 엔드포인트 (services의 변수 확인)
@app.get("/status")
def get_status():
    return {
        "gpt_ready": services.openai_client is not None,
        "sdxl_t2i_ready": services.T2I_PIPE is not None,
        "sdxl_i2i_ready": services.I2I_PIPE is not None,
        "device": services.DEVICE
    }