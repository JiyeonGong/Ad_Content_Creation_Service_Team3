# backend/routers/t2i.py
from fastapi import APIRouter
from pydantic import BaseModel
from services.image_service import generate_t2i_image

router = APIRouter()

class T2IRequest(BaseModel):
    prompt: str
    width: int
    height: int
    steps: int

@router.post("/generate_t2i")
def t2i_endpoint(payload: T2IRequest):
    """
    Text-to-Image 생성
    """
    image_base64 = generate_t2i_image(payload.dict())
    return {"image_base64": image_base64}