"""
백엔드 서비스 커스텀 예외 정의
"""


class ServiceError(Exception):
    """서비스 계층 기본 에러"""
    pass


class PromptOptimizationError(ServiceError):
    """프롬프트 최적화 실패"""
    pass


class ModelLoadError(ServiceError):
    """모델 로딩 실패"""
    pass


class WorkflowExecutionError(ServiceError):
    """ComfyUI 워크플로우 실행 실패"""
    pass


class ImageProcessingError(ServiceError):
    """이미지 처리 실패"""
    pass


class ConfigurationError(ServiceError):
    """설정 오류"""
    pass
