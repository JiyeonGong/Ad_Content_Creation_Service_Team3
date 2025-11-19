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
    """서비스 상태 및 사용 가능한 모델 목록 반환"""
    return services.get_service_status()

@app.get("/models")
def list_models():
    """사용 가능한 모델 목록 조회"""
    registry = services.registry
    models = {}
    
    for name in registry.list_models():
        models[name] = registry.get_model_info(name)
    
    return {
        "models": models,
        "current": services.model_loader.current_model_name if services.model_loader else None,
        "primary": registry.get_primary_model(),
        "fallback_chain": registry.get_fallback_models()
    }