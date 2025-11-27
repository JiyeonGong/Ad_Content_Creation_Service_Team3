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
        experiment_id: "ben2_flux_fill" 또는 "ben2_qwen_image"

    Returns:
        ComfyUI 워크플로우 JSON
    """
    if experiment_id == "ben2_flux_fill":
        return get_ben2_flux_fill_workflow()
    elif experiment_id == "ben2_qwen_image":
        return get_ben2_qwen_image_workflow()
    else:
        raise ValueError(f"알 수 없는 실험 ID: {experiment_id}")


def get_flux_t2i_workflow() -> Dict[str, Any]:
    """
    FLUX T2I 워크플로우 템플릿 (기존 기능)

    주의: 실제 ComfyUI에서 생성한 JSON으로 교체 필요
    """
    workflow = {
        # 노드 1: FLUX 체크포인트 로드
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "flux-dev-bnb-8bit.safetensors"  # 런타임에 변경
            }
        },

        # 노드 2: 프롬프트 인코딩
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",  # 런타임에 설정
                "clip": ["1", 1]
            }
        },

        # 노드 3: Empty Latent
        "3": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 1024,  # 런타임에 설정
                "height": 1024,  # 런타임에 설정
                "batch_size": 1
            }
        },

        # 노드 4: KSampler
        "4": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,  # 런타임에 설정
                "steps": 28,  # 런타임에 설정
                "cfg": 3.5,  # 런타임에 설정
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["2", 0],  # FLUX는 negative 불필요
                "latent_image": ["3", 0]
            }
        },

        # 노드 5: VAE Decode
        "5": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["4", 0],
                "vae": ["1", 2]
            }
        },

        # 노드 6: Save Image
        "6": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "flux_t2i",
                "images": ["5", 0]
            }
        }
    }

    return workflow


def get_flux_t2i_with_impact_workflow() -> Dict[str, Any]:
    """
    FLUX T2I + Impact Pack (FaceDetailer) 워크플로우
    """
    workflow = get_flux_t2i_workflow()

    # FaceDetailer 노드 추가 (노드 5와 6 사이)
    workflow["7"] = {
        "class_type": "FaceDetailer",
        "inputs": {
            "image": ["5", 0],  # VAE Decode 출력
            "model": ["1", 0],
            "clip": ["1", 1],
            "vae": ["1", 2],
            "guide_size": 512,
            "guide_size_for": True,
            "max_size": 1024,
            "seed": 0,  # 런타임에 설정
            "steps": 20,
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

    # Save Image를 FaceDetailer 출력으로 변경
    workflow["6"]["inputs"]["images"] = ["7", 0]

    return workflow


def get_flux_i2i_workflow() -> Dict[str, Any]:
    """
    FLUX I2I 워크플로우 템플릿
    """
    workflow = {
        # 노드 1: 이미지 로드
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": "input.png"  # 런타임에 설정
            }
        },

        # 노드 2: FLUX 체크포인트 로드
        "2": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "flux-dev-bnb-8bit.safetensors"
            }
        },

        # 노드 3: 프롬프트 인코딩
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",  # 런타임에 설정
                "clip": ["2", 1]
            }
        },

        # 노드 4: VAE Encode
        "4": {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["1", 0],
                "vae": ["2", 2]
            }
        },

        # 노드 5: KSampler
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": 28,
                "cfg": 3.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 0.75,  # strength, 런타임에 설정
                "model": ["2", 0],
                "positive": ["3", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0]
            }
        },

        # 노드 6: VAE Decode
        "6": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["5", 0],
                "vae": ["2", 2]
            }
        },

        # 노드 7: Save Image
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "flux_i2i",
                "images": ["6", 0]
            }
        }
    }

    return workflow


def get_ben2_flux_fill_workflow() -> Dict[str, Any]:
    """
    BEN2 + FLUX.1-Fill 워크플로우 템플릿

    GGUF 형식 모델을 위한 올바른 로더 사용
    """
    workflow = {
        # 노드 1: 이미지 로드
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": "input.png"  # 업로드된 이미지 이름 (런타임에 설정)
            }
        },

        # 노드 2: BEN2 배경 제거
        "2": {
            "class_type": "RMBG",
            "inputs": {
                "image": ["1", 0],  # 노드 1의 출력
                "model": "BEN2",
                "sensitivity": 1.0,
                "process_res": 1024
            }
        },

        # 노드 3: FLUX.1-Fill UNET 로드 (GGUF)
        "3": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {
                "unet_name": "FLUX.1-Fill-dev-Q8_0.gguf"
            }
        },

        # 노드 4: CLIP 로드 (GGUF) - T5XXL
        "4": {
            "class_type": "DualCLIPLoaderGGUF",
            "inputs": {
                "clip_name1": "t5-v1_1-xxl-encoder-Q8_0.gguf",  # T5 인코더 (GGUF)
                "clip_name2": "clip_l.safetensors",             # CLIP-L 인코더
                "type": "flux"
            }
        },

        # 노드 5: VAE 로드
        "5": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "ae.safetensors"  # FLUX VAE
            }
        },

        # 노드 6: 프롬프트 인코딩
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",  # 런타임에 설정
                "clip": ["4", 0]  # 노드 4의 CLIP 출력
            }
        },

        # 노드 7: VAE Encode (배경 제거 이미지를 latent로)
        "7": {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["2", 0],  # BEN2 출력
                "vae": ["5", 0]  # 노드 5의 VAE
            }
        },

        # 노드 8: KSampler (이미지 생성)
        "8": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,  # 런타임에 랜덤 시드 설정
                "steps": 28,  # 런타임에 설정
                "cfg": 3.5,  # guidance_scale
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,  # FLUX.1-Fill은 full denoise
                "model": ["3", 0],  # GGUF UNET
                "positive": ["6", 0],
                "negative": ["6", 0],  # FLUX는 negative 사용 안 함
                "latent_image": ["7", 0]  # VAE Encode 출력
            }
        },

        # 노드 9: VAE Decode (latent를 이미지로)
        "9": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["8", 0],  # KSampler 출력
                "vae": ["5", 0]
            }
        },

        # 노드 10: 이미지 저장
        "10": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "flux_fill_output",
                "images": ["9", 0]  # VAE Decode 출력
            }
        }
    }

    return workflow



def get_ben2_qwen_image_workflow() -> Dict[str, Any]:
    """
    BEN2 + Qwen-Image 워크플로우 템플릿

    주의: 이 워크플로우는 실제 ComfyUI에서 생성한 JSON을 기반으로 수정해야 합니다.
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
                "process_res": 1024
            }
        },

        # 노드 3: Qwen-Image 모델 로드
        "3": {
            "class_type": "QwenImageLoader",
            "inputs": {
                "model_path": "/mnt/data4/models/qwen-image"
            }
        },

        # 노드 4: Qwen-Image 프롬프트
        "4": {
            "class_type": "QwenImagePrompt",
            "inputs": {
                "text": "",  # 런타임에 설정
                "model": ["3", 0]
            }
        },

        # 노드 5: Qwen-Image 생성
        "5": {
            "class_type": "QwenImageGenerate",
            "inputs": {
                "image": ["2", 0],  # BEN2 출력
                "prompt": ["4", 0],
                "model": ["3", 0],
                "steps": 30,
                "guidance_scale": 7.5,
                "strength": 0.8
            }
        },

        # 노드 6: 이미지 저장
        "6": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "qwen_output",
                "images": ["5", 0]
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
    """FLUX T2I 워크플로우 파라미터 업데이트"""
    import random

    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    # 모델 이름 설정
    workflow["1"]["inputs"]["ckpt_name"] = f"{model_name}.safetensors"

    # 프롬프트 설정
    workflow["2"]["inputs"]["text"] = prompt

    # 이미지 크기 설정
    workflow["3"]["inputs"]["width"] = width
    workflow["3"]["inputs"]["height"] = height

    # 샘플링 파라미터 설정
    workflow["4"]["inputs"]["seed"] = seed
    workflow["4"]["inputs"]["steps"] = steps
    workflow["4"]["inputs"]["cfg"] = guidance_scale

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
    """FLUX I2I 워크플로우 파라미터 업데이트"""
    import random

    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    # 모델 이름 설정
    workflow["2"]["inputs"]["ckpt_name"] = f"{model_name}.safetensors"

    # 프롬프트 설정
    workflow["3"]["inputs"]["text"] = prompt

    # 샘플링 파라미터 설정
    workflow["5"]["inputs"]["seed"] = seed
    workflow["5"]["inputs"]["steps"] = steps
    workflow["5"]["inputs"]["cfg"] = guidance_scale
    workflow["5"]["inputs"]["denoise"] = strength

    return workflow


def update_workflow_inputs(
    workflow: Dict[str, Any],
    experiment_id: str,
    prompt: str,
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
        prompt: 편집 프롬프트
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
        # 프롬프트 설정 (노드 4)
        if "4" in workflow:
            workflow["4"]["inputs"]["text"] = prompt

        # KSampler 설정 (노드 6)
        if "6" in workflow:
            workflow["6"]["inputs"]["seed"] = seed
            workflow["6"]["inputs"]["steps"] = steps
            workflow["6"]["inputs"]["cfg"] = guidance_scale
            workflow["6"]["inputs"]["denoise"] = strength

    elif experiment_id == "ben2_qwen_image":
        # 프롬프트 설정 (노드 4)
        if "4" in workflow:
            workflow["4"]["inputs"]["text"] = prompt

        # Qwen-Image 생성 설정 (노드 5)
        if "5" in workflow:
            workflow["5"]["inputs"]["steps"] = steps
            workflow["5"]["inputs"]["guidance_scale"] = guidance_scale
            workflow["5"]["inputs"]["strength"] = strength

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
