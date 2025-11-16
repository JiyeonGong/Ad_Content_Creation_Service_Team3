# src/backend/ai_engine.py

import torch
import cv2
import numpy as np
import io
from PIL import Image
from diffusers import StableDiffusionControlNetInpaintPipeline, ControlNetModel, UniPCMultistepScheduler
from rembg import remove

class AIEngine:
    def __init__(self):
        self.pipe = None
        self.device = self._get_device()

    def _get_device(self):
        """Mac(MPS) 또는 CUDA 가속 지원 확인"""
        if torch.backends.mps.is_available():
            print("🚀 Mac MPS(Metal) 가속 활성화! (GPU 사용)")
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
        else:
            print("⚠️ GPU를 찾을 수 없습니다. CPU로 실행됩니다 (느릴 수 있음).")
            return "cpu"

    def load_models(self):
        """서버 시작 시 모델을 메모리에 올립니다."""
        if self.pipe is not None:
            return

        print("⏳ AI 모델 로딩 중... (최초 실행 시 수 GB 다운로드로 시간이 걸립니다)")
        try:
            # 1. ControlNet (Canny) 로드
            controlnet = ControlNetModel.from_pretrained(
                "lllyasviel/control_v11p_sd15_canny",
                torch_dtype=torch.float32  # Mac MPS는 float32가 안정적입니다
            )

            # 2. Inpainting 파이프라인 로드
            self.pipe = StableDiffusionControlNetInpaintPipeline.from_pretrained(
                "runwayml/stable-diffusion-inpainting",
                controlnet=controlnet,
                torch_dtype=torch.float32,
                safety_checker=None # 빠른 실행을 위해 안전 필터 생략
            ).to(self.device)

            # 3. 스케줄러 최적화 (속도 향상)
            self.pipe.scheduler = UniPCMultistepScheduler.from_config(self.pipe.scheduler.config)
            
            # Mac 메모리 최적화 (Attention Slicing)
            self.pipe.enable_attention_slicing()
            
            print("✅ AI 모델 로딩 완료! 언제든 요청을 처리할 준비가 되었습니다.")
            
        except Exception as e:
            print(f"❌ 모델 로딩 실패: {e}")
            raise e

    def process_image(self, image_bytes: bytes, prompt: str):
        """이미지를 받아 배경 제거 및 생성 수행"""
        
        # 1. 이미지 로드 및 전처리 (512px 리사이즈 - SD 1.5 최적화)
        original_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = original_img.size
        scale = 512 / max(w, h)
        new_w = (int(w * scale) // 8) * 8
        new_h = (int(h * scale) // 8) * 8
        original_img = original_img.resize((new_w, new_h))

        # 2. Canny Edge 추출 (윤곽선 따기)
        image_np = np.array(original_img)
        image_np = cv2.Canny(image_np, 100, 200)
        image_np = image_np[:, :, None]
        image_np = np.concatenate([image_np, image_np, image_np], axis=2)
        canny_image = Image.fromarray(image_np)

        # 3. 배경 제거 (Mask 생성)
        # rembg로 배경 제거 후, 알파 채널을 추출하여 마스크로 사용
        no_bg_img = remove(original_img)
        mask = no_bg_img.split()[-1] # 알파 채널(투명도) 추출
        
        # 마스크 처리 (흰색=객체, 검은색=배경 -> Inpainting을 위해 반전 필요)
        # 우리가 지우고 다시 그릴 곳은 '배경'이므로 배경이 흰색이 되어야 함
        mask_arr = np.array(mask)
        mask_inverted = 255 - mask_arr
        mask_img = Image.fromarray(mask_inverted).convert("RGB")

        # 4. 이미지 생성 (Inference)
        negative_prompt = "low quality, ugly, distorted, text, watermark, bad anatomy, extra limbs"
        
        result = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=original_img,       # 원본 (색감 참조)
            control_image=canny_image, # 구조 (형태 고정)
            mask_image=mask_img,      # 마스크 (그릴 영역)
            num_inference_steps=25,   # 스텝 수
            guidance_scale=7.5,
            controlnet_conditioning_scale=0.5, # 형태 유지 강도
            strength=1.0              # 마스크 영역 재창조 강도
        ).images[0]

        return result

# 전역 인스턴스 생성 (다른 파일에서 import해서 사용)
ai_engine = AIEngine()