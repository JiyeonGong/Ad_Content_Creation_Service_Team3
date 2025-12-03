# src/backend/text_overlay.py
"""
텍스트 오버레이 기능 - 3D 캘리그라피 생성
ControlNet Depth SDXL을 활용한 3D 렌더링 (팀원 코드 기반)
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageFont, ImageDraw
from rembg import remove, new_session
import torch
from diffusers import ControlNetModel, StableDiffusionXLControlNetPipeline

# 세션 로드
rembg_session = new_session("u2net")

# ControlNet 캘리그라피 전용 파이프라인 (lazy loading)
_calligraphy_pipeline = None 

def create_base_text_image(text: str, font_path: str, font_size: int = 600) -> Image.Image:
    """
    기본 텍스트 이미지 생성 (팀원 코드)
    """
    # 디버깅 로그
    print(f"🔍 [디버깅] 폰트 로딩 시도: '{font_path}'")
    if not os.path.exists(font_path):
        error_msg = f"❌ 폰트 파일이 없습니다! 경로를 확인하세요: {font_path}"
        print(error_msg)
        raise FileNotFoundError(error_msg)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        print(f"❌ 폰트 로드 실패: {e}")
        raise e
    
    # 텍스트 만들기
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = dummy.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    padding = 200
    cw = ((w + padding) // 64 + 1) * 64
    ch = ((h + padding) // 64 + 1) * 64
    cw, ch = max(1024, cw), max(1024, ch)
    img = Image.new("RGB", (cw, ch), "black")
    draw = ImageDraw.Draw(img)
    tx = (cw - w) // 2 - bbox[0]
    ty = (ch - h) // 2 - bbox[1]
    draw.text((tx, ty), text, font=font, fill="white")
    return img

def get_calligraphy_pipeline():
    """
    캘리그라피 전용 ControlNet 파이프라인 로드 (lazy loading)
    
    Returns:
        StableDiffusionXLControlNetPipeline: ControlNet Depth SDXL 파이프라인
    """
    global _calligraphy_pipeline
    if _calligraphy_pipeline is None:
        print("🔧 캘리그라피 전용 ControlNet Depth SDXL 파이프라인 로딩 중...")
        
        # ControlNet Depth 모델 경로 (Hugging Face 캐시 형식)
        controlnet_path = "diffusers/controlnet-depth-sdxl-1.0-small"
        controlnet_local = "/home/shared/models--diffusers--controlnet-depth-sdxl-1.0-small"
        
        # SDXL Base 모델 경로
        sdxl_base_path = "stabilityai/stable-diffusion-xl-base-1.0"
        sdxl_local = "/home/shared/models--stabilityai--stable-diffusion-xl-base-1.0"
        
        # SDXL VAE 경로
        vae_path = "madebyollin/sdxl-vae-fp16-fix"
        vae_local = "/home/shared/models--madebyollin--sdxl-vae-fp16-fix"
        
        try:
            from diffusers import AutoencoderKL
            
            # VAE 로드 (로컬 캐시 우선)
            vae = AutoencoderKL.from_pretrained(
                vae_path,
                cache_dir="/home/shared",
                local_files_only=True,
                torch_dtype=torch.float16
            )
            
            # ControlNet 로드 (로컬 캐시 우선)
            controlnet = ControlNetModel.from_pretrained(
                controlnet_path,
                cache_dir="/home/shared",
                local_files_only=True,
                torch_dtype=torch.float16
            )
            
            # SDXL + ControlNet 파이프라인 생성 (로컬 캐시 우선)
            # meta 텐서 문제 해결: device_map="auto" 사용
            _calligraphy_pipeline = StableDiffusionXLControlNetPipeline.from_pretrained(
                sdxl_base_path,
                controlnet=controlnet,
                vae=vae,
                cache_dir="/home/shared",
                local_files_only=True,
                torch_dtype=torch.float16,
                device_map="auto"  # meta 텐서 자동 처리
            )
            
            # 메모리 최적화
            # enable_model_cpu_offload()는 device_map="auto"와 함께 사용 불가
            # _calligraphy_pipeline.enable_model_cpu_offload()
            _calligraphy_pipeline.enable_vae_slicing()
            
            print("✅ 캘리그라피 파이프라인 로드 완료")
            
        except Exception as e:
            print(f"❌ 캘리그라피 파이프라인 로드 실패: {e}")
            raise
    
    return _calligraphy_pipeline

def apply_controlnet_3d_rendering(
    base_image: Image.Image,
    color_hex: str,
    style: str = "default"
) -> Image.Image:
    """
    ControlNet Depth SDXL을 사용하여 3D 렌더링 적용 (팀원 코드)
    
    흑백 텍스트 이미지를 깊이 맵으로 사용하고,
    색상과 스타일은 프롬프트를 통해 ControlNet에 전달하여
    다채로운 3D 렌더링 결과를 얻습니다.
    
    Args:
        base_image: 흑백 텍스트 이미지 (형태 제어용)
        color_hex: 원하는 색상 HEX 코드
        style: 렌더링 스타일
    
    Returns:
        PIL.Image: 3D 렌더링이 적용된 컬러 이미지
    """
    try:
        print(f"🎨 ControlNet 3D 렌더링 시작 (색상: {color_hex}, 스타일: {style})")
        
        # 색상 이름 매핑 (HEX -> 영어 색상명)
        color_map = {
            "#FF0000": "red", "#FF5733": "orange red",
            "#FFA500": "orange", "#FFD700": "gold",
            "#FFFF00": "yellow", "#00FF00": "green",
            "#00FFFF": "cyan", "#0000FF": "blue",
            "#FF00FF": "magenta", "#800080": "purple",
            "#FFFFFF": "white", "#000000": "black",
            "#C0C0C0": "silver", "#FFE4E1": "rose"
        }
        
        color_name = color_map.get(color_hex.upper(), "vibrant colored")
        
        # 스타일별 프롬프트 설정
        style_prompts = {
            "default": f"3D {color_name} calligraphy text, natural embossed letters, professional studio lighting, high quality, detailed texture, realistic depth",
            "emboss": f"3D {color_name} embossed calligraphy, raised metallic surface, dramatic shadows, reflective finish, photorealistic, strong depth effect",
            "carved": f"3D {color_name} carved calligraphy, engraved stone letters, chiseled effect, deep grooves, ancient style, strong relief",
            "floating": f"3D {color_name} floating calligraphy, levitating letters, depth of field, soft shadows, cinematic lighting, aerial perspective"
        }
        
        prompt = style_prompts.get(style, style_prompts["default"])
        negative_prompt = "flat, 2d, low quality, blurry, distorted, monochrome, grayscale"
        
        print(f"  프롬프트: {prompt}")
        
        # ControlNet 파이프라인 로드
        pipeline = get_calligraphy_pipeline()
        
        # 3D 렌더링 생성
        result = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=base_image,  # 흑백 이미지를 깊이 맵으로 사용
            num_inference_steps=30,
            controlnet_conditioning_scale=0.8,
            guidance_scale=7.5,
            width=base_image.width,
            height=base_image.height
        ).images[0]
        
        print("✅ ControlNet 3D 렌더링 완료")
        return result
        
    except Exception as e:
        print(f"⚠️ ControlNet 렌더링 실패, 원본 반환: {e}")
        import traceback
        print(traceback.format_exc())
        return base_image

def remove_background(image: Image.Image) -> Image.Image:
    """
    배경 제거 및 후처리 (팀원 코드)
    
    1. Rembg: 1차 배경 제거
    2. Threshold: 애매한 반투명 찌꺼기 강제 제거 
    3. Erode: 테두리 안쪽으로 깎기
    4. Blur: 깎인 단면 부드럽게 처리
    """
    # 1. AI 배경 제거
    no_bg_image = remove(
        image, 
        session=rembg_session,
        alpha_matting=True,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=5  # rembg 자체 erode는 줄임
    )
    
    img_np = np.array(no_bg_image)
    
    if img_np.shape[2] == 4:
        # 알파 채널 분리
        alpha = img_np[:, :, 3]
        
        # 이진화 (Thresholding)
        # 투명도가 127(중간값)보다 낮으면 아예 0으로 만든다.
        _, binary_alpha = cv2.threshold(alpha, 127, 255, cv2.THRESH_BINARY)
        
        # 이진화된 마스크를 안쪽으로 살짝 깎음
        kernel = np.ones((3, 3), np.uint8)
        eroded_alpha = cv2.erode(binary_alpha, kernel, iterations=1)
        
        # 가우시안 블러 (Smoothing)
        # 딱딱하게 깎인 경계면을 아주 살짝 부드럽게 만듦 (안티앨리어싱)
        final_alpha = cv2.GaussianBlur(eroded_alpha, (3, 3), 0)
        
        # 최종 알파 채널 적용
        img_np[:, :, 3] = final_alpha
        
        img_np[final_alpha == 0] = 0
        
    return Image.fromarray(img_np)
