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
    AutoPipelineForImage2Image
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
    
    def _apply_memory_optimizations(self, pipe, model_type: str):
        """메모리 최적화 적용 (ai-ad 방식 강화)"""
        memory_config = self.registry.get_memory_config()

        # FLUX 전용: Sequential CPU offload (더 공격적인 메모리 절약)
        if model_type == "flux" and memory_config.get("enable_cpu_offload", False):
            try:
                pipe.enable_sequential_cpu_offload()
                print("  ✓ Sequential CPU 오프로드 활성화 (FLUX 전용, 메모리 70% 절약)")
            except Exception as e:
                print(f"  ⚠️ Sequential CPU offload 실패: {e}")
                try:
                    pipe.enable_model_cpu_offload()
                    print("  ✓ 일반 CPU 오프로드로 폴백")
                except:
                    pass
        elif memory_config.get("enable_cpu_offload", False):
            try:
                pipe.enable_model_cpu_offload()
                print("  ✓ CPU 오프로드 활성화")
            except:
                pass

        # VAE Tiling (고해상도 처리)
        if hasattr(pipe, 'vae'):
            try:
                pipe.vae.enable_tiling()
                print("  ✓ VAE Tiling 활성화 (메모리 절약, 속도 영향 없음)")
            except:
                pass

        # VAE Slicing (배치 처리)
        if memory_config.get("enable_vae_slicing", False):
            if hasattr(pipe, 'vae'):
                try:
                    pipe.vae.enable_slicing()
                    print("  ✓ VAE 슬라이싱 활성화")
                except:
                    pass

        # Attention Slicing (선택적)
        if memory_config.get("enable_attention_slicing", False):
            try:
                pipe.enable_attention_slicing()
                print("  ✓ 어텐션 슬라이싱 활성화")
            except:
                pass

        return pipe
    
    def _load_model_by_type(self, model_config: ModelConfig) -> Tuple[Any, Any]:
        """모델 타입에 따라 적절한 파이프라인 로드"""
        model_id = model_config.id
        model_type = model_config.type.lower()
        
        print(f"  📦 타입: {model_type}")
        
        # 8-bit 로딩 옵션
        load_kwargs = {
            "cache_dir": self.cache_dir,
            "torch_dtype": self.dtype
        }
        
        if self.registry.get_memory_config().get("use_8bit", False):
            load_kwargs["load_in_8bit"] = True
            print("  ✓ 8-bit 양자화 모드")
        
        # 모델 타입별 로딩
        if model_type == "flux":
            # FLUX 계열 (ai-ad 방식: CPU offload 사용 시 .to(device) 생략)
            t2i = DiffusionPipeline.from_pretrained(model_id, **load_kwargs)

            # CPU offload 미사용 시에만 .to(device)
            if not self.registry.get_memory_config().get("enable_cpu_offload", False):
                t2i = t2i.to(self.device)
                print(f"  ✓ 모델을 {self.device}로 이동")

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
        
        # 메모리 최적화 적용 (model_type 전달)
        t2i = self._apply_memory_optimizations(t2i, model_type)
        if i2i != t2i:
            i2i = self._apply_memory_optimizations(i2i, model_type)
        
        return t2i, i2i
    
    def load_model(self, model_name: str) -> bool:
        """특정 모델 로드"""
        # 이미 로드된 경우 스킵
        if self.is_loaded() and self.current_model_name == model_name:
            print(f"ℹ️ 모델 '{model_name}' 이미 로드됨 — 스킵")
            return True
        
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