import asyncio
from services.pipeline_loader import init_image_pipelines

async def load_pipelines():
    """앱 startup 시 모델 1회만 로드"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, init_image_pipelines)
    print("✅ 모델 로드 완료")