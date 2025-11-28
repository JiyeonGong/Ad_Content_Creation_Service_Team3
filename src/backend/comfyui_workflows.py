# comfyui_workflows.py
"""
ComfyUI 워크플로우 정의
실제 워크플로우 JSON은 ComfyUI에서 생성 후 여기에 템플릿으로 저장
"""
import yaml
import os
from typing import Dict, Any


def load_image_editing_config() -> Dict[str, Any]:
    """이미지 편집 설정 로드"""
    config_path = os.path.join(
        os.path.dirname(__file__),
        "..", "..",
        "configs", "image_editing_config.yaml"
    )

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_workflow_template(experiment_id: str) -> Dict[str, Any]:
    """
    실험 ID에 따라 워크플로우 템플릿 반환

    Args:
        experiment_id: 모델 ID (portrait_mode, product_mode, hybrid_mode, FLUX.1-dev-Q8, FLUX.1-dev-Q4)

    Returns:
        ComfyUI 워크플로우 JSON
    """
    # 새로운 편집 모드
    if experiment_id == "portrait_mode":
        return get_portrait_mode_workflow()
    elif experiment_id == "product_mode":
        return get_product_mode_workflow()
    elif experiment_id == "hybrid_mode":
        return get_hybrid_mode_workflow()

    # 기존 실험 (하위 호환성)
    elif experiment_id == "ben2_flux_fill":
        return get_ben2_flux_fill_workflow()
    elif experiment_id == "ben2_qwen_image":
        return get_ben2_qwen_workflow()
    elif experiment_id in ["FLUX.1-dev-Q8", "FLUX.1-dev-Q4"]:
        return get_flux_t2i_workflow()
    else:
        raise ValueError(f"알 수 없는 실험 ID: {experiment_id}")


def get_flux_t2i_workflow() -> Dict[str, Any]:
    """
    FLUX T2I 워크플로우 템플릿 (GGUF 모델 사용)
    """
    workflow = {
        # 노드 1: FLUX UNET 로드 (GGUF)
        "1": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {
                "unet_name": "flux1-dev-Q8_0.gguf"  # 런타임에 변경
            }
        },

        # 노드 2: Dual CLIP 로드 (CLIP-L + T5-XXL)
        "2": {
            "class_type": "DualCLIPLoaderGGUF",
            "inputs": {
                "clip_name1": "clip_l.safetensors",
                "clip_name2": "t5-v1_1-xxl-encoder-Q8_0.gguf",
                "type": "flux"
            }
        },

        # 노드 3: 프롬프트 인코딩
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",  # 런타임에 설정
                "clip": ["2", 0]
            }
        },

        # [NEW] 노드 30: Negative 프롬프트 (Flux는 보통 비워둠)
        "30": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",  # 항상 비워둠
                "clip": ["2", 0]
            }
        },

        # ----------------------------------------------------------
        # [핵심 추가] 노드 35: Flux Guidance
        # 이 노드가 있어야 프롬프트 말을 잘 듣습니다.
        # guidance 값이 높을수록(예: 6.0) 프롬프트 반영률이 올라갑니다.
        # ----------------------------------------------------------
        "35": {
            "class_type": "FluxGuidance",
            "inputs": {
                "conditioning": ["3", 0], # Positive 프롬프트를 받음
                "guidance": 50 # [중요] 기본값 3.5 -> 4.5~6.0으로 올리세요!
            }
        },

        # 노드 4: VAE 로드
        "4": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "ae.safetensors"
            }
        },

        # 노드 5: Empty Latent
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 1024,  # 런타임에 설정
                "height": 1024,  # 런타임에 설정
                "batch_size": 1
            }
        },

        # 노드 6: KSampler
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,  # 런타임에 설정
                "steps": 28,  # 런타임에 설정
                "cfg": 1.0,  # 런타임에 설정
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["35", 0],
                "negative": ["30", 0],  # FLUX는 negative 불필요
                "latent_image": ["5", 0]
            }
        },

        # 노드 7: VAE Decode
        "7": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["6", 0],
                "vae": ["4", 0]
            }
        },

        # 노드 8: Save Image
        "8": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "flux_t2i",
                "images": ["7", 0]
            }
        }
    }

    return workflow


def get_flux_t2i_with_impact_workflow() -> Dict[str, Any]:
    """
    FLUX T2I + Impact Pack (FaceDetailer) 워크플로우
    """
    workflow = get_flux_t2i_workflow()

    # 기존 노드 8 (SaveImage) 삭제
    del workflow["8"]

    # BBox Detector 노드 (얼굴 감지용)
    workflow["9"] = {
        "class_type": "UltralyticsDetectorProvider",
        "inputs": {
            "model_name": "bbox/face_yolov8m.pt"
        }
    }

    # FaceDetailer 노드 추가 (노드 7 (VAEDecode) 이후)
    workflow["10"] = {
        "class_type": "FaceDetailer",
        "inputs": {
            "image": ["7", 0],  # VAE Decode 출력
            "model": ["1", 0],  # UNET
            "clip": ["2", 0],   # CLIP
            "vae": ["4", 0],    # VAE
            "positive": ["35", 0],  # FluxGuidance 출력 (조건부)
            "negative": ["30", 0],  # Negative 프롬프트 (빈 텍스트)
            "bbox_detector": ["9", 0],  # BBox Detector
            "wildcard": "",
            "cycle": 1,
            "guide_size": 512,
            "guide_size_for": True,
            "max_size": 1024,
            "seed": 0,  # 런타임에 설정
            "steps": 3,  # 얼굴 후처리 steps
            "cfg": 8.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 0.5,
            "feather": 5,
            "noise_mask": True,
            "force_inpaint": True,
            "bbox_threshold": 0.5,
            "bbox_dilation": 10,
            "bbox_crop_factor": 3.0,
            "sam_detection_hint": "center-1",
            "sam_dilation": 0,
            "sam_threshold": 0.93,
            "sam_bbox_expansion": 0,
            "sam_mask_hint_threshold": 0.7,
            "sam_mask_hint_use_negative": "False",
            "drop_size": 10
        }
    }

    # Hand Detector 노드 (손 감지용)
    workflow["12"] = {
        "class_type": "UltralyticsDetectorProvider",
        "inputs": {
            "model_name": "bbox/hand_yolov8s.pt"
        }
    }

    # HandDetailer 노드 추가 (FaceDetailer 출력 이후)
    workflow["13"] = {
        "class_type": "FaceDetailer",  # HandDetailer는 FaceDetailer와 같은 노드 사용
        "inputs": {
            "image": ["10", 0],  # FaceDetailer 출력
            "model": ["1", 0],
            "clip": ["2", 0],
            "vae": ["4", 0],
            "positive": ["35", 0],
            "negative": ["30", 0],
            "bbox_detector": ["12", 0],  # Hand Detector
            "wildcard": "",
            "cycle": 1,
            "guide_size": 384,  # 손은 작으므로 guide_size 줄임
            "guide_size_for": True,
            "max_size": 1024,
            "seed": 0,
            "steps": 6,
            "cfg": 8.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 0.5,
            "feather": 5,
            "noise_mask": True,
            "force_inpaint": True,
            "bbox_threshold": 0.5,
            "bbox_dilation": 10,
            "bbox_crop_factor": 3.0,
            "sam_detection_hint": "center-1",
            "sam_dilation": 0,
            "sam_threshold": 0.93,
            "sam_bbox_expansion": 0,
            "sam_mask_hint_threshold": 0.7,
            "sam_mask_hint_use_negative": "False",
            "drop_size": 10
        }
    }

    # Save Image를 HandDetailer 출력으로 연결
    workflow["11"] = {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "flux_t2i_impact",
            "images": ["13", 0]  # HandDetailer 출력
        }
    }

    return workflow


def get_flux_i2i_workflow() -> Dict[str, Any]:
    """
    FLUX I2I 워크플로우 템플릿 (GGUF)
    """
    workflow = {
        # 노드 1: FLUX UNET 로드 (GGUF)
        "1": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {
                "unet_name": "flux1-dev-Q8_0.gguf"  # 런타임에 변경
            }
        },

        # 노드 2: Dual CLIP 로드 (CLIP-L + T5-XXL)
        "2": {
            "class_type": "DualCLIPLoaderGGUF",
            "inputs": {
                "clip_name1": "clip_l.safetensors",
                "clip_name2": "t5-v1_1-xxl-encoder-Q8_0.gguf",
                "type": "flux"
            }
        },

        # 노드 3: 프롬프트 인코딩
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",  # 런타임에 설정
                "clip": ["2", 0]
            }
        },

        # 노드 4: VAE 로드
        "4": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "ae.safetensors"
            }
        },

        # 노드 5: 이미지 로드
        "5": {
            "class_type": "LoadImage",
            "inputs": {
                "image": "input.png"  # 런타임에 설정
            }
        },

        # 노드 6: VAE Encode
        "6": {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["5", 0],
                "vae": ["4", 0]
            }
        },

        # 노드 7: KSampler
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,  # 런타임에 설정
                "steps": 28,  # 런타임에 설정
                "cfg": 3.5,  # 런타임에 설정
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 0.75,  # strength, 런타임에 설정
                "model": ["1", 0],
                "positive": ["3", 0],
                "negative": ["3", 0],  # FLUX는 negative 불필요
                "latent_image": ["6", 0]
            }
        },

        # 노드 8: VAE Decode
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["7", 0],
                "vae": ["4", 0]
            }
        },

        # 노드 9: Save Image
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "flux_i2i",
                "images": ["8", 0]
            }
        }
    }

    return workflow


def get_ben2_flux_fill_workflow() -> Dict[str, Any]:
    """
    BEN2 + FLUX.1-Fill 워크플로우 템플릿 (올바른 Inpainting 구조)

    워크플로우:
    1. 원본 이미지 로드
    2. BEN2로 배경 제거하여 마스크 생성
    3. 마스크를 사용해 InpaintModelConditioning 적용
    4. FLUX.1-Fill로 배경 채우기
    """
    workflow = {
        # 노드 1: 원본 이미지 로드
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": "input.png"  # 업로드된 이미지 이름 (런타임에 설정)
            }
        },

        # 노드 2: BEN2 배경 제거 (출력: IMAGE, MASK, MASK_IMAGE)
        "2": {
            "class_type": "RMBG",
            "inputs": {
                "image": ["1", 0],
                "model": "BEN2",
                "sensitivity": 1.0,
                "process_res": 1024,
                "mask_blur": 0,
                "mask_offset": 0,
                "background": "Alpha",
                "invert_output": True  # True: 배경만 편집, False: 사람만 편집
            }
        },

        # 노드 3: FLUX.1-Fill UNET 로드 (GGUF)
        "3": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {
                "unet_name": "FLUX.1-Fill-dev-Q8_0.gguf"
            }
        },

        # 노드 4: CLIP 로드 (DualCLIPLoaderGGUF)
        "4": {
            "class_type": "DualCLIPLoaderGGUF",
            "inputs": {
                "clip_name1": "t5-v1_1-xxl-encoder-Q8_0.gguf",
                "clip_name2": "clip_l.safetensors",
                "type": "flux"
            }
        },

        # 노드 5: VAE 로드
        "5": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "ae.safetensors"
            }
        },

        # 노드 6: 프롬프트 인코딩 (FLUX용)
        "6": {
            "class_type": "CLIPTextEncodeFlux",
            "inputs": {
                "clip": ["4", 0],
                "clip_l": "",  # 런타임에 설정
                "t5xxl": "",   # 런타임에 설정
                "guidance": 3.5  # FLUX.1-Fill Inpainting: 3.5~7.5 권장
            }
        },

        # 노드 7: FluxGuidance
        "7": {
            "class_type": "FluxGuidance",
            "inputs": {
                "conditioning": ["6", 0],
                "guidance": 3.5  # FLUX.1-Fill Inpainting: 3.5~7.5 (런타임에 설정)
            }
        },

        # 노드 8: VAEEncodeForInpaint (원본 이미지 + 마스크)
        "8": {
            "class_type": "VAEEncodeForInpaint",
            "inputs": {
                "pixels": ["1", 0],  # 원본 이미지
                "vae": ["5", 0],
                "mask": ["2", 1],  # BEN2의 마스크 출력
                "grow_mask_by": 6
            }
        },

        # 노드 9: InpaintModelConditioning
        "9": {
            "class_type": "InpaintModelConditioning",
            "inputs": {
                "positive": ["7", 0],  # FluxGuidance의 conditioning
                "negative": ["7", 0],  # FLUX는 negative를 사용하지 않지만 필수 입력
                "pixels": ["1", 0],    # 원본 이미지
                "vae": ["5", 0],
                "mask": ["2", 1],      # BEN2의 마스크 출력
                "noise_mask": True     # Boolean - 노이즈 마스크 사용 여부
            }
        },

        # 노드 10: KSampler
        "10": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,  # 런타임에 설정
                "steps": 28,
                "cfg": 1.0,  # FluxGuidance를 사용하므로 1.0
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,  # Inpainting은 마스크 영역을 완전히 새로 생성해야 함
                "model": ["3", 0],
                "positive": ["9", 0],
                "negative": ["9", 1],
                "latent_image": ["8", 0]
            }
        },

        # 노드 11: VAE Decode
        "11": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["10", 0],
                "vae": ["5", 0]
            }
        },

        # 노드 12: SaveImage
        "12": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "ben2_flux_fill",
                "images": ["11", 0]
            }
        }
    }

    return workflow



def get_ben2_qwen_workflow() -> Dict[str, Any]:
    """
    BEN2 + Qwen-Image-Edit (GGUF) 워크플로우 템플릿
    
    워크플로우:
    1. 원본 이미지 로드
    2. BEN2로 배경 제거
    3. Qwen-Image-Edit (GGUF) + CLIP + VAE 로드
    4. TextEncodeQwenImageEditPlus (Positive/Negative)
    5. KSampler (Editing)
    """
    workflow = {
        # 노드 1: 이미지 로드
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": "input.png"
            }
        },

        # 노드 2: BEN2 배경 제거
        "2": {
            "class_type": "RMBG",
            "inputs": {
                "image": ["1", 0],
                "model": "BEN2",
                "sensitivity": 1.0,
                "process_res": 1024,
                "mask_blur": 0,
                "mask_offset": 0,
                "background": "Alpha",
                "invert_output": True
            }
        },

        # 노드 3: 이미지 리사이즈 (Qwen은 일정한 픽셀 수 필요)
        "3": {
            "class_type": "ImageScaleToTotalPixels",
            "inputs": {
                "image": ["2", 0],  # BEN2 출력
                "upscale_method": "bicubic",
                "megapixels": 1.0  # 1 메가픽셀 (1024x1024)
            }
        },

        # 노드 11: Qwen-Image-Edit UNET 로드 (GGUF)
        "11": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {
                "unet_name": "qwen-image-edit/Qwen-Image-Edit-2509-Q8_0.gguf"
            }
        },

        # 노드 4: Dual CLIP 로드 (Qwen용)
        "4": {
            "class_type": "DualCLIPLoaderGGUF",
            "inputs": {
                "clip_name1": "clip_l.safetensors",
                "clip_name2": "t5-v1_1-xxl-encoder-Q8_0.gguf",
                "type": "flux"
            }
        },

        # 노드 5: VAE 로드
        "5": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "ae.safetensors"
            }
        },

        # 노드 6: Qwen Positive Conditioning (TextEncodeQwenImageEditPlus)
        "6": {
            "class_type": "TextEncodeQwenImageEditPlus_lrzjason",
            "inputs": {
                "clip": ["4", 0],
                "prompt": "",  # 런타임에 설정
                "vae": ["5", 0],
                "image1": ["3", 0],  # 리사이즈된 이미지
                "enable_resize": True,
                "enable_vl_resize": True,
                "skip_first_image_resize": False,
                "upscale_method": "bicubic",
                "crop": "center",
                "instruction": "Describe the key features of the input image (color, shape, size, texture, objects, background), then explain how the user's text instruction should alter or modify the image. Generate a new image that meets the user's requirements while maintaining consistency with the original input where appropriate."
            }
        },

        # 노드 7: Negative Conditioning (텍스트만, 이미지 없음)
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["4", 0],
                "text": "text, watermark, low quality, blurry"
            }
        },

        # 노드 8: KSampler
        "8": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": 28,
                "cfg": 3.5,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 0.8,  # Strength
                "model": ["11", 0],  # Qwen UNET
                "positive": ["6", 0],  # Qwen Positive Conditioning
                "negative": ["7", 0],  # Simple Negative Conditioning
                "latent_image": ["6", 6]  # Latent from TextEncodeQwenImageEditPlus
            }
        },

        # 노드 9: VAE Decode
        "9": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["8", 0],
                "vae": ["5", 0]
            }
        },

        # 노드 10: 이미지 저장
        "10": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "qwen_output",
                "images": ["9", 0]
            }
        }
    }

    return workflow


def update_flux_t2i_workflow(
    workflow: Dict[str, Any],
    model_name: str,
    prompt: str,
    width: int,
    height: int,
    steps: int,
    guidance_scale: float,
    seed: int = None
) -> Dict[str, Any]:
    """FLUX T2I 워크플로우 파라미터 업데이트 (GGUF)"""
    import random
    from .model_registry import get_model_config

    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    # config에서 model_id 가져오기
    model_config = get_model_config()
    model_id = model_config["models"][model_name]["id"]

    # UNET GGUF 파일 설정 (노드 1)
    workflow["1"]["inputs"]["unet_name"] = model_id

    # 프롬프트 설정 (노드 3)
    workflow["3"]["inputs"]["text"] = prompt

    # 이미지 크기 설정 (노드 5: EmptyLatentImage)
    workflow["5"]["inputs"]["width"] = width
    workflow["5"]["inputs"]["height"] = height

    # ------------------------------------------------------------
    # [핵심 수정] Guidance 값을 올바른 노드(35번)에 연결!
    # ------------------------------------------------------------
    
    # 1. KSampler (노드 6)
    workflow["6"]["inputs"]["seed"] = seed
    workflow["6"]["inputs"]["steps"] = steps
    workflow["6"]["inputs"]["cfg"] = 1.0  # [중요] CFG는 1.0 고정! (웹 값 무시)

    # 2. FluxGuidance (노드 35)
    if "35" in workflow:
        workflow["35"]["inputs"]["guidance"] = guidance_scale # 웹 슬라이더 값을 여기에!
    else:
        print("⚠️ 경고: FluxGuidance(35) 노드가 템플릿에 없습니다!")

    return workflow


def update_flux_i2i_workflow(
    workflow: Dict[str, Any],
    model_name: str,
    prompt: str,
    strength: float,
    steps: int,
    guidance_scale: float,
    seed: int = None
) -> Dict[str, Any]:
    """FLUX I2I 워크플로우 파라미터 업데이트 (GGUF)"""
    import random
    from .model_registry import get_model_config

    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    # config에서 model_id 가져오기
    model_config = get_model_config()
    model_id = model_config["models"][model_name]["id"]

    # UNET GGUF 파일 설정 (노드 1)
    workflow["1"]["inputs"]["unet_name"] = model_id

    # 프롬프트 설정 (노드 3)
    workflow["3"]["inputs"]["text"] = prompt

    # 샘플링 파라미터 설정 (노드 7: KSampler)
    workflow["7"]["inputs"]["seed"] = seed
    workflow["7"]["inputs"]["steps"] = steps
    workflow["7"]["inputs"]["cfg"] = guidance_scale
    workflow["7"]["inputs"]["denoise"] = strength

    return workflow


def update_workflow_inputs(
    workflow: Dict[str, Any],
    experiment_id: str,
    prompt: str,
    negative_prompt: str = "",
    steps: int = None,
    guidance_scale: float = None,
    strength: float = None,
    seed: int = None
) -> Dict[str, Any]:
    """
    워크플로우 템플릿에 사용자 입력 반영

    Args:
        workflow: 워크플로우 템플릿
        experiment_id: 실험 ID
        prompt: 편집 프롬프트 (positive)
        negative_prompt: 네거티브 프롬프트
        steps: 추론 단계
        guidance_scale: Guidance scale
        strength: 변화 강도
        seed: 랜덤 시드

    Returns:
        업데이트된 워크플로우
    """
    config = load_image_editing_config()

    # 실험 설정 가져오기
    experiment = None
    for exp in config.get("experiments", []):
        if exp["id"] == experiment_id:
            experiment = exp
            break

    if not experiment:
        raise ValueError(f"실험 ID를 찾을 수 없습니다: {experiment_id}")

    # 기본값 설정
    params = experiment.get("params", {})
    steps = steps or params.get("default_steps", 28)
    guidance_scale = guidance_scale or params.get("guidance_scale", 3.5)
    strength = strength or params.get("strength", 0.8)

    # 랜덤 시드 생성
    if seed is None:
        import random
        seed = random.randint(0, 2**32 - 1)

    # 워크플로우 업데이트
    if experiment_id == "ben2_flux_fill":
        # 프롬프트 설정 (노드 6 - CLIPTextEncodeFlux)
        if "6" in workflow:
            workflow["6"]["inputs"]["clip_l"] = prompt
            workflow["6"]["inputs"]["t5xxl"] = prompt

        # 네거티브 프롬프트 노드 추가 (노드 6_neg)
        if negative_prompt.strip():
            # 네거티브 프롬프트용 별도 노드 생성
            workflow["6_neg"] = {
                "class_type": "CLIPTextEncodeFlux",
                "inputs": {
                    "clip": ["4", 0],
                    "clip_l": negative_prompt,
                    "t5xxl": negative_prompt,
                    "guidance": guidance_scale
                }
            }
            # InpaintModelConditioning의 negative를 6_neg로 변경
            if "9" in workflow:
                workflow["9"]["inputs"]["negative"] = ["6_neg", 0]

        # FluxGuidance 설정 (노드 7)
        if "7" in workflow:
            workflow["7"]["inputs"]["guidance"] = guidance_scale

        # KSampler 설정 (노드 10)
        if "10" in workflow:
            workflow["10"]["inputs"]["seed"] = seed
            workflow["10"]["inputs"]["steps"] = steps

    elif experiment_id == "ben2_qwen_image":
        # 프롬프트 설정 (노드 6: Qwen Positive Conditioning)
        if "6" in workflow:
            workflow["6"]["inputs"]["prompt"] = prompt

        # 네거티브 프롬프트 (노드 7: CLIPTextEncode)
        if "7" in workflow and negative_prompt:
            workflow["7"]["inputs"]["text"] = negative_prompt

        # KSampler 설정 (노드 8)
        if "8" in workflow:
            workflow["8"]["inputs"]["seed"] = seed
            workflow["8"]["inputs"]["steps"] = steps
            workflow["8"]["inputs"]["cfg"] = guidance_scale
            workflow["8"]["inputs"]["denoise"] = strength

    return workflow


# 프리로드 기능 제거됨
def _removed_get_preload_workflow(experiment_id: str) -> Dict[str, Any]:
    """
    모델 프리로딩용 워크플로우 생성
    
    전략:
    1. 전체 워크플로우 유지 (노드 삭제하면 에러 발생)
    2. Steps=1로 최소화 (속도 확보)
    3. SaveImage -> PreviewImage 교체 (디스크 저장 방지)
    
    Args:
        experiment_id: 모델 ID
        
    Returns:
        프리로딩용 워크플로우 JSON
    """
    import copy
    workflow = copy.deepcopy(get_workflow_template(experiment_id))
    
    if experiment_id == "ben2_flux_fill":
        # 1. 파라미터 최소화
        if "10" in workflow:  # KSampler (노드 10)
            workflow["10"]["inputs"]["steps"] = 1
            workflow["10"]["inputs"]["seed"] = 0
        
        if "6" in workflow:  # Prompt
            workflow["6"]["inputs"]["clip_l"] = "preload"
            workflow["6"]["inputs"]["t5xxl"] = "preload"
            
        # 2. SaveImage(12) -> PreviewImage 교체
        if "12" in workflow:
            workflow["12"] = {
                "class_type": "PreviewImage",
                "inputs": {
                    "images": ["11", 0]
                }
            }
            
    elif experiment_id == "ben2_qwen_image":
        # 1. 파라미터 최소화
        if "8" in workflow:  # KSampler
            workflow["8"]["inputs"]["steps"] = 1
            workflow["8"]["inputs"]["seed"] = 0
            
        if "6" in workflow:  # Prompt
            workflow["6"]["inputs"]["prompt"] = "preload"
            
        # 2. SaveImage(10) -> PreviewImage 교체
        if "10" in workflow:
            workflow["10"] = {
                "class_type": "PreviewImage",
                "inputs": {
                    "images": ["9", 0]
                }
            }
                
    elif experiment_id in ["FLUX.1-dev-Q8", "FLUX.1-dev-Q4"]:
        # 1. 파라미터 최소화
        if "4" in workflow:  # KSampler
            workflow["4"]["inputs"]["steps"] = 1
            workflow["4"]["inputs"]["seed"] = 0
            
        if "2" in workflow:  # Prompt
            workflow["2"]["inputs"]["text"] = "preload"
            
        # 2. SaveImage(6) -> PreviewImage 교체
        if "6" in workflow:
            workflow["6"] = {
                "class_type": "PreviewImage",
                "inputs": {
                    "images": ["5", 0]
                }
            }
            
    return workflow




def get_workflow_input_image_node_id(experiment_id: str) -> str:
    """
    워크플로우의 입력 이미지 노드 ID 반환

    Args:
        experiment_id: 실험 ID

    Returns:
        노드 ID (예: "1")
    """
    # 모든 워크플로우에서 노드 1이 LoadImage
    return "1"


# ============================================================
# 새로운 편집 모드 워크플로우 (v3.0)
# ============================================================

def get_portrait_mode_workflow() -> Dict[str, Any]:
    """
    🟢 Portrait Mode 워크플로우
    
    파이프라인:
    1. 얼굴 감지 (Face Detector)
    2. 마스크 반전 (얼굴 제외)
    3. ControlNet 가이드 추출 (Depth/Canny)
    4. Masked I2I 생성 (옷/배경만 변경)
    """
    workflow = {
        # 노드 1: 입력 이미지 로드
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": "input.png"  # 런타임에 변경
            }
        },

        # 노드 2: FLUX UNET 로드
        "2": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {
                "unet_name": "flux1-dev-Q8_0.gguf"
            }
        },

        # 노드 3: Dual CLIP 로드
        "3": {
            "class_type": "DualCLIPLoaderGGUF",
            "inputs": {
                "clip_name1": "clip_l.safetensors",
                "clip_name2": "t5-v1_1-xxl-encoder-Q8_0.gguf",
                "type": "flux"
            }
        },

        # 노드 4: VAE 로드
        "4": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "ae.safetensors"
            }
        },

        # 노드 5: 프롬프트 인코딩
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",  # 런타임에 설정
                "clip": ["3", 0]
            }
        },

        # 노드 6: Negative 프롬프트
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",
                "clip": ["3", 0]
            }
        },

        # 노드 7: FluxGuidance
        "7": {
            "class_type": "FluxGuidance",
            "inputs": {
                "conditioning": ["5", 0],
                "guidance": 3.5  # 런타임에 설정
            }
        },

        # 노드 10: Face Detector
        "10": {
            "class_type": "UltralyticsDetectorProvider",
            "inputs": {
                "model_name": "bbox/face_yolov8m.pt"
            }
        },

        # 노드 11: SEGS from Detection (얼굴 영역 세그먼트)
        "11": {
            "class_type": "SAMLoader",
            "inputs": {
                "model_name": "sam_vit_b_01ec64.pth"
            }
        },

        # 노드 12: BboxDetectorSEGS (얼굴 감지 실행)
        "12": {
            "class_type": "BboxDetectorSEGS",
            "inputs": {
                "image": ["1", 0],
                "bbox_detector": ["10", 0],
                "threshold": 0.5,
                "dilation": 10,
                "crop_factor": 3.0,
                "drop_size": 10
            }
        },

        # 노드 13: SEGS to Mask (얼굴 마스크 생성)
        "13": {
            "class_type": "SegsToCombinedMask",
            "inputs": {
                "segs": ["12", 0]
            }
        },

        # 노드 14: Invert Mask (얼굴 제외한 나머지 영역)
        "14": {
            "class_type": "InvertMask",
            "inputs": {
                "mask": ["13", 0]
            }
        },

        # 노드 20: ControlNet Preprocessor (Depth 또는 Canny)
        "20": {
            "class_type": "DepthAnythingPreprocessor",
            "inputs": {
                "image": ["1", 0],
                "ckpt_name": "depth_anything_v2_vitl.pth",
                "resolution": 1024
            }
        },

        # 노드 21: ControlNet 로드
        "21": {
            "class_type": "ControlNetLoader",
            "inputs": {
                "control_net_name": "InstantX-FLUX.1-dev-Controlnet-Union.safetensors"
            }
        },

        # 노드 22: Apply ControlNet
        "22": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["7", 0],
                "negative": ["6", 0],
                "control_net": ["21", 0],
                "image": ["20", 0],
                "strength": 0.7,  # 런타임에 설정
                "start_percent": 0.0,
                "end_percent": 1.0
            }
        },

        # 노드 30: VAE Encode (입력 이미지)
        "30": {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["1", 0],
                "vae": ["4", 0]
            }
        },

        # 노드 31: Set Latent Noise Mask (마스크 적용)
        "31": {
            "class_type": "SetLatentNoiseMask",
            "inputs": {
                "samples": ["30", 0],
                "mask": ["14", 0]  # 반전된 마스크 (얼굴 제외)
            }
        },

        # 노드 40: KSampler (Masked I2I)
        "40": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,  # 런타임에 설정
                "steps": 28,  # 런타임에 설정
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,  # 런타임에 설정
                "model": ["2", 0],
                "positive": ["22", 0],  # ControlNet 적용된 조건
                "negative": ["6", 0],
                "latent_image": ["31", 0]  # 마스크 적용된 latent
            }
        },

        # 노드 41: VAE Decode
        "41": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["40", 0],
                "vae": ["4", 0]
            }
        },

        # 노드 50: Save Image
        "50": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "portrait_mode",
                "images": ["41", 0]
            }
        }
    }

    return workflow


def get_product_mode_workflow() -> Dict[str, Any]:
    """
    🔵 Product Mode 워크플로우
    
    파이프라인:
    1. BEN2로 제품 누끼 따기
    2. Flux Dev T2I로 배경 생성
    3. 레이어 합성 (배경 + 제품)
    4. Flux Fill로 자연스럽게 융합
    """
    workflow = {
        # 노드 1: 입력 이미지 로드
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": "input.png"
            }
        },

        # 노드 2: BEN2 배경 제거
        "2": {
            "class_type": "BEN2",
            "inputs": {
                "image": ["1", 0]
            }
        },

        # 노드 10: FLUX UNET 로드 (T2I용)
        "10": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {
                "unet_name": "flux1-dev-Q8_0.gguf"
            }
        },

        # 노드 11: Dual CLIP 로드
        "11": {
            "class_type": "DualCLIPLoaderGGUF",
            "inputs": {
                "clip_name1": "clip_l.safetensors",
                "clip_name2": "t5-v1_1-xxl-encoder-Q8_0.gguf",
                "type": "flux"
            }
        },

        # 노드 12: VAE 로드
        "12": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "ae.safetensors"
            }
        },

        # 노드 13: 배경 프롬프트 인코딩
        "13": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",  # 런타임에 설정 (배경 프롬프트)
                "clip": ["11", 0]
            }
        },

        # 노드 14: Negative 프롬프트
        "14": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",
                "clip": ["11", 0]
            }
        },

        # 노드 15: FluxGuidance
        "15": {
            "class_type": "FluxGuidance",
            "inputs": {
                "conditioning": ["13", 0],
                "guidance": 5.0  # 런타임에 설정
            }
        },

        # 노드 16: Empty Latent (배경 생성용)
        "16": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 1024,  # 런타임에 설정
                "height": 1024,
                "batch_size": 1
            }
        },

        # 노드 17: KSampler (배경 생성)
        "17": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,  # 런타임에 설정
                "steps": 28,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["10", 0],
                "positive": ["15", 0],
                "negative": ["14", 0],
                "latent_image": ["16", 0]
            }
        },

        # 노드 18: VAE Decode (배경 이미지)
        "18": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["17", 0],
                "vae": ["12", 0]
            }
        },

        # 노드 20: ImageCompositeM (레이어 합성)
        "20": {
            "class_type": "ImageCompositeAbsolute",
            "inputs": {
                "image_base": ["18", 0],  # 배경
                "image_overlay": ["2", 0],  # BEN2 누끼 이미지
                "x": 0,
                "y": 0
            }
        },

        # 노드 30: FLUX Fill UNET 로드
        "30": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {
                "unet_name": "FLUX.1-Fill-dev-Q8_0.gguf"
            }
        },

        # 노드 31: BEN2 마스크 추출
        "31": {
            "class_type": "ImageToMask",
            "inputs": {
                "image": ["2", 0],
                "channel": "alpha"
            }
        },

        # 노드 32: Invert Mask (제품 외곽만)
        "32": {
            "class_type": "InvertMask",
            "inputs": {
                "mask": ["31", 0]
            }
        },

        # 노드 33: Dilate Mask (외곽 확장)
        "33": {
            "class_type": "GrowMask",
            "inputs": {
                "mask": ["31", 0],
                "expand": 10,
                "tapered_corners": True
            }
        },

        # 노드 40: VAE Encode (합성 이미지)
        "40": {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["20", 0],
                "vae": ["12", 0]
            }
        },

        # 노드 41: Set Latent Noise Mask (외곽만 블렌딩)
        "41": {
            "class_type": "SetLatentNoiseMask",
            "inputs": {
                "samples": ["40", 0],
                "mask": ["33", 0]
            }
        },

        # 노드 42: KSampler (Blending)
        "42": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": 28,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 0.35,  # 런타임에 설정 (블렌딩 강도)
                "model": ["30", 0],  # Flux Fill
                "positive": ["15", 0],  # 배경 프롬프트 재사용
                "negative": ["14", 0],
                "latent_image": ["41", 0]
            }
        },

        # 노드 43: VAE Decode
        "43": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["42", 0],
                "vae": ["12", 0]
            }
        },

        # 노드 50: Save Image
        "50": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "product_mode",
                "images": ["43", 0]
            }
        }
    }

    return workflow


def get_hybrid_mode_workflow() -> Dict[str, Any]:
    """
    🟣 Hybrid Mode 워크플로우
    
    파이프라인:
    1. 얼굴 감지 (Face Detector)
    2. 제품 감지 (BEN2)
    3. 멀티 마스크 합성 (얼굴 + 제품)
    4. 마스크 반전 (옷/배경만 수정)
    5. ControlNet (Canny) + Masked I2I
    """
    workflow = {
        # 노드 1: 입력 이미지 로드
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": "input.png"
            }
        },

        # 노드 2: FLUX UNET 로드
        "2": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {
                "unet_name": "flux1-dev-Q8_0.gguf"
            }
        },

        # 노드 3: Dual CLIP 로드
        "3": {
            "class_type": "DualCLIPLoaderGGUF",
            "inputs": {
                "clip_name1": "clip_l.safetensors",
                "clip_name2": "t5-v1_1-xxl-encoder-Q8_0.gguf",
                "type": "flux"
            }
        },

        # 노드 4: VAE 로드
        "4": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "ae.safetensors"
            }
        },

        # 노드 5: 프롬프트 인코딩
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",  # 런타임에 설정
                "clip": ["3", 0]
            }
        },

        # 노드 6: Negative 프롬프트
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",
                "clip": ["3", 0]
            }
        },

        # 노드 7: FluxGuidance
        "7": {
            "class_type": "FluxGuidance",
            "inputs": {
                "conditioning": ["5", 0],
                "guidance": 3.5
            }
        },

        # 노드 10: Face Detector
        "10": {
            "class_type": "UltralyticsDetectorProvider",
            "inputs": {
                "model_name": "bbox/face_yolov8m.pt"
            }
        },

        # 노드 11: BboxDetectorSEGS (얼굴)
        "11": {
            "class_type": "BboxDetectorSEGS",
            "inputs": {
                "image": ["1", 0],
                "bbox_detector": ["10", 0],
                "threshold": 0.5,
                "dilation": 10,
                "crop_factor": 3.0,
                "drop_size": 10
            }
        },

        # 노드 12: SEGS to Mask (얼굴 마스크)
        "12": {
            "class_type": "SegsToCombinedMask",
            "inputs": {
                "segs": ["11", 0]
            }
        },

        # 노드 15: BEN2 (제품 누끼)
        "15": {
            "class_type": "BEN2",
            "inputs": {
                "image": ["1", 0]
            }
        },

        # 노드 16: ImageToMask (제품 마스크)
        "16": {
            "class_type": "ImageToMask",
            "inputs": {
                "image": ["15", 0],
                "channel": "alpha"
            }
        },

        # 노드 17: MaskComposite (얼굴 + 제품 마스크 합성)
        "17": {
            "class_type": "MaskComposite",
            "inputs": {
                "destination": ["12", 0],  # 얼굴 마스크
                "source": ["16", 0],  # 제품 마스크
                "x": 0,
                "y": 0,
                "operation": "add"  # 합집합
            }
        },

        # 노드 18: Invert Mask (얼굴+제품 제외한 나머지)
        "18": {
            "class_type": "InvertMask",
            "inputs": {
                "mask": ["17", 0]
            }
        },

        # 노드 20: ControlNet Preprocessor (Canny)
        "20": {
            "class_type": "CannyEdgePreprocessor",
            "inputs": {
                "image": ["1", 0],
                "low_threshold": 100,
                "high_threshold": 200,
                "resolution": 1024
            }
        },

        # 노드 21: ControlNet 로드
        "21": {
            "class_type": "ControlNetLoader",
            "inputs": {
                "control_net_name": "InstantX-FLUX.1-dev-Controlnet-Union.safetensors"
            }
        },

        # 노드 22: Apply ControlNet
        "22": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["7", 0],
                "negative": ["6", 0],
                "control_net": ["21", 0],
                "image": ["20", 0],
                "strength": 0.8,  # 런타임에 설정
                "start_percent": 0.0,
                "end_percent": 1.0
            }
        },

        # 노드 30: VAE Encode
        "30": {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["1", 0],
                "vae": ["4", 0]
            }
        },

        # 노드 31: Set Latent Noise Mask
        "31": {
            "class_type": "SetLatentNoiseMask",
            "inputs": {
                "samples": ["30", 0],
                "mask": ["18", 0]  # 얼굴+제품 제외
            }
        },

        # 노드 40: KSampler
        "40": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": 28,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 0.9,  # 런타임에 설정
                "model": ["2", 0],
                "positive": ["22", 0],
                "negative": ["6", 0],
                "latent_image": ["31", 0]
            }
        },

        # 노드 41: VAE Decode
        "41": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["40", 0],
                "vae": ["4", 0]
            }
        },

        # 노드 50: Save Image
        "50": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "hybrid_mode",
                "images": ["41", 0]
            }
        }
    }

    return workflow
