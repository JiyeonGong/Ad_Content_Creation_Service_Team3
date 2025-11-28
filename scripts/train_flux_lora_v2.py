#!/usr/bin/env python3
"""
FLUX.1-dev LoRA 학습 - V2: device_map 제거 및 명시적 GPU 이동 최적화

사용법:
  python scripts/train_flux_lora_gcp_v2.py --config configs/train_flux_lora.yaml
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

# ---------- 로깅 설정 ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("flux-lora-train")


# ---------- 핵패치: CombinedTimestepGuidanceTextProjEmbeddings 안전 패치 ----------
def apply_nuclear_patch():
    try:
        from diffusers.models.embeddings import CombinedTimestepGuidanceTextProjEmbeddings
        def safe_forward(self, timestep, guidance=None, pooled_projection=None):
            pooled = pooled_projection if pooled_projection is not None else guidance
            t_vec = self.time_proj(timestep) if hasattr(self, "time_proj") else timestep
            if hasattr(self, "linear_1"):
                t_proj = self.linear_1(t_vec)
            elif hasattr(self, "timestep_embedder"):
                t_proj = self.timestep_embedder(t_vec)
            else:
                t_proj = torch.zeros((t_vec.shape[0], 3072), device=t_vec.device, dtype=t_vec.dtype)
            
            g_proj = getattr(self, "guidance_proj", getattr(self, "guidance_embedder", lambda x: 0))(guidance) if guidance is not None and guidance.dim() > 0 else 0
            text_proj = getattr(self, "text_proj", getattr(self, "text_embedder", lambda x: 0))(pooled) if pooled is not None and pooled.dim() > 0 else 0
            
            try:
                return t_proj + g_proj + text_proj
            except Exception:
                return t_proj
        CombinedTimestepGuidanceTextProjEmbeddings.forward = safe_forward
        logger.info("☢️ Nuclear patch applied.")
    except Exception as e:
        logger.warning(f"Nuclear patch failed: {e}. Skipping.")

# ---------- Dataset ----------
class SimpleImageCaptionDataset(Dataset):
    def __init__(self, data_dir: str, image_size: int = 512, caption_ext: str = ".txt"):
        self.data_dir = Path(data_dir)
        self.image_size = int(image_size)
        exts = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
        self.items = []
        for img_path in self.data_dir.rglob("*"):
            if img_path.suffix.lower() in exts:
                cap_path = img_path.with_suffix(caption_ext)
                if cap_path.exists():
                    self.items.append((img_path, cap_path))
        
        if len(self.items) == 0:
            raise ValueError(f"No matched image/caption pairs found under {data_dir}")
        logger.info(f"Dataset: {len(self.items)} image/caption pairs found.")

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        # ... (이전 코드와 동일한 이미지/캡션 로드 로직)
        img_path, cap_path = self.items[idx]
        try:
            img = Image.open(str(img_path)).convert("RGB")
            img = img.resize((self.image_size, self.image_size))
            arr = np.array(img).astype(np.float32) / 255.0
            tensor = torch.from_numpy(arr).permute(2, 0, 1) # C,H,W

            with open(cap_path, 'r', encoding='utf-8') as f:
                prompt = f.read().strip()
                if not prompt: prompt = "default fine-tuning prompt"
            
            return {"pixel_values": tensor, "prompt": prompt}
        except Exception as e:
            logger.warning(f"Error processing {img_path}: {e}. Returning next item.")
            return self.__getitem__((idx + 1) % len(self.items))


# ---------- Small helpers (safe_to_device 강화) ----------
def safe_to_device(module: nn.Module, device: str, dtype: torch.dtype = None, name: str = None):
    """모듈을 명시적으로 GPU로 이동 (오류 회피 목적)"""
    try:
        # 1. 모든 파라미터를 명시된 장치로 이동
        module = module.to(device)
        # 2. dtype 변경 (주로 bfloat16 적용)
        if dtype is not None:
            module = module.to(dtype=dtype)
        logger.debug(f"Moved module {name or ''} to {device} and dtype {dtype}")
    except Exception as e:
        logger.warning(f"Failed moving {name} to {device}/{dtype}: {e}. Trying parameter-wise move.")
        try:
            # Fallback: 개별 파라미터 이동
            for n, p in module.named_parameters():
                if p.device != torch.device(device):
                    p.data = p.data.to(device)
            if dtype is not None:
                module = module.to(dtype=dtype)
        except Exception as e2:
             logger.error(f"FATAL: Final device move attempt failed for {name}: {e2}")
             raise RuntimeError(f"Cannot move component {name} to GPU. Check VRAM or library versions.")
    return module


# ---------- Text Encoder helper ----------
class TextEncoderManager:
    # ... (이전 코드와 동일)
    def __init__(self, pipeline: FluxPipeline, device: str, dtype: torch.dtype):
        self.pipe = pipeline
        self.device = device
        self.dtype = dtype

    @torch.no_grad()
    def encode(self, prompts: List[str]) -> tuple:
        clip_tokens = self.pipe.tokenizer(prompts, padding="max_length", truncation=True, max_length=77, return_tensors="pt").to(self.device)
        clip_out = self.pipe.text_encoder(clip_tokens.input_ids)
        clip_pooled = clip_out.pooler_output.to(self.dtype)
        clip_seq = clip_out.last_hidden_state.to(self.dtype)
        
        t5_tokens = self.pipe.tokenizer_2(prompts, padding="max_length", truncation=True, max_length=256, return_tensors="pt").to(self.device)
        t5_out = self.pipe.text_encoder_2(input_ids=t5_tokens.input_ids)
        t5_seq = t5_out.last_hidden_state.to(self.dtype)
        
        return clip_seq, clip_pooled, t5_seq


# ---------- LoRA manager / ForwardPassTester / train_loop / load_config (이전 코드와 동일) ----------
class LoRAManager:
    @staticmethod
    def apply_lora(transformer: nn.Module, r: int = 8, alpha: int = 16, target_modules=None):
        if target_modules is None: target_modules = ["to_q", "to_k", "to_v", "to_out.0"] 
        cfg = LoraConfig(r=r, lora_alpha=alpha, target_modules=target_modules, lora_dropout=0.1, bias="none")
        logger.info(f"Applying LoRA r={r}, alpha={alpha} to {target_modules}")
        lora_mod = get_peft_model(transformer, cfg)
        lora_mod.print_trainable_parameters()
        return lora_mod

    @staticmethod
    def freeze_base(pipeline: FluxPipeline):
        for comp_name in ("vae", "text_encoder", "text_encoder_2"):
            mod = getattr(pipeline, comp_name, None)
            if mod is None: continue
            for p in mod.parameters():
                p.requires_grad = False
        logger.info("Frozen VAE and Text Encoders.")

class ForwardPassTester:
    @staticmethod
    def test_forward(pipeline: FluxPipeline, device: str, dtype: torch.dtype) -> bool:
        try:
            logger.info("Starting Forward Pass Test...")
            # 더미 데이터 (Latent, Text Seq, Pooled)
            lat = torch.randn(1, 4, 32, 32, device=device, dtype=dtype)
            pooled = torch.zeros(1, 768, device=device, dtype=dtype)
            t5_seq = torch.zeros(1, 256, 4096, device=device, dtype=dtype)
            
            kwargs = dict(
                hidden_states=lat, timestep=torch.zeros(1, device=device, dtype=dtype),
                pooled_projections=pooled, encoder_hidden_states=t5_seq,
                txt_ids=torch.zeros(1, 256, 3, device=device, dtype=torch.long),
                img_ids=torch.zeros(1, 32*32, 3, device=device, dtype=torch.long),
                return_dict=True
            )
            _ = pipeline.transformer(**kwargs)
            logger.info("✅ Forward Pass Test Succeeded.")
            return True
        except Exception as e:
            logger.exception(f"❌ Forward Pass Test Failed: {e}")
            return False

def train_loop(pipeline: FluxPipeline, lora_model: nn.Module, dataloader: DataLoader, optimizer, 
               num_epochs: int, device: str, dtype: torch.dtype, cfg: Dict[str, Any]):
    cfg_save_every_steps = cfg.get("save_every_n_steps", 50)
    max_steps_per_epoch = cfg.get("max_steps_per_epoch", 999999) # config에서 가져옴
    
    vae = pipeline.vae
    text_mgr = TextEncoderManager(pipeline, device, dtype)
    lora_model.train()
    vae.eval()
    
    for epoch in range(num_epochs):
        logger.info(f"\n📖 Epoch {epoch+1}/{num_epochs} start")
        epoch_loss = 0.0
        steps_done = 0
        
        for step, batch in enumerate(dataloader):
            if steps_done >= max_steps_per_epoch: break

            try:
                pixel_values = batch["pixel_values"].to(device=vae.parameters().__next__().device, dtype=torch.float32)
                prompts = batch["prompt"]
                bsz = pixel_values.shape[0]

                # 1) Encode (no_grad)
                with torch.no_grad():
                    clip_seq, clip_pooled, t5_seq = text_mgr.encode(prompts)
                    clip_pooled = clip_pooled.repeat(bsz, 1)
                    t5_seq = t5_seq.repeat(bsz, 1, 1)

                    latents = vae.encode(pixel_values).latent_dist.sample().to(dtype)
                    latents = latents * getattr(vae.config, "scaling_factor", 0.18215)

                # 2) Noise & Timestep
                noise = torch.randn_like(latents).to(dtype)
                u = torch.rand(bsz, device=device, dtype=dtype)
                noisy_latents = (1.0 - u.view(-1, 1, 1, 1)) * latents + u.view(-1, 1, 1, 1) * noise
                
                # 3) IDS (Image/Text)
                _, _, h, w = latents.shape
                img_ids = torch.zeros((h, w, 3), device=device, dtype=torch.long)
                img_ids[..., 1] = torch.arange(h, device=device)[:, None]
                img_ids[..., 2] = torch.arange(w, device=device)[None, :]
                img_ids = img_ids.reshape(1, -1, 3).repeat(bsz, 1, 1)

                txt_seq_len = t5_seq.shape[1]
                txt_ids = torch.zeros((bsz, txt_seq_len, 3), device=device, dtype=torch.long)
                txt_ids[..., 1] = torch.arange(txt_seq_len, device=device)

                # 4) Forward
                out = lora_model(
                    hidden_states=noisy_latents, timestep=u, pooled_projections=clip_pooled, 
                    encoder_hidden_states=t5_seq, txt_ids=txt_ids, img_ids=img_ids,
                )
                pred = out.sample if hasattr(out, "sample") else out[0]
                
                # 5) Loss
                loss = F.mse_loss(pred.float(), (noise - latents).float(), reduction="mean")

                # 6) Backward
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(lora_model.parameters(), max_norm=1.0)
                optimizer.step()

                epoch_loss += loss.item()
                steps_done += 1

                if steps_done % cfg_save_every_steps == 0:
                    logger.info(f"[Epoch {epoch+1}] Step {steps_done} Loss: {loss.item():.6f}")

                gc.collect()
                if torch.cuda.is_available(): torch.cuda.empty_cache()

            except Exception as e:
                logger.exception(f"❌ Error in training step {steps_done}: {e}")
                continue

        avg_loss = epoch_loss / max(1, steps_done)
        logger.info(f"✅ Epoch {epoch+1} finished - Avg Loss: {avg_loss:.6f}")

    return lora_model

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg


# ---------- Flux Model Loader (device_map 제거) ----------
class FluxModelLoader:
    def __init__(self, device: str, dtype: torch.dtype):
        self.device = device
        self.dtype = dtype

    def load(self, pretrained_path: str) -> FluxPipeline:
        logger.info(f"Loading local FluxPipeline from: {pretrained_path} (No device_map)")
        # ⭐️ device_map 옵션 제거
        pipe = FluxPipeline.from_pretrained(
            pretrained_path, 
            local_files_only=True,
            torch_dtype=self.dtype,
        )
        logger.info("FluxPipeline loaded into CPU memory (or default).")
        return pipe


# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/train_flux_lora.yaml", help="Path to the config YAML file.")
    args = parser.parse_args()

    cfg_all = load_config(args.config)
    
    model_cfg = cfg_all.get("model", {})
    training_cfg = cfg_all.get("training", {})
    lora_cfg = cfg_all.get("lora", {})
    output_cfg = cfg_all.get("output", {})
    dataset_cfg = cfg_all.get("dataset", {})

    # 설정 변수
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
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if (dtype_name == "bf16" and torch.cuda.is_bf16_supported()) else torch.float16
    
    logger.info(f"--- Training Configuration ---")
    logger.info(f"Device: {device}, DType: {dtype}, LR: {lr}")

    # 1. 핵 패치 적용
    apply_nuclear_patch()

    # 2. 파이프라인 로드 (CPU 로드)
    loader = FluxModelLoader(device=device, dtype=dtype)
    pipeline = loader.load(pretrained_model)
    
    # 3. LoRA 적용 및 Freeze
    LoRAManager.freeze_base(pipeline)
    lora_model = LoRAManager.apply_lora(pipeline.transformer, r=lora_r, alpha=lora_alpha)
    pipeline.transformer = lora_model

    # 4. ⭐️ 명시적 디바이스 이동 (오류 회피 핵심)
    # VAE (Float32 유지)
    pipeline.vae = safe_to_device(pipeline.vae, device, dtype=torch.float32, name="vae")
    # 인코더 (Bfloat16/Target DType 적용)
    pipeline.text_encoder = safe_to_device(pipeline.text_encoder, device, dtype=dtype, name="text_encoder_1")
    pipeline.text_encoder_2 = safe_to_device(pipeline.text_encoder_2, device, dtype=dtype, name="text_encoder_2")
    # Transformer/LoRA (Bfloat16/Target DType 적용)
    pipeline.transformer = safe_to_device(pipeline.transformer, device, dtype=dtype, name="transformer-lora")

    # 5. 포워드 테스트
    ok = ForwardPassTester.test_forward(pipeline, device, dtype)
    if not ok:
        logger.error("Forward test failed. Abort training.")
        return

    # 6. 데이터 로드 및 옵티마이저
    dataset = SimpleImageCaptionDataset(dataset_path, image_size)
    # num_workers를 0으로 설정하여 데이터 로드 관련 오류 가능성 최소화
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=True)
    
    trainable_params = [p for p in pipeline.transformer.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=lr)

    # 7. 학습 실행
    trained_lora = train_loop(
        pipeline, pipeline.transformer, dataloader, optimizer, 
        num_epochs=num_epochs, device=device, dtype=dtype, cfg=training_cfg
    )

    # 8. LoRA 가중치 저장
    os.makedirs(output_dir, exist_ok=True)
    try:
        trained_lora.save_pretrained(output_dir)
        logger.info(f"✨ LoRA weights saved to {output_dir}")
    except Exception as e:
        logger.exception(f"❌ Failed to save LoRA: {e}")

    logger.info("--- Training finished. ---")


if __name__ == "__main__":
    main()