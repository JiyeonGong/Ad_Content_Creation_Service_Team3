# /home/spai0323/Ad_Content_Creation_Service_Team3/src/backend/services.py (리팩토링 버전)
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
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
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
    
    # 이미 영어인 경우 스킵
    if not opt_config.get("translate_korean", True):
        return text
    
    if all(ord(char) < 128 for char in text[:20]):
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
Output ONLY the English prompt, no explanations."""

        resp = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            input=f"Convert to image prompt:\n{text}",
            reasoning={"effort": "minimal"},
            max_output_tokens=200,
        )
        
        result = getattr(resp, "output_text", None) or str(resp)
        optimized = result.strip()
        print(f"🔄 프롬프트 최적화:\n  원본: {text[:80]}...\n  최적화: {optimized[:80]}...")
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
def generate_t2i_core(prompt: str, width: int, height: int, steps: int) -> bytes:
    global model_loader
    
    if not model_loader or not model_loader.is_loaded():
        raise RuntimeError("이미지 파이프라인이 초기화되지 않았습니다.")
    
    model_config = model_loader.current_model_config
    
    # 프롬프트 최적화
    optimized_prompt = optimize_prompt(prompt, model_config)
    
    # Steps 검증
    if steps < 1:
        steps = model_config.default_steps
    steps = min(steps, model_config.max_steps)
    
    # 생성 파라미터 구성
    gen_params = {
        "prompt": optimized_prompt,
        "width": width,
        "height": height,
        "num_inference_steps": steps,
    }
    
    # 조건부 파라미터 추가
    if model_config.use_negative_prompt:
        gen_params["negative_prompt"] = model_config.negative_prompt
    
    if model_config.guidance_scale is not None:
        gen_params["guidance_scale"] = model_config.guidance_scale
    
    print(f"🎨 이미지 생성 중")
    print(f"   모델: {model_loader.current_model_name}")
    print(f"   Steps: {steps}")
    print(f"   크기: {width}x{height}")
    
    # 생성
    result = model_loader.t2i_pipe(**gen_params)
    image = result.images[0]
    
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

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