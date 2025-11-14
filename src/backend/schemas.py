# Pydantic Models

from pydantic import BaseModel
from typing import List

class AnalysisRequest(BaseModel):
    target: str
    purpose: str

class AnalysisResult(BaseModel):
    pose_analysis: str
    expert_comment: str

class ContentOption(BaseModel):
    option_name: str
    image_url: str
    copy_text: str

class GenerationResponse(BaseModel):
    analysis: AnalysisResult
    contents: List[ContentOption]
    hashtags: List[str]
    upload_guide: str