# model_loader.py
"""
모델 로더 - 설정 기반 모델 로딩 및 관리
"""
import os
import traceback
from typing import Optional, Tuple, Any
import torch
from diffusers import (
    DiffusionPipeline,
    StableDiffusionXLPipeline,
    StableDiffusionXLImg2ImgPipeline,
    AutoPipelineForImage2Image,
    FluxTransformer2DModel,
    BitsAndBytesConfig
)

from .model_registry import ModelConfig, get_registry


class ModelLoader:
    """모델 로딩 및 관리 클래스"""
    
    def __init__(self, cache_dir: str, use_bfloat16: bool = True):
        self.cache_dir = cache_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # FLUX는 bfloat16 권장 (ai-ad 방식)
        if use_bfloat16 and self.device == "cuda":
            self.dtype = torch.bfloat16
        else:
            self.dtype = torch.float16 if self.device == "cuda" else torch.float32

        self.t2i_pipe = None
        self.i2i_pipe = None
        self.current_model_name = None
        self.current_model_config: Optional[ModelConfig] = None

        self.registry = get_registry()

        print(f"🔧 ModelLoader 초기화 (Device: {self.device}, dtype: {self.dtype}, Cache: {cache_dir})")
    
    def is_loaded(self) -> bool:
        """모델 로드 여부 확인"""
        return self.t2i_pipe is not None
    
    def get_current_model_info(self) -> dict:
        """현재 로드된 모델 정보"""
        if not self.current_model_config:
            return {"loaded": False}
        
        return {
            "loaded": True,
            "name": self.current_model_name,
            "id": self.current_model_config.id,
            "type": self.current_model_config.type,
            "device": self.device,
            "description": self.current_model_config.description
        }
    
    def _apply_memory_optimizations(self, pipe, model_type: str, pipe_name: str = "", is_quantized: bool = False):
        """메모리 최적화 및 속도 최적화 적용"""
        memory_config = self.registry.get_memory_config()

        # 파이프라인 이름 표시 (T2I/I2I 구분)
        prefix = f"[{pipe_name}] " if pipe_name else "  "

        # CPU offload 설정 (양자화 사용 시 자동 비활성화)
        if memory_config.get("enable_cpu_offload", False) and not is_quantized:
            try:
                # FLUX 모델은 sequential offload 사용 (더 공격적인 메모리 절약)
                if model_type == "flux":
                    pipe.enable_sequential_cpu_offload()
                    print(f"{prefix}✓ Sequential CPU 오프로드 활성화 (FLUX 전용)")
                else:
                    pipe.enable_model_cpu_offload()
                    print(f"{prefix}✓ Model CPU 오프로드 활성화")
            except Exception as e:
                print(f"{prefix}⚠️ CPU offload 실패: {e}")

        # VAE Tiling (고해상도 처리)
        if hasattr(pipe, 'vae'):
            try:
                pipe.vae.enable_tiling()
                print(f"{prefix}✓ VAE Tiling 활성화 (메모리 절약, 속도 영향 없음)")
            except:
                pass

        # VAE Slicing (배치 처리)
        if memory_config.get("enable_vae_slicing", False):
            if hasattr(pipe, 'vae'):
                try:
                    pipe.vae.enable_slicing()
                    print(f"{prefix}✓ VAE 슬라이싱 활성화")
                except:
                    pass

        # Attention Slicing (선택적)
        if memory_config.get("enable_attention_slicing", False):
            try:
                pipe.enable_attention_slicing()
                print(f"{prefix}✓ 어텐션 슬라이싱 활성화")
            except:
                pass

        # Flash Attention 2 적용 (양자화와 함께 사용 시 추가 속도 개선)
        if memory_config.get("use_flash_attention", False):
            try:
                if hasattr(pipe, 'transformer') and hasattr(pipe.transformer, 'enable_flash_attention_2'):
                    pipe.transformer.enable_flash_attention_2()
                    print(f"{prefix}✓ Flash Attention 2 활성화")
                else:
                    print(f"{prefix}ℹ️ Flash Attention 2 미지원 모델")
            except ImportError:
                print(f"{prefix}⚠️ Flash Attention 2 미설치, 기본 attention 사용")
            except Exception as e:
                print(f"{prefix}⚠️ Flash Attention 2 적용 실패: {e}")

        return pipe
    
    def _load_model_by_type(self, model_config: ModelConfig) -> Tuple[Any, Any]:
        """모델 타입에 따라 적절한 파이프라인 로드"""
        model_id = model_config.id
        model_type = model_config.type.lower()
        memory_config = self.registry.get_memory_config()

        print(f"  📦 타입: {model_type}")

        # 기본 로딩 옵션
        load_kwargs = {
            "cache_dir": self.cache_dir,
            "torch_dtype": self.dtype
        }

        # 사전 양자화 모델 체크 (모델 ID에 "int8", "fp8", "nf4" 포함 시)
        is_prequantized = any(keyword in model_id.lower() for keyword in ["int8", "fp8", "nf4", "gguf"])

        if is_prequantized:
            print("  ✅ 사전 양자화 모델 감지 - 바로 로드 (양자화 과정 생략)")
            use_quantization = False
        else:
            # 양자화 설정 (FLUX에만 적용)
            quant_type = memory_config.get("quantization_type", "none").lower()
            use_quantization = quant_type in ["fp8", "nf4"] and model_type == "flux"

            if use_quantization:
                if quant_type == "fp8":
                    print("  🚀 FP8 양자화 모드 활성화 (22GB → 12GB, 품질 99%+, 2-2.6배 속도)")
                elif quant_type == "nf4":
                    print("  🚀 NF4 양자화 모드 활성화 (22GB → 12GB, 품질 98%, 3-4배 속도)")
            elif memory_config.get("use_8bit", False):
                load_kwargs["load_in_8bit"] = True
                print("  ✓ 8-bit 양자화 모드 (deprecated)")

        # 모델 타입별 로딩
        if model_type == "flux-bnb-4bit":
            # 사전 양자화 4-bit 모델 (diffusers/FLUX.1-dev-bnb-4bit)
            from diffusers import FluxPipeline
            print("  📥 사전 양자화 4-bit 모델 (bitsandbytes) 로딩 중...")
            print("  ⚠️ 첫 로드 시 다운로드에 시간이 걸릴 수 있습니다.")

            t2i = FluxPipeline.from_pretrained(
                model_id,
                torch_dtype=self.dtype,
                cache_dir=self.cache_dir
            )
            t2i = t2i.to(self.device)
            print("  ✓ 사전 양자화 4-bit 모델 로드 완료")

            # GPU 메모리 확인
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / 1024**3
                print(f"  📊 GPU 메모리: {allocated:.2f} GB")

            # I2I 파이프라인
            try:
                i2i = AutoPipelineForImage2Image.from_pipe(t2i)
            except:
                i2i = t2i
                print("  ⚠️ I2I 파이프라인 공유")

        elif model_type == "flux-bnb-8bit":
            # 사전 양자화 8-bit 모델 (diffusers/FLUX.1-dev-bnb-8bit)
            from diffusers import FluxPipeline
            print("  📥 사전 양자화 8-bit 모델 (bitsandbytes) 로딩 중...")
            print("  ⚠️ 첫 로드 시 다운로드에 시간이 걸릴 수 있습니다.")

            t2i = FluxPipeline.from_pretrained(
                model_id,
                torch_dtype=self.dtype,
                cache_dir=self.cache_dir
            )
            print("  ✓ 사전 양자화 8-bit 모델 로드 완료")

            # GPU 메모리 확인
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / 1024**3
                print(f"  📊 GPU 메모리: {allocated:.2f} GB")

            # I2I 파이프라인
            try:
                i2i = AutoPipelineForImage2Image.from_pipe(t2i)
            except:
                i2i = t2i
                print("  ⚠️ I2I 파이프라인 공유")

        elif model_type == "flux-fp8-pretrained":
            # 사전 양자화 FP8 모델 (diffusers/FLUX.1-dev-torchao-fp8)
            # torchao 버전 호환 문제로 사용 불가
            from diffusers import FluxPipeline
            print("  📥 사전 양자화 FP8 모델 로딩 중...")
            print("  ⚠️ 첫 로드 시 다운로드에 시간이 걸릴 수 있습니다.")

            t2i = FluxPipeline.from_pretrained(
                model_id,
                torch_dtype=self.dtype,
                use_safetensors=False,
                device_map="cuda:0",
                cache_dir=self.cache_dir
            )
            print("  ✓ 사전 양자화 FP8 모델 로드 완료")

            # GPU 메모리 확인
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / 1024**3
                print(f"  📊 GPU 메모리: {allocated:.2f} GB")

            # I2I 파이프라인
            try:
                i2i = AutoPipelineForImage2Image.from_pipe(t2i)
            except:
                i2i = t2i
                print("  ⚠️ I2I 파이프라인 공유")

        elif model_type == "flux":
            # FLUX 계열: FP8 / NF4 양자화 지원
            if use_quantization:
                try:
                    if quant_type == "fp8":
                        # FP8 양자화 (TorchAO)
                        # Transformer만 양자화, 나머지는 원본
                        print("  📥 FP8 Transformer 로딩 중...")
                        from torchao.quantization import quantize_
                        from torchao.quantization.quant_api import Float8WeightOnlyConfig

                        # Transformer 로드 후 양자화
                        transformer = FluxTransformer2DModel.from_pretrained(
                            model_id,
                            subfolder="transformer",
                            torch_dtype=self.dtype,
                            cache_dir=self.cache_dir
                        )

                        # 양자화 전 모델 크기 확인
                        param_size_before = sum(p.numel() * p.element_size() for p in transformer.parameters()) / 1024**3
                        print(f"  📊 양자화 전 Transformer 크기: {param_size_before:.2f} GB")

                        # FP8 양자화 적용 (Float8WeightOnlyConfig 사용)
                        print("  🔄 FP8 양자화 적용 중...")
                        quantize_(transformer, Float8WeightOnlyConfig())

                        # 양자화 후 모델 크기 확인
                        param_size_after = sum(p.numel() * p.element_size() for p in transformer.parameters()) / 1024**3
                        print(f"  📊 양자화 후 Transformer 크기: {param_size_after:.2f} GB")

                        # 양자화 성공 여부 확인
                        if param_size_after < param_size_before * 0.7:
                            print(f"  ✓ FP8 양자화 성공 (크기 {param_size_before:.2f}GB → {param_size_after:.2f}GB)")
                        else:
                            print(f"  ⚠️ FP8 양자화 실패 또는 미적용 (크기 변화 없음)")
                            raise RuntimeError("FP8 양자화가 적용되지 않았습니다")

                        # 전체 파이프라인 구성
                        print("  🔧 파이프라인 구성 중...")
                        t2i = DiffusionPipeline.from_pretrained(
                            model_id,
                            transformer=transformer,
                            torch_dtype=self.dtype,
                            cache_dir=self.cache_dir
                        )

                        # GPU로 이동
                        t2i = t2i.to(self.device)
                        print(f"  ✓ FP8 모델을 {self.device}로 이동")

                        # 최종 GPU 메모리 확인
                        if torch.cuda.is_available():
                            allocated = torch.cuda.memory_allocated() / 1024**3
                            print(f"  📊 전체 GPU 메모리: {allocated:.2f} GB")

                    elif quant_type == "nf4":
                        # NF4 양자화 (BitsAndBytes)
                        # ⚠️ NF4 양자화 모델은 저장/로드 복잡 - 매번 양자화 수행
                        print("  📥 NF4 Transformer 로딩 중...")
                        nf4_config = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_quant_type="nf4",
                            bnb_4bit_compute_dtype=self.dtype
                        )

                        # Transformer만 양자화 로드
                        transformer = FluxTransformer2DModel.from_pretrained(
                            model_id,
                            subfolder="transformer",
                            quantization_config=nf4_config,
                            torch_dtype=self.dtype,
                            cache_dir=self.cache_dir
                        )
                        print("  ✓ NF4 양자화 로드 완료")

                        # 전체 파이프라인 구성
                        print("  🔧 파이프라인 구성 중...")
                        t2i = DiffusionPipeline.from_pretrained(
                            model_id,
                            transformer=transformer,
                            torch_dtype=self.dtype,
                            cache_dir=self.cache_dir
                        )
                        t2i = t2i.to(self.device)
                        print(f"  ✓ 양자화된 모델을 {self.device}로 이동")

                    print(f"  ✅ {quant_type.upper()} 양자화 로딩 완료")

                except Exception as e:
                    print(f"  ⚠️ {quant_type.upper()} 로딩 실패: {e}")
                    print(f"  🔄 CPU offload 모드로 폴백 시도...")
                    use_quantization = False
                    # 폴백: CPU offload 모드 (CPU 16GB로는 분산로딩 불가)
                    # enable_sequential_cpu_offload 방식 사용
                    t2i = DiffusionPipeline.from_pretrained(
                        model_id,
                        torch_dtype=self.dtype,
                        cache_dir=self.cache_dir
                    )
                    t2i.enable_sequential_cpu_offload()
                    print(f"  ✓ Sequential CPU offload 적용 (느리지만 메모리 안정적)")
            else:
                # 일반 FLUX 로딩 (양자화 미사용)
                # device_map="balanced"로 GPU 우선, 넘치면 CPU 분산
                load_kwargs["device_map"] = "balanced"
                t2i = DiffusionPipeline.from_pretrained(model_id, **load_kwargs)
                print(f"  ✓ device_map='balanced' 적용 (GPU 우선, 넘치면 CPU 분산)")

            # I2I 파이프라인 생성 시도
            try:
                i2i = AutoPipelineForImage2Image.from_pipe(t2i)
            except:
                i2i = t2i  # 폴백
                print("  ⚠️ I2I 파이프라인 공유")
        
        elif model_type in ["sdxl", "sd3", "playground"]:
            # SDXL 계열
            t2i = StableDiffusionXLPipeline.from_pretrained(model_id, **load_kwargs).to(self.device)
            i2i = StableDiffusionXLImg2ImgPipeline.from_pretrained(model_id, **load_kwargs).to(self.device)
        
        elif model_type == "kandinsky":
            # Kandinsky 계열
            from diffusers import AutoPipelineForText2Image
            t2i = AutoPipelineForText2Image.from_pretrained(model_id, **load_kwargs).to(self.device)
            i2i = AutoPipelineForImage2Image.from_pipe(t2i)
        
        else:
            # 기본 (Auto 파이프라인)
            print(f"  ⚠️ 알 수 없는 타입 '{model_type}', Auto 파이프라인 사용")
            t2i = DiffusionPipeline.from_pretrained(model_id, **load_kwargs).to(self.device)
            try:
                i2i = AutoPipelineForImage2Image.from_pipe(t2i)
            except:
                i2i = t2i
        
        # 메모리 최적화 적용 (사전 양자화 모델은 CPU offload 하면 안 됨)
        if model_type == "flux-fp8-pretrained":
            print("  ℹ️ 사전 양자화 모델 - CPU offload 비활성화")
        else:
            t2i = self._apply_memory_optimizations(t2i, model_type, "T2I", use_quantization)
            if i2i != t2i:
                i2i = self._apply_memory_optimizations(i2i, model_type, "I2I", use_quantization)

        return t2i, i2i
    
    def load_model(self, model_name: str) -> bool:
        """특정 모델 로드"""
        # 이미 로드된 경우 스킵
        if self.is_loaded() and self.current_model_name == model_name:
            print(f"ℹ️ 모델 '{model_name}' 이미 로드됨 — 스킵")
            return True

        # 기존 모델 해제 (메모리 확보)
        if self.is_loaded():
            print(f"🧹 기존 모델 '{self.current_model_name}' 해제 중...")
            self.unload_model()

        # 모델 설정 가져오기
        model_config = self.registry.get_model(model_name)
        if not model_config:
            print(f"❌ 알 수 없는 모델: {model_name}")
            return False

        print(f"🔄 모델 로딩 시작: {model_name}")
        print(f"  ID: {model_config.id}")
        
        # 인증 필요 여부 체크
        if model_config.requires_auth:
            print(f"  ⚠️ 인증 필요 모델입니다.")
            print(f"  해결: huggingface-cli login")
        
        try:
            self.t2i_pipe, self.i2i_pipe = self._load_model_by_type(model_config)
            self.current_model_name = model_name
            self.current_model_config = model_config
            
            print(f"✅ 모델 '{model_name}' 로딩 성공!")
            return True
            
        except Exception as e:
            error_msg = str(e).lower()
            print(f"❌ 모델 '{model_name}' 로딩 실패: {e}")
            
            # 인증 에러 상세 안내
            if any(kw in error_msg for kw in ["401", "authentication", "gated", "access"]):
                print(f"\n🔐 인증 필요:")
                print(f"1. https://huggingface.co/{model_config.id} 방문")
                print(f"2. 'Agree and access repository' 클릭")
                print(f"3. 터미널: huggingface-cli login")
            
            # GPU OOM 에러
            elif "out of memory" in error_msg and self.device == "cuda":
                print(f"\n💾 메모리 부족 감지")
                print(f"해결 방법:")
                print(f"1. model_config.yaml에서 memory.use_8bit: true 설정")
                print(f"2. 더 작은 모델 사용 (sdxl, playground)")
                print(f"3. CPU 모드로 실행")
            
            print(traceback.format_exc())
            return False
    
    def load_with_fallback(self) -> bool:
        """
        Primary 모델 로드 시도, 실패 시 폴백 체인 실행
        """
        # 이미 로드된 경우 스킵
        if self.is_loaded():
            print(f"ℹ️ 모델 이미 로드됨 — 스킵")
            return True
        
        # Primary 모델 시도
        primary = self.registry.get_primary_model()
        print(f"🎯 Primary 모델 시도: {primary}")
        
        if self.load_model(primary):
            return True
        
        # 폴백 비활성화된 경우 종료
        if not self.registry.is_fallback_enabled():
            print("⚠️ 폴백이 비활성화되어 있습니다.")
            return False
        
        # 폴백 체인 실행
        fallback_chain = self.registry.get_fallback_models()
        print(f"🔄 폴백 체인 실행: {fallback_chain}")
        
        for fallback_name in fallback_chain:
            if fallback_name == primary:
                continue  # 이미 시도한 모델 스킵
            
            print(f"\n🔄 폴백 시도: {fallback_name}")
            if self.load_model(fallback_name):
                print(f"✅ 폴백 성공: {fallback_name}")
                return True
        
        # 모든 폴백 실패
        print("❌ 모든 모델 로딩 실패")
        return False
    
    def unload_model(self):
        """모델 언로드 (메모리 해제)"""
        if self.t2i_pipe:
            del self.t2i_pipe
            self.t2i_pipe = None
        
        if self.i2i_pipe:
            del self.i2i_pipe
            self.i2i_pipe = None
        
        self.current_model_name = None
        self.current_model_config = None
        
        # GPU 메모리 정리
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        print("🗑️ 모델 언로드 완료")