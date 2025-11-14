# FastAPI APP 실행

from fastapi import FastAPI, UploadFile, File, Form
# 같은 패키지 내의 모듈 임포트
from .services import process_ad_creation
from .schemas import GenerationResponse

app = FastAPI(title="Trainer Ad Creator API")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Backend is running"}

@app.post("/generate", response_model=GenerationResponse)
async def generate_ad(
    target: str = Form(...),
    purpose: str = Form(...),
    file: UploadFile = File(...)
):
    image_bytes = await file.read()
    result = await process_ad_creation(image_bytes, target, purpose)
    return result