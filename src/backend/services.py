# services.py (리팩토링 버전)
"""
AI 서비스 레이어 - 설정 기반 모델 관리
"""
import os
import io
from typing import Optional

from openai import OpenAI
import torch
from PIL import Image
from dotenv import load_dotenv

from .model_registry import get_registry
from .model_loader import ModelLoader

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# 토크나이저 병렬 처리 경고 억제
os.environ["TOKENIZERS_PARALLELISM"] = "false"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_GPT_MINI = "gpt-5-mini"

# HF cache location
# GCP: /home/shared 사용 (이미 다운로드된 모델 재사용)
# 로컬: project_root/cache/hf_models 사용
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.exists("/home/shared"):
    hf_cache_dir = "/home/shared"
else:
    hf_cache_dir = os.path.join(project_root, "cache", "hf_models")
    os.makedirs(hf_cache_dir, exist_ok=True)

# 전역 인스턴스
openai_client: Optional[OpenAI] = None
model_loader: Optional[ModelLoader] = None
registry = get_registry()

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
# 모델 초기화
# ===========================
def init_image_pipelines():
    """
    설정 파일 기반으로 이미지 생성 모델 로드
    """
    global model_loader
    
    # 이미 로드된 경우 스킵
    if model_loader and model_loader.is_loaded():
        print("ℹ️ 이미지 파이프라인 이미 로드됨 — 스킵")
        return
    
    # ModelLoader 생성
    if model_loader is None:
        model_loader = ModelLoader(cache_dir=hf_cache_dir)
    
    # 폴백 체인으로 로딩 시도
    success = model_loader.load_with_fallback()
    
    if success:
        info = model_loader.get_current_model_info()
        print(f"✅ 이미지 생성 준비 완료")
        print(f"   모델: {info['name']} ({info['type']})")
        print(f"   장치: {info['device']}")
    else:
        print("❌ 모든 모델 로딩 실패 - 이미지 생성 불가")

# ===========================
# 프롬프트 최적화
# ===========================
def optimize_prompt(text: str, model_config) -> str:
    """
    한국어 프롬프트를 영어로 번역 및 최적화
    모델별 토큰 제한 고려
    """
    if not openai_client:
        return text
    
    # 프롬프트 최적화 설정 확인
    opt_config = registry.get_prompt_optimization_config()
    if not opt_config.get("enabled", True):
        return text
    
    # 한글 번역 비활성화 설정 확인
    if not opt_config.get("translate_korean", True):
        return text
    
    try:
        # 모델별 길이 제약
        max_tokens = model_config.max_tokens if model_config else 77
        
        if max_tokens <= 77:
            constraint = f"Keep it under 60 words (model has {max_tokens} token limit)."
        else:
            constraint = "Keep it concise but descriptive (under 150 words)."
        
        system_prompt = f"""You are a professional prompt engineer for image generation AI.
Translate Korean marketing text to optimized English prompts.
Focus on visual elements, style, mood, and composition.
{constraint}

IMPORTANT - Quality keywords to prevent AI artifacts:

1. If the scene involves people:
   - Hands: "detailed hands, five fingers, natural hand pose, anatomically correct hands, Hand Position Left Right Proper Position, correct thumb direction"
   - Faces: "detailed face, clear facial features, symmetric face, symmetric eyes, natural eye shape"
   - Body: "correct human anatomy, natural body proportions, well-fitted clothing"

2. If the scene involves objects being held or touched:
   - "proper object interaction, object not clipping through body"
   - "realistic grip, natural holding pose"
   - "physically accurate, no overlapping body parts with objects"

3. If the scene involves fitness/gym/sports equipment:
   - "equipment not penetrating body, proper form"
   - "hands gripping equipment correctly, realistic weight interaction"

Always include relevant keywords based on the scene content.

Output ONLY the English prompt, no explanations."""

        resp = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            input=f"Convert to image prompt:\n{text}",
            reasoning={"effort": "minimal"},
            max_output_tokens=200,
        )
        
        result = getattr(resp, "output_text", None) or str(resp)
        optimized = result.strip()
        print(f"🔄 프롬프트 최적화:\n  원본: {text}\n  최적화: {optimized}")
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
# 🆕 이미지 생성 (T2I) - ComfyUI 기반
# ===========================
def generate_t2i_core(
    prompt: str,
    width: int,
    height: int,
    steps: int,
    guidance_scale: float = None,
    enable_adetailer: bool = True,
    adetailer_targets: list = None,
    post_process_method: str = "none"  # "none", "impact_pack", "adetailer"
) -> bytes:
    """
    ComfyUI를 사용한 T2I 이미지 생성

    Args:
        post_process_method: 후처리 방식
            - "none": 후처리 없음
            - "impact_pack": ComfyUI Impact Pack (YOLO+SAM)
            - "adetailer": 기존 ADetailer (YOLO+MediaPipe)
    """
    from .comfyui_client import ComfyUIClient
    from .comfyui_workflows import (
        get_flux_t2i_workflow,
        get_flux_t2i_with_impact_workflow,
        update_flux_t2i_workflow,
        load_image_editing_config
    )

    # 현재 로드된 모델 이름 가져오기
    global model_loader
    if not model_loader or not model_loader.is_loaded():
        raise RuntimeError("모델이 로드되지 않았습니다. 먼저 모델을 로드하세요.")

    current_model_name = model_loader.current_model_name
    model_config = model_loader.current_model_config

    # 프롬프트 최적화
    optimized_prompt = optimize_prompt(prompt, model_config)

    # Steps 검증
    if steps < 1:
        steps = model_config.default_steps
    steps = min(steps, model_config.max_steps)

    # Guidance scale 설정
    if guidance_scale is None:
        guidance_scale = model_config.guidance_scale or 3.5

    print(f"🎨 ComfyUI로 T2I 이미지 생성 중")
    print(f"   모델: {current_model_name}")
    print(f"   후처리: {post_process_method}")
    print(f"   Steps: {steps}")
    print(f"   크기: {width}x{height}")
    print(f"   Guidance: {guidance_scale}")

    try:
        # ComfyUI 클라이언트 초기화
        config = load_image_editing_config()
        comfyui_config = config.get("comfyui", {})
        base_url = comfyui_config.get("base_url", "http://localhost:8188")
        timeout = comfyui_config.get("timeout", 300)

        client = ComfyUIClient(base_url=base_url, timeout=timeout)

        # 워크플로우 선택
        if post_process_method == "impact_pack":
            workflow = get_flux_t2i_with_impact_workflow()
        else:
            workflow = get_flux_t2i_workflow()

        # 워크플로우 파라미터 업데이트
        workflow = update_flux_t2i_workflow(
            workflow=workflow,
            model_name=current_model_name,
            prompt=optimized_prompt,
            width=width,
            height=height,
            steps=steps,
            guidance_scale=guidance_scale
        )

        # ComfyUI 실행
        output_images, history = client.execute_workflow(workflow=workflow)

        if not output_images:
            raise Exception("출력 이미지가 생성되지 않았습니다.")

        image_bytes = output_images[0]

        # 기존 ADetailer 후처리 (선택 시)
        if post_process_method == "adetailer" and enable_adetailer:
            image = Image.open(io.BytesIO(image_bytes))
            image = apply_adetailer(
                image=image,
                prompt=optimized_prompt,
                targets=adetailer_targets or ["hand"]
            )

            buf = io.BytesIO()
            image.save(buf, format="PNG")
            image_bytes = buf.getvalue()

        print(f"✅ 생성 완료: {len(image_bytes)} bytes")
        return image_bytes

    except Exception as e:
        print(f"❌ ComfyUI T2I 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"이미지 생성 실패: {e}")


# ===========================
# ADetailer 후처리
# ===========================
def apply_adetailer(
    image: Image,
    prompt: str,
    targets: list = None,
    strength: float = 0.4
) -> Image:
    """
    ADetailer 스타일 후처리
    - 손/얼굴 감지 후 해당 영역만 Inpaint로 재생성
    """
    global model_loader

    if targets is None:
        targets = ["hand"]

    try:
        from .post_processor import get_post_processor

        print(f"🔧 ADetailer 후처리 시작 (targets: {targets})")

        post_processor = get_post_processor()

        # I2I 파이프라인을 Inpaint용으로 사용
        inpaint_pipe = model_loader.i2i_pipe

        processed_image, info = post_processor.full_pipeline(
            image=image,
            inpaint_pipeline=inpaint_pipe,
            prompt=prompt,
            auto_detect=True,
            adetailer_targets=targets,
            adetailer_strength=strength
        )

        if not info["processed"]:
            print(f"ℹ️ ADetailer: 이상 없음, 원본 유지")

        return processed_image

    except Exception as e:
        print(f"⚠️ ADetailer 실패, 원본 반환: {e}")
        return image

# ===========================
# 🆕 이미지 편집 (I2I) - ComfyUI 기반
# ===========================
def generate_i2i_core(
    input_image_bytes: bytes,
    prompt: str,
    strength: float,
    width: int,
    height: int,
    steps: int,
    guidance_scale: float = None,
    enable_adetailer: bool = False,
    adetailer_targets: list = None,
    post_process_method: str = "none"  # "none", "impact_pack", "adetailer"
) -> bytes:
    """
    ComfyUI를 사용한 I2I 이미지 편집

    Args:
        input_image_bytes: 입력 이미지 바이트
        prompt: 편집 프롬프트
        strength: 편집 강도 (0.0~1.0)
        width, height: 출력 크기
        steps: 샘플링 스텝
        guidance_scale: CFG 스케일
        enable_adetailer: ADetailer 활성화 여부 (legacy)
        adetailer_targets: 후처리 타겟
        post_process_method: 후처리 방식
            - "none": 후처리 없음
            - "impact_pack": ComfyUI Impact Pack (YOLO+SAM)
            - "adetailer": 기존 ADetailer (YOLO+MediaPipe)
    """
    from .comfyui_client import ComfyUIClient
    from .comfyui_workflows import (
        get_flux_i2i_workflow,
        update_flux_i2i_workflow,
        load_image_editing_config
    )

    # 현재 로드된 모델 정보 가져오기
    global model_loader
    if not model_loader or not model_loader.is_loaded():
        raise RuntimeError("모델이 로드되지 않았습니다. 먼저 모델을 로드하세요.")

    current_model_name = model_loader.current_model_name
    model_config = model_loader.current_model_config

    # I2I 지원 확인
    if not model_config.supports_i2i:
        raise RuntimeError(f"현재 모델({current_model_name})은 I2I를 지원하지 않습니다.")

    # 프롬프트 최적화
    optimized_prompt = optimize_prompt(prompt, model_config)

    # Steps 검증
    if steps < 1:
        steps = model_config.default_steps
    steps = min(steps, model_config.max_steps)

    # Guidance scale 설정
    if guidance_scale is None:
        guidance_scale = model_config.guidance_scale or 3.5

    print(f"✏️ ComfyUI로 I2I 이미지 편집 중")
    print(f"   모델: {current_model_name}")
    print(f"   후처리: {post_process_method}")
    print(f"   Strength: {strength}")
    print(f"   Steps: {steps}")
    print(f"   크기: {width}x{height}")
    print(f"   Guidance: {guidance_scale}")

    try:
        # ComfyUI 클라이언트 초기화
        config = load_image_editing_config()
        comfyui_config = config.get("comfyui", {})
        base_url = comfyui_config.get("base_url", "http://localhost:8188")
        timeout = comfyui_config.get("timeout", 300)

        client = ComfyUIClient(base_url=base_url, timeout=timeout)

        # I2I 워크플로우 가져오기
        workflow = get_flux_i2i_workflow()

        # 워크플로우 파라미터 업데이트
        workflow = update_flux_i2i_workflow(
            workflow=workflow,
            model_name=current_model_name,
            prompt=optimized_prompt,
            strength=strength,
            steps=steps,
            guidance_scale=guidance_scale
        )

        # ComfyUI 실행 (입력 이미지 포함)
        output_images, history = client.execute_workflow(
            workflow=workflow,
            input_image=input_image_bytes,
            input_image_node_id="11"  # LoadImage 노드 ID
        )

        if not output_images:
            raise Exception("출력 이미지가 생성되지 않았습니다.")

        image_bytes = output_images[0]

        # 기존 ADetailer 후처리 (선택 시)
        if post_process_method == "adetailer" and enable_adetailer:
            image = Image.open(io.BytesIO(image_bytes))
            image = apply_adetailer(
                image=image,
                prompt=optimized_prompt,
                targets=adetailer_targets or ["hand"]
            )

            buf = io.BytesIO()
            image.save(buf, format="PNG")
            image_bytes = buf.getvalue()

        print(f"✅ 편집 완료: {len(image_bytes)} bytes")
        return image_bytes

    except Exception as e:
        print(f"❌ ComfyUI I2I 편집 실패: {e}")
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"이미지 편집 실패: {e}")

# ===========================
# 모델 전환
# ===========================
def switch_model(model_name: str) -> dict:
    """
    다른 모델로 전환
    Returns: {"success": bool, "message": str, "model_info": dict}
    """
    global model_loader

    if not model_loader:
        model_loader = ModelLoader(cache_dir=hf_cache_dir)

    # 모델 존재 여부 확인
    model_config = registry.get_model(model_name)
    if not model_config:
        return {
            "success": False,
            "message": f"알 수 없는 모델: {model_name}",
            "model_info": None
        }

    # 이미 로드된 경우
    if model_loader.is_loaded() and model_loader.current_model_name == model_name:
        return {
            "success": True,
            "message": f"모델 '{model_name}' 이미 로드됨",
            "model_info": model_loader.get_current_model_info()
        }

    # 모델 로드
    print(f"🔄 모델 전환 중: {model_name}")
    success = model_loader.load_model(model_name)

    if success:
        info = model_loader.get_current_model_info()
        return {
            "success": True,
            "message": f"모델 '{model_name}' 로드 성공",
            "model_info": info
        }
    else:
        return {
            "success": False,
            "message": f"모델 '{model_name}' 로드 실패",
            "model_info": None
        }

# ===========================
# 상태 조회
# ===========================
def get_service_status() -> dict:
    """서비스 상태 반환"""
    status = {
        "gpt_ready": openai_client is not None,
        "image_ready": model_loader and model_loader.is_loaded(),
    }

    if model_loader:
        status.update(model_loader.get_current_model_info())

    return status

def unload_model_service() -> dict:
    """모델 언로드"""
    global model_loader

    if model_loader and model_loader.is_loaded():
        model_loader.unload_model()
        return {"success": True, "message": "모델 언로드 완료"}

    return {"success": True, "message": "이미 언로드 상태입니다."}

# ===========================
# 🆕 이미지 편집 (ComfyUI)
# ===========================
def edit_image_with_comfyui(
    experiment_id: str,
    input_image_bytes: bytes,
    prompt: str,
    steps: int = None,
    guidance_scale: float = None,
    strength: float = None
) -> dict:
    """
    ComfyUI를 사용한 이미지 편집 (BEN2 + 선택 모델)

    Args:
        experiment_id: 실험 ID ("ben2_flux_fill" 또는 "ben2_qwen_image")
        input_image_bytes: 입력 이미지 바이트
        prompt: 편집 프롬프트
        steps: 추론 단계
        guidance_scale: Guidance scale
        strength: 변화 강도

    Returns:
        {
            "success": bool,
            "experiment_id": str,
            "experiment_name": str,
            "output_image_base64": str,
            "background_removed_image_base64": str,
            "error": str,
            "elapsed_time": float
        }
    """
    import base64
    import time
    from .comfyui_client import ComfyUIClient
    from .comfyui_workflows import (
        get_workflow_template,
        update_workflow_inputs,
        get_workflow_input_image_node_id,
        load_image_editing_config
    )

    start_time = time.time()

    try:
        # 설정 로드
        config = load_image_editing_config()

        # 실험 정보 찾기
        experiment = None
        for exp in config.get("experiments", []):
            if exp["id"] == experiment_id:
                experiment = exp
                break

        if not experiment:
            return {
                "success": False,
                "experiment_id": experiment_id,
                "experiment_name": "Unknown",
                "output_image_base64": None,
                "background_removed_image_base64": None,
                "error": f"알 수 없는 실험 ID: {experiment_id}",
                "elapsed_time": None
            }

        # ComfyUI 클라이언트 초기화
        comfyui_config = config.get("comfyui", {})
        base_url = comfyui_config.get("base_url", "http://localhost:8188")
        timeout = comfyui_config.get("timeout", 300)

        client = ComfyUIClient(base_url=base_url, timeout=timeout)

        # 워크플로우 템플릿 가져오기
        workflow = get_workflow_template(experiment_id)

        # 워크플로우 업데이트 (사용자 입력 반영)
        workflow = update_workflow_inputs(
            workflow=workflow,
            experiment_id=experiment_id,
            prompt=prompt,
            steps=steps,
            guidance_scale=guidance_scale,
            strength=strength
        )

        # 입력 이미지 노드 ID
        input_node_id = get_workflow_input_image_node_id(experiment_id)

        print(f"🎨 ComfyUI 이미지 편집 시작")
        print(f"   실험: {experiment['name']}")
        print(f"   프롬프트: {prompt}")

        # 워크플로우 실행
        output_images, history = client.execute_workflow(
            workflow=workflow,
            input_image=input_image_bytes,
            input_image_node_id=input_node_id
        )

        if not output_images:
            raise Exception("출력 이미지가 생성되지 않았습니다.")

        # 첫 번째 이미지를 최종 결과로 사용
        output_image_bytes = output_images[0]
        output_image_base64 = base64.b64encode(output_image_bytes).decode("utf-8")

        # 배경 제거 이미지 (선택적)
        background_removed_base64 = None
        if len(output_images) > 1:
            background_removed_base64 = base64.b64encode(output_images[1]).decode("utf-8")

        elapsed_time = time.time() - start_time

        print(f"✅ ComfyUI 편집 완료! (소요 시간: {elapsed_time:.1f}초)")

        return {
            "success": True,
            "experiment_id": experiment_id,
            "experiment_name": experiment["name"],
            "output_image_base64": output_image_base64,
            "background_removed_image_base64": background_removed_base64,
            "error": None,
            "elapsed_time": elapsed_time
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        error_msg = str(e)
        print(f"❌ ComfyUI 편집 실패: {error_msg}")

        return {
            "success": False,
            "experiment_id": experiment_id,
            "experiment_name": experiment.get("name", "Unknown") if experiment else "Unknown",
            "output_image_base64": None,
            "background_removed_image_base64": None,
            "error": error_msg,
            "elapsed_time": elapsed_time
        }


def get_image_editing_experiments() -> dict:
    """사용 가능한 이미지 편집 실험 목록 반환"""
    from .comfyui_workflows import load_image_editing_config

    try:
        config = load_image_editing_config()
        experiments = config.get("experiments", [])

        return {
            "success": True,
            "experiments": [
                {
                    "id": exp["id"],
                    "name": exp["name"],
                    "description": exp["description"],
                    "background_removal_model": exp["background_removal"]["model"],
                    "editing_model": exp["image_editing"]["model"]
                }
                for exp in experiments
            ]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "experiments": []
        }


def check_comfyui_status() -> dict:
    """ComfyUI 서버 상태 확인"""
    from .comfyui_client import ComfyUIClient
    from .comfyui_workflows import load_image_editing_config

    try:
        config = load_image_editing_config()
        comfyui_config = config.get("comfyui", {})
        base_url = comfyui_config.get("base_url", "http://localhost:8188")

        client = ComfyUIClient(base_url=base_url)
        connected = client.check_connection()

        if connected:
            queue_info = client.get_queue_info()
            return {
                "connected": True,
                "base_url": base_url,
                "queue_info": queue_info
            }
        else:
            return {
                "connected": False,
                "base_url": base_url,
                "error": "ComfyUI 서버에 연결할 수 없습니다."
            }

    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }
