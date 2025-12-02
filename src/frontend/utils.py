"""
프론트엔드 유틸리티 함수
"""
import re


class PromptHelper:
    """프롬프트 조합 유틸리티"""
    
    @staticmethod
    def combine_caption_and_prompt(
        main_prompt: str,
        caption: str = "",
        hashtags: str = "",
        connect_mode: bool = False
    ) -> str:
        """페이지1 문구와 사용자 프롬프트 조합
        
        Args:
            main_prompt: 사용자가 직접 입력한 기본 프롬프트
            caption: 페이지1에서 생성된 캡션
            hashtags: 페이지1에서 생성된 해시태그
            connect_mode: 페이지1 문구와 연결할지 여부
            
        Returns:
            조합된 최종 프롬프트 (백엔드에서 추가 처리됨)
        """
        if not connect_mode or not caption:
            return main_prompt.strip()
        
        if main_prompt.strip():
            return f"{main_prompt.strip()} — {caption} {hashtags}".strip()
        return f"{caption} {hashtags}".strip()
    
    @staticmethod
    def build_support_prompt(
        text: str,
        method: str = "단순 키워드 변환",
        strength: str = "중간"
    ) -> str:
        """보조 프롬프트 생성 (I2I, 편집 공용)
        
        Args:
            text: 원본 텍스트
            method: 변환 방식 ("단순 키워드 변환", "GPT 기반 자연스럽게", "사용자 조절형 혼합")
            strength: 적용 강도 ("약하게", "중간", "강하게")
            
        Returns:
            가중치가 적용된 프롬프트 문자열 (예: "(keywords:0.6)")
        """
        if not text:
            return ""
        
        # 방식별 처리
        base_prompts = {
            "단순 키워드 변환": ", ".join(re.split(r"[ ,.\n]+", text)[:20]),
            "GPT 기반 자연스럽게": f"{text}, cinematic soft light, premium mood, refined rendering",
            "사용자 조절형 혼합": f"{text}, balanced framing, clean aesthetic"
        }
        base = base_prompts.get(method, text)
        
        # 강도 적용
        weights = {"약하게": "0.3", "중간": "0.6", "강하게": "1.0"}
        weight = weights.get(strength, "0.6")
        
        return f"({base}:{weight})"
