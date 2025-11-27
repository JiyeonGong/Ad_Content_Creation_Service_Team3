# services.py (FLUX 3단계 프롬프팅 통합 버전)
"""
AI 서비스 레이어 - 설정 기반 모델 관리
------------------------------------
기능:
1. GPT를 이용한 한국어 프롬프트 최적화 (3단계 파이프라인) 및 인스타그램 문구 생성
2. ModelLoader 기반의 T2I (Text-to-Image) 및 I2I (Image-to-Image) 이미지 생성/편집
3. FLUX 모델을 위한 3단계 프롬프트 파이프라인 적용
4. ADetailer 후처리 모듈화 및 통합 적용
"""
import os
import io
import random
import traceback
from typing import Optional, Any

from openai import OpenAI # OpenAI 클라이언트
import torch              # 텐서 및 Generator (시드 관리)
from PIL import Image     # 이미지 처리
from dotenv import load_dotenv # 환경 변수 로드

# 외부 모듈을 사용한다고 가정
from .model_registry import get_registry 
from .model_loader import ModelLoader    

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# 토크나이저 병렬 처리 경고 억제
os.environ["TOKENIZERS_PARALLELISM"] = "false"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_GPT_MINI = "gpt-5-mini" # 프롬프트 최적화/문구 생성에 사용되는 GPT 모델

# ===========================
# 💡 HF 캐시 위치 설정
# ===========================
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.exists("/home/shared"):
    # GCP 환경 (공유 캐시 사용)
    hf_cache_dir = "/home/shared"
else:
    # 로컬 환경 (프로젝트 루트의 캐시 사용)
    hf_cache_dir = os.path.join(project_root, "cache", "hf_models")
    os.makedirs(hf_cache_dir, exist_ok=True)

# ===========================
# 💡 전역 인스턴스 초기화
# ===========================
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
# 🛠️ Utility helpers (유틸리티 함수)
# ===========================
def align_to_64(x: Any) -> int:
    """
    입력된 값을 64의 배수로 정렬하고, 최소값을 64로 보장합니다.
    (이미지 생성 모델의 크기 제약 준수용)
    """
    try:
        xi = int(x)
    except (ValueError, TypeError):
        print(f"⚠️ align_to_64: 입력 값({x})이 유효하지 않아 64 사용")
        xi = 64
    return max(64, (xi // 64) * 64)

def ensure_steps(steps: Any) -> int:
    """
    추론 단계(Steps)가 유효한 양의 정수인지 확인합니다.
    """
    try:
        s = int(steps)
    except (ValueError, TypeError):
        print(f"⚠️ ensure_steps: 입력 값({steps})이 유효하지 않아 1 사용")
        s = 1
    return max(1, s)

# ===========================
# 🚀 모델 초기화
# ===========================
def init_image_pipelines():
    """
    설정 파일 기반으로 이미지 생성 모델 로드 (폴백 포함)
    """
    global model_loader
    
    if model_loader and model_loader.is_loaded():
        print("ℹ️ 이미지 파이프라인 이미 로드됨 — 스킵")
        return
    
    if model_loader is None:
        model_loader = ModelLoader(cache_dir=hf_cache_dir)
    
    # 설정 파일 기반 폴백 체인으로 로딩 시도
    success = model_loader.load_with_fallback()
    
    if success:
        info = model_loader.get_current_model_info()
        print(f"✅ 이미지 생성 준비 완료")
        print(f"   모델: {info.get('name')} ({info.get('type')})")
        print(f"   장치: {info.get('device')}")
    else:
        print("❌ 모든 모델 로딩 실패 - 이미지 생성 불가")


# =======================================================
# 1단계: 한국어 시각 확장 (한국어 → 더 상세한 한국어)
# =======================================================
def expand_prompt_with_gpt(text: str) -> str:
    """한국어 묘사를 자연스럽게 확장"""
    if not openai_client:
        return text

    # 프롬프트 최적화 비활성화 시 원본 반환
    opt_config = registry.get_prompt_optimization_config()
    if not opt_config.get("enabled", True) or not opt_config.get("translate_korean", True):
        return text

    system = """
당신은 이미지 생성용 시각 묘사를 구체적으로 확장하는 전문가입니다.
규칙: 장면의 배경, 조명, 동작, 분위기, 구도 등을 자연스럽고 구체적으로 확장합니다. 2~3 문장으로 작성하며, 출력은 반드시 한국어로 유지합니다.
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
        print(f"🔄 1/3 확장 (한국어):\n  원본: {text}\n  확장: {expanded.strip()[:50]}...")
        return expanded.strip()
    except Exception as e:
        print(f"⚠️ 1단계 한국어 확장 실패 → 원본 사용: {e}")
        return text


# =======================================================
# 2단계: FLUX 템플릿 기반 영어 변환 (한국어 → 영어 FLUX 구조)
# =======================================================
def apply_flux_template(expanded_kor_text: str) -> str:
    """한국어 확장 설명을 FLUX 템플릿 영어로 변환"""
    if not openai_client:
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
        print(f"🔄 2/3 템플릿 (영어):\n  입력: {expanded_kor_text[:50]}...\n  결과: {templated.strip()[:50]}...")
        return templated.strip()
    except Exception as e:
        print(f"⚠️ 2단계 FLUX 템플릿 변환 실패 → 원본 사용: {e}")
        return expanded_kor_text


# =======================================================
# 3단계: 최종 최적화 (영어 → 영어 더 짧고 안전하게 / SDXL: 키워드 강화)
# =======================================================
def optimize_prompt(text: str, model_config) -> str:
    """FLUX/SDXL 최종 프롬프트 최적화 및 다듬기"""
    if not openai_client:
        return text

    # 모델 타입 확인 및 제약 조건 설정
    model_type = (model_config.type if model_config else "").lower()
    is_flux = "flux" in model_type
    
    try:
        if is_flux:
            # FLUX는 템플릿 기반으로 작성되었으므로 간단히 다듬기
            system_prompt = f"""
You are an expert FLUX prompt polisher. Polish the prompt below.
IMPORTANT: Keep under 60 tokens, 2–3 short descriptive sentences, no keyword lists. Do NOT add negative prompts.
"""
        else:
            # SDXL 등 기타 모델은 기존 services.py의 상세 키워드 주입 로직 사용
            max_tokens = model_config.max_tokens if model_config else 77
            constraint = f"Keep it under 60 words (model has {max_tokens} token limit)." if max_tokens <= 77 else "Keep it concise but descriptive (under 150 words)."
            
            system_prompt = f"""
You are a professional prompt engineer for image generation AI.
Refine the prompt below for better clarity, realism, and aesthetic quality.
{constraint}
Always include relevant quality keywords based on the scene content to prevent artifacts (e.g., "detailed hands, correct anatomy, clear facial features").
"""
        
        full_prompt = f"{system_prompt}\n\n[Input Prompt]\n{text}\n\nOutput ONLY the polished final English prompt."
        
        resp = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            reasoning={"effort": "minimal"}, 
            input=full_prompt,
            max_output_tokens=200,
        )
        optimized = getattr(resp, "output_text", None) or str(resp)
        print(f"🔄 3/3 최종 최적화:\n  입력: {text[:50]}...\n  최종: {optimized.strip()[:50]}...")
        return optimized.strip()

    except Exception as e:
        print(f"⚠️ 3단계 최종 최적화 실패 → 원본 사용: {e}")
        return text


# ===========================
# 💬 GPT-5 Mini: 문구 생성
# ===========================
def generate_caption_core(info: dict, tone: str) -> str:
    """
    헬스케어 인스타그램 홍보 문구 및 해시태그 생성
    """
    if not openai_client:
        raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다.")

    prompt = f"""
당신은 헬스케어 소상공인을 위한 전문 인스타그램 콘텐츠 크리에이터입니다.
아래 정보를 바탕으로 인스타그램 게시물에 최적화된 콘텐츠를 생성해 주세요.

[요청]
1. 인스타그램 홍보 문구 3개 작성 (각 문구는 후킹 → 핵심 메시지 → CTA 구조)
2. 이모티콘 사용
3. 문체 스타일: {tone}
4. 해시태그 15개 추천 (중복 제거)

[정보]
서비스 종류: {info.get('service_type')}
서비스명: {info.get('service_name')}
핵심 특징: {info.get('features')}
지역: {info.get('location')}

[출력 형식]
문구:
1. [여기에 첫 번째 문구]
2. [여기에 두 번째 문구]
3. [여기에 세 번째 문구]

해시태그:
#[태그1] #[태그2] ... #[태그15]
"""
    try:
        resp = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            reasoning={"effort": "minimal"},
            input=prompt,
            max_output_tokens=512,
        )
        text = getattr(resp, "output_text", None) or str(resp)
        return text.strip()
    except Exception as e:
        print(f"🚨 GPT 호출 실패: {e}")
        raise RuntimeError(f"문구 생성 GPT 호출 실패: {e}")

# ===========================
# 🖼️ ADetailer 후처리 (모듈화)
# ===========================
def apply_adetailer(
    image: Image.Image,
    prompt: str,
    targets: list = None,
    strength: float = 0.4
) -> Image.Image:
    """
    ADetailer 스타일 후처리: 손/얼굴 감지 후 해당 영역만 Inpaint로 재생성
    """
    global model_loader

    if targets is None:
        targets = ["hand"]

    try:
        # services2.py와 동일하게 외부 모듈에 post_processor가 있다고 가정
        from .post_processor import get_post_processor 

        print(f"🔧 ADetailer 후처리 시작 (targets: {targets}, strength: {strength})")

        post_processor = get_post_processor()
        inpaint_pipe = model_loader.i2i_pipe # I2I 파이프라인을 Inpaint용으로 사용

        processed_image, info = post_processor.full_pipeline(
            image=image,
            inpaint_pipeline=inpaint_pipe,
            prompt=prompt,
            auto_detect=True,
            adetailer_targets=targets,
            adetailer_strength=strength
        )

        if info.get("processed"):
            print(f"✅ ADetailer 처리 완료: {info.get('detected_count')}개 영역 보정")
        else:
            print(f"ℹ️ ADetailer: 보정 대상 없음, 원본 유지")

        return processed_image

    except Exception as e:
        print(f"⚠️ ADetailer 실패, 원본 반환: {e}")
        return image

# ===========================
# 🎨 이미지 생성 (T2I)
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
    """텍스트 기반 이미지 생성"""
    global model_loader

    if not model_loader or not model_loader.is_loaded():
        raise RuntimeError("이미지 파이프라인이 초기화되지 않았습니다.")

    model_config = model_loader.current_model_config
    model_type = (model_config.type if model_config else "").lower()

    # 1. 프롬프트 최적화 (FLUX 3단계 파이프라인 적용)
    if "flux" in model_type:
        expanded = expand_prompt_with_gpt(prompt)
        templated = apply_flux_template(expanded)
        final_prompt = optimize_prompt(templated, model_config)
    else:
        # SDXL 등 기타 모델은 3단계 중 최종 최적화만 적용
        final_prompt = optimize_prompt(prompt, model_config)

    # 2. 파라미터 검증 및 설정
    width = align_to_64(width)
    height = align_to_64(height)
    steps = ensure_steps(min(steps, model_config.max_steps))
    
    random_seed = random.randint(0, 2**32 - 1)
    generator = torch.Generator(device=model_loader.device).manual_seed(random_seed)

    gen_params = {
        "prompt": final_prompt,
        "width": width,
        "height": height,
        "num_inference_steps": steps,
        "generator": generator,
    }

    # Negative Prompt 설정
    if "flux" in model_type:
        # services2.py의 명시적 FLUX Negative Prompt 반영
        gen_params["negative_prompt"] = "no distortions, no extra limbs, missing fingers, watermark, low quality"
    elif model_config.use_negative_prompt:
        gen_params["negative_prompt"] = model_config.negative_prompt

    # Guidance Scale 설정 (사용자 지정값 우선)
    if guidance_scale is not None:
        gen_params["guidance_scale"] = guidance_scale
    elif model_config.guidance_scale is not None:
        gen_params["guidance_scale"] = model_config.guidance_scale

    print(f"🎨 T2I 생성 중 (Model: {model_loader.current_model_name}, Prompt: {final_prompt[:50]}...)")

    # 3. 생성 및 후처리
    try:
        result = model_loader.t2i_pipe(**gen_params)
        image = result.images[0]

        if enable_adetailer:
            image = apply_adetailer(
                image=image,
                prompt=final_prompt,
                targets=adetailer_targets or ["hand"]
            )

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        image_bytes = buf.getvalue()
        print(f"✅ 생성 완료: {width}x{height} PNG, {len(image_bytes)} bytes")
        return image_bytes
    except Exception as gen_err:
        print(f"❌ T2I 이미지 생성 또는 변환 실패: {gen_err}")
        traceback.print_exc()
        raise RuntimeError(f"이미지 생성 실패: {gen_err}")


# ===========================
# ✏️ 이미지 편집 (I2I)
# ===========================
def generate_i2i_core(
    input_image_bytes: bytes,
    prompt: str,
    strength: float,
    width: int,
    height: int,
    steps: int,
    guidance_scale: float = None,
    enable_adetailer: bool = True,
    adetailer_targets: list = None
) -> bytes:
    """이미지 기반 편집 (I2I)"""
    global model_loader

    if not model_loader or not model_loader.is_loaded():
        raise RuntimeError("이미지 파이프라인이 초기화되지 않았습니다.")

    model_config = model_loader.current_model_config
    model_type = (model_config.type if model_config else "").lower()

    if not model_config.supports_i2i:
        raise RuntimeError(f"현재 모델({model_loader.current_model_name})은 I2I를 지원하지 않습니다.")

    # 1. 프롬프트 최적화 (T2I와 동일한 3단계 파이프라인 적용)
    if "flux" in model_type:
        expanded = expand_prompt_with_gpt(prompt)
        templated = apply_flux_template(expanded)
        final_prompt = optimize_prompt(templated, model_config)
    else:
        final_prompt = optimize_prompt(prompt, model_config)

    # 2. 파라미터 및 입력 이미지 준비
    width = align_to_64(width)
    height = align_to_64(height)
    steps = ensure_steps(min(steps, model_config.max_steps))
    
    input_image = Image.open(io.BytesIO(input_image_bytes)).convert("RGB").resize((width, height))

    gen_params = {
        "prompt": final_prompt,
        "image": input_image,
        "strength": float(strength),
        "num_inference_steps": steps,
    }

    # Negative Prompt 설정
    if "flux" in model_type:
        # services2.py의 명시적 FLUX Negative Prompt 반영
        gen_params["negative_prompt"] = "no distortions, no extra limbs, low quality" 
    elif model_config.use_negative_prompt:
        gen_params["negative_prompt"] = model_config.negative_prompt

    # Guidance Scale 설정
    if guidance_scale is not None:
        gen_params["guidance_scale"] = guidance_scale
    elif model_config.guidance_scale is not None:
        gen_params["guidance_scale"] = model_config.guidance_scale

    print(f"✏️ I2I 편집 중 (Model: {model_loader.current_model_name}, Strength: {strength})")
    
    # 3. 생성 및 후처리
    try:
        result = model_loader.i2i_pipe(**gen_params)
        image = result.images[0]

        if enable_adetailer:
            # services2.py의 모듈화된 apply_adetailer 함수 호출
            image = apply_adetailer(
                image=image,
                prompt=final_prompt,
                targets=adetailer_targets or ["hand", "face"],
                strength=0.4 # I2I 디테일링은 통상적으로 0.4 사용
            )

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        image_bytes = buf.getvalue()
        return image_bytes
    except Exception as gen_err:
        print(f"❌ I2I 이미지 편집 또는 변환 실패: {gen_err}")
        traceback.print_exc()
        raise RuntimeError(f"이미지 편집 실패: {gen_err}")


# ===========================
# 🔄 모델 전환 및 상태 조회
# ===========================
def switch_model(model_name: str) -> dict:
    """
    다른 이미지 생성 모델로 전환
    Returns: {"success": bool, "message": str, "model_info": dict}
    """
    global model_loader

    if not model_loader:
        model_loader = ModelLoader(cache_dir=hf_cache_dir)

    model_config = registry.get_model(model_name)
    if not model_config:
        return {
            "success": False,
            "message": f"알 수 없는 모델: {model_name}",
            "model_info": None
        }

    # 이미 로드된 경우 스킵
    if model_loader.is_loaded() and model_loader.current_model_name == model_name:
        return {
            "success": True,
            "message": f"모델 '{model_name}' 이미 로드됨",
            "model_info": model_loader.get_current_model_info()
        }

    print(f"🔄 모델 전환 중: {model_name}")
    try:
        success = model_loader.load_model(model_name)
    except Exception as e:
        success = False
        error_message = f"모델 로드 중 예외 발생: {e}"
        print(f"❌ {error_message}")
        
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