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


def get_pipeline_steps_for_mode(experiment_id: str) -> Dict[str, str]:
    """
    모드별 노드 ID -> 파이프라인 단계명 매핑

    Args:
        experiment_id: 모드 ID (portrait_mode, product_mode, hybrid_mode)

    Returns:
        {node_id: step_name} 딕셔너리
    """
    if experiment_id == "portrait_mode":
        return {
            "1": "📥 이미지 로드",
            "10": "🔍 얼굴 감지 모델 로드",
            "12": "👤 얼굴 영역 감지 중...",
            "13": "🎭 얼굴 마스크 생성",
            "14": "🔄 마스크 반전 (편집 영역 설정)",
            "20": "📊 Depth/Canny 맵 추출 중...",
            "21": "🎮 ControlNet 모델 로드",
            "22": "🎨 ControlNet 적용",
            "3": "📝 CLIP 텍스트 인코딩",
            "4": "🧠 GGUF 모델 로드",
            "6": "⚙️ Negative 프롬프트 처리",
            "30": "🎲 Latent 노이즈 생성",
            "31": "🖌️ 마스크 적용 (편집 영역 제한)",
            "40": "🚀 이미지 생성 중... (KSampler)",
            "41": "🎬 VAE 디코딩",
            "50": "💾 결과 저장"
        }
    elif experiment_id == "product_mode":
        return {
            "1": "📥 이미지 로드",
            "2": "✂️ BEN2 배경 제거 중...",
            "3": "📝 배경 프롬프트 인코딩",
            "4": "🧠 GGUF 모델 로드 (배경 생성)",
            "5": "🎲 Latent 노이즈 생성",
            "6": "🎨 배경 이미지 생성 중...",
            "7": "🎬 VAE 디코딩 (배경)",
            "8": "🔗 제품 + 배경 레이어 합성",
            "9": "🖼️ FLUX Fill 입력 준비",
            "10": "📝 블렌딩 프롬프트 인코딩",
            "11": "🧠 FLUX Fill 모델 로드",
            "12": "🎨 자연스러운 블렌딩 중...",
            "13": "🎬 VAE 디코딩 (최종)",
            "50": "💾 결과 저장"
        }
    elif experiment_id == "hybrid_mode":
        return {
            "1": "📥 이미지 로드",
            "10": "🔍 얼굴 감지 모델 로드",
            "11": "👤 얼굴 영역 감지 중...",
            "12": "🎭 얼굴 마스크 생성",
            "20": "🔍 제품 감지 모델 로드",
            "21": "📦 제품 영역 감지 중...",
            "22": "📦 제품 마스크 생성",
            "30": "🔗 얼굴+제품 마스크 합성",
            "31": "🔄 마스크 반전 (편집 영역 설정)",
            "40": "📊 Canny 맵 추출 중...",
            "41": "🎮 ControlNet 모델 로드",
            "42": "🎨 ControlNet 적용",
            "3": "📝 CLIP 텍스트 인코딩",
            "4": "🧠 GGUF 모델 로드",
            "6": "⚙️ Negative 프롬프트 처리",
            "50": "🎲 Latent 노이즈 생성",
            "51": "🖌️ 마스크 적용 (편집 영역 제한)",
            "60": "🚀 이미지 생성 중... (KSampler)",
            "61": "🎬 VAE 디코딩",
            "70": "💾 결과 저장"
        }
    else:
        return {}


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


# 🗑️ 기존 실험 워크플로우 제거됨 (ben2_flux_fill, ben2_qwen_image)
# 새로운 3가지 모드로 대체: portrait_mode, product_mode, hybrid_mode


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
    seed: int = None,
    # 새로운 모드 파라미터
    controlnet_type: str = "depth",
    controlnet_strength: float = 0.7,
    denoise_strength: float = 1.0,
    blending_strength: float = 0.35,
    background_prompt: str = None
) -> Dict[str, Any]:
    """
    워크플로우 템플릿에 사용자 입력 반영

    Args:
        workflow: 워크플로우 템플릿
        experiment_id: 실험 ID (portrait_mode, product_mode, hybrid_mode)
        prompt: 편집 프롬프트 (positive)
        negative_prompt: 네거티브 프롬프트
        steps: 추론 단계
        guidance_scale: Guidance scale
        strength: 변화 강도 (deprecated, denoise_strength 사용)
        seed: 랜덤 시드
        controlnet_type: ControlNet 타입 ("depth" 또는 "canny")
        controlnet_strength: ControlNet 강도 (0.0~1.0)
        denoise_strength: 변경 강도 (0.0~1.0)
        blending_strength: 블렌딩 강도 (Product 모드)
        background_prompt: 배경 프롬프트 (Product 모드)

    Returns:
        업데이트된 워크플로우
    """
    config = load_image_editing_config()

    # 모드 설정 가져오기
    mode_config = None
    for mode_id, mode_data in config.get("editing_modes", {}).items():
        if mode_data["id"] == experiment_id:
            mode_config = mode_data
            break

    if not mode_config:
        raise ValueError(f"알 수 없는 모드 ID: {experiment_id}")

    # 기본값 설정
    params = mode_config.get("params", {})
    steps = steps or params.get("default_steps", 28)
    guidance_scale = guidance_scale or params.get("guidance_scale", 3.5)

    # 랜덤 시드 생성
    if seed is None:
        import random
        seed = random.randint(0, 2**32 - 1)

    # ============================================================
    # Portrait Mode 워크플로우 업데이트
    # ============================================================
    if experiment_id == "portrait_mode":
        # 프롬프트 설정 (노드 5)
        if "5" in workflow:
            workflow["5"]["inputs"]["text"] = prompt

        # Negative 프롬프트 (노드 6)
        if "6" in workflow:
            workflow["6"]["inputs"]["text"] = negative_prompt

        # FluxGuidance (노드 7)
        if "7" in workflow:
            workflow["7"]["inputs"]["guidance"] = guidance_scale

        # ControlNet 타입 변경 (노드 20)
        if "20" in workflow and controlnet_type == "canny":
            workflow["20"] = {
                "class_type": "CannyEdgePreprocessor",
                "inputs": {
                    "image": ["1", 0],
                    "low_threshold": 100,
                    "high_threshold": 200,
                    "resolution": 1024
                }
            }

        # ControlNet 강도 (노드 22)
        if "22" in workflow:
            workflow["22"]["inputs"]["strength"] = controlnet_strength

        # KSampler (노드 40)
        if "40" in workflow:
            workflow["40"]["inputs"]["seed"] = seed
            workflow["40"]["inputs"]["steps"] = steps
            workflow["40"]["inputs"]["denoise"] = denoise_strength

    # ============================================================
    # Product Mode 워크플로우 업데이트
    # ============================================================
    elif experiment_id == "product_mode":
        # 배경 프롬프트 설정 (노드 13)
        bg_prompt = background_prompt or prompt
        if "13" in workflow:
            workflow["13"]["inputs"]["text"] = bg_prompt

        # Negative 프롬프트 (노드 14)
        if "14" in workflow:
            workflow["14"]["inputs"]["text"] = negative_prompt

        # FluxGuidance (노드 15)
        if "15" in workflow:
            workflow["15"]["inputs"]["guidance"] = guidance_scale

        # 배경 생성 KSampler (노드 17)
        if "17" in workflow:
            workflow["17"]["inputs"]["seed"] = seed
            workflow["17"]["inputs"]["steps"] = steps

        # 블렌딩 KSampler (노드 42)
        if "42" in workflow:
            workflow["42"]["inputs"]["seed"] = seed
            workflow["42"]["inputs"]["denoise"] = blending_strength

    # ============================================================
    # Hybrid Mode 워크플로우 업데이트
    # ============================================================
    elif experiment_id == "hybrid_mode":
        # 프롬프트 설정 (노드 5)
        if "5" in workflow:
            workflow["5"]["inputs"]["text"] = prompt

        # Negative 프롬프트 (노드 6)
        if "6" in workflow:
            workflow["6"]["inputs"]["text"] = negative_prompt

        # FluxGuidance (노드 7)
        if "7" in workflow:
            workflow["7"]["inputs"]["guidance"] = guidance_scale

        # ControlNet 타입 변경 (노드 20 - 기본은 Canny)
        if "20" in workflow and controlnet_type == "depth":
            workflow["20"] = {
                "class_type": "DepthAnythingPreprocessor",
                "inputs": {
                    "image": ["1", 0],
                    "ckpt_name": "depth_anything_v2_vitl.pth",
                    "resolution": 1024
                }
            }

        # ControlNet 강도 (노드 22)
        if "22" in workflow:
            workflow["22"]["inputs"]["strength"] = controlnet_strength

        # KSampler (노드 40)
        if "40" in workflow:
            workflow["40"]["inputs"]["seed"] = seed
            workflow["40"]["inputs"]["steps"] = steps
            workflow["40"]["inputs"]["denoise"] = denoise_strength

    return workflow


# 🗑️ 프리로드 기능 제거됨 (모델 자동 로딩 제거로 불필요)




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
                "drop_size": 10,
                "labels": "all"
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
                "ckpt_name": "depth_anything_vitl14.pth",
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

        # 노드 2: RMBG 배경 제거 (BEN2 모델 사용)
        "2": {
            "class_type": "RMBG",
            "inputs": {
                "image": ["1", 0],
                "model": "BEN2",
                "sensitivity": 1.0,
                "process_res": 1024,
                "background": "Alpha"
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
