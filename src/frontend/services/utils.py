# frontend/services/utils.py
import re
from io import BytesIO

# ===============================
# 입력 유효성 검사
# ===============================
def validate_inputs(service_name: str, features: str, location: str) -> bool:
    if not service_name.strip() or not features.strip() or not location.strip():
        return False
    return True

# ===============================
# GPT 출력 파싱
# ===============================
def parse_output(output: str):
    captions, hashtags = [], ""
    try:
        m = re.search(r"문구:(.*?)해시태그:(.*)", output, re.S)
        if m:
            caption_text = m.group(1).strip()
            hashtags = m.group(2).strip()
            captions = [line.split(".",1)[1].strip() if "." in line else line.strip()
                        for line in caption_text.split("\n") if line.strip()]
        else:
            captions = [output]
    except Exception:
        captions = [output]
    return captions, hashtags

# ===============================
# 문구 → 이미지 프롬프트
# ===============================
def caption_to_image_prompt(caption: str, style: str = "Instagram banner") -> str:
    return f"{caption}, {style}, vibrant, professional, motivational"

# ===============================
# 64배수 정렬
# ===============================
def align64(val: int) -> int:
    try:
        v = int(val)
    except Exception:
        v = 64
    return max(64, (v // 64) * 64)