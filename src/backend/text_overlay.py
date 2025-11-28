# text_overlay.py
# 모델 로드를 제외하고 캘리그라피 생성의 비지니스 로직만 담겨있음.

import io
import torch
import numpy as np
from PIL import Image, ImageFont, ImageDraw
from rembg import remove

def create_base_text_image(text: str, font_path: str, font_size: int = 600) -> Image.Image:
    """텍스트를 검은 배경 흰 글씨 이미지로 변환"""
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        print("⚠️ 폰트 로드 실패, 기본 폰트 사용")
        font = ImageFont.load_default()
        
    # 텍스트 크기 측정
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = dummy.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    # 캔버스 크기 (64 배수)
    padding = 200
    cw = ((w + padding) // 64 + 1) * 64
    ch = ((h + padding) // 64 + 1) * 64
    cw, ch = max(1024, cw), max(1024, ch)
    
    img = Image.new("RGB", (cw, ch), "black")
    draw = ImageDraw.Draw(img)
    
    # 중앙 정렬
    tx = (cw - w) // 2 - bbox[0]
    ty = (ch - h) // 2 - bbox[1]
    draw.text((tx, ty), text, font=font, fill="white")
    
    return img

def remove_background(image: Image.Image) -> Image.Image:
    """Rembg를 이용한 누끼 따기"""
    return remove(image)