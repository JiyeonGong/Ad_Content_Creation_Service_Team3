import os
from dotenv import load_dotenv
load_dotenv()

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_GPT_MINI = os.getenv("MODEL_GPT_MINI", "gpt-5-mini")

# 이미지 모델
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "black-forest-labs/FLUX.1-schnell")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
USE_FALLBACK = os.getenv("USE_FALLBACK", "true").lower() == "true"
HF_API_TOKEN = os.getenv("HF_API_TOKEN", None)