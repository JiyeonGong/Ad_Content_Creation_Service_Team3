from pydantic import BaseModel

class CaptionRequest(BaseModel):
    service_type: str
    service_name: str
    features: str
    location: str
    tone: str

class CaptionResponse(BaseModel):
    output_text: str

class T2IRequest(BaseModel):
    prompt: str
    width: int = 1024
    height: int = 1024
    steps: int = 4

class T2IResponse(BaseModel):
    image_base64: str

class I2IRequest(BaseModel):
    input_image_base64: str
    prompt: str
    strength: float = 0.75
    width: int = 1024
    height: int = 1024
    steps: int = 4