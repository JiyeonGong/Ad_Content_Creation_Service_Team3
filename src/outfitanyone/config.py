# C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\outfitanyone\config.py
from pathlib import Path
import os

# 프로젝트 루트
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # src/outfitanyone → 프로젝트 루트

# 임시 이미지 저장 폴더
TMP_DIR = BASE_DIR / "experiments" / "tmp_image"
TMP_DIR.mkdir(parents=True, exist_ok=True)

# 결과 이미지 저장 폴더
RESULT_DIR = BASE_DIR / "experiments" / "outputanyone_results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)

# Hugging Face API 환경 변수
HF_MODEL = os.getenv("HF_MODEL", "HumanAIGC/OutfitAnyone")
HF_API_NAME = os.getenv("HF_API_NAME", "/get_tryon_result")

# 지원하는 이미지 파일 형식 상수
SUPPORTED_TYPES = ["png"]
