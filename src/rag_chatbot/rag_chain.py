"""
RAG 체인 (Retrieval-Augmented Generation)

기능:
1. 검색 시스템 통합 (retriever.py)
2. Qwen3-30B-A3B-2507 생성 (Ollama GPU)
3. 대화 메모리 관리 (최근 5턴)
4. 컨텍스트 기반 응답 생성

사용법:
    from rag_chatbot.rag_chain import RAGChain

    rag = RAGChain()
    response = rag.chat("운동 방법을 알려줘")
    print(response)
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from langchain_community.llms import Ollama
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate

from .retriever import Retriever


class RAGChain:
    """RAG 체인"""

    def __init__(
        self,
        model_name: str = "qwen3-30b-a3b-2507:latest",
        ollama_base_url: str = "http://localhost:11434",
        milvus_host: str = "localhost",
        milvus_port: str = "19530",
        collection_name: str = "healthcare_docs",
        memory_k: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ):
        """
        Args:
            model_name: Ollama 모델 이름
            ollama_base_url: Ollama 서버 URL
            milvus_host: Milvus 호스트
            milvus_port: Milvus 포트
            collection_name: 컬렉션 이름
            memory_k: 대화 메모리 턴 수 (기본값: 5)
            temperature: 생성 temperature (기본값: 0.7)
            max_tokens: 최대 토큰 수 (기본값: 2048)
        """
        self.model_name = model_name
        self.ollama_base_url = ollama_base_url
        self.memory_k = memory_k
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Retriever 초기화
        print("🔧 Retriever 초기화 중...")
        self.retriever = Retriever(
            milvus_host=milvus_host,
            milvus_port=milvus_port,
            collection_name=collection_name
        )
        print("✅ Retriever 초기화 완료")

        # Ollama LLM 초기화
        print(f"🔧 Ollama LLM 초기화 중... (model: {model_name})")
        self.llm = Ollama(
            model=model_name,
            base_url=ollama_base_url,
            temperature=temperature,
            num_predict=max_tokens
        )
        print("✅ Ollama LLM 초기화 완료")

        # 대화 메모리 (최근 5턴)
        self.memory = ConversationBufferWindowMemory(
            k=memory_k,
            memory_key="chat_history",
            return_messages=True
        )

        # 프롬프트 템플릿
        self.prompt_template = PromptTemplate(
            input_variables=["context", "chat_history", "question"],
            template="""당신은 헬스케어 전문 상담사입니다. 제공된 문서를 기반으로 사용자의 질문에 답변하세요.

## 검색된 문서:
{context}

## 대화 기록:
{chat_history}

## 사용자 질문:
{question}

## 답변 지침:
1. 검색된 문서의 정보를 우선적으로 활용하세요.
2. 문서에 없는 내용은 일반적인 헬스케어 지식으로 보완하세요.
3. 친절하고 이해하기 쉽게 설명하세요.
4. 운동이나 식단 관련 질문에는 구체적인 예시를 제공하세요.
5. 관련 이미지가 있다면 언급하세요.

답변:"""
        )

    def format_context(self, search_results: List[Dict[str, Any]]) -> str:
        """
        검색 결과를 컨텍스트 문자열로 포맷팅

        Args:
            search_results: Retriever.search() 결과

        Returns:
            포맷팅된 컨텍스트 문자열
        """
        if not search_results:
            return "관련 문서를 찾지 못했습니다."

        context_parts = []
        for i, result in enumerate(search_results, 1):
            source_type = result["source_type"]
            source_path = result["source_path"]
            text = result["text"]
            score = result["score"]

            # 문서 정보
            context_part = f"[문서 {i}] (점수: {score:.3f}, 소스: {source_type})\n"
            context_part += f"파일: {source_path}\n"
            context_part += f"내용: {text}\n"

            # 이미지 경로 (있는 경우)
            if result.get("image_path"):
                context_part += f"이미지: {result['image_path']}\n"

            context_parts.append(context_part)

        return "\n".join(context_parts)

    def format_chat_history(self) -> str:
        """
        대화 기록을 문자열로 포맷팅

        Returns:
            포맷팅된 대화 기록 문자열
        """
        messages = self.memory.load_memory_variables({})
        if not messages or "chat_history" not in messages:
            return "없음"

        chat_history = messages["chat_history"]
        if not chat_history:
            return "없음"

        history_parts = []
        for msg in chat_history:
            if msg.type == "human":
                history_parts.append(f"사용자: {msg.content}")
            elif msg.type == "ai":
                history_parts.append(f"상담사: {msg.content}")

        return "\n".join(history_parts)

    def chat(
        self,
        question: str,
        top_k: int = 20,
        rerank_top_k: int = 5,
        source_type_filter: Optional[str] = None,
        return_sources: bool = False
    ) -> str:
        """
        RAG 기반 채팅

        Args:
            question: 사용자 질문
            top_k: Dense 검색 개수 (기본값: 20)
            rerank_top_k: 재순위 후 개수 (기본값: 5)
            source_type_filter: 소스 타입 필터 (pdf, image, json)
            return_sources: 소스 문서도 함께 반환할지 (기본값: False)

        Returns:
            return_sources=False: 응답 문자열
            return_sources=True: {"answer": "응답", "sources": [...]}
        """
        print("\n" + "="*60)
        print("RAG 체인 실행")
        print("="*60)
        print(f"질문: {question}")

        try:
            # 1. 문서 검색
            print("\n📚 문서 검색 중...")
            search_results = self.retriever.search(
                query=question,
                top_k=top_k,
                rerank_top_k=rerank_top_k,
                source_type_filter=source_type_filter
            )

            # 2. 컨텍스트 포맷팅
            context = self.format_context(search_results)

            # 3. 대화 기록 포맷팅
            chat_history = self.format_chat_history()

            # 4. 프롬프트 생성
            prompt = self.prompt_template.format(
                context=context,
                chat_history=chat_history,
                question=question
            )

            # 5. LLM 생성
            print("\n🤖 Qwen3-30B-A3B-2507 응답 생성 중...")
            response = self.llm.invoke(prompt)

            # 6. 메모리 저장
            self.memory.save_context(
                {"input": question},
                {"output": response}
            )

            print("✅ 응답 생성 완료")

            # 7. 결과 반환
            if return_sources:
                return {
                    "answer": response,
                    "sources": search_results
                }
            else:
                return response

        except Exception as e:
            error_msg = f"❌ RAG 체인 실행 중 오류 발생: {e}"
            print(error_msg)
            return error_msg

    def chat_with_image(
        self,
        question: str,
        image_path: Optional[str] = None,
        top_k: int = 20,
        rerank_top_k: int = 5
    ) -> str:
        """
        이미지 포함 채팅

        Args:
            question: 사용자 질문
            image_path: 사용자가 업로드한 이미지 경로 (선택)
            top_k: Dense 검색 개수
            rerank_top_k: 재순위 후 개수

        Returns:
            응답 문자열
        """
        # 이미지 경로가 제공된 경우 질문에 추가
        if image_path:
            question_with_image = f"{question}\n[사용자 이미지: {image_path}]"
        else:
            question_with_image = question

        return self.chat(
            question=question_with_image,
            top_k=top_k,
            rerank_top_k=rerank_top_k
        )

    def clear_memory(self):
        """대화 메모리 초기화"""
        print("🔄 대화 메모리 초기화 중...")
        self.memory.clear()
        print("✅ 대화 메모리 초기화 완료")

    def close(self):
        """리소스 정리"""
        print("\n🔄 리소스 정리 중...")
        self.retriever.close()
        print("✅ 리소스 정리 완료")


if __name__ == "__main__":
    """
    테스트 실행 예시
    """
    import sys

    print("="*60)
    print("RAG Chain 테스트")
    print("="*60)

    # RAG 체인 초기화
    rag = RAGChain()

    # 대화 시작
    print("\n💬 대화를 시작합니다. (종료: 'quit' 또는 'exit')")
    print("메모리 초기화: 'clear'")
    print("소스 문서 포함 응답: '/sources <질문>'")
    print("="*60)

    while True:
        try:
            # 사용자 입력
            user_input = input("\n사용자: ").strip()

            if not user_input:
                continue

            # 종료
            if user_input.lower() in ["quit", "exit", "종료"]:
                print("\n👋 대화를 종료합니다.")
                break

            # 메모리 초기화
            if user_input.lower() == "clear":
                rag.clear_memory()
                continue

            # 소스 문서 포함 응답
            if user_input.startswith("/sources "):
                question = user_input[9:].strip()
                result = rag.chat(question, return_sources=True)

                print(f"\n상담사: {result['answer']}")

                print("\n" + "="*60)
                print("참고 문서")
                print("="*60)
                for i, source in enumerate(result["sources"], 1):
                    print(f"\n[{i}] {source['source_type']} - 점수: {source['score']:.3f}")
                    print(f"파일: {source['source_path']}")
                    print(f"내용: {source['text'][:150]}...")
                    if source.get("image_path"):
                        print(f"이미지: {source['image_path']}")
                continue

            # 일반 채팅
            response = rag.chat(user_input)
            print(f"\n상담사: {response}")

        except KeyboardInterrupt:
            print("\n\n👋 대화를 종료합니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")

    # 정리
    rag.close()
