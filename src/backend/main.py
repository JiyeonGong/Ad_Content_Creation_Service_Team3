# main.py (개선)
import base64
import time
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio

from . import services

app = FastAPI(title="헬스케어 AI 콘텐츠 API (개선)")

# 서버 시작 시간 (재시작 감지용)
SERVER_START_TIME = time.time()

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
    guidance_scale: Optional[float] = None  # FLUX-dev는 3.5 권장, schnell은 None

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
    """앱 시작 시 초기화 (모델 자동 로딩은 하지 않음)"""
    # 디폴트 unload 상태 유지를 위해 자동 로딩 제거
    print("✅ FastAPI 시작 완료 - 모델은 Unload 상태입니다.")

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
    guidance_scale = req.guidance_scale

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
            steps,
            guidance_scale
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
    result = services.get_service_status()
    result["server_start_time"] = SERVER_START_TIME
    return result

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

class SwitchModelRequest(BaseModel):
    model_name: str

# 모델 전환 상태 관리
_model_switch_status = {
    "in_progress": False,
    "target_model": None,
    "success": None,
    "message": None,
    "error": None
}
_switch_task = None

@app.post("/api/switch_model")
def switch_model(req: SwitchModelRequest):
    """모델 전환 (동기 - 기존 호환)"""
    result = services.switch_model(req.model_name)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result

@app.post("/api/switch_model_async")
async def switch_model_async(req: SwitchModelRequest):
    """모델 전환 (비동기 - 즉시 응답)"""
    global _model_switch_status, _switch_task

    # 이미 전환 중이면 거부
    if _model_switch_status["in_progress"]:
        raise HTTPException(
            status_code=409,
            detail=f"모델 전환 진행 중: {_model_switch_status['target_model']}"
        )

    # 상태 초기화
    _model_switch_status = {
        "in_progress": True,
        "target_model": req.model_name,
        "success": None,
        "message": "모델 전환 시작...",
        "error": None
    }

    # 백그라운드에서 모델 전환 실행
    loop = asyncio.get_event_loop()
    _switch_task = loop.run_in_executor(None, _do_switch_model, req.model_name)

    return {
        "status": "started",
        "target_model": req.model_name,
        "message": "모델 전환이 백그라운드에서 시작되었습니다. /api/switch_model_status로 상태를 확인하세요."
    }

def _do_switch_model(model_name: str):
    """백그라운드 모델 전환 실행"""
    global _model_switch_status
    try:
        result = services.switch_model(model_name)
        _model_switch_status["success"] = result["success"]
        _model_switch_status["message"] = result["message"]
        if not result["success"]:
            _model_switch_status["error"] = result["message"]
    except Exception as e:
        _model_switch_status["success"] = False
        _model_switch_status["message"] = f"모델 전환 실패: {e}"
        _model_switch_status["error"] = str(e)
    finally:
        _model_switch_status["in_progress"] = False

@app.get("/api/switch_model_status")
def get_switch_model_status():
    """모델 전환 상태 조회"""
    current_model = None
    if services.model_loader and services.model_loader.is_loaded():
        current_model = services.model_loader.current_model_name

    return {
        **_model_switch_status,
        "current_model": current_model
    }

@app.post("/api/load_model")
def load_model(req: SwitchModelRequest):
    """모델 로드 (Switch Model 재사용)"""
    # 로드도 결국 switch_model과 동일한 로직
    result = services.switch_model(req.model_name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/api/unload_model")
def unload_model():
    """모델 언로드"""
    return services.unload_model_service()
