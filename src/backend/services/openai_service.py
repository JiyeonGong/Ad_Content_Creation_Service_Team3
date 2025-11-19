import os
from core.config import OPENAI_API_KEY, MODEL_GPT_MINI
from openai import OpenAI

openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"⚠️ OpenAI 초기화 실패: {e}")

PROMPT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "templates", "caption_prompt.txt")
with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
    CAPTION_PROMPT_TEMPLATE = f.read()

from core.utils import get_model_params
from services.pipeline_loader import CURRENT_MODEL

def optimize_prompt(text: str) -> str:
    if not openai_client:
        return text
    if all(ord(c)<128 for c in text[:20]):
        return text
    try:
        constraint = "Keep it under 60 words." if CURRENT_MODEL and "stable-diffusion" in CURRENT_MODEL.lower() else "Keep it concise under 150 words."
        system_prompt = f"You are a professional prompt engineer. {constraint}"
        resp = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            input=f"Convert to image prompt:\n{text}",
            reasoning={"effort":"minimal"},
            max_output_tokens=200,
        )
        return getattr(resp, "output_text", None) or str(resp)
    except Exception as e:
        print(f"⚠️ 프롬프트 최적화 실패: {e}")
        return text

def generate_caption_core(info: dict, tone: str) -> str:
    if not openai_client:
        raise RuntimeError("OpenAI 초기화 실패")
    prompt = CAPTION_PROMPT_TEMPLATE.format(
        service_type=info.get("service_type"),
        service_name=info.get("service_name"),
        features=info.get("features"),
        location=info.get("location"),
        tone=tone
    )
    try:
        resp = openai_client.responses.create(
            model=MODEL_GPT_MINI,
            input=prompt,
            reasoning={"effort":"minimal"},
            max_output_tokens=512,
        )
        return getattr(resp, "output_text", None) or str(resp)
    except Exception as e:
        raise RuntimeError(f"GPT 호출 실패: {e}")