# backend/routers/i2i.py
from fastapi import APIRouter
from pydantic import BaseModel
from services.image_service import generate_i2i_image

router = APIRouter()

class I2IRequest(BaseModel):
    input_image_base64: str
    prompt: str
    strength: float
    width: int
    height: int
    steps: int

@router.post("/generate_i2i")
def i2i_endpoint(payload: I2IRequest):
    """
    Image-to-Image 생성
    """
    image_base64 = generate_i2i_image(payload.dict())
    return {"image_base64": image_base64}