# main.py (개선)
import base64
import time
import logging
import sys
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio

from . import services
from .exceptions import (
    ServiceError,
    PromptOptimizationError,
    ModelLoadError,
    WorkflowExecutionError,
    ImageProcessingError,
    ConfigurationError
)

# 로깅 설정 - stdout으로 출력하여 uvicorn 로그에 포함
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="소상공인 AI 콘텐츠 API (개선)")

# 서버 시작 시간 (재시작 감지용)
SERVER_START_TIME = time.time()

# Pydantic schemas
class CaptionRequest(BaseModel):
    shop_name: str
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
    steps: int = 28  # FLUX-dev 기본값
    guidance_scale: Optional[float] = None  # FLUX-dev는 3.5 권장
    post_process_method: str = "none"  # "none", "impact_pack", "adetailer"
    enable_adetailer: bool = False  # legacy
    adetailer_targets: Optional[List[str]] = None
    model_name: Optional[str] = None  # 사용할 모델 이름 (프론트엔드에서 선택한 모델)

class T2IResponse(BaseModel):
    image_base64: str

class I2IRequest(BaseModel):
    input_image_base64: str
    prompt: str
    strength: float = 0.75
    width: int = 1024
    height: int = 1024
    steps: int = 28  # FLUX-dev 기본값
    guidance_scale: Optional[float] = None
    post_process_method: str = "none"  # "none", "impact_pack", "adetailer"
    enable_adetailer: bool = False  # legacy
    adetailer_targets: Optional[List[str]] = None
    model_name: Optional[str] = None  # 사용할 모델 이름 (프론트엔드에서 선택한 모델)

# 🆕 이미지 편집 실험 스키마
class ImageEditingRequest(BaseModel):
    experiment_id: str  # "portrait_mode", "product_mode", "hybrid_mode", "ben2_flux_fill"
    input_image_base64: str
    prompt: str
    negative_prompt: Optional[str] = ""
    steps: Optional[int] = None
    guidance_scale: Optional[float] = None
    strength: Optional[float] = None

    # 새로운 모드용 파라미터
    controlnet_type: Optional[str] = "depth"  # "depth" 또는 "canny" (Portrait/Hybrid)
    controlnet_strength: Optional[float] = 0.7  # ControlNet 강도
    denoise_strength: Optional[float] = 1.0  # 변경 강도
    blending_strength: Optional[float] = 0.35  # 합성 자연스러움 (Product)
    background_prompt: Optional[str] = None  # 배경 프롬프트 (Product)

class ImageEditingResponse(BaseModel):
    success: bool
    experiment_id: str
    experiment_name: str
    output_image_base64: Optional[str] = None
    background_removed_image_base64: Optional[str] = None
    error: Optional[str] = None
    elapsed_time: Optional[float] = None

class CalligraphyRequest(BaseModel):
    text: str
    color_hex: str = "#FFFFFF"  # 기본값: 흰색
    style: str = "default"
    font_path: str = ""  # 비어있으면 기본 폰트 사용

# 🆕 개선: startup에서 모델 로드 (1회만)
@app.on_event("startup")
async def startup_event():
    """앱 시작 시 초기화 (모델 자동 로딩은 하지 않음)"""
    # 디폴트 unload 상태 유지를 위해 자동 로딩 제거
    logger.info("✅ FastAPI 시작 완료 - 모델은 Unload 상태입니다.")

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

        # 후처리 파라미터 준비
        from functools import partial
        generate_func = partial(
            services.generate_t2i_core,
            req.prompt,
            width,
            height,
            steps,
            guidance_scale,
            req.enable_adetailer,
            req.adetailer_targets,
            req.post_process_method,
            req.model_name  # 선택된 모델 전달
        )

        image_bytes = await loop.run_in_executor(None, generate_func)
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        return T2IResponse(image_base64=b64)
    except PromptOptimizationError as e:
        # 프롬프트 처리 실패
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e), "type": "prompt_error"}
        )
    except ModelLoadError as e:
        # 모델 로딩 실패
        return JSONResponse(
            status_code=503,
            content={"success": False, "error": str(e), "type": "model_error"}
        )
    except WorkflowExecutionError as e:
        # 워크플로우 실행 실패
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "type": "workflow_error"}
        )
    except ServiceError as e:
        # 일반 서비스 에러
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "type": "service_error"}
        )
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

        # 후처리 파라미터 준비
        from functools import partial
        generate_func = partial(
            services.generate_i2i_core,
            input_bytes,
            req.prompt,
            strength,
            width,
            height,
            steps,
            req.guidance_scale,
            req.enable_adetailer,
            req.adetailer_targets,
            req.post_process_method,
            req.model_name  # 선택된 모델 전달
        )

        image_bytes = await loop.run_in_executor(None, generate_func)
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

# 🆕 이미지 편집 실험 엔드포인트
@app.post("/api/edit_with_comfyui", response_model=ImageEditingResponse)
async def edit_image_with_comfyui(req: ImageEditingRequest):
    """
    ComfyUI를 사용한 이미지 편집 (3가지 모드)

    편집 모드:
    - portrait_mode: 얼굴 보존, 의상/배경 변경
    - product_mode: 제품 보존, 배경 생성/합성
    - hybrid_mode: 얼굴+제품 보존, 나머지 변경
    """
    try:
        # Base64 디코딩
        try:
            input_bytes = base64.b64decode(req.input_image_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="입력 이미지 Base64 디코딩 실패")

        # 서비스 레이어 호출
        loop = asyncio.get_event_loop()

        from functools import partial
        edit_func = partial(
            services.edit_image_with_comfyui,
            req.experiment_id,
            input_bytes,
            req.prompt,
            req.negative_prompt,
            req.steps,
            req.guidance_scale,
            req.strength,
            # 새로운 모드 파라미터
            req.controlnet_type,
            req.controlnet_strength,
            req.denoise_strength,
            req.blending_strength,
            req.background_prompt
        )

        result = await loop.run_in_executor(None, edit_func)

        return ImageEditingResponse(**result)

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except ConnectionError as ce:
        raise HTTPException(status_code=503, detail=str(ce))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 편집 실패: {e}")

@app.get("/api/image_editing/experiments")
def get_image_editing_experiments():
    """사용 가능한 이미지 편집 실험 목록 조회"""
    return services.get_image_editing_experiments()

@app.get("/api/comfyui/status")
def get_comfyui_status():
    """ComfyUI 서버 상태 확인"""
    return services.check_comfyui_status()

@app.post("/api/unload")
def unload_model_comfyui():
    """ComfyUI 모델 언로드"""
    return services.unload_comfyui_model()

@app.get("/api/current_model")
def get_current_model():
    """현재 로드된 모델 확인"""
    return {"current_model": services.get_current_comfyui_model()}

@app.post("/api/generate_calligraphy")
async def generate_calligraphy(req: CalligraphyRequest):
    """
    3D 캘리그라피 이미지 생성
    
    Args:
        req: CalligraphyRequest (text, color_hex, style, font_path)
    
    Returns:
        PNG 이미지 (Response with media_type="image/png")
    """
    try:
        loop = asyncio.get_event_loop()
        
        from functools import partial
        generate_func = partial(
            services.generate_calligraphy_core,
            req.text,
            req.color_hex,
            req.style,
            req.font_path
        )
        
        image_bytes = await loop.run_in_executor(None, generate_func)
        
        # PNG 이미지를 직접 반환
        from fastapi.responses import Response
        return Response(content=image_bytes, media_type="image/png")
        
    except ImageProcessingError as e:
        # 이미지 처리 실패
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "type": "image_processing_error"}
        )
    except Exception as e:
        logger.error(f"캘리그라피 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"캘리그라피 생성 실패: {e}")
