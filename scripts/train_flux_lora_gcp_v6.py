#!/usr/bin/env python3
"""
FLUX.1-dev LoRA 학습 - V6: DeepSpeed VAE/TextEncoder 강제 통합 및 to(device) 제거

VRAM 부족 및 디바이스 불일치 오류를 완전히 방지하기 위해, 
VAE와 Text Encoder까지 DeepSpeed의 prepare 관리 하에 두어 메모리 관리를 자동화합니다.
"""

import os
import argparse
import logging
import gc
from pathlib import Path
from typing import List, Dict, Any

import yaml
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from PIL import Image

from peft import LoraConfig, get_peft_model
from diffusers import FluxPipeline
from accelerate import Accelerator

# ---------- 로깅 설정 ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("flux-lora-train")

# (이전 코드와 동일한 apply_nuclear_patch, SimpleImageCaptionDataset, LoRAManager, ForwardPassTester, load_config 코드를 여기에 삽입해 주세요.)
# ********************************************************************************

# ---------- Small helpers (VRAM 부족 시도 회피를 위해 V5에서 사용된 함수 유지) ----------
def safe_to_device(module: nn.Module, device: str, dtype: torch.dtype = None, name: str = None):
    """DeepSpeed prepare 전에 LoRA 모듈을 GPU로 이동"""
    try:
        module = module.to(device)
        if dtype is not None:
            module = module.to(dtype=dtype)
        logger.info(f"Successfully moved trainable module ({name}) to {device}/{dtype}")
    except Exception as e:
        logger.error(f"FATAL: Failed to move trainable component {name} to GPU: {e}")
        raise RuntimeError(f"Cannot move component {name} to GPU. Check VRAM or library versions.")
    return module

# ---------- Text Encoder helper (V6: to(device) 제거, Accelerator에 의존) ----------
class TextEncoderManager:
    """Accelerator에 래핑된 인코더를 사용하여 인코딩"""
    def __init__(self, pipeline: FluxPipeline, device: str, dtype: torch.dtype):
        self.pipe = pipeline
        self.device = device
        self.dtype = dtype

    @torch.no_grad()
    def encode(self, prompts: List[str]) -> tuple:
        # ⭐️ V6 변경: 모든 to(device) 호출을 제거합니다. 
        # DeepSpeed prepare가 이미 컴포넌트를 관리하고 있으므로, 
        # 입력 텐서만 현재 장치(self.device)로 옮기면 됩니다.
        
        # 1. CLIP (Text Encoder 1)
        # tokenizer는 DeepSpeed 래핑 대상이 아니므로 입력만 장치로 옮김
        clip_tokens = self.pipe.tokenizer(prompts, padding="max_length", truncation=True, max_length=77, return_tensors="pt").to(self.device)
        self.pipe.text_encoder.eval() 
        clip_out = self.pipe.text_encoder(clip_tokens.input_ids)
        clip_pooled = clip_out.pooler_output.to(self.dtype)
        clip_seq = clip_out.last_hidden_state.to(self.dtype)
        
        # 2. T5 (Text Encoder 2)
        t5_tokens = self.pipe.tokenizer_2(prompts, padding="max_length", truncation=True, max_length=256, return_tensors="pt").to(self.device)
        self.pipe.text_encoder_2.eval()
        t5_out = self.pipe.text_encoder_2(input_ids=t5_tokens.input_ids)
        t5_seq = t5_out.last_hidden_state.to(self.dtype)

        return clip_seq, clip_pooled, t5_seq

# ---------- Flux Model Loader (V4/V5와 동일: CPU 로드) ----------
class FluxModelLoader:
    def __init__(self, device: str, dtype: torch.dtype):
        self.device = device
        self.dtype = dtype

    def load(self, pretrained_path: str) -> FluxPipeline:
        pipe = FluxPipeline.from_pretrained(
            pretrained_path, 
            local_files_only=True,
            torch_dtype=self.dtype,
        )
        return pipe


# ---------- Training loop (V6: to(device) 제거, Accelerator 의존) ----------
def train_loop(pipeline: FluxPipeline, lora_model: nn.Module, dataloader: DataLoader, optimizer, 
               num_epochs: int, device: str, dtype: torch.dtype, cfg: Dict[str, Any], accelerator: Accelerator):
    
    cfg_save_every_steps = cfg.get("save_every_n_steps", 50)
    max_steps_per_epoch = cfg.get("max_steps_per_epoch", 999999) 

    logger.info(f"Starting training loop (Epochs: {num_epochs}, Max Steps/Epoch: {max_steps_per_epoch})")
    
    # ⭐️ V6 변경: VAE에 대한 수동 to(device) 호출 제거. Accelerator가 관리합니다.
    pipeline.vae.eval() 
    lora_model.train() 

    for epoch in range(num_epochs):
        # ... (중략)
        for step, batch in enumerate(dataloader):
            # ... (중략)

            try:
                # 1) Encode (no_grad)
                with torch.no_grad():
                    # ⭐️ V6 변경: pixel_values를 Accelerator가 지정한 장치로 옮깁니다.
                    pixel_values = batch["pixel_values"].to(device, dtype=torch.float32)
                    prompts = batch["prompt"]
                    bsz = pixel_values.shape[0]

                    # Text Encoder는 Manager 내에서 이미 올바른 장치를 사용함
                    clip_seq, clip_pooled, t5_seq = pipeline.text_encoder_manager.encode(prompts)
                    clip_pooled = clip_pooled.repeat(bsz, 1)
                    t5_seq = t5_seq.repeat(bsz, 1, 1)
                    
                    # Latent
                    # ⭐️ V6 변경: VAE는 prepare로 래핑되었으므로 to(device) 없이 사용
                    latents = pipeline.vae.encode(pixel_values).latent_dist.sample().to(dtype)
                    latents = latents * getattr(pipeline.vae.config, "scaling_factor", 0.18215)

                # 2) Noise, Timestep, IDS (데이터 텐서는 모두 device로 이동)
                noise = torch.randn_like(latents).to(device).to(dtype)
                u = torch.rand(bsz, device=device, dtype=dtype)
                noisy_latents = (1.0 - u.view(-1, 1, 1, 1)) * latents + u.view(-1, 1, 1, 1) * noise
                
                _, _, h, w = latents.shape
                img_ids = torch.zeros((h, w, 3), device=device, dtype=torch.long)
                img_ids[..., 1] = torch.arange(h, device=device)[:, None]
                img_ids[..., 2] = torch.arange(w, device=device)[None, :]
                img_ids = img_ids.reshape(1, -1, 3).repeat(bsz, 1, 1)

                txt_seq_len = t5_seq.shape[1]
                txt_ids = torch.zeros((bsz, txt_seq_len, 3), device=device, dtype=torch.long)
                txt_ids[..., 1] = torch.arange(txt_seq_len, device=device)

                # 3) Forward (LoRA 모델)
                out = lora_model(
                    hidden_states=noisy_latents, timestep=u, pooled_projections=clip_pooled, 
                    encoder_hidden_states=t5_seq, txt_ids=txt_ids, img_ids=img_ids,
                )
                pred = out.sample if hasattr(out, "sample") else out[0]
                
                # 4) Loss
                loss = F.mse_loss(pred.float(), (noise - latents).float(), reduction="mean")

                # 5) Backward: accelerator.backward 사용
                accelerator.backward(loss)
                
                # 6) Gradient Clipping
                if accelerator.sync_gradients:
                    accelerator.clip_grad_norm_(lora_model.parameters(), 1.0)
                
                # 7) Optimizer Step
                optimizer.step()
                optimizer.zero_grad() 

                epoch_loss += loss.item()
                steps_done += 1

                if accelerator.sync_gradients and steps_done % cfg_save_every_steps == 0:
                    logger.info(f"[Epoch {epoch+1}] Step {steps_done} Loss: {loss.item():.6f}")

                gc.collect()
                if torch.cuda.is_available(): torch.cuda.empty_cache()

            except Exception as e:
                logger.exception(f"❌ Error in training step {steps_done}: {e}")
                continue

        # ... (후략)
    return lora_model


# ---------- Main (V6: 모든 컴포넌트 prepare) ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/train_flux_lora.yaml", help="Path to the config YAML file.")
    args = parser.parse_args()

    # ... (중략: 설정 로드)
    cfg_all = load_config(args.config)
    model_cfg = cfg_all.get("model", {})
    training_cfg = cfg_all.get("training", {})
    lora_cfg = cfg_all.get("lora", {})
    output_cfg = cfg_all.get("output", {})
    dataset_cfg = cfg_all.get("dataset", {})

    pretrained_model = model_cfg.get("pretrained_model")
    dataset_path = dataset_cfg.get("path")
    image_size = dataset_cfg.get("image_size")
    batch_size = training_cfg.get("batch_size")
    num_epochs = training_cfg.get("num_epochs")
    lr = training_cfg.get("learning_rate")
    dtype_name = training_cfg.get("mixed_precision")
    lora_r = lora_cfg.get("r")
    lora_alpha = lora_cfg.get("alpha")
    output_dir = output_cfg.get("lora_weights_dir")
    
    # 1. Accelerator 초기화
    accelerator = Accelerator(mixed_precision=dtype_name)
    device = accelerator.device 
    dtype = torch.bfloat16 if (dtype_name == "bf16" and torch.cuda.is_bf16_supported()) else torch.float16
    
    logger.info(f"Accelerator Initialized. Device: {device}, DType: {dtype}")

    # 2. 핵 패치 적용
    apply_nuclear_patch()

    # 3. 파이프라인 로드 (CPU 로드)
    loader = FluxModelLoader(device=device, dtype=dtype)
    pipeline = loader.load(pretrained_model)
    
    # 4. LoRA 적용 및 Freeze
    LoRAManager.freeze_base(pipeline)
    lora_model = LoRAManager.apply_lora(pipeline.transformer, r=lora_r, alpha=lora_alpha)
    
    # Text Encoder Manager 인스턴스화
    pipeline.text_encoder_manager = TextEncoderManager(pipeline, device, dtype)

    # 5. LoRA 모듈 GPU로 이동 (prepare 전에 수행)
    pipeline.transformer = safe_to_device(lora_model, device, dtype=dtype, name="transformer-lora")

    # 6. 데이터 로드 및 옵티마이저
    dataset = SimpleImageCaptionDataset(dataset_path, image_size)
    # ⭐️ V6 변경: DeepSpeed 충돌 방지를 위해 pin_memory=False로 설정 (기본값)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0) 
    
    trainable_params = [p for p in pipeline.transformer.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=lr)

    # ⭐️ 7. V6 핵심: 모든 컴포넌트(VAE, TE, TE2, Transformer)를 prepare로 래핑
    # 래핑된 컴포넌트는 DeepSpeed의 메모리 관리 하에 놓여 디바이스 불일치를 완벽히 방지합니다.
    (
        pipeline.vae, 
        pipeline.text_encoder, 
        pipeline.text_encoder_2, 
        pipeline.transformer, 
        optimizer, 
        dataloader
    ) = accelerator.prepare(
        pipeline.vae, 
        pipeline.text_encoder, 
        pipeline.text_encoder_2, 
        pipeline.transformer, 
        optimizer, 
        dataloader
    )
    
    # 8. 포워드 테스트 (prepare 이후)
    # (ForwardPassTester 로직은 여기서 생략하거나, prepare된 모델로 테스트할 수 있음)
    
    # 9. 학습 실행
    trained_lora = train_loop(
        pipeline, pipeline.transformer, dataloader, optimizer, 
        num_epochs=num_epochs, device=device, dtype=dtype, cfg=training_cfg,
        accelerator=accelerator 
    )

    # 10. LoRA 가중치 저장
    os.makedirs(output_dir, exist_ok=True)
    try:
        lora_to_save = accelerator.unwrap_model(trained_lora)
        lora_to_save.save_pretrained(output_dir)
        logger.info(f"✨ LoRA weights saved to {output_dir}")
    except Exception as e:
        logger.exception(f"❌ Failed to save LoRA: {e}")

    logger.info("--- Training finished. ---")


if __name__ == "__main__":
    # main()
    pass # 실제 실행 시 main() 호출