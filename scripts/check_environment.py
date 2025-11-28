#!/usr/bin/env python3
"""
FLUX 환경 정보 확인 스크립트
uv run python check_environment.py 로 실행
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print(f"Project root: {project_root}")
print(f"Python path: {sys.path}")

import torch
import diffusers
import transformers
from peft import __version__ as peft_version

# ============================================================================
# 1. 버전 정보
# ============================================================================

print("\n" + "="*70)
print("📊 버전 정보")
print("="*70)

print(f"Python: {sys.version}")
print(f"PyTorch: {torch.__version__}")
print(f"Diffusers: {diffusers.__version__}")
print(f"Transformers: {transformers.__version__}")
print(f"PEFT: {peft_version}")
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA Device: {torch.cuda.get_device_name(0)}")
    print(f"CUDA Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f}GB")

# ============================================================================
# 2. 로컬 모델 직접 로드
# ============================================================================

print("\n" + "="*70)
print("🔄 모델 직접 로드 중...")
print("="*70)

try:
    from diffusers import FluxPipeline
    
    model_path = "/home/shared/FLUX.1-dev"
    print(f"모델 경로: {model_path}")
    
    if not Path(model_path).exists():
        print(f"❌ 모델 경로 없음: {model_path}")
        sys.exit(1)
    
    print("모델 로드 중... (시간이 걸릴 수 있습니다)")
    
    pipe = FluxPipeline.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16
    )
    
    pipe.enable_attention_slicing()
    if hasattr(pipe.vae, 'enable_tiling'):
        pipe.vae.enable_tiling()
    
    print("✅ 모델 로드 성공")
    
except Exception as e:
    print(f"❌ 모델 로드 오류: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# 3. Text Encoder 1 (CLIP) 구조
# ============================================================================

print("\n" + "="*70)
print("📝 TEXT ENCODER 1 (CLIP-L)")
print("="*70)

try:
    text_encoder = pipe.text_encoder
    tokenizer = pipe.tokenizer
    
    print(f"Type: {type(text_encoder).__name__}")
    
    if hasattr(text_encoder, 'config'):
        config = text_encoder.config
        print(f"Hidden Size: {config.hidden_size}")
        print(f"Model Type: {config.model_type}")
        print(f"Vocab Size: {config.vocab_size}")
    
    # CLIP 출력 확인
    print("\n🔍 CLIP 출력 구조:")
    sample_input = tokenizer(
        ["test"],
        padding="max_length",
        max_length=77,
        truncation=True,
        return_tensors="pt"
    ).to("cuda" if torch.cuda.is_available() else "cpu")
    
    with torch.no_grad():
        output = text_encoder(sample_input.input_ids)
    
    print(f"Output type: {type(output).__name__}")
    print(f"Output attributes/keys: {list(output.keys()) if hasattr(output, 'keys') else dir(output)}")
    
    if hasattr(output, 'last_hidden_state'):
        print(f"last_hidden_state shape: {output.last_hidden_state.shape}")
    
    if hasattr(output, 'pooler_output'):
        print(f"✅ pooler_output shape: {output.pooler_output.shape}")
    else:
        print(f"❌ pooler_output 없음 (대체: last_hidden_state[:, 0] 또는 mean)")
    
    print(f"Output dtype: {output.last_hidden_state.dtype if hasattr(output, 'last_hidden_state') else 'N/A'}")

except Exception as e:
    print(f"❌ CLIP 구조 확인 오류: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 4. Text Encoder 2 (T5) 구조
# ============================================================================

print("\n" + "="*70)
print("📝 TEXT ENCODER 2 (T5-XXL)")
print("="*70)

try:
    text_encoder_2 = pipe.text_encoder_2
    tokenizer_2 = pipe.tokenizer_2
    
    print(f"Type: {type(text_encoder_2).__name__}")
    
    if hasattr(text_encoder_2, 'config'):
        config = text_encoder_2.config
        print(f"Hidden Size: {config.hidden_size}")
        print(f"Model Type: {config.model_type}")
        print(f"Num Layers: {config.num_layers if hasattr(config, 'num_layers') else 'N/A'}")
    
    # T5 출력 확인
    print("\n🔍 T5 출력 구조:")
    sample_input_2 = tokenizer_2(
        ["test"],
        padding="max_length",
        max_length=256,
        truncation=True,
        return_tensors="pt"
    ).to("cuda" if torch.cuda.is_available() else "cpu")
    
    with torch.no_grad():
        output_2 = text_encoder_2(sample_input_2.input_ids)
    
    print(f"Output type: {type(output_2).__name__}")
    print(f"Output attributes/keys: {list(output_2.keys()) if hasattr(output_2, 'keys') else dir(output_2)}")
    
    if hasattr(output_2, 'last_hidden_state'):
        print(f"✅ last_hidden_state shape: {output_2.last_hidden_state.shape}")
        print(f"   Hidden dim: {output_2.last_hidden_state.shape[-1]}")
    
    print(f"Output dtype: {output_2.last_hidden_state.dtype if hasattr(output_2, 'last_hidden_state') else 'N/A'}")

except Exception as e:
    print(f"❌ T5 구조 확인 오류: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 5. Transformer 구조
# ============================================================================

print("\n" + "="*70)
print("⚙️ TRANSFORMER 구조")
print("="*70)

try:
    transformer = pipe.transformer
    
    print(f"Type: {type(transformer).__name__}")
    
    if hasattr(transformer, 'config'):
        config = transformer.config
        print(f"In Channels: {config.in_channels if hasattr(config, 'in_channels') else 'N/A'}")
        print(f"Joint Attention Dim: {config.joint_attention_dim if hasattr(config, 'joint_attention_dim') else 'N/A'}")
    
    # time_text_embed 구조
    print("\n🔍 CombinedTimestepGuidanceTextProjEmbeddings:")
    time_text_embed = transformer.time_text_embed
    
    print(f"Type: {type(time_text_embed).__name__}")
    print(f"Attributes: {[attr for attr in dir(time_text_embed) if not attr.startswith('_')]}")
    
    # Linear layers 찾기
    import torch.nn as nn
    print(f"\n📋 Linear layers in time_text_embed:")
    
    linear_layers = []
    for name, module in time_text_embed.named_modules():
        if isinstance(module, nn.Linear):
            linear_layers.append((name, module.in_features, module.out_features))
            print(f"   {name}: {module.in_features} → {module.out_features}")
    
    if not linear_layers:
        print("   ⚠️ Linear layers not found by name, searching by direct attributes...")
        for attr_name in dir(time_text_embed):
            attr = getattr(time_text_embed, attr_name)
            if isinstance(attr, nn.Linear):
                print(f"   {attr_name}: {attr.in_features} → {attr.out_features}")

except Exception as e:
    print(f"❌ Transformer 구조 확인 오류: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 6. VAE 구조
# ============================================================================

print("\n" + "="*70)
print("🎨 VAE 구조")
print("="*70)

try:
    vae = pipe.vae
    
    print(f"Type: {type(vae).__name__}")
    
    if hasattr(vae, 'config'):
        config = vae.config
        print(f"In Channels: {config.in_channels}")
        print(f"Out Channels: {config.out_channels}")
        print(f"Scaling Factor: {config.scaling_factor}")
        print(f"Latent Channels: {config.latent_channels}")

except Exception as e:
    print(f"❌ VAE 구조 확인 오류: {e}")

# ============================================================================
# 7. 데이터셋 정보
# ============================================================================

print("\n" + "="*70)
print("📂 데이터셋 정보")
print("="*70)

try:
    dataset_path = Path("/home/spai0312/Ad_Content_Creation_Service_Team3/training_data")
    
    if dataset_path.exists():
        image_files = list(dataset_path.rglob("*.jpg")) + \
                     list(dataset_path.rglob("*.png")) + \
                     list(dataset_path.rglob("*.jpeg"))
        
        print(f"Dataset path: {dataset_path}")
        print(f"✅ 이미지 수: {len(image_files)}")
        
        if image_files:
            print(f"First 5 images:")
            for img in image_files[:5]:
                print(f"   - {img.name}")
    else:
        print(f"❌ 데이터셋 경로 없음: {dataset_path}")

except Exception as e:
    print(f"❌ 데이터셋 확인 오류: {e}")

# ============================================================================
# 8. 정리
# ============================================================================

print("\n" + "="*70)
print("✨ 환경 정보 확인 완료")
print("="*70)

print("\n💾 결과를 다음과 같이 정리해서 전달해주세요:")
print("""
=== 환경 정보 ===

1. 버전:
   - PyTorch: [위 결과에서 복사]
   - Diffusers: [위 결과에서 복사]
   - Transformers: [위 결과에서 복사]

2. Text Encoder 1 (CLIP):
   - Hidden Size: [위 결과에서 복사]
   - pooler_output 있음? [Yes/No]
   - last_hidden_state shape: [위 결과에서 복사]

3. Text Encoder 2 (T5):
   - Hidden Size: [위 결과에서 복사]
   - last_hidden_state shape: [위 결과에서 복사]

4. Transformer time_text_embed:
   - Linear layers: [위 결과 전체]

5. 데이터셋:
   - 이미지 수: [위 결과에서 복사]
   - 경로: [위 결과에서 복사]
""")