# frontend/services/api_client.py
import requests
import base64
from io import BytesIO
from typing import Optional
from .utils import align64

API_BASE_URL = "http://localhost:8000"

def _post_json(url: str, payload: dict, timeout: int = 300) -> requests.Response:
    """POST 요청 (예외는 그대로 던짐)"""
    return requests.post(url, json=payload, timeout=timeout)

def base64_to_bytesio(base64_str: str) -> BytesIO:
    """Base64 → BytesIO"""
    image_bytes = base64.b64decode(base64_str)
    return BytesIO(image_bytes)

# ===============================
# Caption API
# ===============================
def call_caption_api(payload: dict) -> str:
    url = f"{API_BASE_URL}/api/caption"
    try:
        response = _post_json(url, payload, timeout=120)
        response.raise_for_status()
        return response.json()["output_text"]
    except requests.exceptions.RequestException as e:
        return f"문구:\n1. [API 연결 오류]\n해시태그:\n#[API오류]"

# ===============================
# Text-to-Image API (T2I)
# ===============================
def call_t2i_api(payload: dict, fallback_attempts: int = 2) -> Optional[BytesIO]:
    url = f"{API_BASE_URL}/api/generate_t2i"
    current_payload = payload.copy()
    for attempt in range(fallback_attempts + 1):
        try:
            response = _post_json(url, current_payload)
            response.raise_for_status()
            base64_str = response.json()["image_base64"]
            return base64_to_bytesio(base64_str)
        except requests.exceptions.RequestException:
            # GPU OOM 등 실패 시 해상도 절반으로 재시도
            if attempt < fallback_attempts:
                w, h = current_payload.get("width", 1024), current_payload.get("height", 1024)
                current_payload["width"], current_payload["height"] = align64(max(64, w//2)), align64(max(64, h//2))
                continue
            return None

# ===============================
# Image-to-Image API (I2I)
# ===============================
def call_i2i_api(payload: dict, fallback_attempts: int = 2) -> Optional[BytesIO]:
    url = f"{API_BASE_URL}/api/generate_i2i"
    current_payload = payload.copy()
    for attempt in range(fallback_attempts + 1):
        try:
            response = _post_json(url, current_payload)
            response.raise_for_status()
            base64_str = response.json()["image_base64"]
            return base64_to_bytesio(base64_str)
        except requests.exceptions.RequestException:
            if attempt < fallback_attempts:
                w, h = current_payload.get("width", 1024), current_payload.get("height", 1024)
                current_payload["width"], current_payload["height"] = align64(max(64, w//2)), align64(max(64, h//2))
                continue
            return None