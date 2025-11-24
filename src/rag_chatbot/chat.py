"""
RAG 챗봇 터미널 인터페이스

기능:
1. 텍스트 질문 입력
2. 이미지 경로 입력 지원
3. 관련 이미지 경로 출력
4. 대화 메모리 관리
5. 소스 문서 표시

사용법:
    python -m src.rag_chatbot.chat

명령어:
    - 일반 채팅: 질문 입력
    - 이미지 포함: /image <이미지 경로> <질문>
    - 소스 표시: /sources <질문>
    - 메모리 초기화: /clear
    - 도움말: /help
    - 종료: /quit, /exit, quit, exit
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

from .rag_chain import RAGChain


class ChatInterface:
    """터미널 채팅 인터페이스"""

    def __init__(
        self,
        model_name: str = "qwen3-30b-a3b-2507:latest",
        ollama_base_url: str = "http://localhost:11434",
        milvus_host: str = "localhost",
        milvus_port: str = "19530"
    ):
        """
        Args:
            model_name: Ollama 모델 이름
            ollama_base_url: Ollama 서버 URL
            milvus_host: Milvus 호스트
            milvus_port: Milvus 포트
        """
        self.model_name = model_name
        self.ollama_base_url = ollama_base_url
        self.milvus_host = milvus_host
        self.milvus_port = milvus_port

        # RAG 체인
        self.rag = None
        self.initialized = False

    def initialize(self):
        """RAG 체인 초기화"""
        if not self.initialized:
            print("\n" + "="*60)
            print("RAG 챗봇 초기화 중...")
            print("="*60)

            try:
                self.rag = RAGChain(
                    model_name=self.model_name,
                    ollama_base_url=self.ollama_base_url,
                    milvus_host=self.milvus_host,
                    milvus_port=self.milvus_port
                )
                self.initialized = True
                print("\n✅ RAG 챗봇 초기화 완료")
            except Exception as e:
                print(f"\n❌ 초기화 실패: {e}")
                print("\n확인 사항:")
                print("1. Milvus Docker가 실행 중인지 확인: docker ps")
                print("2. Ollama 서버가 실행 중인지 확인: ollama list")
                print(f"3. Qwen3-30B-A3B-2507 모델이 설치되어 있는지 확인")
                sys.exit(1)

    def print_welcome(self):
        """환영 메시지 출력"""
        print("\n" + "="*60)
        print("🏥 헬스케어 RAG 챗봇")
        print("="*60)
        print("\n💬 대화를 시작합니다.")
        print("\n📌 명령어:")
        print("  - 일반 채팅: 질문 입력")
        print("  - 이미지 포함: /image <이미지 경로> <질문>")
        print("  - 소스 표시: /sources <질문>")
        print("  - 메모리 초기화: /clear")
        print("  - 도움말: /help")
        print("  - 종료: /quit, /exit")
        print("="*60)

    def print_help(self):
        """도움말 출력"""
        print("\n" + "="*60)
        print("📖 명령어 도움말")
        print("="*60)
        print("\n1. 일반 채팅")
        print("   예시: 운동 방법을 알려줘")
        print("\n2. 이미지 포함 채팅")
        print("   예시: /image data/user_uploads/pose.jpg 이 자세가 맞나요?")
        print("\n3. 소스 문서 표시")
        print("   예시: /sources 다이어트 식단 추천해줘")
        print("\n4. 메모리 초기화")
        print("   예시: /clear")
        print("\n5. 도움말")
        print("   예시: /help")
        print("\n6. 종료")
        print("   예시: /quit 또는 /exit")
        print("="*60)

    def handle_image_command(self, user_input: str):
        """이미지 포함 채팅 처리"""
        parts = user_input[7:].strip().split(maxsplit=1)

        if len(parts) < 2:
            print("\n⚠️  사용법: /image <이미지 경로> <질문>")
            print("   예시: /image data/user_uploads/pose.jpg 이 자세가 맞나요?")
            return

        image_path, question = parts

        # 이미지 파일 존재 확인
        if not Path(image_path).exists():
            print(f"\n⚠️  이미지 파일을 찾을 수 없습니다: {image_path}")
            return

        # 이미지 포함 채팅
        response = self.rag.chat_with_image(
            question=question,
            image_path=image_path
        )

        print(f"\n상담사: {response}")

    def handle_sources_command(self, user_input: str):
        """소스 문서 표시 채팅 처리"""
        question = user_input[9:].strip()

        if not question:
            print("\n⚠️  사용법: /sources <질문>")
            print("   예시: /sources 운동 방법을 알려줘")
            return

        # 소스 포함 채팅
        result = self.rag.chat(question, return_sources=True)

        print(f"\n상담사: {result['answer']}")

        # 소스 문서 출력
        print("\n" + "="*60)
        print("📚 참고 문서")
        print("="*60)

        for i, source in enumerate(result["sources"], 1):
            print(f"\n[{i}] {source['source_type']} - 점수: {source['score']:.3f}")
            print(f"파일: {source['source_path']}")
            print(f"내용: {source['text'][:200]}...")

            if source.get("image_path"):
                print(f"🖼️  이미지: {source['image_path']}")

    def handle_normal_chat(self, user_input: str):
        """일반 채팅 처리"""
        response = self.rag.chat(user_input)
        print(f"\n상담사: {response}")

    def run(self):
        """채팅 인터페이스 실행"""
        # 초기화
        self.initialize()

        # 환영 메시지
        self.print_welcome()

        # 채팅 루프
        while True:
            try:
                # 사용자 입력
                user_input = input("\n사용자: ").strip()

                if not user_input:
                    continue

                # 종료
                if user_input.lower() in ["/quit", "/exit", "quit", "exit", "종료"]:
                    print("\n👋 대화를 종료합니다.")
                    break

                # 도움말
                if user_input.lower() == "/help":
                    self.print_help()
                    continue

                # 메모리 초기화
                if user_input.lower() == "/clear":
                    self.rag.clear_memory()
                    continue

                # 이미지 포함 채팅
                if user_input.startswith("/image "):
                    self.handle_image_command(user_input)
                    continue

                # 소스 문서 표시 채팅
                if user_input.startswith("/sources "):
                    self.handle_sources_command(user_input)
                    continue

                # 일반 채팅
                self.handle_normal_chat(user_input)

            except KeyboardInterrupt:
                print("\n\n👋 대화를 종료합니다.")
                break
            except Exception as e:
                print(f"\n❌ 오류 발생: {e}")
                print("계속 진행하려면 Enter를 누르세요...")
                input()

        # 정리
        if self.rag:
            self.rag.close()

        print("\n✅ RAG 챗봇을 종료했습니다.\n")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="RAG 챗봇 터미널 인터페이스"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="qwen3-30b-a3b-2507:latest",
        help="Ollama 모델 이름 (기본값: qwen3-30b-a3b-2507:latest)"
    )

    parser.add_argument(
        "--ollama-url",
        type=str,
        default="http://localhost:11434",
        help="Ollama 서버 URL (기본값: http://localhost:11434)"
    )

    parser.add_argument(
        "--milvus-host",
        type=str,
        default="localhost",
        help="Milvus 호스트 (기본값: localhost)"
    )

    parser.add_argument(
        "--milvus-port",
        type=str,
        default="19530",
        help="Milvus 포트 (기본값: 19530)"
    )

    args = parser.parse_args()

    # 채팅 인터페이스 실행
    chat = ChatInterface(
        model_name=args.model,
        ollama_base_url=args.ollama_url,
        milvus_host=args.milvus_host,
        milvus_port=args.milvus_port
    )

    chat.run()


if __name__ == "__main__":
    main()
