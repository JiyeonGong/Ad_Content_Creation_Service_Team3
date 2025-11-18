# # src/backend/main.py
# # ============================================================
# # 🚀 FastAPI 백엔드 API 서버 (게이트웨이 역할)
# # - AI 추론 로직은 'services.py'로 위임
# # - Pydantic 스키마 정의
# # ============================================================

# import base64
# from fastapi import FastAPI, HTTPException, Body
# from pydantic import BaseModel, Field

# # ⭐️ 1. AI 핵심 로직을 services 모듈에서 import
# from . import services

# # ============================================================
# # 📜 Pydantic 스키마 정의 (데이터 구조)
# # (이 부분은 변경 없음)
# # ============================================================

# class CaptionRequest(BaseModel):
#     service_type: str = Field(..., description="서비스 종류 (예: 헬스장)")
#     service_name: str = Field(..., description="제품/클래스 이름")
#     features: str = Field(..., description="핵심 특징 및 장점")
#     location: str = Field(..., description="지역")
#     tone: str = Field(..., description="문체 스타일")

# class CaptionResponse(BaseModel):
#     output_text: str = Field(..., description="GPT-5 Mini가 생성한 원본 텍스트")

# class T2IRequest(BaseModel):
#     prompt: str = Field(..., description="이미지 생성 프롬프트")
#     width: int = 1024
#     height: int = 1024
#     steps: int = 30

# class T2IResponse(BaseModel):
#     image_base64: str = Field(..., description="생성된 이미지의 Base64 인코딩 문자열 (PNG 형식)")

# class I2IRequest(BaseModel):
#     input_image_base64: str = Field(..., description="원본 이미지의 Base64 인코딩 문자열 (PNG/JPG)")
#     prompt: str = Field(..., description="이미지 편집 프롬프트")
#     strength: float = 0.75
#     width: int = 1024
#     height: int = 1024
#     steps: int = 30

# # ============================================================
# # 🚀 FastAPI 앱 생성 및 이벤트 핸들러
# # ============================================================

# app = FastAPI(title="헬스케어 AI 콘텐츠 API")

# @app.on_event("startup")
# async def startup_event():
#     """서버 시작 시 SDXL 모델을 로드합니다. (services 모듈의 함수 호출)"""
#     # ⭐️ 2. services의 초기화 함수 호출
#     services.init_sdxl_pipelines()

# # ============================================================
# # 🚀 API 엔드포인트 정의 (핵심 로직은 'services'로 위임)
# # ============================================================

# @app.post("/api/caption", response_model=CaptionResponse)
# async def create_caption(request: CaptionRequest):
#     """
#     GPT-5 Mini를 사용하여 홍보 문구와 해시태그를 생성합니다.
#     """
#     if not services.openai_client:
#         raise HTTPException(status_code=503, detail="GPT-5 Mini 서비스가 준비되지 않았습니다.")
        
#     info = {
#         "service_type": request.service_type,
#         "service_name": request.service_name,
#         "features": request.features,
#         "location": request.location,
#     }

#     try:
#         # ⭐️ 3. services의 핵심 함수 호출
#         output_text = services.generate_caption_core(info, request.tone)
#         return CaptionResponse(output_text=output_text)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"문구 생성 중 오류 발생: {e}")


# @app.post("/api/generate_t2i", response_model=T2IResponse)
# async def generate_t2i_image(request: T2IRequest):
#     """
#     SDXL T2I를 사용하여 텍스트 프롬프트 기반으로 이미지를 생성합니다.
#     """
#     if not services.T2I_PIPE:
#         raise HTTPException(status_code=503, detail="SDXL T2I 모델이 로드되지 않았습니다.")

#     try:
#         # ⭐️ 3. services의 핵심 함수 호출
#         image_bytes = await app.loop.run_in_executor(
#             None, 
#             services.generate_t2i_core,
#             request.prompt,
#             request.width,
#             request.height,
#             request.steps
#         )
        
#         image_base64 = base64.b64encode(image_bytes).decode('utf-8')
#         return T2IResponse(image_base64=image_base64)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"T2I 이미지 생성 중 오류 발생: {e}")


# @app.post("/api/generate_i2i", response_model=T2IResponse) 
# async def generate_i2i_image(request: I2IRequest):
#     """
#     SDXL I2I를 사용하여 원본 이미지를 기반으로 편집/합성 이미지를 생성합니다.
#     """
#     if not services.I2I_PIPE:
#         raise HTTPException(status_code=503, detail="SDXL I2I 모델이 로드되지 않았습니다.")
        
#     try:
#         input_image_bytes = base64.b64decode(request.input_image_base64)
        
#         # ⭐️ 3. services의 핵심 함수 호출
#         image_bytes = await app.loop.run_in_executor(
#             None,
#             services.generate_i2i_core,
#             input_image_bytes,
#             request.prompt,
#             request.strength,
#             request.width,
#             request.height,
#             request.steps
#         )
        
#         image_base64 = base64.b64encode(image_bytes).decode('utf-8')
#         return T2IResponse(image_base64=image_base64)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"I2I 이미지 생성 중 오류 발생: {e}")

# # 상태 확인용 엔드포인트 (services의 변수 확인)
# @app.get("/status")
# def get_status():
#     return {
#         "gpt_ready": services.openai_client is not None,
#         "sdxl_t2i_ready": services.T2I_PIPE is not None,
#         "sdxl_i2i_ready": services.I2I_PIPE is not None,
#         "device": services.DEVICE
#     }























# main.py (개선)
import base64
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio

from . import services

app = FastAPI(title="헬스케어 AI 콘텐츠 API (개선)")

# Pydantic schemas
class CaptionRequest(BaseModel):
    service_type: str
    service_name: str
    features: str
    location: str
    tone: str

class CaptionResponse(BaseModel):
    output_text: str

class T2IRequest(BaseModel):
    prompt: str
    width: int = 1024
    height: int = 1024
    steps: int = 4  # 🆕 FLUX-schnell은 4 steps 권장

class T2IResponse(BaseModel):
    image_base64: str

class I2IRequest(BaseModel):
    input_image_base64: str
    prompt: str
    strength: float = 0.75
    width: int = 1024
    height: int = 1024
    steps: int = 4  # 🆕 FLUX-schnell은 4 steps 권장

# 🆕 개선: startup에서 모델 로드 (1회만)
@app.on_event("startup")
async def startup_event():
    """앱 시작 시 모델을 1회만 로드"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, services.init_image_pipelines)
    print("✅ FastAPI 시작 완료 - 모델 로드됨")

# 🆕 개선: reload 시 모델 재로딩 방지를 위한 shutdown 핸들러 제거
# (기존에 있었다면) - uvicorn reload 시 메모리에 모델 유지

# Endpoints
@app.post("/api/caption", response_model=CaptionResponse)
def create_caption(req: CaptionRequest):
    try:
        info = {
            "service_type": req.service_type,
            "service_name": req.service_name,
            "features": req.features,
            "location": req.location,
        }
        output_text = services.generate_caption_core(info, req.tone)
        return CaptionResponse(output_text=output_text)
    except RuntimeError as re_err:
        raise HTTPException(status_code=503, detail=str(re_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문구 생성 중 오류: {e}")

@app.post("/api/generate_t2i", response_model=T2IResponse)
async def generate_t2i_image(req: T2IRequest):
    steps = services.ensure_steps(req.steps)
    width = services.align_to_64(req.width)
    height = services.align_to_64(req.height)

    if width > 2048 or height > 2048:
        raise HTTPException(status_code=400, detail="width/height 값이 너무 큽니다.")

    try:
        loop = asyncio.get_event_loop()
        image_bytes = await loop.run_in_executor(
            None,
            services.generate_t2i_core,
            req.prompt,
            width,
            height,
            steps
        )
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        return T2IResponse(image_base64=b64)
    except RuntimeError as re_err:
        raise HTTPException(status_code=503, detail=str(re_err))
    except Exception as e:
        err = str(e).lower()
        if "out of memory" in err or "cuda" in err:
            raise HTTPException(status_code=503, detail="GPU 메모리 부족")
        raise HTTPException(status_code=500, detail=f"T2I 생성 실패: {e}")

@app.post("/api/generate_i2i", response_model=T2IResponse)
async def generate_i2i_image(req: I2IRequest):
    steps = services.ensure_steps(req.steps)
    width = services.align_to_64(req.width)
    height = services.align_to_64(req.height)
    strength = float(req.strength)

    try:
        try:
            input_bytes = base64.b64decode(req.input_image_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="입력 이미지 Base64 디코딩 실패")

        loop = asyncio.get_event_loop()
        image_bytes = await loop.run_in_executor(
            None,
            services.generate_i2i_core,
            input_bytes,
            req.prompt,
            strength,
            width,
            height,
            steps
        )
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        return T2IResponse(image_base64=b64)
    except RuntimeError as re_err:
        raise HTTPException(status_code=503, detail=str(re_err))
    except Exception as e:
        err = str(e).lower()
        if "out of memory" in err or "cuda" in err:
            raise HTTPException(status_code=503, detail="GPU 메모리 부족")
        raise HTTPException(status_code=500, detail=f"I2I 생성 실패: {e}")

@app.get("/status")
def status():
    return {
        "gpt_ready": services.openai_client is not None,
        "image_pipeline_ready": services.T2I_PIPE is not None,
        "device": services.DEVICE,
        "model": services.MODEL_ID
    }