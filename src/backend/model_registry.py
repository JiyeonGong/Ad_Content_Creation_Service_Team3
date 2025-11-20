# /home/spai0323/Ad_Content_Creation_Service_Team3/src/backend/model_registry.py
"""
모델 레지스트리 - 모델 설정 로드 및 관리
"""
import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ModelConfig:
    """모델 설정 데이터 클래스"""
    id: str
    type: str
    requires_auth: bool
    params: Dict[str, Any]
    description: str
    
    @property
    def default_steps(self) -> int:
        return self.params.get("default_steps", 30)
    
    @property
    def max_steps(self) -> int:
        return self.params.get("max_steps", 50)
    
    @property
    def use_negative_prompt(self) -> bool:
        return self.params.get("use_negative_prompt", False)
    
    @property
    def guidance_scale(self) -> Optional[float]:
        return self.params.get("guidance_scale")
    
    @property
    def supports_i2i(self) -> bool:
        return self.params.get("supports_i2i", True)
    
    @property
    def max_tokens(self) -> int:
        return self.params.get("max_tokens", 77)
    
    @property
    def negative_prompt(self) -> str:
        return self.params.get("negative_prompt", "low quality, blurry")
    
    @property
    def default_size(self) -> tuple:
        size = self.params.get("default_size", [1024, 1024])
        return tuple(size)
    
    @property
    def max_size(self) -> tuple:
        size = self.params.get("max_size", [2048, 2048])
        return tuple(size)


class ModelRegistry:
    """모델 레지스트리 - 설정 파일에서 모델 정보 로드"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # 기본 경로: src/backend/model_config.yaml
            config_path = os.path.join(
                os.path.dirname(__file__), 
                "model_config.yaml"
            )
        
        self.config_path = config_path
        self.models: Dict[str, ModelConfig] = {}
        self.runtime_config: Dict[str, Any] = {}
        
        self._load_config()
    
    def _load_config(self):
        """YAML 설정 파일 로드"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 모델 설정 파싱
            for name, model_data in config.get('models', {}).items():
                self.models[name] = ModelConfig(
                    id=model_data['id'],
                    type=model_data['type'],
                    requires_auth=model_data.get('requires_auth', False),
                    params=model_data.get('params', {}),
                    description=model_data.get('description', '')
                )
            
            # 런타임 설정
            self.runtime_config = config.get('runtime', {})
            
            print(f"✅ 모델 레지스트리 로드 완료: {len(self.models)}개 모델")
            
        except FileNotFoundError:
            print(f"⚠️ 설정 파일 없음: {self.config_path}")
            self._create_default_config()
        except Exception as e:
            print(f"❌ 설정 파일 로드 실패: {e}")
            raise
    
    def _create_default_config(self):
        """기본 설정 생성 (폴백)"""
        print("📝 기본 설정 생성 중...")
        self.models['sdxl'] = ModelConfig(
            id="stabilityai/stable-diffusion-xl-base-1.0",
            type="sdxl",
            requires_auth=False,
            params={
                "default_steps": 30,
                "use_negative_prompt": True,
                "guidance_scale": 7.5,
                "supports_i2i": True,
                "max_tokens": 77
            },
            description="Fallback SDXL"
        )
        self.runtime_config = {
            "primary_model": "sdxl",
            "enable_fallback": False
        }
    
    def get_model(self, name: str) -> Optional[ModelConfig]:
        """모델 설정 조회"""
        return self.models.get(name)
    
    def get_primary_model(self) -> str:
        """환경변수 또는 설정 파일에서 기본 모델 이름 가져오기"""
        return os.getenv(
            "PRIMARY_MODEL", 
            self.runtime_config.get("primary_model", "sdxl")
        )
    
    def get_fallback_models(self) -> List[str]:
        """폴백 모델 리스트"""
        return self.runtime_config.get("fallback_models", ["sdxl"])
    
    def is_fallback_enabled(self) -> bool:
        """폴백 활성화 여부"""
        env_value = os.getenv("ENABLE_FALLBACK", "").lower()
        if env_value in ["true", "false"]:
            return env_value == "true"
        return self.runtime_config.get("enable_fallback", True)
    
    def get_prompt_optimization_config(self) -> Dict[str, Any]:
        """프롬프트 최적화 설정"""
        return self.runtime_config.get("prompt_optimization", {})
    
    def get_memory_config(self) -> Dict[str, Any]:
        """메모리 최적화 설정"""
        return self.runtime_config.get("memory", {})
    
    def list_models(self) -> List[str]:
        """사용 가능한 모델 목록"""
        return list(self.models.keys())
    
    def get_model_info(self, name: str) -> Dict[str, Any]:
        """모델 정보 딕셔너리로 반환"""
        model = self.get_model(name)
        if not model:
            return {}
        
        return {
            "id": model.id,
            "type": model.type,
            "requires_auth": model.requires_auth,
            "description": model.description,
            "default_steps": model.default_steps,
            "max_tokens": model.max_tokens,
            "supports_i2i": model.supports_i2i
        }


# 싱글톤 인스턴스
_registry_instance: Optional[ModelRegistry] = None

def get_registry() -> ModelRegistry:
    """모델 레지스트리 싱글톤 인스턴스 반환"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ModelRegistry()
    return _registry_instance