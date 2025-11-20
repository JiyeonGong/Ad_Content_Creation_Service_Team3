# /home/spai0323/Ad_Content_Creation_Service_Team3/src/backend/model_loader.py
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
    
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        
        self.t2i_pipe = None
        self.i2i_pipe = None
        self.current_model_name = None
        self.current_model_config: Optional[ModelConfig] = None
        
        self.registry = get_registry()
        
        print(f"🔧 ModelLoader 초기화 (Device: {self.device}, Cache: {cache_dir})")
    
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
    
    def _apply_memory_optimizations(self, pipe):
        """메모리 최적화 적용 (팀원 최적화 기법 포함)"""
        memory_config = self.registry.get_memory_config()
        model_type = self.current_model_config.type if self.current_model_config else "unknown"
        
        print(f"  🔧 메모리 최적화 적용 중...")
        
        # 1. VAE 타일링 (최우선, 속도 영향 없음) ⭐
        if memory_config.get("enable_vae_tiling", True):
            if hasattr(pipe, 'vae'):
                try:
                    pipe.vae.enable_tiling()
                    print(f"    ✓ VAE 타일링 활성화 (메모리 절약, 속도 영향 없음)")
                except Exception as e:
                    print(f"    ⚠️ VAE 타일링 실패: {e}")
        
        # 2. VAE 슬라이싱
        if memory_config.get("enable_vae_slicing", True):
            if hasattr(pipe, 'vae'):
                try:
                    pipe.vae.enable_slicing()
                    print(f"    ✓ VAE 슬라이싱 활성화")
                except Exception as e:
                    print(f"    ⚠️ VAE 슬라이싱 실패: {e}")
        
        # 3. 어텐션 슬라이싱
        if memory_config.get("enable_attention_slicing", True):
            try:
                pipe.enable_attention_slicing()
                print(f"    ✓ 어텐션 슬라이싱 활성화")
            except Exception as e:
                print(f"    ⚠️ 어텐션 슬라이싱 실패: {e}")
        
        # 4. xFormers (설치된 경우)
        if memory_config.get("enable_xformers", False):
            try:
                pipe.enable_xformers_memory_efficient_attention()
                print(f"    ✓ xFormers 활성화 (메모리 효율 + 속도 향상)")
            except Exception as e:
                print(f"    ℹ️ xFormers 사용 불가 (pip install xformers)")
        
        # 5. Sequential CPU Offload (FLUX 전용, 최대 메모리 절약)
        if memory_config.get("enable_sequential_cpu_offload", False):
            if model_type == "flux":
                try:
                    pipe.enable_sequential_cpu_offload()
                    print(f"    ✓ Sequential CPU 오프로드 활성화 (FLUX, 최대 메모리 절약)")
                    print(f"    ⚠️ 주의: 생성 속도가 매우 느려집니다")
                except Exception as e:
                    print(f"    ⚠️ Sequential CPU 오프로드 실패: {e}")
            else:
                print(f"    ℹ️ Sequential CPU offload는 FLUX 모델 전용입니다")
        
        # 6. Model CPU Offload (일반, 메모리 절약)
        elif memory_config.get("enable_cpu_offload", False):
            try:
                pipe.enable_model_cpu_offload()
                print(f"    ✓ CPU 오프로드 활성화 (메모리 절약)")
                print(f"    ⚠️ 주의: 생성 속도가 느려집니다")
            except Exception as e:
                print(f"    ⚠️ CPU 오프로드 실패: {e}")
        
        # 7. Torch Compile (PyTorch 2.0+)
        if memory_config.get("enable_torch_compile", False):
            try:
                import torch
                if hasattr(torch, 'compile'):
                    pipe.unet = torch.compile(pipe.unet, mode="reduce-overhead")
                    print(f"    ✓ Torch Compile 활성화 (첫 실행 느림, 이후 빠름)")
                else:
                    print(f"    ℹ️ PyTorch 2.0+ 필요 (torch.compile)")
            except Exception as e:
                print(f"    ⚠️ Torch Compile 실패: {e}")
        
        return pipe
    
    def _load_model_by_type(self, model_config: ModelConfig) -> Tuple[Any, Any]:
        """모델 타입에 따라 적절한 파이프라인 로드"""
        model_id = model_config.id
        model_type = model_config.type.lower()
        
        print(f"  📦 타입: {model_type}")
        
        # dtype 결정 (bfloat16 최적화 포함)
        memory_config = self.registry.get_memory_config()
        use_bfloat16 = memory_config.get("use_bfloat16", False)
        use_8bit = memory_config.get("use_8bit", False)
        
        # bfloat16은 FLUX에 특히 좋음 (FP16보다 안정적)
        if use_bfloat16 and torch.cuda.is_available():
            load_dtype = torch.bfloat16
            print("  ✓ bfloat16 사용 (FLUX 권장)")
        elif use_8bit:
            load_dtype = torch.float16  # 8bit는 FP16 기반
            print("  ✓ 8비트 양자화 준비")
        else:
            load_dtype = self.dtype
        
        # 로딩 옵션
        load_kwargs = {
            "cache_dir": self.cache_dir,
            "torch_dtype": load_dtype
        }
        
        if use_8bit:
            load_kwargs["load_in_8bit"] = True
            print("  ✓ 8비트 양자화 모드")
        
        # 모델 타입별 로딩
        if model_type == "flux":
            # FLUX 계열
            t2i = DiffusionPipeline.from_pretrained(model_id, **load_kwargs).to(self.device)
            
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
        
        # 메모리 최적화 적용
        t2i = self._apply_memory_optimizations(t2i)
        if i2i != t2i:
            i2i = self._apply_memory_optimizations(i2i)
        
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
            
            # 🆕 GPU 메모리 강제 정리 (OOM 반복 방지)
            if torch.cuda.is_available():
                print(f"  🧹 GPU 메모리 정리 중...")
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                print(f"  ✓ GPU 메모리 정리 완료")
            
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
                print(f"1. model_config.yaml에서 memory.enable_sequential_cpu_offload: true")
                print(f"2. 더 작은 모델 사용 (sdxl, playground)")
                print(f"3. GPU 메모리 확인: nvidia-smi")
            
            print(traceback.format_exc())
            return False
    
    def load_with_fallback(self) -> bool:
        """
        Primary 모델 로드 시도, 실패 시 폴백 체인 실행
        🆕 각 실패 시마다 GPU 메모리 정리로 OOM 반복 방지
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
        
        # 🆕 Primary 실패 후 메모리 정리 대기
        if torch.cuda.is_available():
            import time
            print(f"  ⏳ GPU 메모리 안정화 대기 중...")
            time.sleep(2)  # 2초 대기
        
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
            
            # 🆕 각 폴백 실패 후 메모리 정리 및 대기
            if torch.cuda.is_available():
                import time
                print(f"  ⏳ GPU 메모리 안정화 대기 중...")
                time.sleep(2)  # 2초 대기
        
        # 모든 폴백 실패
        print("❌ 모든 모델 로딩 실패")
        return False
    
    def unload_model(self):
        """모델 언로드, GPU VRAM 및 상태 변수 정리"""
        
        # 1. 파이프라인 객체 삭제
        if self.t2i_pipe:
            del self.t2i_pipe
            self.t2i_pipe = None
        
        if self.i2i_pipe:
            del self.i2i_pipe
            self.i2i_pipe = None

        # 2. 모델 상태 초기화
        self.current_model_name = None
        self.current_model_config = None

        # 3. Python 가비지 컬렉션 강제 실행
        import gc
        gc.collect()
        
        # 4. CUDA 캐시 및 IPC 메모리 해제
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()  # 캐시된 메모리 해제
                torch.cuda.ipc_collect()  # IPC 메모리 해제 
                print("🗑️ 모델 언로드 및 GPU 메모리 정리 완료")
            else:
                print("🗑️ 모델 언로드 완료 (GPU 미사용)")
        except Exception as e:
            # 예외 처리로 안정성 확보
            print(f"⚠️ GPU 메모리 정리 실패: {e}")















































# # model_loader.py
# """
# 모델 로더 - 설정 기반 모델 로딩 및 관리
# """
# import os
# import traceback
# from typing import Optional, Tuple, Any
# import torch
# from diffusers import (
#     DiffusionPipeline,
#     StableDiffusionXLPipeline,
#     StableDiffusionXLImg2ImgPipeline,
#     AutoPipelineForImage2Image
# )

# from .model_registry import ModelConfig, get_registry


# class ModelLoader:
#     """모델 로딩 및 관리 클래스"""
    
#     def __init__(self, cache_dir: str):
#         self.cache_dir = cache_dir
#         self.device = "cuda" if torch.cuda.is_available() else "cpu"
#         self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        
#         self.t2i_pipe = None
#         self.i2i_pipe = None
#         self.current_model_name = None
#         self.current_model_config: Optional[ModelConfig] = None
        
#         self.registry = get_registry()
        
#         print(f"🔧 ModelLoader 초기화 (Device: {self.device}, Cache: {cache_dir})")
    
#     def is_loaded(self) -> bool:
#         """모델 로드 여부 확인"""
#         return self.t2i_pipe is not None
    
#     def get_current_model_info(self) -> dict:
#         """현재 로드된 모델 정보"""
#         if not self.current_model_config:
#             return {"loaded": False}
        
#         return {
#             "loaded": True,
#             "name": self.current_model_name,
#             "id": self.current_model_config.id,
#             "type": self.current_model_config.type,
#             "device": self.device,
#             "description": self.current_model_config.description
#         }
    
#     def _apply_memory_optimizations(self, pipe):
#         """메모리 최적화 적용"""
#         memory_config = self.registry.get_memory_config()
        
#         if memory_config.get("enable_cpu_offload", False):
#             try:
#                 pipe.enable_model_cpu_offload()
#                 print("  ✓ CPU 오프로드 활성화")
#             except:
#                 pass
        
#         if memory_config.get("enable_attention_slicing", False):
#             try:
#                 pipe.enable_attention_slicing()
#                 print("  ✓ 어텐션 슬라이싱 활성화")
#             except:
#                 pass
        
#         if memory_config.get("enable_vae_slicing", False):
#             try:
#                 pipe.enable_vae_slicing()
#                 print("  ✓ VAE 슬라이싱 활성화")
#             except:
#                 pass
        
#         return pipe
    
#     def _load_model_by_type(self, model_config: ModelConfig) -> Tuple[Any, Any]:
#         """모델 타입에 따라 적절한 파이프라인 로드"""
#         model_id = model_config.id
#         model_type = model_config.type.lower()
        
#         print(f"  📦 타입: {model_type}")
        
#         # 8-bit 로딩 옵션
#         load_kwargs = {
#             "cache_dir": self.cache_dir,
#             "torch_dtype": self.dtype
#         }
        
#         if self.registry.get_memory_config().get("use_8bit", False):
#             load_kwargs["load_in_8bit"] = True
#             print("  ✓ 8-bit 양자화 모드")
        
#         # 모델 타입별 로딩
#         if model_type == "flux":
#             # FLUX 계열
#             t2i = DiffusionPipeline.from_pretrained(model_id, **load_kwargs).to(self.device)
            
#             # I2I 파이프라인 생성 시도
#             try:
#                 i2i = AutoPipelineForImage2Image.from_pipe(t2i)
#             except:
#                 i2i = t2i  # 폴백
#                 print("  ⚠️ I2I 파이프라인 공유")
        
#         elif model_type in ["sdxl", "sd3", "playground"]:
#             # SDXL 계열
#             t2i = StableDiffusionXLPipeline.from_pretrained(model_id, **load_kwargs).to(self.device)
#             i2i = StableDiffusionXLImg2ImgPipeline.from_pretrained(model_id, **load_kwargs).to(self.device)
        
#         elif model_type == "kandinsky":
#             # Kandinsky 계열
#             from diffusers import AutoPipelineForText2Image
#             t2i = AutoPipelineForText2Image.from_pretrained(model_id, **load_kwargs).to(self.device)
#             i2i = AutoPipelineForImage2Image.from_pipe(t2i)
        
#         else:
#             # 기본 (Auto 파이프라인)
#             print(f"  ⚠️ 알 수 없는 타입 '{model_type}', Auto 파이프라인 사용")
#             t2i = DiffusionPipeline.from_pretrained(model_id, **load_kwargs).to(self.device)
#             try:
#                 i2i = AutoPipelineForImage2Image.from_pipe(t2i)
#             except:
#                 i2i = t2i
        
#         # 메모리 최적화 적용
#         t2i = self._apply_memory_optimizations(t2i)
#         if i2i != t2i:
#             i2i = self._apply_memory_optimizations(i2i)
        
#         return t2i, i2i
    
#     def load_model(self, model_name: str) -> bool:
#         """특정 모델 로드"""
#         # 이미 로드된 경우 스킵
#         if self.is_loaded() and self.current_model_name == model_name:
#             print(f"ℹ️ 모델 '{model_name}' 이미 로드됨 — 스킵")
#             return True
        
#         # 모델 설정 가져오기
#         model_config = self.registry.get_model(model_name)
#         if not model_config:
#             print(f"❌ 알 수 없는 모델: {model_name}")
#             return False
        
#         print(f"🔄 모델 로딩 시작: {model_name}")
#         print(f"  ID: {model_config.id}")
        
#         # 인증 필요 여부 체크
#         if model_config.requires_auth:
#             print(f"  ⚠️ 인증 필요 모델입니다.")
#             print(f"  해결: huggingface-cli login")
        
#         try:
#             self.t2i_pipe, self.i2i_pipe = self._load_model_by_type(model_config)
#             self.current_model_name = model_name
#             self.current_model_config = model_config
            
#             print(f"✅ 모델 '{model_name}' 로딩 성공!")
#             return True
            
#         except Exception as e:
#             error_msg = str(e).lower()
#             print(f"❌ 모델 '{model_name}' 로딩 실패: {e}")
            
#             # 인증 에러 상세 안내
#             if any(kw in error_msg for kw in ["401", "authentication", "gated", "access"]):
#                 print(f"\n🔐 인증 필요:")
#                 print(f"1. https://huggingface.co/{model_config.id} 방문")
#                 print(f"2. 'Agree and access repository' 클릭")
#                 print(f"3. 터미널: huggingface-cli login")
            
#             # GPU OOM 에러
#             elif "out of memory" in error_msg and self.device == "cuda":
#                 print(f"\n💾 메모리 부족 감지")
#                 print(f"해결 방법:")
#                 print(f"1. model_config.yaml에서 memory.use_8bit: true 설정")
#                 print(f"2. 더 작은 모델 사용 (sdxl, playground)")
#                 print(f"3. CPU 모드로 실행")
            
#             print(traceback.format_exc())
#             return False
    
#     def load_with_fallback(self) -> bool:
#         """
#         Primary 모델 로드 시도, 실패 시 폴백 체인 실행
#         """
#         # 이미 로드된 경우 스킵
#         if self.is_loaded():
#             print(f"ℹ️ 모델 이미 로드됨 — 스킵")
#             return True
        
#         # Primary 모델 시도
#         primary = self.registry.get_primary_model()
#         print(f"🎯 Primary 모델 시도: {primary}")
        
#         if self.load_model(primary):
#             return True
        
#         # 폴백 비활성화된 경우 종료
#         if not self.registry.is_fallback_enabled():
#             print("⚠️ 폴백이 비활성화되어 있습니다.")
#             return False
        
#         # 폴백 체인 실행
#         fallback_chain = self.registry.get_fallback_models()
#         print(f"🔄 폴백 체인 실행: {fallback_chain}")
        
#         for fallback_name in fallback_chain:
#             if fallback_name == primary:
#                 continue  # 이미 시도한 모델 스킵
            
#             print(f"\n🔄 폴백 시도: {fallback_name}")
#             if self.load_model(fallback_name):
#                 print(f"✅ 폴백 성공: {fallback_name}")
#                 return True
        
#         # 모든 폴백 실패
#         print("❌ 모든 모델 로딩 실패")
#         return False
    
#     def unload_model(self):
#         """모델 언로드 (메모리 해제)"""
#         if self.t2i_pipe:
#             del self.t2i_pipe
#             self.t2i_pipe = None
        
#         if self.i2i_pipe:
#             del self.i2i_pipe
#             self.i2i_pipe = None
        
#         self.current_model_name = None
#         self.current_model_config = None
        
#         # GPU 메모리 정리
#         if torch.cuda.is_available():
#             torch.cuda.empty_cache()
        
#         print("🗑️ 모델 언로드 완료")