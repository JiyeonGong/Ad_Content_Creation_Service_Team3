# backend/routers/caption.py
from fastapi import APIRouter
from pydantic import BaseModel
from services.openai_service import generate_caption

router = APIRouter()

class CaptionRequest(BaseModel):
    service_type: str
    service_name: str
    features: str
    location: str
    tone: str

@router.post("/caption")
def caption_endpoint(payload: CaptionRequest):
    """
    GPT 문구 + 해시태그 생성
    """
    output_text = generate_caption(payload.dict())
    return {"output_text": output_text}