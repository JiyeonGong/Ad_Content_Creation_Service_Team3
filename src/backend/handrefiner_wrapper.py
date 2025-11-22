"""
HandRefiner 래퍼 모듈
Mesh Graphormer 기반 3D 손 메시 재구성으로 정확한 손가락 개수 보장

참조: ai-ad 프로젝트의 handrefiner_wrapper.py
"""

import torch
import numpy as np
import cv2
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from PIL import Image
import os

# 로깅
def log_info(msg): print(f"[HandRefiner] {msg}")
def log_warning(msg): print(f"[HandRefiner] ⚠️ {msg}")
def log_error(msg): print(f"[HandRefiner] ❌ {msg}")
def log_success(msg): print(f"[HandRefiner] ✅ {msg}")


class HandRefinerWrapper:
    """
    HandRefiner 래퍼 클래스
    (wenquanlu/HandRefiner를 git clone하여 models/handrefiner에 설치 필요)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        HandRefiner 래퍼 초기화 (Lazy loading - 실제 사용 시 로드)

        Args:
            config: 설정 딕셔너리 (handrefiner 섹션)
        """
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # HandRefiner 관련 (lazy loading)
        self.handrefiner_available = False
        self.handrefiner_loaded = False  # 로드 상태 플래그
        self.hand_detector = None
        self.mesh_graphormer = None
        self.inpaint_model = None

        log_info("HandRefinerWrapper initialized (lazy loading enabled)")

    def load_handrefiner(self) -> bool:
        """
        HandRefiner 모델 로드 (MeshGraphormer + ControlNet Inpainting)

        Returns:
            성공 여부
        """
        if not self.config.get("enable", False):
            log_info("HandRefiner disabled in config")
            return False

        try:
            # HandRefiner 경로 설정
            model_path = Path(self.config.get("model_path", "models/handrefiner"))

            if not model_path.exists():
                log_warning(f"HandRefiner not found at {model_path}")
                log_info("Please clone HandRefiner repository:")
                log_info("  git clone https://github.com/wenquanlu/HandRefiner.git models/handrefiner")
                log_info("  cd models/handrefiner && pip install -r requirements.txt")
                return False

            # sys.path 설정
            import sys
            handrefiner_str = str(model_path)
            meshgraphormer_str = str(model_path / "MeshGraphormer")
            preprocessor_str = str(model_path / "preprocessor")

            for path_str in [handrefiner_str, meshgraphormer_str, preprocessor_str]:
                if path_str not in sys.path:
                    sys.path.insert(0, path_str)
                    log_info(f"Added to sys.path: {path_str}")

            # HandRefiner 핵심 모듈 import
            try:
                # ControlNet 모델
                from cldm.model import create_model, load_state_dict
                from cldm.ddim_hacked import DDIMSampler

                # MeshGraphormer preprocessor
                from preprocessor.meshgraphormer import MeshGraphormerMediapipe

                log_info("HandRefiner modules imported successfully")

                # ControlNet 모델 로드
                weights_path = self.config.get(
                    "weights_path",
                    "models/handrefiner/inpaint_depth_control.ckpt"
                )

                config_path = model_path / "control_depth_inpaint.yaml"
                if not config_path.exists():
                    log_error(f"Config file not found: {config_path}")
                    return False

                log_info(f"Loading ControlNet model from {weights_path}")
                self.inpaint_model = create_model(str(config_path)).cpu()
                self.inpaint_model.load_state_dict(
                    load_state_dict(weights_path, location=self.device),
                    strict=False
                )

                # GPU로 이동 후 float16 변환 (순서 중요!)
                self.inpaint_model = self.inpaint_model.to(self.device)

                if self.device == "cuda":
                    self.inpaint_model = self.inpaint_model.half()
                    log_info("Converted ControlNet model to float16 for xformers compatibility")

                log_success("ControlNet inpaint model loaded")

                # MeshGraphormer 로드
                log_info("Loading MeshGraphormer...")
                self.mesh_graphormer = MeshGraphormerMediapipe()
                log_success("MeshGraphormer loaded")

                self.handrefiner_available = True
                log_success("HandRefiner loaded successfully")
                return True

            except ImportError as e:
                log_warning(f"Failed to import HandRefiner modules: {e}")
                log_info("HandRefiner repository may not be properly installed")
                import traceback
                traceback.print_exc()
                return False

        except Exception as e:
            log_error(f"Failed to load HandRefiner: {e}")
            import traceback
            traceback.print_exc()
            return False

    def refine_hands(
        self,
        image: Image.Image,
        prompt: str,
        control_strength: Optional[float] = None,
    ) -> Image.Image:
        """
        HandRefiner로 손 보정 (MeshGraphormer depth map + ControlNet inpainting)
        Lazy loading: 첫 호출 시 자동으로 모델 로드

        Args:
            image: 입력 이미지
            prompt: 원본 프롬프트
            control_strength: ControlNet 강도 (0.4-0.8 권장, None이면 config 값)

        Returns:
            보정된 이미지
        """
        # Lazy loading: 아직 로드되지 않았으면 지금 로드
        if not self.handrefiner_loaded:
            log_info("HandRefiner not loaded yet, loading now...")
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            success = self.load_handrefiner()
            if not success:
                log_warning("Failed to load HandRefiner, returning original image")
                return image
            self.handrefiner_loaded = True

        if not self.handrefiner_available:
            log_warning("HandRefiner not available, returning original image")
            return image

        try:
            log_info("Applying HandRefiner...")

            # Control strength 설정
            if control_strength is None:
                control_strength = self.config.get("control_strength", 0.6)

            # 이미지를 numpy array로 변환
            image_np = np.array(image)
            H, W, C = image_np.shape

            # MeshGraphormer로 손 depth map 및 mask 생성
            # 임시 파일로 저장 (MeshGraphormer가 파일 경로를 요구함)
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_img_path = Path(temp_dir) / "temp.png"
                image.save(temp_img_path)

                try:
                    depthmap, mask, info = self.mesh_graphormer.get_depth(
                        temp_dir, "temp.png", padding=10
                    )

                    # 손 감지 실패 시 None 반환됨
                    if depthmap is None or mask is None:
                        log_warning("MeshGraphormer: No hands detected in image")
                        return image

                except Exception as e:
                    log_warning(f"MeshGraphormer failed to detect hands: {e}")
                    return image

            # ControlNet inpainting 준비
            from cldm.ddim_hacked import DDIMSampler
            from cv2 import resize, INTER_LINEAR, INTER_NEAREST

            # 이미지 정규화
            source = (image_np.astype(np.float32) / 127.5) - 1.0
            source = source.transpose([2, 0, 1])  # HWC -> CHW

            # Mask와 depthmap을 원본 이미지 크기로 리사이즈
            if mask.shape[:2] != (H, W):
                mask = resize(mask, (W, H), interpolation=INTER_NEAREST)
            if depthmap.shape[:2] != (H, W):
                depthmap = resize(depthmap, (W, H), interpolation=INTER_LINEAR)

            # Mask 처리
            mask = mask.astype(np.float32) / 255.0
            mask = mask[None]  # Add channel dimension
            mask[mask < 0.5] = 0
            mask[mask >= 0.5] = 1

            # Control (depth) 처리 - 3 channel로 변환
            hint = depthmap.astype(np.float32) / 255.0
            if len(hint.shape) == 2:  # Grayscale -> RGB
                hint = np.stack([hint, hint, hint], axis=2)
            hint = hint.transpose([2, 0, 1])  # HWC -> CHW

            # Masked image
            masked_image = source * (mask < 0.5)

            # Batch 준비 (float16 변환)
            dtype = torch.float16 if self.device == "cuda" else torch.float32
            control_tensor = torch.from_numpy(hint.copy()).to(dtype).to(self.device)

            # Mask와 masked_image를 VAE latent space로 인코딩
            # VAE는 8배 다운샘플링하므로 (H, W) -> (H//8, W//8)
            with torch.no_grad():
                # Masked image를 latent로 인코딩 (float16)
                masked_image_tensor = torch.from_numpy(masked_image.copy()).to(dtype).unsqueeze(0).to(self.device)
                masked_latent = self.inpaint_model.encode_first_stage(masked_image_tensor)
                masked_latent = self.inpaint_model.get_first_stage_encoding(masked_latent)

                # Mask를 latent 크기로 리사이즈 (H, W) -> (H//8, W//8) (float16)
                import torch.nn.functional as F
                mask_tensor = torch.from_numpy(mask.copy()).to(dtype).unsqueeze(0).to(self.device)
                mask_latent = F.interpolate(mask_tensor, size=(H // 8, W // 8), mode='nearest')

            # DDIM sampler 설정
            ddim_sampler = DDIMSampler(self.inpaint_model)
            num_samples = 1
            ddim_steps = self.config.get("inpaint_steps", 20)
            scale = 9.0

            # Prompts
            a_prompt = "realistic, best quality, extremely detailed"
            n_prompt = "fake 3D rendered image, longbody, lowres, bad anatomy, bad hands, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, blue"

            full_prompt = f"{prompt}, {a_prompt}"

            # ControlNet inpainting 실행
            cond = {
                "c_concat": [mask_latent, masked_latent],  # Inpainting: mask + masked image
                "c_crossattn": [
                    self.inpaint_model.get_learned_conditioning([full_prompt] * num_samples)
                ],
                "c_control": [control_tensor.unsqueeze(0)],  # ControlNet depth control
            }

            un_cond = {
                "c_concat": [mask_latent, masked_latent],  # Same structure
                "c_crossattn": [
                    self.inpaint_model.get_learned_conditioning([n_prompt] * num_samples)
                ],
                "c_control": [control_tensor.unsqueeze(0)],  # Same control
            }

            shape = (4, H // 8, W // 8)

            # Latent 생성 with inpainting (mask와 x0는 c_concat에 이미 포함됨)
            samples, _ = ddim_sampler.sample(
                ddim_steps,
                num_samples,
                shape,
                cond,
                verbose=False,
                eta=0.0,
                unconditional_guidance_scale=scale,
                unconditional_conditioning=un_cond,
                x_T=None,
            )

            # Decode
            x_samples = self.inpaint_model.decode_first_stage(samples)
            x_samples = (
                (torch.clamp(x_samples, -1.0, 1.0) + 1.0) / 2.0 * 255.0
            ).cpu().numpy()
            x_samples = x_samples.transpose([0, 2, 3, 1])[0].astype(np.uint8)  # CHW -> HWC

            # PIL Image로 변환
            refined_image = Image.fromarray(x_samples)

            log_success("HandRefiner processing completed")
            return refined_image

        except Exception as e:
            log_error(f"HandRefiner processing failed: {e}")
            log_warning("Returning original image")
            import traceback
            traceback.print_exc()
            return image

    def is_available(self) -> bool:
        """HandRefiner 사용 가능 여부"""
        return self.handrefiner_available

    def is_enabled(self) -> bool:
        """HandRefiner 활성화 여부 (config 설정)"""
        return self.config.get("enable", False)
