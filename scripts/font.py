import os
import cv2
import numpy as np
import torch
from PIL import Image, ImageFont, ImageDraw
from diffusers import StableDiffusionXLControlNetPipeline, ControlNetModel, AutoencoderKL
from datetime import datetime
import psutil

# ==========================================
# 1. 설정 (Configuration)
# ==========================================
INPUT_TEXT = "헬스케어 프로젝트"
# 스타일 프롬프트 (수정하며 실험하세요)
PROMPT = "made of flowing blue water, liquid texture, splashing water droplets, high quality, realistic, 8k, 3d render"
NEGATIVE_PROMPT = "text, watermark, low quality, blurry, ugly, messy, distorted letters, jpeg artifacts"

# [핵심] 완벽한 노란색을 위한 프롬프트
# - vivid canary yellow: 쨍한 노란색
# - solid black background: 노란색을 돋보이게 하는 검은 배경
# - minimal, matte finish: 질감을 없애고 색상에 집중
# PROMPT = "minimalist 3d typography, vivid canary yellow color, hex code #FFD700, smooth matte plastic material, clean surface, isolated on solid black background, studio lighting, high contrast, 8k"

# 질감을 날리기를 원할 때 
# NEGATIVE_PROMPT = "dirty, messy, texture, pattern, grunge, water, liquid, metallic, reflection, blue, red, green, white, rainbow, gradient, low quality"
FONT_PATH = "/home/shared/RiaSans-Bold.ttf" 
OUTPUT_DIR = "./outputs"

# ==========================================
# 2. 유틸리티 함수 (전처리)
# ==========================================
#def download_font():
    #if not os.path.exists(FONT_PATH):
        #print(f"⬇️ 폰트 다운로드 중: {FONT_URL}")
        #os.system(f"wget -O {FONT_PATH} {FONT_URL} -q")

def create_base_image(text, font_size=600): # size 인자 제거됨
    dummy_image = Image.new("RGB", (1, 1), "black")
    draw = ImageDraw.Draw(dummy_image)
    
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        print("⚠️ 폰트 로드 실패. 기본 폰트 사용.")
        font = ImageFont.load_default()
    
    # 1. 텍스트의 실제 크기 측정 (Bounding Box)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_width = right - left
    text_height = bottom - top
    
    # 2. 여백(Padding) 추가 (글자가 꽉 차면 답답하고 AI가 배경 효과를 못 그림)
    padding_x = 200  # 좌우 여백
    padding_y = 200  # 상하 여백
    
    raw_width = text_width + padding_x
    raw_height = text_height + padding_y
    
    # 3. SDXL 친화적 해상도 보정 (64의 배수로 맞춤 - 중요!)
    # 예: 1000px -> 1024px, 500px -> 512px
    width = ((raw_width // 64) + 1) * 64
    height = ((raw_height // 64) + 1) * 64
    
    # 너무 작으면 최소 1024로 맞춤 (SDXL 화질 보장용)
    width = max(1024, width)
    height = max(1024, height)

    print(f"📏 캔버스 크기 자동 조정: {width} x {height}")

    # 4. 최종 캔버스 생성 및 중앙 정렬
    image = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(image)
    
    # 텍스트를 캔버스 정중앙에 배치
    text_x = (width - text_width) / 2 - left
    text_y = (height - text_height) / 2 - top
    
    draw.text((text_x, text_y), text, font=font, fill="white")
    return image

def prepare_canny(image):
    image_np = np.array(image)
    # 고딕체용 설정: 굵은 폰트는 엣지를 더 단호하게 따도 됩니다.
    # (기존 100, 200 -> 50, 150 또는 100, 250 등 실험 가능)
    # 일단 기본값으로도 잘 될 테니 유지하되, 만약 지저분하면 수치를 높이세요(100, 200).
    detected_map = cv2.Canny(image_np, 100, 200) 
    detected_map = detected_map[:, :, None]
    detected_map = np.concatenate([detected_map, detected_map, detected_map], axis=2)
    return Image.fromarray(detected_map)

# 모니터링
def print_system_usage(step_name=""):
    # 시스템 RAM 사용량
    ram = psutil.virtual_memory()
    ram_used = ram.used / (1024 ** 3) # GB 단위 변환
    ram_total = ram.total / (1024 ** 3)
    
    # GPU VRAM 사용량 (PyTorch 기준)
    if torch.cuda.is_available():
        vram_reserved = torch.cuda.memory_reserved() / (1024 ** 3)
        vram_allocated = torch.cuda.memory_allocated() / (1024 ** 3)
    else:
        vram_reserved = 0
        vram_allocated = 0
        
    print(f"\n📊 [{step_name}] Resource Usage:")
    print(f"   🖥️  System RAM: {ram_used:.2f} GB / {ram_total:.2f} GB ({ram.percent}%)")
    print(f"   🚀 GPU VRAM: {vram_reserved:.2f} GB (Reserved) / {vram_allocated:.2f} GB (Allocated)")
    print("-" * 40)

# ==========================================
# 3. 메인 로직
# ==========================================
def main():
    # 폴더 생성
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 폰트 준비
    #download_font()
    
    print("🚀 모델 로딩 시작...")
    
    # VAE 로드 (fp16)
    vae = AutoencoderKL.from_pretrained(
        "madebyollin/sdxl-vae-fp16-fix", 
        torch_dtype=torch.float16
    )
    
    # ControlNet 로드
    controlnet = ControlNetModel.from_pretrained(
        "diffusers/controlnet-canny-sdxl-1.0",
        torch_dtype=torch.float16,
        use_safetensors=True
    )
    
    # 파이프라인 로드
    pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        controlnet=controlnet,
        vae=vae,
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
        use_safetensors=True,
        variant="fp16"
    )
    
    # GCP L4 최적화: 모델을 통째로 GPU로 이동
    pipe.to("cuda") 
    
    # 만약 시스템 RAM 부족으로 여기서 죽으면, 위 pipe.to("cuda")를 지우고
    # 아래 주석을 해제하여 CPU Offload를 사용하세요.
    # pipe.enable_model_cpu_offload() 
    
    print("✅ 모델 준비 완료. 이미지 생성 시작.")

    # 텍스트 이미지 생성
    base_image = create_base_image(INPUT_TEXT)
    canny_image = prepare_canny(base_image)
    
    # 디버깅용 저장 (Canny가 잘 따졌는지 확인용)
    canny_image.save(f"{OUTPUT_DIR}/debug_canny.png")

    # 생성 실행
    generator = torch.Generator(device="cuda").manual_seed(42) # 시드 고정
    
    image = pipe(
        prompt=PROMPT,
        negative_prompt=NEGATIVE_PROMPT,
        image=canny_image,
        controlnet_conditioning_scale=1.0, # 스타일 강도 조절 (0.5 ~ 1.0)
        num_inference_steps=30,
        guidance_scale=7.5,
        generator=generator,
    ).images[0]
    
    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{OUTPUT_DIR}/result_{timestamp}.png"
    image.save(filename)
    print_system_usage("시작 전")
    
    # 모델 로드 직후
    # pipe = ... (모델 로드)
    # pipe.to("cuda")
    print_system_usage("모델 로드 후")
    
    # 이미지 생성 직후
    # image = pipe(...)
    print_system_usage("이미지 생성 후")
    
    print(f"\n🎉 생성 완료! 결과 파일: {filename}")
    print(f"👉 로컬로 다운로드하려면 scp 명령어를 사용하거나 VSCode Remote 등을 확인하세요.")

if __name__ == "__main__":
    main()