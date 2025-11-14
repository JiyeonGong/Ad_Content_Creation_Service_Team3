# AI Logic (Service Layer)

# 지금은 더미(Mock) 데이터를 반환

# 상대 경로 임포트 (.)를 사용하여 패키지 내부 의존성 해결
from .schemas import GenerationResponse, AnalysisResult, ContentOption

async def process_ad_creation(image_bytes: bytes, target: str, purpose: str) -> GenerationResponse:
    """
    [TODO] AI 모델 파이프라인 (VLM -> Seg -> Inpainting -> LLM)
    현재는 Mock 데이터를 반환
    """
    return GenerationResponse(
        analysis=AnalysisResult(
            pose_analysis="데드리프트 자세: 허리가 약간 굽어 있습니다.",
            expert_comment="초보자가 흔히 하는 실수입니다. 척추 중립 유지가 핵심 소구점입니다."
        ),
        contents=[
            ContentOption(
                option_name="옵션 A (감성형)",
                image_url="https://via.placeholder.com/400x400.png?text=Yoga+Mood",
                copy_text="퇴근 후, 온전히 나에게 집중하는 시간."
            ),
            ContentOption(
                option_name="옵션 B (동기부여형)",
                image_url="https://via.placeholder.com/400x400.png?text=Muscle+Power",
                copy_text="지금 시작하면 여름엔 달라집니다."
            ),
            ContentOption(
                option_name="옵션 C (정보성)",
                image_url="https://via.placeholder.com/400x400.png?text=Expert+Analysis",
                copy_text="10년 차 트레이너가 알려주는 허리 통증 없는 데드리프트."
            )
        ],
        hashtags=["#오운완", "#판교PT", "#직장인운동", "#거북목교정"],
        upload_guide="퇴근 시간인 오후 6시 30분에 업로드하는 것을 추천합니다."
    )