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
# 프롬프트 최적화 (FLUX 전용 템플릿 반영)
# ===========================
def optimize_prompt(text: str, model_config) -> str:
    """
    한국어 프롬프트를 영어로 번역 및 최적화
    - FLUX 계열: 서술형 FLUX 템플릿 구조 사용
    - 그 외(SDXL 등): 기존 키워드/묘사형 이미지 프롬프트
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
            length_rule = "Keep it under 60 words (the image model has a tight token limit)."
        else:
            length_rule = "Keep it concise but descriptive (under 150 words)."
        
        model_type = getattr(model_config, "type", "").lower() if model_config else ""
        is_flux = "flux" in model_type

        if is_flux:
            # 🔹 FLUX 전용 템플릿: 자연어/서술형, 짧은 negative, 카메라/조명/환경 강조
            gpt_prompt = f"""
You are a professional prompt engineer specialized in FLUX image generation models.

Goal:
- Convert the following Korean marketing text into a detailed FLUX-style English prompt.
- Use natural descriptive sentences, NOT comma-separated keyword lists.

Follow this FLUX prompt structure:

1. Subject (main focus of the image)
   - e.g. "A professional photo of a young female Pilates trainer"

2. Action / Pose / Context (what they are doing)
   - e.g. "performing a reformer leg stretch with perfect posture"

3. Environment (where the scene takes place)
   - e.g. "inside a clean bright Pilates studio" or "in a modern gym with chrome equipment"

4. Lighting (mood and light quality)
   - e.g. "with soft natural lighting and realistic shadows"

5. Quality / Camera / Style
   - e.g. "shot on a 50mm lens, ultra realistic, high-resolution, detailed skin texture"

Then optionally add ONE short negative line:
- e.g. "no distorted face, no extra limbs, no blurry details"

IMPORTANT FLUX RULES:
- Avoid long keyword chains.
- Avoid very long negative prompts.
- Emphasize camera, lighting, and environment.
- {length_rule}

Quality guidelines for people and fitness scenes:
- If the scene involves people, naturally include phrases like:
  "detailed hands, five fingers, natural hand pose, anatomically correct hands, correct thumb direction,
   detailed face, clear facial features, symmetric face, natural eye shape,
   correct human anatomy, natural body proportions, well-fitted clothing".
- If the scene involves objects being held or touched, mention:
  "proper object interaction, realistic grip, natural holding pose,
   physically accurate, object not clipping through body".
- If the scene involves fitness/gym/sports equipment, mention:
  "equipment not penetrating the body, proper form,
   hands gripping equipment correctly, realistic weight interaction".

Korean input marketing text:
{text}

Output:
- Write ONLY the final FLUX-style English prompt.
- 2–4 sentences following the structure above.
- Do NOT add explanations or bullets.
"""
        else:
            # 🔹 SDXL 등 일반 모델용: 기존 스타일 유지 (키워드+묘사형)
            gpt_prompt = f"""
You are a professional prompt engineer for image generation AI (e.g. SDXL).
Convert the following Korean marketing text into an optimized English image prompt.

Requirements:
- Focus on visual elements, style, mood, and composition.
- Use a mix of short descriptive phrases and concise sentences.
- {length_rule}

Quality guidelines for people and fitness scenes:
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

Korean input marketing text:
{text}

Output ONLY the English prompt, no explanations.
"""

        resp = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            input=gpt_prompt,
            reasoning={"effort": "minimal"},
            max_output_tokens=200,
        )
        
        result = getattr(resp, "output_text", None) or str(resp)
        optimized = result.strip()
        print("🔄 프롬프트 최적화 완료")
        print(f"  원본: {text}")
        print(f"  최적화: {optimized}")
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
# 이미지 생성 (T2I)
# ===========================
def generate_t2i_core(
    prompt: str,
    width: int,
    height: int,
    steps: int,
    guidance_scale: float = None,
    enable_adetailer: bool = True,
    adetailer_targets: list = None
) -> bytes:
    global model_loader

    if not model_loader or not model_loader.is_loaded():
        raise RuntimeError("이미지 파이프라인이 초기화되지 않았습니다.")

    model_config = model_loader.current_model_config

    # 🔹 페이지2에서 들어오는 모든 프롬프트는 여기서
    #    - 연결 모드 ON: 페이지1 문구 기반 + FLUX 템플릿
    #    - 연결 모드 OFF: 사용자가 직접 쓴 설명 + FLUX 템플릿
    optimized_prompt = optimize_prompt(prompt, model_config)

    # Steps 검증
    if steps < 1:
        steps = model_config.default_steps
    steps = min(steps, model_config.max_steps)

    # 랜덤 seed 생성 (매번 다른 이미지)
    import random
    random_seed = random.randint(0, 2**32 - 1)
    generator = torch.Generator(device=model_loader.device).manual_seed(random_seed)

    # 생성 파라미터 구성
    gen_params = {
        "prompt": optimized_prompt,
        "width": width,
        "height": height,
        "num_inference_steps": steps,
        "generator": generator,
    }

    # 조건부 파라미터 추가
    if model_config.use_negative_prompt:
        gen_params["negative_prompt"] = model_config.negative_prompt

    # guidance_scale: 사용자 지정값 우선, 없으면 모델 기본값
    if guidance_scale is not None:
        gen_params["guidance_scale"] = guidance_scale
    elif model_config.guidance_scale is not None:
        gen_params["guidance_scale"] = model_config.guidance_scale

    print(f"🎨 이미지 생성 중")
    print(f"   모델: {model_loader.current_model_name}")
    print(f"   Steps: {steps}")
    print(f"   크기: {width}x{height}")
    print(f"   Seed: {random_seed}")
    if "guidance_scale" in gen_params:
        print(f"   Guidance: {gen_params['guidance_scale']}")

    # 생성
    try:
        result = model_loader.t2i_pipe(**gen_params)
        image = result.images[0]

        # 이미지 크기 확인
        print(f"✅ 생성 완료: 실제 크기 = {image.size}")

        # ADetailer 후처리 (손/얼굴 개선)
        if enable_adetailer:
            image = apply_adetailer(
                image=image,
                prompt=optimized_prompt,
                targets=adetailer_targets or ["hand"]
            )

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        image_bytes = buf.getvalue()
        print(f"✅ PNG 변환 완료: {len(image_bytes)} bytes")
        return image_bytes
    except Exception as gen_err:
        print(f"❌ 이미지 생성 또는 변환 실패: {gen_err}")
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"이미지 생성 실패: {gen_err}")


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

        if info["processed"]:
            print(f"✅ ADetailer 처리 완료")
        else:
            print(f"ℹ️ ADetailer: 이상 없음, 원본 유지")

        return processed_image

    except Exception as e:
        print(f"⚠️ ADetailer 실패, 원본 반환: {e}")
        return image

# ===========================
# 이미지 편집 (I2I)
# ===========================
def generate_i2i_core(input_image_bytes: bytes, prompt: str, strength: float, 
                      width: int, height: int, steps: int) -> bytes:
    global model_loader
    
    if not model_loader or not model_loader.is_loaded():
        raise RuntimeError("이미지 파이프라인이 초기화되지 않았습니다.")
    
    model_config = model_loader.current_model_config
    
    # I2I 지원 확인
    if not model_config.supports_i2i:
        raise RuntimeError(f"현재 모델({model_loader.current_model_name})은 I2I를 지원하지 않습니다.")
    
    # 프롬프트 최적화
    optimized_prompt = optimize_prompt(prompt, model_config)
    
    # 입력 이미지 준비
    input_image = Image.open(io.BytesIO(input_image_bytes)).convert("RGB").resize((width, height))
    
    # Steps 검증
    if steps < 1:
        steps = model_config.default_steps
    steps = min(steps, model_config.max_steps)
    
    # 생성 파라미터
    gen_params = {
        "prompt": optimized_prompt,
        "image": input_image,
        "strength": float(strength),
        "num_inference_steps": steps,
    }
    
    if model_config.use_negative_prompt:
        gen_params["negative_prompt"] = model_config.negative_prompt
    
    if model_config.guidance_scale is not None:
        gen_params["guidance_scale"] = model_config.guidance_scale
    
    print(f"✏️ 이미지 편집 중")
    print(f"   모델: {model_loader.current_model_name}")
    print(f"   Strength: {strength}")
    print(f"   Steps: {steps}")
    
    # 생성
    result = model_loader.i2i_pipe(**gen_params)
    image = result.images[0]
    
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

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


















# # services.py (리팩토링 버전)
# """
# AI 서비스 레이어 - 설정 기반 모델 관리
# """
# import os
# import io
# from typing import Optional

# from openai import OpenAI
# import torch
# from PIL import Image
# from dotenv import load_dotenv

# from .model_registry import get_registry
# from .model_loader import ModelLoader

# # Load env
# load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# MODEL_GPT_MINI = "gpt-5-mini"

# # HF cache location
# # GCP: /home/shared 사용 (이미 다운로드된 모델 재사용)
# # 로컬: project_root/cache/hf_models 사용
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# if os.path.exists("/home/shared"):
#     hf_cache_dir = "/home/shared"
# else:
#     hf_cache_dir = os.path.join(project_root, "cache", "hf_models")
#     os.makedirs(hf_cache_dir, exist_ok=True)

# # 전역 인스턴스
# openai_client: Optional[OpenAI] = None
# model_loader: Optional[ModelLoader] = None
# registry = get_registry()

# # Initialize OpenAI client
# if OPENAI_API_KEY:
#     try:
#         openai_client = OpenAI(api_key=OPENAI_API_KEY)
#     except Exception as e:
#         print(f"⚠️ OpenAI 초기화 실패: {e}")
#         openai_client = None
# else:
#     print("⚠️ OPENAI_API_KEY 미설정 — GPT 기능 불가")

# # ===========================
# # Utility helpers
# # ===========================
# def align_to_64(x: int) -> int:
#     """64의 배수로 정렬 (최소 64)"""
#     try:
#         xi = int(x)
#     except Exception:
#         xi = 64
#     return max(64, (xi // 64) * 64)

# def ensure_steps(steps: int) -> int:
#     try:
#         s = int(steps)
#     except Exception:
#         s = 1
#     return max(1, s)

# # ===========================
# # 모델 초기화
# # ===========================
# def init_image_pipelines():
#     """
#     설정 파일 기반으로 이미지 생성 모델 로드
#     """
#     global model_loader
    
#     # 이미 로드된 경우 스킵
#     if model_loader and model_loader.is_loaded():
#         print("ℹ️ 이미지 파이프라인 이미 로드됨 — 스킵")
#         return
    
#     # ModelLoader 생성
#     if model_loader is None:
#         model_loader = ModelLoader(cache_dir=hf_cache_dir)
    
#     # 폴백 체인으로 로딩 시도
#     success = model_loader.load_with_fallback()
    
#     if success:
#         info = model_loader.get_current_model_info()
#         print(f"✅ 이미지 생성 준비 완료")
#         print(f"   모델: {info['name']} ({info['type']})")
#         print(f"   장치: {info['device']}")
#     else:
#         print("❌ 모든 모델 로딩 실패 - 이미지 생성 불가")

# # ===========================
# # 프롬프트 최적화
# # ===========================
# def optimize_prompt(text: str, model_config) -> str:
#     """
#     한국어 프롬프트를 영어로 번역 및 최적화
#     모델별 토큰 제한 고려
#     """
#     if not openai_client:
#         return text
    
#     # 프롬프트 최적화 설정 확인
#     opt_config = registry.get_prompt_optimization_config()
#     if not opt_config.get("enabled", True):
#         return text
    
#     # 한글 번역 비활성화 설정 확인
#     if not opt_config.get("translate_korean", True):
#         return text
    
#     try:
#         # 모델별 길이 제약
#         max_tokens = model_config.max_tokens if model_config else 77
        
#         if max_tokens <= 77:
#             constraint = f"Keep it under 60 words (model has {max_tokens} token limit)."
#         else:
#             constraint = "Keep it concise but descriptive (under 150 words)."
        
#         system_prompt = f"""You are a professional prompt engineer for image generation AI.
# Translate Korean marketing text to optimized English prompts.
# Focus on visual elements, style, mood, and composition.
# {constraint}

# IMPORTANT - Quality keywords to prevent AI artifacts:

# 1. If the scene involves people:
#    - Hands: "detailed hands, five fingers, natural hand pose, anatomically correct hands, Hand Position Left Right Proper Position, correct thumb direction"
#    - Faces: "detailed face, clear facial features, symmetric face, symmetric eyes, natural eye shape"
#    - Body: "correct human anatomy, natural body proportions, well-fitted clothing"

# 2. If the scene involves objects being held or touched:
#    - "proper object interaction, object not clipping through body"
#    - "realistic grip, natural holding pose"
#    - "physically accurate, no overlapping body parts with objects"

# 3. If the scene involves fitness/gym/sports equipment:
#    - "equipment not penetrating body, proper form"
#    - "hands gripping equipment correctly, realistic weight interaction"

# Always include relevant keywords based on the scene content.

# Output ONLY the English prompt, no explanations."""

#         resp = openai_client.responses.create(
#             model=MODEL_GPT_MINI,
#             input=f"Convert to image prompt:\n{text}",
#             reasoning={"effort": "minimal"},
#             max_output_tokens=200,
#         )
        
#         result = getattr(resp, "output_text", None) or str(resp)
#         optimized = result.strip()
#         print(f"🔄 프롬프트 최적화:\n  원본: {text}\n  최적화: {optimized}")
#         return optimized
        
#     except Exception as e:
#         print(f"⚠️ 프롬프트 최적화 실패, 원본 사용: {e}")
#         return text

# # ===========================
# # GPT-5 Mini: 문구 생성
# # ===========================
# def generate_caption_core(info: dict, tone: str) -> str:
#     if not openai_client:
#         raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다.")

#     prompt = f"""
# 당신은 헬스케어 소상공인을 위한 전문 인스타그램 콘텐츠 크리에이터입니다.
# 아래 정보를 바탕으로 인스타그램 게시물에 최적화된 콘텐츠를 생성해 주세요.

# 요청:
# 1. 인스타그램 홍보 문구 3개 작성
#     - 각 문구: 후킹 → 핵심 메시지 → CTA
#     - 이모티콘 사용
#     - 문체 스타일: {tone}
# 2. 해시태그 15개 추천 (중복 제거)

# [정보]
# 서비스 종류: {info.get('service_type')}
# 서비스명: {info.get('service_name')}
# 핵심 특징: {info.get('features')}
# 지역: {info.get('location')}

# 출력 형식:
# 문구:
# 1. [문구1]
# 2. [문구2]
# 3. [문구3]

# 해시태그:
# #[태그1] #[태그2] ... #[태그N]
# """
#     try:
#         resp = openai_client.responses.create(
#             model=MODEL_GPT_MINI,
#             input=prompt,
#             reasoning={"effort": "minimal"},
#             max_output_tokens=512,
#         )
#         text = getattr(resp, "output_text", None) or str(resp)
#         return text.strip()
#     except Exception as e:
#         print(f"🚨 GPT 호출 실패: {e}")
#         raise

# # ===========================
# # 이미지 생성 (T2I)
# # ===========================
# def generate_t2i_core(
#     prompt: str,
#     width: int,
#     height: int,
#     steps: int,
#     guidance_scale: float = None,
#     enable_adetailer: bool = True,
#     adetailer_targets: list = None
# ) -> bytes:
#     global model_loader

#     if not model_loader or not model_loader.is_loaded():
#         raise RuntimeError("이미지 파이프라인이 초기화되지 않았습니다.")

#     model_config = model_loader.current_model_config

#     # 프롬프트 최적화
#     optimized_prompt = optimize_prompt(prompt, model_config)

#     # Steps 검증
#     if steps < 1:
#         steps = model_config.default_steps
#     steps = min(steps, model_config.max_steps)

#     # 랜덤 seed 생성 (매번 다른 이미지)
#     import random
#     random_seed = random.randint(0, 2**32 - 1)
#     generator = torch.Generator(device=model_loader.device).manual_seed(random_seed)

#     # 생성 파라미터 구성
#     gen_params = {
#         "prompt": optimized_prompt,
#         "width": width,
#         "height": height,
#         "num_inference_steps": steps,
#         "generator": generator,
#     }

#     # 조건부 파라미터 추가
#     if model_config.use_negative_prompt:
#         gen_params["negative_prompt"] = model_config.negative_prompt

#     # guidance_scale: 사용자 지정값 우선, 없으면 모델 기본값
#     if guidance_scale is not None:
#         gen_params["guidance_scale"] = guidance_scale
#     elif model_config.guidance_scale is not None:
#         gen_params["guidance_scale"] = model_config.guidance_scale

#     print(f"🎨 이미지 생성 중")
#     print(f"   모델: {model_loader.current_model_name}")
#     print(f"   Steps: {steps}")
#     print(f"   크기: {width}x{height}")
#     print(f"   Seed: {random_seed}")
#     if "guidance_scale" in gen_params:
#         print(f"   Guidance: {gen_params['guidance_scale']}")

#     # 생성
#     try:
#         result = model_loader.t2i_pipe(**gen_params)
#         image = result.images[0]

#         # 이미지 크기 확인
#         print(f"✅ 생성 완료: 실제 크기 = {image.size}")

#         # ADetailer 후처리 (손/얼굴 개선)
#         if enable_adetailer:
#             image = apply_adetailer(
#                 image=image,
#                 prompt=optimized_prompt,
#                 targets=adetailer_targets or ["hand"]
#             )

#         buf = io.BytesIO()
#         image.save(buf, format="PNG")
#         image_bytes = buf.getvalue()
#         print(f"✅ PNG 변환 완료: {len(image_bytes)} bytes")
#         return image_bytes
#     except Exception as gen_err:
#         print(f"❌ 이미지 생성 또는 변환 실패: {gen_err}")
#         import traceback
#         traceback.print_exc()
#         raise RuntimeError(f"이미지 생성 실패: {gen_err}")


# # ===========================
# # ADetailer 후처리
# # ===========================
# def apply_adetailer(
#     image: Image,
#     prompt: str,
#     targets: list = None,
#     strength: float = 0.4
# ) -> Image:
#     """
#     ADetailer 스타일 후처리
#     - 손/얼굴 감지 후 해당 영역만 Inpaint로 재생성
#     """
#     global model_loader

#     if targets is None:
#         targets = ["hand"]

#     try:
#         from .post_processor import get_post_processor

#         print(f"🔧 ADetailer 후처리 시작 (targets: {targets})")

#         post_processor = get_post_processor()

#         # I2I 파이프라인을 Inpaint용으로 사용
#         inpaint_pipe = model_loader.i2i_pipe

#         processed_image, info = post_processor.full_pipeline(
#             image=image,
#             inpaint_pipeline=inpaint_pipe,
#             prompt=prompt,
#             auto_detect=True,
#             adetailer_targets=targets,
#             adetailer_strength=strength
#         )

#         if info["processed"]:
#             print(f"✅ ADetailer 처리 완료")
#         else:
#             print(f"ℹ️ ADetailer: 이상 없음, 원본 유지")

#         return processed_image

#     except Exception as e:
#         print(f"⚠️ ADetailer 실패, 원본 반환: {e}")
#         return image

# # ===========================
# # 이미지 편집 (I2I)
# # ===========================
# def generate_i2i_core(input_image_bytes: bytes, prompt: str, strength: float, 
#                       width: int, height: int, steps: int) -> bytes:
#     global model_loader
    
#     if not model_loader or not model_loader.is_loaded():
#         raise RuntimeError("이미지 파이프라인이 초기화되지 않았습니다.")
    
#     model_config = model_loader.current_model_config
    
#     # I2I 지원 확인
#     if not model_config.supports_i2i:
#         raise RuntimeError(f"현재 모델({model_loader.current_model_name})은 I2I를 지원하지 않습니다.")
    
#     # 프롬프트 최적화
#     optimized_prompt = optimize_prompt(prompt, model_config)
    
#     # 입력 이미지 준비
#     input_image = Image.open(io.BytesIO(input_image_bytes)).convert("RGB").resize((width, height))
    
#     # Steps 검증
#     if steps < 1:
#         steps = model_config.default_steps
#     steps = min(steps, model_config.max_steps)
    
#     # 생성 파라미터
#     gen_params = {
#         "prompt": optimized_prompt,
#         "image": input_image,
#         "strength": float(strength),
#         "num_inference_steps": steps,
#     }
    
#     if model_config.use_negative_prompt:
#         gen_params["negative_prompt"] = model_config.negative_prompt
    
#     if model_config.guidance_scale is not None:
#         gen_params["guidance_scale"] = model_config.guidance_scale
    
#     print(f"✏️ 이미지 편집 중")
#     print(f"   모델: {model_loader.current_model_name}")
#     print(f"   Strength: {strength}")
#     print(f"   Steps: {steps}")
    
#     # 생성
#     result = model_loader.i2i_pipe(**gen_params)
#     image = result.images[0]
    
#     buf = io.BytesIO()
#     image.save(buf, format="PNG")
#     return buf.getvalue()

# # ===========================
# # 모델 전환
# # ===========================
# def switch_model(model_name: str) -> dict:
#     """
#     다른 모델로 전환
#     Returns: {"success": bool, "message": str, "model_info": dict}
#     """
#     global model_loader

#     if not model_loader:
#         model_loader = ModelLoader(cache_dir=hf_cache_dir)

#     # 모델 존재 여부 확인
#     model_config = registry.get_model(model_name)
#     if not model_config:
#         return {
#             "success": False,
#             "message": f"알 수 없는 모델: {model_name}",
#             "model_info": None
#         }

#     # 이미 로드된 경우
#     if model_loader.is_loaded() and model_loader.current_model_name == model_name:
#         return {
#             "success": True,
#             "message": f"모델 '{model_name}' 이미 로드됨",
#             "model_info": model_loader.get_current_model_info()
#         }

#     # 모델 로드
#     print(f"🔄 모델 전환 중: {model_name}")
#     success = model_loader.load_model(model_name)

#     if success:
#         info = model_loader.get_current_model_info()
#         return {
#             "success": True,
#             "message": f"모델 '{model_name}' 로드 성공",
#             "model_info": info
#         }
#     else:
#         return {
#             "success": False,
#             "message": f"모델 '{model_name}' 로드 실패",
#             "model_info": None
#         }

# # ===========================
# # 상태 조회
# # ===========================
# def get_service_status() -> dict:
#     """서비스 상태 반환"""
#     status = {
#         "gpt_ready": openai_client is not None,
#         "image_ready": model_loader and model_loader.is_loaded(),
#     }

#     if model_loader:
#         status.update(model_loader.get_current_model_info())

#     return status
