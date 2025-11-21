# /home/spai0323/Ad_Content_Creation_Service_Team3/src/backend/main.py
# import base64
# import asyncio
# import logging
# from contextlib import asynccontextmanager
# from typing import Optional

# from fastapi import FastAPI, HTTPException, Depends
# from pydantic import BaseModel, Field

# # 로컬 모듈 임포트
# from . import services

# # 로깅 설정
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("main")

# # 🔒 글로벌 GPU 락 (매우 중요)
# # 동시에 여러 요청이 들어와도 GPU 작업은 한 번에 하나씩만 수행하도록 강제함.
# # FLUX 같은 거대 모델 사용 시 OOM(Out Of Memory) 방지를 위해 필수.
# gpu_lock = asyncio.Lock()

# # 🏗️ Lifespan (앱 시작/종료 생명주기 관리 - 최신 FastAPI 표준)
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # [시작 시]
#     logger.info("🚀 서비스 시작: 모델 로딩 시도...")
#     try:
#         # 이벤트 루프 블로킹 방지를 위해 executor 사용
#         loop = asyncio.get_running_loop()
#         await loop.run_in_executor(None, services.init_image_pipelines)
#         logger.info("✅ 모델 초기화 완료")
#     except Exception as e:
#         logger.error(f"❌ 초기화 중 치명적 오류: {e}")
#         # 모델 로드 실패해도 서버는 켜지도록 함 (API로 복구 시도 가능)
    
#     yield  # 앱 실행 중...
    
#     # [종료 시]
#     logger.info("🛑 서비스 종료: 리소스 정리")
#     # 필요 시 services.unload_model() 등 호출 가능

# app = FastAPI(
#     title="헬스케어 AI 콘텐츠 API (Team3)", 
#     description="FLUX/SDXL 기반 광고 생성 서비스",
#     lifespan=lifespan
# )

# # --- Pydantic Models (데이터 검증 강화) ---

# class CaptionRequest(BaseModel):
#     service_type: str
#     service_name: str
#     features: str
#     location: str
#     tone: str = "polite"  # 기본값 설정

# class CaptionResponse(BaseModel):
#     output_text: str

# class ChangeModelRequest(BaseModel):
#     model_name: str

# class T2IRequest(BaseModel):
#     prompt: str
#     width: int = Field(1024, le=2048, description="최대 2048")
#     height: int = Field(1024, le=2048, description="최대 2048")
#     steps: int = Field(4, ge=1, le=50, description="FLUX-schnell: 4, Dev: 20~30")

# class T2IResponse(BaseModel):
#     image_base64: str

# class I2IRequest(BaseModel):
#     input_image_base64: str
#     prompt: str
#     strength: float = Field(0.75, ge=0.0, le=1.0, description="0.0(원본유지) ~ 1.0(완전변경)")
#     width: int = 1024
#     height: int = 1024
#     steps: int = 4

# # --- Endpoints ---

# @app.post("/api/change_model")
# async def change_model(req: ChangeModelRequest):
#     """🔄 실행 중 모델 변경 (Flux <-> SDXL 등)"""
#     async with gpu_lock:  # 모델 로딩 중에는 생성 요청 차단
#         logger.info(f"🔄 모델 변경 요청: {req.model_name}")
        
#         loop = asyncio.get_running_loop()
#         success = await loop.run_in_executor(
#             None, 
#             services.model_loader.load_model, 
#             req.model_name
#         )
        
#         if not success:
#             raise HTTPException(status_code=400, detail=f"모델 '{req.model_name}' 로딩 실패")
            
#         return {
#             "status": "success", 
#             "current_model": services.model_loader.current_model_name,
#             "info": services.model_loader.get_current_model_info()
#         }

# @app.post("/api/caption", response_model=CaptionResponse)
# async def create_caption(req: CaptionRequest):
#     """📝 광고 문구 생성 (GPU Lock 불필요 - LLM이 API 방식이라면)"""
#     try:
#         info = req.dict()
#         # 문구 생성은 보통 API(GPT/Claude)를 쓰므로 GPU Lock 제외
#         # 만약 로컬 LLM을 쓴다면 async with gpu_lock: 필요
#         output_text = await asyncio.to_thread(services.generate_caption_core, info, req.tone)
#         return CaptionResponse(output_text=output_text)
#     except Exception as e:
#         logger.error(f"문구 생성 실패: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/api/generate_t2i", response_model=T2IResponse)
# async def generate_t2i_image(req: T2IRequest):
#     """🎨 텍스트 -> 이미지 생성 (순차 처리 적용)"""
    
#     # 크기 조정 (64배수)
#     width = services.align_to_64(req.width)
#     height = services.align_to_64(req.height)
#     steps = services.ensure_steps(req.steps)

#     # 🔒 동시 요청 시 대기 (Queueing)
#     async with gpu_lock:
#         logger.info(f"🎨 T2I 시작: {req.prompt[:30]}... (Model: {services.model_loader.current_model_name})")
#         try:
#             loop = asyncio.get_running_loop()
#             image_bytes = await loop.run_in_executor(
#                 None,
#                 services.generate_t2i_core,
#                 req.prompt,
#                 width,
#                 height,
#                 steps
#             )
            
#             b64 = base64.b64encode(image_bytes).decode("utf-8")
#             return T2IResponse(image_base64=b64)
            
#         except RuntimeError as e:
#             # ModelLoader에서 발생시킨 에러 전달
#             raise HTTPException(status_code=503, detail=str(e))
#         except Exception as e:
#             logger.error(f"T2I 에러: {e}")
#             if "out of memory" in str(e).lower():
#                 raise HTTPException(status_code=503, detail="GPU 메모리 부족. 잠시 후 다시 시도해주세요.")
#             raise HTTPException(status_code=500, detail=str(e))

# @app.post("/api/generate_i2i", response_model=T2IResponse)
# async def generate_i2i_image(req: I2IRequest):
#     """🖼️ 이미지 -> 이미지 생성 (순차 처리 적용)"""
    
#     width = services.align_to_64(req.width)
#     height = services.align_to_64(req.height)
#     steps = services.ensure_steps(req.steps)

#     # 🔒 동시 요청 시 대기
#     async with gpu_lock:
#         logger.info(f"🖼️ I2I 시작 (Strength: {req.strength})")
#         try:
#             # 입력 이미지 디코딩
#             try:
#                 input_bytes = base64.b64decode(req.input_image_base64)
#             except:
#                 raise HTTPException(status_code=400, detail="이미지 Base64 디코딩 실패")

#             loop = asyncio.get_running_loop()
#             image_bytes = await loop.run_in_executor(
#                 None,
#                 services.generate_i2i_core,
#                 input_bytes,
#                 req.prompt,
#                 req.strength,
#                 width,
#                 height,
#                 steps
#             )
            
#             b64 = base64.b64encode(image_bytes).decode("utf-8")
#             return T2IResponse(image_base64=b64)
            
#         except RuntimeError as e:
#             raise HTTPException(status_code=503, detail=str(e))
#         except Exception as e:
#             logger.error(f"I2I 에러: {e}")
#             if "out of memory" in str(e).lower():
#                 raise HTTPException(status_code=503, detail="GPU 메모리 부족")
#             raise HTTPException(status_code=500, detail=str(e))

# @app.get("/status")
# def status():
#     """서버 상태 및 현재 모델 정보"""
#     return services.get_service_status()

# @app.get("/models")
# def list_models():
#     """사용 가능한 모델 목록 및 현재 설정"""
#     registry = services.registry
#     # 현재 로더 상태 안전하게 접근
#     current_name = services.model_loader.current_model_name if services.model_loader else None
    
#     return {
#         "current_model": current_name,
#         "available_models": registry.list_models(),
#         "model_details": {name: registry.get_model_info(name) for name in registry.list_models()},
#         "fallback_enabled": registry.is_fallback_enabled()
#     }






























# /home/spai0323/Ad_Content_Creation_Service_Team3/src/backend/main.py (개선)
import base64
from typing import Optional
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

class SwitchModelRequest(BaseModel):
    model_name: str

@app.post("/api/switch_model")
def switch_model(req: SwitchModelRequest):
    """모델 전환"""
    result = services.switch_model(req.model_name)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result
