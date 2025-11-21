"""
FLUX.1-dev FP8 양자화 모델 로딩 (LoRA 학습용)

사용법:
    python scripts/load_flux_fp8_for_lora.py

이 스크립트는:
1. FLUX.1-dev를 FP8로 양자화하여 메모리에 로드
2. LoRA 학습을 위한 준비 (base_model 반환)
3. 메모리 사용량 출력
"""
import torch
from diffusers import FluxTransformer2DModel, DiffusionPipeline
from torchao.quantization import quantize_, int8_weight_only
import gc


def load_flux_fp8_for_lora(
    model_path: str = "/home/shared/FLUX.1-dev",
    device: str = "cuda",
    dtype: torch.dtype = torch.bfloat16
):
    """
    FLUX.1-dev를 FP8로 양자화하여 로드

    Args:
        model_path: FLUX.1-dev 모델 경로
        device: 디바이스 (cuda)
        dtype: 데이터 타입 (bfloat16)

    Returns:
        pipe: FLUX 파이프라인 (FP8 양자화됨)
    """
    print("=" * 60)
    print("FLUX.1-dev FP8 양자화 로딩 (LoRA 학습용)")
    print("=" * 60)

    # 1. Transformer 로드
    print("\n📥 FLUX Transformer 로딩 중...")
    transformer = FluxTransformer2DModel.from_pretrained(
        model_path,
        subfolder="transformer",
        torch_dtype=dtype
    )
    print("✅ Transformer 로드 완료")

    # 2. FP8 양자화 적용
    print("\n🔄 FP8 양자화 적용 중... (5-15분 소요)")
    quantize_(transformer, int8_weight_only())
    print("✅ FP8 양자화 완료")

    # 3. 파이프라인 구성
    print("\n🔧 파이프라인 구성 중...")
    pipe = DiffusionPipeline.from_pretrained(
        model_path,
        transformer=transformer,
        torch_dtype=dtype
    )
    print("✅ 파이프라인 구성 완료")

    # 4. GPU로 이동
    print(f"\n🚀 GPU로 이동 중... (device: {device})")
    pipe = pipe.to(device)
    print("✅ GPU 이동 완료")

    # 5. 메모리 사용량 출력
    if device == "cuda":
        print("\n" + "=" * 60)
        print("메모리 사용량")
        print("=" * 60)
        allocated = torch.cuda.memory_allocated() / 1024**3
        reserved = torch.cuda.memory_reserved() / 1024**3
        print(f"할당된 메모리: {allocated:.2f} GB")
        print(f"예약된 메모리: {reserved:.2f} GB")
        print(f"사용 가능한 메모리: {23 - reserved:.2f} GB (L4 기준)")

    return pipe


def prepare_for_lora_training(pipe):
    """
    LoRA 학습 준비

    Args:
        pipe: FLUX 파이프라인

    Returns:
        base_model: LoRA 학습에 사용할 base model
    """
    print("\n" + "=" * 60)
    print("LoRA 학습 준비")
    print("=" * 60)

    # Transformer를 LoRA 학습 모드로 전환
    transformer = pipe.transformer

    # Gradient checkpointing 활성화 (메모리 절약)
    if hasattr(transformer, "enable_gradient_checkpointing"):
        transformer.enable_gradient_checkpointing()
        print("✅ Gradient checkpointing 활성화")

    # 학습 모드로 전환
    transformer.train()
    print("✅ 학습 모드 전환 완료")

    print("\n📌 다음 단계:")
    print("1. PEFT 라이브러리로 LoRA 설정:")
    print("   from peft import LoraConfig, get_peft_model")
    print("   lora_config = LoraConfig(")
    print("       r=8,  # LoRA rank")
    print("       lora_alpha=16,")
    print("       target_modules=['to_q', 'to_k', 'to_v', 'to_out'],")
    print("       lora_dropout=0.1")
    print("   )")
    print("   model = get_peft_model(pipe.transformer, lora_config)")
    print("\n2. 데이터셋 준비 및 학습 시작")

    return pipe


def unload_model(pipe):
    """모델 언로드 (메모리 해제)"""
    print("\n" + "=" * 60)
    print("모델 언로드 중...")
    print("=" * 60)

    del pipe
    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    print("✅ 메모리 해제 완료")


if __name__ == "__main__":
    # 1. FLUX FP8 로드
    pipe = load_flux_fp8_for_lora()

    # 2. LoRA 학습 준비
    pipe = prepare_for_lora_training(pipe)

    print("\n" + "=" * 60)
    print("준비 완료!")
    print("=" * 60)
    print("\n이제 LoRA 학습을 시작할 수 있습니다.")
    print("pipe.transformer를 사용하여 PEFT 설정 후 학습하세요.")

    # 예시: 학습 후 저장
    print("\n📌 LoRA 가중치 저장 방법:")
    print("   model.save_pretrained('./lora_weights')")
    print("\n📌 LoRA 적용 방법:")
    print("   from peft import PeftModel")
    print("   model = PeftModel.from_pretrained(base_model, './lora_weights')")

    # 테스트 생성 (선택)
    test_generation = input("\n테스트 이미지 생성을 해보시겠습니까? (y/n): ")
    if test_generation.lower() == 'y':
        print("\n🎨 테스트 이미지 생성 중...")
        image = pipe(
            prompt="A cute cat",
            width=1024,
            height=1024,
            num_inference_steps=4,
            guidance_scale=3.5,
            generator=torch.Generator(device="cuda").manual_seed(42)
        ).images[0]
        image.save("test_flux_fp8.png")
        print("✅ 저장 완료: test_flux_fp8.png")

    # 언로드 여부
    unload = input("\n모델을 언로드하시겠습니까? (y/n): ")
    if unload.lower() == 'y':
        unload_model(pipe)
