# services.py (리팩토링 + FLUX 3단계 프롬프팅 통합 버전)
"""
AI 서비스 레이어 - 설정 기반 모델 관리
"""
import os
import io
import logging
from typing import Optional

from openai import OpenAI
import torch
from PIL import Image
from dotenv import load_dotenv

from .model_registry import get_registry
from .model_loader import ModelLoader
from .exceptions import (
    ServiceError,
    PromptOptimizationError,
    ModelLoadError,
    WorkflowExecutionError,
    ImageProcessingError,
    ConfigurationError
)

logger = logging.getLogger(__name__)

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# 토크나이저 병렬 처리 경고 억제
os.environ["TOKENIZERS_PARALLELISM"] = "false"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_GPT_MINI = "gpt-5-mini"

# HF cache location
# /mnt/data4/models 우선 사용 (모든 모델 통합 저장소)
# GCP: /home/shared 사용
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.exists("/mnt/data4/models"):
    hf_cache_dir = "/mnt/data4/models"
elif os.path.exists("/home/shared"):
    hf_cache_dir = "/home/shared"
else:
    raise RuntimeError("모델 디렉토리를 찾을 수 없습니다!")

# 전역 인스턴스
openai_client: Optional[OpenAI] = None
model_loader: Optional[ModelLoader] = None
registry = get_registry()

# Initialize OpenAI client
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        logger.warning(f"⚠️ OpenAI 초기화 실패: {e}")
        openai_client = None
else:
    logger.warning("⚠️ OPENAI_API_KEY 미설정 — GPT 기능 불가")

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
        logger.info(f"✅ 이미지 생성 준비 완료")
        print(f"   모델: {info['name']} ({info['type']})")
        print(f"   장치: {info['device']}")
    else:
        print("❌ 모든 모델 로딩 실패 - 이미지 생성 불가")

# ===========================
# 프롬프트 최적화 (FLUX 3단계 통합)
# ===========================
def expand_prompt_with_gpt(text: str) -> str:
    """
    1단계: 한국어 시각 묘사 확장
    - 배경/조명/분위기/동작 등을 2~3문장 한국어로 자연스럽게 확장
    """
    if not openai_client:
        return text
    
    opt_config = registry.get_prompt_optimization_config()
    if not opt_config.get("enabled", True):
        return text
    if not opt_config.get("translate_korean", True):
        return text

    system = """
당신은 이미지 생성용 시각 묘사를 구체적으로 확장하는 전문가입니다.
규칙:
- 장면의 배경, 조명, 동작, 분위기, 구도 등을 자연스럽고 구체적으로 확장합니다.
- 2~3 문장으로 작성하며, 출력은 반드시 한국어로 유지합니다.
"""

    prompt = f"{system}\n\n[원본 문장]\n{text}\n\n위 문장을 시각적으로 더 자세한 묘사로 자연스럽게 확장해줘."

    try:
        resp = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            reasoning={"effort": "minimal"},
            input=prompt,
            max_output_tokens=300,
        )
        expanded = getattr(resp, "output_text", None) or str(resp)
        expanded = expanded.strip()
        logger.info(f"🔄 1/3 확장 (한국어): {expanded[:80]}...")
        return expanded
    except Exception as e:
        logger.warning(f"⚠️ 1단계 한국어 확장 실패 → 원본 사용: {e}")
        return text


def apply_flux_template(expanded_kor_text: str) -> str:
    """
    2단계: 확장된 한국어 설명을 FLUX 스타일 영어 프롬프트로 변환
    - 2~3개의 자연스러운 영어 문장
    """
    if not openai_client:
        return expanded_kor_text

    opt_config = registry.get_prompt_optimization_config()
    if not opt_config.get("enabled", True):
        return expanded_kor_text

    system = """
You are an expert FLUX prompt engineer. Convert the expanded Korean visual description into a compact FLUX-style English prompt.

Rules:
- MUST stay under 60 English tokens.
- Use 2–3 short natural sentences (NOT keyword lists).
- Include: Subject, Action/Pose, Environment, Lighting, (Optional) Camera/Style.
- Insert concise realism hints: "realistic hands and face", "correct anatomy".
- Do NOT add negative prompts.

Output ONLY the final English FLUX prompt.
"""
    prompt = f"{system}\n\n[Korean expanded description]\n{expanded_kor_text}\n\nConvert following the FLUX rules."

    try:
        resp = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            reasoning={"effort": "minimal"},
            input=prompt,
            max_output_tokens=200,
        )
        templated = getattr(resp, "output_text", None) or str(resp)
        templated = templated.strip()
        logger.info(f"🔄 2/3 템플릿 (영어): {templated[:80]}...")
        return templated
    except Exception as e:
        logger.warning(f"⚠️ 2단계 FLUX 템플릿 변환 실패 → 원본 사용: {e}")
        return expanded_kor_text


def optimize_prompt(text: str, model_config) -> str:
    """
    3단계: FLUX/SDXL 최종 프롬프트 다듬기
    - FLUX: 60 토큰 이내, 2~3문장, negative prompt 추가 금지
    - 그 외: 길이 제약에 맞게 명료하게 다듬기
    """
    if not openai_client:
        return text
    
    opt_config = registry.get_prompt_optimization_config()
    if not opt_config.get("enabled", True):
        return text

    model_type = (model_config.type if model_config else "").lower()
    is_flux = "flux" in model_type

    try:
        if is_flux:
            system_prompt = """
You are an expert FLUX prompt polisher.
Polish the prompt below.

IMPORTANT:
- Keep under 60 tokens.
- 2–3 short descriptive sentences (no keyword lists).
- Do NOT add negative prompts.
"""
        else:
            max_tokens = getattr(model_config, "max_tokens", 77) if model_config else 77
            if max_tokens <= 77:
                constraint = f"Keep it under 60 words (model has {max_tokens} token limit)."
            else:
                constraint = "Keep it concise but descriptive (under 150 words)."

            system_prompt = f"""
You are a professional prompt engineer for image generation AI.
Refine the prompt below for better clarity, realism, and aesthetic quality.
{constraint}
Always include relevant quality hints based on the scene to prevent artifacts 
(e.g., "detailed hands, correct anatomy, clear facial features").
"""

        full_prompt = f"{system_prompt}\n\n[Input Prompt]\n{text}\n\nOutput ONLY the polished final English prompt."

        resp = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            reasoning={"effort": "minimal"},
            input=full_prompt,
            max_output_tokens=200,
        )
        optimized = getattr(resp, "output_text", None) or str(resp)
        optimized = optimized.strip()
        logger.info(f"🔄 3/3 최종 최적화: {optimized[:80]}...")
        return optimized

    except Exception as e:
        logger.warning(f"⚠️ 3단계 최종 최적화 실패 → 원본 사용: {e}")
        return text







def build_final_prompt_v2(raw_prompt: str, context: dict = None, model_config=None) -> str:
    """통합 프롬프트 빌더 (Phase 1 개선 버전)
    
    GPT 호출을 3회 → 1회로 통합하여 비용 66% 절감, 처리 시간 50% 단축
    
    Args:
        raw_prompt: 원본 프롬프트 (한국어/영어 모두 가능)
        context: 추가 컨텍스트 (style, mood, caption, hashtags 등)
        model_config: 모델 설정 (None이면 현재 ComfyUI 모델 기준)
        
    Returns:
        최적화된 최종 프롬프트
        
    Raises:
        PromptOptimizationError: 프롬프트 처리 실패 시
    """
    # 0) model_config 자동 추론
    if model_config is None:
        try:
            current_model_name = get_current_comfyui_model()
        except NameError as e:
            raise PromptOptimizationError(
                f"모델 정보를 가져올 수 없습니다: {e}"
            ) from e

        if current_model_name:
            try:
                model_config = registry.get_model(current_model_name)
            except Exception as e:
                logger.exception("모델 설정 조회 실패")
                raise PromptOptimizationError(
                    f"모델 설정을 찾을 수 없습니다: {current_model_name}"
                ) from e

    # 1) 모델 정보를 얻지 못했다면 원본 반환
    if not model_config:
        return raw_prompt.strip()

    # 2) GPT 최적화 비활성화 시 원본 반환
    opt_config = registry.get_prompt_optimization_config()
    if not opt_config.get("enabled", True):
        return raw_prompt.strip()

    # 3) Context 통합
    context = context or {}
    full_input = raw_prompt
    if context.get("caption"):
        full_input = f"{full_input} ({context['caption']})".strip()
    
    model_type = (getattr(model_config, "type", "") or "").lower()
    is_flux = "flux" in model_type

    # 4) 단일 GPT 호출로 처리 (기존 3단계 통합)
    if not openai_client:
        return full_input

    try:
        if is_flux:
            # FLUX 전용 통합 프롬프트 (기존 3단계를 하나로)
            system_prompt = f"""You are an expert FLUX prompt engineer.
Convert Korean/English input to an optimized FLUX prompt.

Required style: {context.get('style', 'professional')}
Mood: {context.get('mood', 'natural, vivid')}

Rules:
- Expand visual details: background, lighting, action, atmosphere, composition
- Output 2-3 natural English sentences (NOT keyword lists)
- Keep under 60 tokens total
- Include concise realism hints: "realistic hands and face", "correct anatomy"
- Do NOT add negative prompts

Output ONLY the final FLUX prompt."""
        else:
            # 기타 모델용 통합 프롬프트
            max_tokens = getattr(model_config, "max_tokens", 77) if model_config else 77
            constraint = f"Keep under {max_tokens} tokens" if max_tokens <= 77 else "Keep concise but descriptive (under 150 words)"
            
            system_prompt = f"""You are a professional prompt engineer for image generation AI.
Convert and refine the input for clarity, realism, and aesthetic quality.

Style: {context.get('style', 'professional')}
Mood: {context.get('mood', 'natural')}

Rules:
- Expand visual details naturally
- {constraint}
- Include quality hints: "detailed hands, correct anatomy, clear facial features"

Output ONLY the polished English prompt."""

        full_prompt = f"{system_prompt}\n\n[Input]\n{full_input}\n\nGenerate the optimized prompt:"

        resp = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            reasoning={"effort": "minimal"},
            input=full_prompt,
            max_output_tokens=200,
        )
        result = getattr(resp, "output_text", None) or str(resp)
        result = result.strip()
        logger.info(f"✅ 통합 프롬프트 생성 완료 (1회 GPT 호출): {result[:80]}...")
        return result

    except Exception as e:
        logger.exception("프롬프트 최적화 중 예외 발생")
        raise PromptOptimizationError(
            f"프롬프트 처리 실패: {e}"
        ) from e


def build_final_prompt(raw_prompt: str, model_config=None) -> str:
    """공용 최종 프롬프트 빌더 (T2I / I2I / 편집 공용)

    - FLUX 계열 모델:
        1) expand_prompt_with_gpt   : 한국어/짧은 문장을 자연스러운 영어 이미지 프롬프트로 확장
        2) apply_flux_template      : FLUX 전용 스타일/구도 템플릿 적용
        3) optimize_prompt          : 모델별 토큰 제한/정책에 맞게 최종 다듬기
    - 그 외 모델: optimize_prompt 한 번만 적용

    model_config 가 None 인 경우:
        - 현재 ComfyUI에서 로드된 모델 이름을 가져와(registry 기반)
        - 해당 ModelConfig 를 자동으로 사용
        - 모델 정보를 얻지 못하면 raw_prompt 를 그대로 반환
        
    NOTE: 이 함수는 하위 호환성을 위해 유지됩니다. 새 코드는 build_final_prompt_v2() 사용을 권장합니다.
    """
    # 0) model_config 가 명시되지 않은 경우(예: 편집 모드)는
    #    현재 ComfyUI 모델 기준으로 자동 추론
    if model_config is None:
        try:
            current_model_name = get_current_comfyui_model()
        except NameError:
            current_model_name = None

        if current_model_name:
            try:
                model_config = registry.get_model(current_model_name)
            except Exception:
                model_config = None

    # 1) 여전히 모델 정보를 얻지 못했다면, 원본 프롬프트를 그대로 사용
    if not model_config:
        return raw_prompt.strip()

    model_type = (getattr(model_config, "type", "") or "").lower()

    # 2) FLUX 계열 모델인 경우 3단계 파이프라인 적용
    if "flux" in model_type:
        expanded = expand_prompt_with_gpt(raw_prompt)
        templated = apply_flux_template(expanded)
        final_prompt = optimize_prompt(templated, model_config)
    else:
        # 3) 그 외 모델은 단일 최적화만 적용
        final_prompt = optimize_prompt(raw_prompt, model_config)

    # 4) 혹시 결과가 비어 있으면 폴백으로 raw_prompt 사용
    return final_prompt.strip() or raw_prompt.strip()













# def build_final_prompt(raw_prompt: str, model_config) -> str:
#     """
#     공용 최종 프롬프트 빌더 (T2I / I2I / 편집 공용)
#     - FLUX: 3단계 (한국어 확장 → FLUX 템플릿 → 최종 폴리시)
#     - 그 외: 단일 최종 폴리시
#     """
#     if not model_config:
#         return raw_prompt

#     model_type = (model_config.type if model_config else "").lower()

#     if "flux" in model_type:
#         expanded = expand_prompt_with_gpt(raw_prompt)
#         templated = apply_flux_template(expanded)
#         final_prompt = optimize_prompt(templated, model_config)
#     else:
#         final_prompt = optimize_prompt(raw_prompt, model_config)

#     return final_prompt.strip() or raw_prompt

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
        logger.error(f"🚨 GPT 호출 실패: {e}")
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
    post_process_method: str = "none",  # "none", "impact_pack", "adetailer"
    model_name: str = None  # 사용할 모델 이름 (없으면 현재 로드된 모델 사용)
) -> bytes:
    """
    ComfyUI를 사용한 T2I 이미지 생성

    Args:
        post_process_method: 후처리 방식
            - "none": 후처리 없음
            - "impact_pack": ComfyUI Impact Pack (YOLO+SAM)
            - "adetailer": 기존 ADetailer (YOLO+MediaPipe)
        model_name: 사용할 모델 이름 (선택사항, 없으면 현재 로드된 모델 사용)
    """
    from .comfyui_client import ComfyUIClient
    from .comfyui_workflows import (
        get_flux_t2i_workflow,
        get_flux_t2i_with_impact_workflow,
        update_flux_t2i_workflow,
        load_image_editing_config
    )

    # 현재 로드된 ComfyUI 모델 확인
    current_model_name = get_current_comfyui_model()

    # 모델이 로드되지 않았고, 요청에 model_name이 있으면 자동 로드
    if not current_model_name and model_name:
        logger.info(f"🔄 모델 자동 로드 시작: {model_name}")
        # 전역 변수 업데이트 (실제 워크플로우에서 사용됨)
        global current_comfyui_model
        current_comfyui_model = model_name
        current_model_name = model_name
    elif not current_model_name:
        raise RuntimeError("모델이 로드되지 않았습니다. 먼저 모델을 선택하세요.")

    # 모델 설정 가져오기
    model_config = registry.get_model(current_model_name)
    if not model_config:
        raise RuntimeError(f"모델 설정을 찾을 수 없습니다: {current_model_name}")

    # ✅ 통합 프롬프트 빌더 사용 (Phase 1 개선)
    context = {
        "style": "Instagram banner, professional",
        "mood": "vibrant, motivational"
    }
    final_prompt = build_final_prompt_v2(prompt, context, model_config)

    # Steps 검증
    if steps < 1:
        steps = model_config.default_steps
    steps = min(steps, model_config.max_steps)

    # Guidance scale 설정
    if guidance_scale is None:
        guidance_scale = model_config.guidance_scale

    logger.info(f"🎨 ComfyUI로 T2I 이미지 생성 중")
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
        timeout = comfyui_config.get("timeout", 600)

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
            prompt=final_prompt,
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
                prompt=final_prompt,
                targets=adetailer_targets or ["hand"]
            )

            buf = io.BytesIO()
            image.save(buf, format="PNG")
            image_bytes = buf.getvalue()

        logger.info(f"✅ 생성 완료: {len(image_bytes)} bytes")
        return image_bytes

    except Exception as e:
        logger.error(f"❌ ComfyUI T2I 생성 실패: {e}")
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

        logger.info(f"🔧 ADetailer 후처리 시작 (targets: {targets})")

        # model_loader 초기화 (ADetailer용)
        if model_loader is None or not model_loader.is_loaded():
            model_loader = ModelLoader(cache_dir=hf_cache_dir)
            success = model_loader.load_with_fallback()
            if not success:
                logger.warning("⚠️ 모델 로드 실패 - ADetailer 건너뜀")
                return image

        post_processor = get_post_processor()

        # I2I 파이프라인을 Inpaint용으로 사용
        inpaint_pipe = model_loader.i2i_pipe

        # ComfyUI 사용 시 i2i_pipe가 None이므로 ADetailer 사용 불가
        if inpaint_pipe is None:
            logger.warning("⚠️ ComfyUI 사용 중 - ADetailer는 Impact Pack을 사용하세요")
            return image

        processed_image, info = post_processor.full_pipeline(
            image=image,
            inpaint_pipeline=inpaint_pipe,
            prompt=prompt,
            auto_detect=True,
            adetailer_targets=targets,
            adetailer_strength=strength
        )

        if not info["processed"]:
            logger.info(f"ℹ️ ADetailer: 이상 없음, 원본 유지")

        return processed_image

    except Exception as e:
        logger.warning(f"⚠️ ADetailer 실패, 원본 반환: {e}")
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
    post_process_method: str = "none",  # "none", "impact_pack", "adetailer"
    model_name: str = None  # 사용할 모델 이름 (없으면 현재 로드된 모델 사용)
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
        model_name: 사용할 모델 이름 (선택사항, 없으면 현재 로드된 모델 사용)
    """
    from .comfyui_client import ComfyUIClient
    from .comfyui_workflows import (
        get_flux_i2i_workflow,
        update_flux_i2i_workflow,
        load_image_editing_config
    )

    # 현재 로드된 ComfyUI 모델 확인
    current_model_name = get_current_comfyui_model()

    # 모델이 로드되지 않았고, 요청에 model_name이 있으면 자동 로드
    if not current_model_name and model_name:
        logger.info(f"🔄 모델 자동 로드 시작: {model_name}")
        # 전역 변수 업데이트 (실제 워크플로우에서 사용됨)
        global current_comfyui_model
        current_comfyui_model = model_name
        current_model_name = model_name
    elif not current_model_name:
        raise RuntimeError("모델이 로드되지 않았습니다. 먼저 모델을 선택하세요.")

    # 모델 설정 가져오기
    model_config = registry.get_model(current_model_name)
    if not model_config:
        raise RuntimeError(f"모델 설정을 찾을 수 없습니다: {current_model_name}")

    # ✅ 통합 프롬프트 빌더 사용 (Phase 1 개선)
    context = {
        "style": "professional, natural",
        "mood": "balanced, refined"
    }
    final_prompt = build_final_prompt_v2(prompt, context, model_config)

    # Steps 검증
    if steps < 1:
        steps = model_config.default_steps
    steps = min(steps, model_config.max_steps)

    # Guidance scale 설정
    if guidance_scale is None:
        guidance_scale = model_config.guidance_scale

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
        timeout = comfyui_config.get("timeout", 600)

        client = ComfyUIClient(base_url=base_url, timeout=timeout)

        # I2I 워크플로우 가져오기
        workflow = get_flux_i2i_workflow()

        # 워크플로우 파라미터 업데이트
        workflow = update_flux_i2i_workflow(
            workflow=workflow,
            model_name=current_model_name,
            prompt=final_prompt,
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
                prompt=final_prompt,
                targets=adetailer_targets or ["hand"]
            )

            buf = io.BytesIO()
            image.save(buf, format="PNG")
            image_bytes = buf.getvalue()

        logger.info(f"✅ 편집 완료: {len(image_bytes)} bytes")
        return image_bytes

    except Exception as e:
        logger.error(f"❌ ComfyUI I2I 편집 실패: {e}")
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"이미지 편집 실패: {e}")

# ===========================
# 모델 전환
# ===========================
# ===========================
# 상태 조회
# ===========================
def get_service_status() -> dict:
    """서비스 상태 반환"""
    current_model = get_current_comfyui_model()
    status = {
        "gpt_ready": openai_client is not None,
        "image_ready": current_model is not None,
        "current_model": current_model
    }

    return status

# ===========================
# 🆕 이미지 편집 (ComfyUI)
# ===========================
def edit_image_with_comfyui(
    experiment_id: str,
    input_image_bytes: bytes,
    prompt: str,
    negative_prompt: str = "",
    steps: int = None,
    guidance_scale: float = None,
    strength: float = None,
    # 새로운 모드용 파라미터
    controlnet_type: str = "depth",
    controlnet_strength: float = 0.7,
    denoise_strength: float = 1.0,
    blending_strength: float = 0.35,
    background_prompt: str = None
) -> dict:
    """
    ComfyUI를 사용한 이미지 편집

    Args:
        experiment_id: 실험 ID ("portrait_mode", "product_mode", "hybrid_mode", "ben2_flux_fill", "ben2_qwen_image")
        input_image_bytes: 입력 이미지 바이트
        prompt: 편집 프롬프트
        steps: 추론 단계
        guidance_scale: Guidance scale
        strength: 변화 강도
        controlnet_type: ControlNet 타입 ("depth" 또는 "canny")
        controlnet_strength: ControlNet 강도
        denoise_strength: 변경 강도
        blending_strength: 합성 자연스러움 (Product 모드)
        background_prompt: 배경 프롬프트 (Product 모드)
    """
    import base64
    import time
    import logging
    from .comfyui_client import ComfyUIClient
    from .comfyui_workflows import (
        get_workflow_template,
        update_workflow_inputs,
        get_workflow_input_image_node_id,
        load_image_editing_config,
        get_pipeline_steps_for_mode
    )

    logger = logging.getLogger(__name__)
    start_time = time.time()

    try:
        # 설정 로드
        config = load_image_editing_config()

        # 파이프라인 단계 매핑 로드
        pipeline_steps = get_pipeline_steps_for_mode(experiment_id)

        # 모드 정보 찾기 (새로운 구조)
        mode_info = None
        for mode_id, mode_data in config.get("editing_modes", {}).items():
            if mode_data["id"] == experiment_id:
                mode_info = mode_data
                break

        if not mode_info:
            return {
                "success": False,
                "experiment_id": experiment_id,
                "experiment_name": "Unknown",
                "output_image_base64": None,
                "background_removed_image_base64": None,
                "error": f"알 수 없는 모드 ID: {experiment_id}",
                "elapsed_time": None
            }

        # ✅ 편집 프롬프트에도 통합 빌더 적용 (Phase 1 개선)
        # 편집 모드는 특정 모델 설정을 바로 가져오기 어려우므로 model_config=None으로 동작 (fallback)
        context = {
            "style": "professional editing",
            "mood": "refined, enhanced"
        }
        final_prompt = build_final_prompt_v2(prompt, context, model_config=None)

        # ComfyUI 클라이언트 초기화
        comfyui_config = config.get("comfyui", {})
        base_url = comfyui_config.get("base_url", "http://localhost:8188")
        timeout = comfyui_config.get("timeout", 600)

        client = ComfyUIClient(base_url=base_url, timeout=timeout)

        # 워크플로우 템플릿 가져오기
        workflow = get_workflow_template(experiment_id)

        # 워크플로우 업데이트 (사용자 입력 반영)
        workflow = update_workflow_inputs(
            workflow=workflow,
            experiment_id=experiment_id,
            prompt=final_prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            guidance_scale=guidance_scale,
            strength=strength,
            # 새로운 모드 파라미터
            controlnet_type=controlnet_type,
            controlnet_strength=controlnet_strength,
            denoise_strength=denoise_strength,
            blending_strength=blending_strength,
            background_prompt=background_prompt
        )

        # 입력 이미지 노드 ID
        input_node_id = get_workflow_input_image_node_id(experiment_id)

        logger.info(f"🎨 ComfyUI 이미지 편집 시작")
        logger.info(f"   모드: {mode_info['name']}")
        logger.info(f"   설명: {mode_info['description']}")
        logger.info(f"   프롬프트: {final_prompt}")
        logger.info(f"   파라미터: steps={steps}, guidance={guidance_scale}")
        if experiment_id == "portrait_mode" or experiment_id == "hybrid_mode":
            logger.info(f"   ControlNet: type={controlnet_type}, strength={controlnet_strength}, denoise={denoise_strength}")
        elif experiment_id == "product_mode":
            logger.info(f"   배경: {background_prompt or final_prompt}, blending={blending_strength}")

        # 진행상황 콜백 함수 정의
        step_count = [0]  # 완료된 단계 수 (mutable 리스트로 클로저에서 수정 가능)

        def progress_callback(node_id: str, elapsed: float):
            """노드 완료 시 호출되는 콜백"""
            step_name = pipeline_steps.get(node_id, f"노드 {node_id}")
            step_count[0] += 1
            logger.info(f"   [{step_count[0]:2d}/{len(pipeline_steps):2d}] {step_name} (경과: {elapsed:.1f}초)")

        # 워크플로우 실행
        logger.info(f"🔄 워크플로우 실행 시작 (총 {len(pipeline_steps)}단계)")
        output_images, history = client.execute_workflow(
            workflow=workflow,
            input_image=input_image_bytes,
            input_image_node_id=input_node_id,
            progress_callback=progress_callback
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

        logger.info(f"✅ ComfyUI 편집 완료! (소요 시간: {elapsed_time:.1f}초)")

        return {
            "success": True,
            "experiment_id": experiment_id,
            "experiment_name": mode_info["name"],
            "output_image_base64": output_image_base64,
            "background_removed_image_base64": background_removed_base64,
            "error": None,
            "elapsed_time": elapsed_time
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        error_msg = str(e)
        logger.error(f"❌ ComfyUI 편집 실패: {error_msg}")

        return {
            "success": False,
            "experiment_id": experiment_id,
            "experiment_name": "Unknown",
            "output_image_base64": None,
            "background_removed_image_base64": None,
            "error": error_msg,
            "elapsed_time": elapsed_time
        }


def get_image_editing_experiments() -> dict:
    """사용 가능한 이미지 편집 실험 목록 반환 (생성 모델 + 편집 모델)"""
    from .comfyui_workflows import load_image_editing_config

    try:
        config = load_image_editing_config()
        experiments = config.get("experiments", [])

        # 편집 실험 목록
        editing_experiments = [
            {
                "id": exp["id"],
                "name": exp["name"],
                "description": exp["description"],
                "background_removal_model": exp["background_removal"]["model"],
                "editing_model": exp["image_editing"]["model"],
                "features": exp.get("features", [])  # 모델별 기능 목록 포함
            }
            for exp in experiments
        ]

        # 생성 모델 목록 추가
        generation_models = [
            {
                "id": "FLUX.1-dev-Q8",
                "name": "FLUX.1-dev Q8",
                "description": "FLUX.1-dev GGUF 8-bit 양자화 (이미지 생성, 권장)"
            },
            {
                "id": "FLUX.1-dev-Q4",
                "name": "FLUX.1-dev Q4",
                "description": "FLUX.1-dev GGUF 4-bit 양자화 (메모리 절약)"
            }
        ]

        # 생성 모델 + 편집 모델 모두 반환
        all_experiments = generation_models + editing_experiments

        return {
            "success": True,
            "experiments": all_experiments
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "experiments": []
        }


# ===========================
# 🆕 ComfyUI 모델 관리 (프리로딩/언로드)
# ===========================
current_comfyui_model: Optional[str] = None

# 프리로드 기능 제거됨
def _removed_preload_model_in_comfyui(experiment_id: str) -> dict:
    """
    ComfyUI에 모델 미리 로드 (최소 실행 워크플로우 전송)
    """
    global current_comfyui_model
    
    # 이미 로드된 모델이면 스킵
    if current_comfyui_model == experiment_id:
        return {"success": True, "message": "이미 로드된 모델입니다.", "model": experiment_id}

    from .comfyui_client import ComfyUIClient
    from .comfyui_workflows import _removed_get_preload_workflow, load_image_editing_config, get_workflow_input_image_node_id
    import io
    from PIL import Image
    
    try:
        config = load_image_editing_config()
        comfyui_config = config.get("comfyui", {})
        base_url = comfyui_config.get("base_url", "http://localhost:8188")
        
        client = ComfyUIClient(base_url=base_url)
        
        # 1. 더미 이미지 생성 (64x64 검은색)
        dummy_image = Image.new('RGB', (64, 64), color='black')
        img_byte_arr = io.BytesIO()
        dummy_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # 2. 이미지 업로드
        filename = "preload_dummy.png"
        upload_resp = client.upload_image(img_byte_arr.read(), filename)
        if not upload_resp:
            return {"success": False, "message": "더미 이미지 업로드 실패"}
        
        # 3. 프리로딩 워크플로우 생성
        workflow = _removed_get_preload_workflow(experiment_id)
        if not workflow:
            return {"success": False, "message": "프리로딩 워크플로우 생성 실패"}
        
        # 4. 입력 이미지 노드 설정
        input_node_id = get_workflow_input_image_node_id(experiment_id)
        if input_node_id in workflow:
            workflow[input_node_id]["inputs"]["image"] = filename
            
        # 5. 큐에 전송
        logger.info(f"🚀 모델 프리로딩 시작: {experiment_id}")
        client.queue_prompt(workflow)
        
        # 6. 상태 업데이트
        current_comfyui_model = experiment_id
        
        return {"success": True, "message": "모델 로딩 요청 완료", "model": experiment_id}
        
    except Exception as e:
        error_msg = str(e)
        # prompt_no_outputs 에러는 명확하게 실패로 처리
        if "prompt_no_outputs" in error_msg.lower():
            logger.error(f"❌ 워크플로우에 출력 노드가 없어 실행 불가")
            return {"success": False, "message": "워크플로우 구성 오류 (출력 노드 필요)"}
        
        logger.error(f"❌ 모델 프리로딩 실패: {e}")
        return {"success": False, "message": str(e)}

def unload_comfyui_model() -> dict:
    """ComfyUI 모델 언로드 및 메모리 해제"""
    global current_comfyui_model
    
    from .comfyui_client import ComfyUIClient
    from .comfyui_workflows import load_image_editing_config
    
    try:
        config = load_image_editing_config()
        base_url = config.get("comfyui", {}).get("base_url", "http://localhost:8188")
        
        client = ComfyUIClient(base_url=base_url)
        
        # 메모리 해제 요청
        success = client.free_memory(unload_models=True, free_memory=True)
        
        if success:
            current_comfyui_model = None
            return {"success": True, "message": "모델 언로드 및 메모리 해제 완료"}
        else:
            return {"success": False, "message": "메모리 해제 요청 실패"}
            
    except Exception as e:
        return {"success": False, "message": str(e)}

def get_current_comfyui_model() -> Optional[str]:
    """현재 로드된 ComfyUI 모델 ID 반환"""
    return current_comfyui_model

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
                "queue_info": queue_info,
                "current_model": current_comfyui_model  # 현재 모델 정보 추가
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
