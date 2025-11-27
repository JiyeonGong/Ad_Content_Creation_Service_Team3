#!/usr/bin/env python3
"""
T5XXL GGUF 모델 다운로드 스크립트
"""
from huggingface_hub import hf_hub_download
import os

# 다운로드 경로
clip_dir = "comfyui/models/clip"
os.makedirs(clip_dir, exist_ok=True)

print("=" * 60)
print("T5XXL GGUF 모델 다운로드 중...")
print("=" * 60)

# T5XXL Q8_0 GGUF 다운로드 (품질과 크기의 균형)
print("\n📥 T5XXL Q8_0 GGUF 다운로드 중... (약 4.9GB)")
t5_path = hf_hub_download(
    repo_id="city96/t5-v1_1-xxl-encoder-gguf",
    filename="t5-v1_1-xxl-encoder-Q8_0.gguf",
    local_dir=clip_dir,
)
print(f"✅ 다운로드 완료: {t5_path}")

# CLIP-L은 이미 있는지 확인
clip_l_path = os.path.join(clip_dir, "clip_l.safetensors")
if os.path.exists(clip_l_path):
    print(f"✅ CLIP-L 이미 존재: {clip_l_path}")
else:
    print(f"⚠️  CLIP-L 파일이 없습니다: {clip_l_path}")
    print("   심볼릭 링크를 생성해야 합니다.")

print("\n" + "=" * 60)
print("✅ 모든 CLIP 모델 준비 완료!")
print("=" * 60)
