# /home/spai0323/Ad_Content_Creation_Service_Team3/test/prompt_self_test.py
import os
import sys
import re
from typing import Dict, Any, Optional
from pprint import pprint

# ============================================================
# 📌 경로 설정 — backend 패키지가 import 가능하도록 sys.path에 추가
# ============================================================

PROJECT_ROOT = "/home/spai0323/Ad_Content_Creation_Service_Team3"
SRC_PATH = os.path.join(PROJECT_ROOT, "src")   # backend 상위 폴더

if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

# 이제 backend 패키지 import 가능
from backend import services
from backend.model_registry import get_registry

registry = get_registry()   # 반드시 import 바로 아래!

# ============================================================
# 🔍 보조 함수
# ============================================================

def has_korean(text: str) -> bool:
    """한글 포함 여부 간단 체크"""
    return bool(re.search(r"[가-힣]", text or ""))


def rough_token_count(text: str) -> int:
    """아주 단순한 토큰 수 근사치 (공백 기준)"""
    if not text:
        return 0
    return len(text.split())


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"🔎 {title}")
    print("=" * 80)


# ============================================================
# 🔬 단일 테스트 실행
# ============================================================

def run_single_test(
    name: str,
    raw_prompt: str,
    context: Optional[Dict[str, Any]],
    model_name: str
):
    print_header(f"테스트 케이스: {name}")
    print(f"📌 모델: {model_name}")
    print(f"📥 RAW 프롬프트: {raw_prompt!r}")
    if context:
        print(f"📥 컨텍스트: {context}")

    model_config = registry.get_model(model_name)
    if not model_config:
        print(f"❌ 모델 설정을 찾을 수 없습니다: {model_name}")
        return

    try:
        final_prompt = services.build_final_prompt_v2(
            raw_prompt=raw_prompt,
            context=context,
            model_config=model_config,
        )
    except Exception as e:
        print(f"❌ build_final_prompt_v2 실행 중 예외 발생: {e}")
        return

    print("-" * 80)
    print(f"📤 최종 프롬프트:\n{final_prompt}\n")

    raw_tokens = rough_token_count(raw_prompt)
    final_tokens = rough_token_count(final_prompt)

    print(f"🔢 토큰 수 추정: RAW={raw_tokens}, FINAL={final_tokens}")

    warnings = []

    # FLUX 모델 판정
    is_flux = "flux" in (getattr(model_config, "type") or "").lower()

    if is_flux:
        if final_tokens > 70:
            warnings.append(f"FLUX 프롬프트가 너무 길어 보입니다 (약 {final_tokens} 토큰).")

        if has_korean(final_prompt):
            warnings.append("FLUX 최종 프롬프트에 한글이 남아 있습니다.")

        banned_keywords = ["negative prompt", "low quality", "worst quality"]
        for kw in banned_keywords:
            if kw.lower() in final_prompt.lower():
                warnings.append(f"FLUX 금지 표현 포함 가능성: {kw}")

    if raw_prompt.strip() and not final_prompt.strip():
        warnings.append("RAW는 비어있지 않은데 FINAL이 비어 있음")

    if warnings:
        print("\n⚠ 경고:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("✅ 특이사항 없음")


# ============================================================
# 🧪 테스트 케이스 실행
# ============================================================

def main():
    print_header("프롬프트 최적화 셀프 테스트 툴")

    # OpenAI 사용 여부
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("⚠ OPENAI_API_KEY 없음 → GPT 최적화는 비활성화됨.")
    else:
        print("✅ OPENAI_API_KEY 설정됨 → GPT 최적화 사용 가능")

    opt_config = registry.get_prompt_optimization_config()
    print(f"\n🧩 prompt_optimization 설정: {opt_config}")

    # FLUX 모델 우선 선택
    candidate_models = list(registry.models.keys())
    flux_models = [
        name for name in candidate_models
        if "flux" in (registry.get_model(name).type or "").lower()
    ]
    if flux_models:
        default_model_name = flux_models[0]
    else:
        default_model_name = registry.get_primary_model()

    print(f"\n🎯 기본 테스트 모델: {default_model_name}\n")

    # 테스트 케이스 구성
    test_cases = [
        {
            "name": "한국어 간단 프롬프트",
            "raw": "따뜻한 감성의 요가 스튜디오",
            "context": {"style": "clean", "mood": "warm"},
        },
        {
            "name": "한국어 + caption",
            "raw": "편안한 분위기의 필라테스 공간",
            "context": {
                "style": "instagram",
                "mood": "cozy",
                "caption": "1:1 프리미엄 케어 프로그램"
            },
        },
        {
            "name": "영어 프롬프트",
            "raw": "a bright fitness studio with soft natural light",
            "context": {"style": "professional", "mood": "fresh"},
        },
        {
            "name": "아주 짧은 프롬프트",
            "raw": "헬스장",
            "context": {"style": "minimal", "mood": "clean"},
        },
        {
            "name": "스트레스 테스트 (한국어 긴문장)",
            "raw": (
                "강남에 위치한 프리미엄 헬스장, 자연광이 들어오는 넓은 공간, "
                "전문 트레이너의 1:1 코칭, 고급 머신들로 가득 찬 시설"
            ),
            "context": {"style": "luxury", "mood": "premium"},
        },
    ]

    # 실행
    for case in test_cases:
        run_single_test(
            name=case["name"],
            raw_prompt=case["raw"],
            context=case.get("context"),
            model_name=default_model_name,
        )

    print("\n\n🎉 모든 테스트 케이스 실행 완료!\n")


if __name__ == "__main__":
    main()
