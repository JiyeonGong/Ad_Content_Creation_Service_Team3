import os
import sys
import yaml
import torch
import numpy as np
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple, List
from PIL import Image
import argparse
from datetime import datetime
import traceback
import gc

from diffusers import FluxPipeline
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from accelerate import Accelerator
import torch.nn.functional as F


# ============================================================================
# 로깅 설정
# ============================================================================
def setup_logging(log_dir: str, file_only: bool = False) -> logging.Logger:
    """
    로깅 설정
    
    Args:
        log_dir: 로그 파일이 저장될 디렉토리
        file_only: True면 파일만 저장, False면 콘솔+파일 모두
    """
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거 (중복 방지)
    logger.handlers = []
    
    # 파일 핸들러 - INFO 레벨만 저장
    log_file = os.path.join(log_dir, f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.INFO)
    
    # 콘솔 핸들러 - 선택사항
    if not file_only:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        logger.addHandler(ch)
    
    # 포매터
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    
    logger.addHandler(fh)
    
    return logger


# ============================================================================
# 데이터셋
# ============================================================================
class ImageLoraDataset(Dataset):
    """이미지 LoRA 학습 데이터셋"""
    
    def __init__(self, image_dir: str, resolution: int = 512, logger: logging.Logger = None):
        self.image_dir = Path(image_dir)
        self.resolution = resolution
        self.logger = logger or logging.getLogger(__name__)
        
        # 지원 확장자
        self.supported_exts = {'*.jpg', '*.png', '*.jpeg', '*.JPG', '*.PNG', '*.JPEG'}
        
        # 이미지 파일 수집
        self.image_paths = []
        for ext in self.supported_exts:
            self.image_paths.extend(self.image_dir.glob(ext))
        
        if not self.image_paths:
            raise ValueError(f"No images found in {image_dir}")
        
        self.image_paths = sorted(self.image_paths)
        self.logger.info(f"Found {len(self.image_paths)} images in {image_dir}")
        
        # 이미지 변환
        self.transform = transforms.Compose([
            transforms.Resize((resolution, resolution), interpolation=transforms.InterpolationMode.LANCZOS),
            transforms.CenterCrop(resolution),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5])
        ])
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        
        try:
            img = Image.open(img_path).convert("RGB")
            return self.transform(img)
        except Exception as e:
            self.logger.warning(f"Error loading image {img_path}: {e}")
            # 폴백: 임의의 다른 이미지 선택
            fallback_idx = np.random.randint(0, len(self))
            if fallback_idx == idx:
                fallback_idx = (idx + 1) % len(self)
            return self.__getitem__(fallback_idx)


# ============================================================================
# 설정 로드 및 검증
# ============================================================================
def load_and_validate_config(config_path: str) -> Dict:
    """YAML 설정 로드 및 검증"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 필수 키 검증
    required_keys = {
        'model': ['pretrained_model'],
        'training': ['batch_size', 'num_epochs', 'learning_rate'],
        'lora': ['r', 'alpha'],
        'output': ['lora_weights_dir'],
        'dataset': ['path']
    }
    
    for section, keys in required_keys.items():
        if section not in config:
            raise KeyError(f"Missing section: {section}")
        for key in keys:
            if key not in config[section]:
                raise KeyError(f"Missing key: {section}.{key}")
    
    # 경로 검증
    model_path = config['model']['pretrained_model']
    dataset_path = config['dataset']['path']
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model path not found: {model_path}")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset path not found: {dataset_path}")
    
    return config


def setup_lora_weights(model, rank: int = 8, logger: logging.Logger = None) -> int:
    """LoRA 가중치 초기화"""
    logger = logger or logging.getLogger(__name__)
    lora_count = 0
    
    for name, module in model.named_modules():
        if hasattr(module, 'weight') and module.weight is not None:
            if any(x in name for x in ['to_k', 'to_v', 'to_q', 'to_out']):
                try:
                    in_features = module.weight.shape[1]
                    out_features = module.weight.shape[0]
                    
                    lora_a = torch.nn.Parameter(
                        torch.randn(rank, in_features) * 0.02
                    )
                    lora_b = torch.nn.Parameter(
                        torch.zeros(out_features, rank)
                    )
                    
                    module.register_parameter('lora_a', lora_a)
                    module.register_parameter('lora_b', lora_b)
                    lora_count += 1
                except Exception as e:
                    logger.warning(f"Failed to add LoRA to {name}: {e}")
    
    logger.info(f"LoRA weights initialized for {lora_count} layers")
    return lora_count


def compute_loss(model_pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """손실함수 계산"""
    if model_pred.shape != target.shape:
        raise ValueError(f"Shape mismatch: {model_pred.shape} vs {target.shape}")
    return F.mse_loss(model_pred, target, reduction='mean')


def generate_final_images(
    pipeline: FluxPipeline,
    output_dir: str,
    logger: logging.Logger = None,
    prompts: list = None,
    device: str = "cuda"
) -> None:
    """학습 완료 후 최종 이미지 생성"""
    logger = logger or logging.getLogger(__name__)
    
    if prompts is None:
        prompts = [
            "professional photo of a yoga studio",
            "pilates studio with reformers",
            "modern gym with equipment"
        ]
    
    final_images_dir = Path(output_dir) / "generated_images"
    final_images_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("\n" + "=" * 70)
    logger.info("🎨 Generating Final Images with Trained LoRA Model")
    logger.info("=" * 70)
    
    try:
        with torch.no_grad():
            for idx, prompt in enumerate(prompts):
                try:
                    logger.info(f"\n📸 Generating image {idx+1}/{len(prompts)}")
                    logger.info(f"   Prompt: {prompt}")
                    
                    image = pipeline(
                        prompt=prompt,
                        height=512,
                        width=512,
                        guidance_scale=7.5,
                        num_inference_steps=20,
                        max_sequence_length=512
                    ).images[0]
                    
                    # 카테고리별로 파일명 설정
                    if idx < 3:
                        category = "yoga_studio"
                    elif idx < 6:
                        category = "pilates_studio"
                    else:
                        category = "gym"
                    
                    save_path = final_images_dir / f"{category}_{idx%3+1:02d}.png"
                    image.save(str(save_path))
                    logger.info(f"   ✅ Saved: {save_path.name}")
                    
                except Exception as e:
                    logger.error(f"   ❌ Error generating image: {e}")
        
        # GPU 메모리 정리
        torch.cuda.empty_cache()
        
        logger.info("\n" + "=" * 70)
        logger.info(f"✅ All images generated and saved to:")
        logger.info(f"   {final_images_dir}")
        logger.info("=" * 70 + "\n")
        
    except Exception as e:
        logger.error(f"Error during final image generation: {e}")
        raise


def save_validation_images(
    pipeline: FluxPipeline,
    epoch: int,
    output_dir: str,
    logger: logging.Logger = None,
    prompts: list = None,
    device: str = "cuda"
):
    """검증 이미지 생성 및 저장"""
    logger = logger or logging.getLogger(__name__)
    
    if prompts is None:
        prompts = [
            "a professional photograph",
            "studio portrait lighting",
            "high quality headshot"
        ]
    
    validation_dir = Path(output_dir) / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with torch.no_grad():
            for idx, prompt in enumerate(prompts):
                try:
                    image = pipeline(
                        prompt=prompt,
                        height=512,
                        width=512,
                        guidance_scale=7.5,
                        num_inference_steps=20,
                        max_sequence_length=512
                    ).images[0]
                    
                    save_path = validation_dir / f"epoch_{epoch:03d}_prompt_{idx:02d}.png"
                    image.save(str(save_path))
                    logger.info(f"Validation image saved: {save_path.name}")
                    
                except Exception as e:
                    logger.error(f"Error generating validation image with prompt '{prompt}': {e}")
        
        # GPU 메모리 정리
        torch.cuda.empty_cache()
        
    except Exception as e:
        logger.error(f"Error during validation: {e}")


def train_lora(config: Dict, accelerator: Accelerator, logger: logging.Logger):
    """LoRA 학습 메인 함수"""
    
    try:
        # 설정 파싱
        model_path = config['model']['pretrained_model']
        dataset_path = config['dataset']['path']
        output_dir = config['output']['lora_weights_dir']
        
        batch_size = int(config['training']['batch_size'])
        num_epochs = int(config['training']['num_epochs'])
        learning_rate = float(config['training']['learning_rate'])
        resolution = int(config['training'].get('resolution', 512))
        max_grad_norm = float(config['training'].get('max_grad_norm', 1.0))
        
        rank = int(config['lora']['r'])
        alpha = int(config['lora'].get('alpha', rank * 2))
        
        # 안전한 고정값
        steps_per_epoch = 30
        log_interval = 5
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(f"{output_dir}/checkpoints", exist_ok=True)
        os.makedirs(f"{output_dir}/logs", exist_ok=True)
        
        logger.info("=" * 70)
        logger.info("🚀 FLUX LoRA Training Started")
        logger.info("=" * 70)
        logger.info(f"Model: {model_path}")
        logger.info(f"Dataset: {dataset_path}")
        logger.info(f"Output: {output_dir}")
        logger.info(f"Configuration: {num_epochs} epochs × {steps_per_epoch} steps")
        logger.info(f"Batch size: {batch_size}, Learning rate: {learning_rate}")
        logger.info(f"LoRA Rank: {rank}, Alpha: {alpha}")
        logger.info("=" * 70)
        
        # 모델 로드 (양자화 선택 가능)
        logger.info("Loading model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # yaml에서 precision 설정 읽기
        precision = config['training'].get('precision', 'fp8')  # 기본값: fp8
        
        try:
            if device == "cuda":
                if precision == "fp8":
                    torch_dtype = torch.float8_e4m3fn
                    logger.info("📊 Using fp8 quantization (6-8GB, optimal for 24GB VRAM)")
                elif precision == "bf16":
                    torch_dtype = torch.bfloat16
                    logger.info("📊 Using bf16 quantization (12GB, may have memory issues)")
                elif precision == "fp32":
                    torch_dtype = torch.float32
                    logger.warning("⚠️  Using fp32 (24GB, likely to cause OOM on 24GB GPU!)")
                else:
                    raise ValueError(f"Unknown precision: {precision}")
            else:
                torch_dtype = torch.float32
            
            pipeline = FluxPipeline.from_pretrained(
                model_path,
                torch_dtype=torch_dtype,
                device_map=device
            )
            logger.info(f"✅ Model loaded successfully (device: {device}, precision: {precision})")
            
            # 메모리 상태 확인
            if device == "cuda":
                used_memory = torch.cuda.memory_allocated() / 1e9
                total_memory = torch.cuda.get_device_properties(device).total_memory / 1e9
                logger.info(f"💾 GPU Memory: {used_memory:.1f}GB / {total_memory:.1f}GB")
                
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
        
        # LoRA 가중치 초기화
        logger.info("Initializing LoRA weights...")
        lora_count = setup_lora_weights(pipeline.transformer, rank=rank, logger=logger)
        
        if lora_count == 0:
            raise RuntimeError("No LoRA layers created!")
        
        # LoRA 파라미터 수집
        lora_params = []
        for name, param in pipeline.transformer.named_parameters():
            if 'lora_' in name:
                param.requires_grad = True
                lora_params.append(param)
            else:
                param.requires_grad = False
        
        logger.info(f"Total trainable parameters: {sum(p.numel() for p in lora_params):,}")
        
        # 옵티마이저
        optimizer = torch.optim.AdamW(
            lora_params,
            lr=learning_rate,
            weight_decay=0.01,
            betas=(0.9, 0.999),
            eps=1e-8
        )
        
        # 데이터셋 로드
        logger.info("Loading dataset...")
        try:
            dataset = ImageLoraDataset(dataset_path, resolution=resolution, logger=logger)
            logger.info(f"✅ Dataset loaded: {len(dataset)} images")
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise
        
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=0,
            pin_memory=True if device == "cuda" else False,
            drop_last=True
        )
        
        # Accelerator 준비
        pipeline.transformer, optimizer = accelerator.prepare(
            pipeline.transformer, optimizer
        )
        
        # 학습 루프
        logger.info("\n" + "=" * 70)
        logger.info("Starting training...")
        logger.info("=" * 70 + "\n")
        
        total_steps = 0
        all_losses = []
        
        for epoch in range(num_epochs):
            epoch_losses = []
            logger.info(f"\n--- Epoch {epoch+1}/{num_epochs} ---")
            
            for step, batch in enumerate(dataloader):
                if step >= steps_per_epoch:
                    break
                
                try:
                    batch = batch.to(device)
                    
                    with torch.autocast(device_type=device, enabled=device == "cuda"):
                        # 노이즈 및 타임스텝 생성
                        noise = torch.randn_like(batch)
                        timesteps = torch.randint(
                            0, 1000,
                            (batch.shape[0],),
                            device=device
                        )
                        
                        # 노이즈 스케줄
                        alpha_t = torch.sqrt(1 - timesteps.float() / 1000)
                        sigma_t = torch.sqrt(timesteps.float() / 1000)
                        
                        alpha_t = alpha_t.view(-1, 1, 1, 1)
                        sigma_t = sigma_t.view(-1, 1, 1, 1)
                        
                        noisy_latents = alpha_t * batch + sigma_t * noise
                        
                        # 모델 예측
                        # 주의: 실제 FLUX 모델은 추가 인자(text embeddings 등)가 필요할 수 있음
                        model_pred = pipeline.transformer(
                            noisy_latents,
                            timestep=timesteps
                        ).sample
                        
                        # 손실 계산
                        loss = compute_loss(model_pred, noise)
                    
                    # Backward pass
                    accelerator.backward(loss)
                    
                    # 그래디언트 클리핑
                    if accelerator.sync_gradients:
                        accelerator.clip_grad_norm_(lora_params, max_grad_norm)
                    
                    optimizer.step()
                    optimizer.zero_grad()
                    
                    total_steps += 1
                    loss_item = loss.item()
                    epoch_losses.append(loss_item)
                    all_losses.append(loss_item)
                    
                    # 로그 출력
                    if (step + 1) % log_interval == 0:
                        avg_loss = np.mean(epoch_losses[-log_interval:])
                        logger.info(
                            f"Step [{step+1:3d}/{steps_per_epoch}] "
                            f"Loss: {loss_item:.6f} | Avg: {avg_loss:.6f}"
                        )
                
                except Exception as e:
                    logger.error(f"Error during training step {step}: {e}")
                    logger.error(traceback.format_exc())
                    raise
            
            # 에폭 완료
            if epoch_losses:
                epoch_avg_loss = np.mean(epoch_losses)
                logger.info(f"✅ Epoch {epoch+1} Complete - Avg Loss: {epoch_avg_loss:.6f}")
            
            # 검증 이미지 생성
            try:
                # yaml에서 프롬프트 읽기
                validation_prompts = config.get('validation', {}).get('prompts', None)
                
                save_validation_images(
                    pipeline,
                    epoch + 1,
                    output_dir,
                    logger=logger,
                    prompts=validation_prompts,
                    device=device
                )
            except Exception as e:
                logger.error(f"Error during validation: {e}")
            
            # 체크포인트 저장
            try:
                checkpoint_path = f"{output_dir}/checkpoints/epoch_{epoch+1:03d}"
                os.makedirs(checkpoint_path, exist_ok=True)
                
                lora_state = {}
                for name, param in pipeline.transformer.named_parameters():
                    if 'lora_' in name:
                        lora_state[name] = param.cpu().detach()
                
                torch.save(lora_state, f"{checkpoint_path}/lora_weights.pt")
                logger.info(f"💾 Checkpoint saved: {checkpoint_path}")
                
            except Exception as e:
                logger.error(f"Error saving checkpoint: {e}")
        
        # 최종 LoRA 모델 저장
        logger.info("\n" + "=" * 70)
        logger.info("🎉 Training Complete!")
        logger.info("=" * 70)
        
        try:
            final_path = f"{output_dir}/final_model"
            os.makedirs(final_path, exist_ok=True)
            
            final_lora_state = {}
            for name, param in pipeline.transformer.named_parameters():
                if 'lora_' in name:
                    final_lora_state[name] = param.cpu().detach()
            
            torch.save(final_lora_state, f"{final_path}/lora_weights.pt")
            
            # 메타데이터 저장
            import json
            metadata = {
                'rank': rank,
                'alpha': alpha,
                'epochs': num_epochs,
                'total_steps': total_steps,
                'final_loss': float(np.mean(all_losses[-10:]) if all_losses else 0),
                'training_date': datetime.now().isoformat(),
                'model_path': model_path
            }
            
            with open(f"{final_path}/metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"✅ Final model saved: {final_path}")
            logger.info(f"📊 Total steps: {total_steps}")
            logger.info(f"📉 Final loss: {np.mean(all_losses[-10:]):.6f}")
            
        except Exception as e:
            logger.error(f"Error saving final model: {e}")
            raise
        
        # ✨ 학습된 LoRA로 최종 이미지 생성
        try:
            final_generation_prompts = config.get('validation', {}).get('prompts', None)
            
            generate_final_images(
                pipeline,
                output_dir,
                logger=logger,
                prompts=final_generation_prompts,
                device=device
            )
        except Exception as e:
            logger.error(f"Error generating final images: {e}")
        
        # GPU 메모리 정리
        torch.cuda.empty_cache()
        gc.collect()
        
        logger.info("=" * 70)
        logger.info("Training finished successfully!")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"\n{'='*70}")
        logger.error(f"❌ Training failed: {e}")
        logger.error(traceback.format_exc())
        logger.error(f"{'='*70}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="FLUX LoRA Training Script",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--config",
        type=str,
        default="train_flux_lora.yaml",
        help="Path to training config file"
    )
    
    args = parser.parse_args()
    
    try:
        # 설정 로드 및 검증
        config = load_and_validate_config(args.config)
        
        # 로깅 설정
        log_dir = config['output'].get('log_dir', './logs')
        logger = setup_logging(log_dir, file_only=False)
        
        logger.info(f"Loading config from: {args.config}")
        
        # Accelerator 초기화
        precision = config['training'].get('precision', 'fp8')
        
        if precision == "fp8":
            mixed_precision = "no"  # fp8 이미 양자화되어 있음
        elif precision == "bf16":
            mixed_precision = "bf16"
        else:  # fp32
            mixed_precision = "no"
        
        accelerator = Accelerator(mixed_precision=mixed_precision)
        
        # 학습 시작
        train_lora(config, accelerator, logger)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()