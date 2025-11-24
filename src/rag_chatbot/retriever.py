"""
검색 시스템 (Retriever)

기능:
1. Milvus Dense 검색 (top-20)
2. BGE-M3 ColBERT 재순위 (top-5)
3. 이미지 경로 포함 반환

사용법:
    from rag_chatbot.retriever import Retriever

    retriever = Retriever()
    results = retriever.search("운동 방법 알려줘")

    for result in results:
        print(result["text"])
        if result.get("image_path"):
            print(f"이미지: {result['image_path']}")
"""

from typing import List, Dict, Any, Optional
import torch
from pathlib import Path
from sentence_transformers import SentenceTransformer
from FlagEmbedding import BGEM3FlagModel

from .vector_store import MilvusVectorStore


class Retriever:
    """검색 및 재순위 시스템"""

    def __init__(
        self,
        milvus_host: str = "localhost",
        milvus_port: str = "19530",
        collection_name: str = "healthcare_docs",
        embed_model_name: str = "BAAI/bge-m3",
        device: Optional[str] = None
    ):
        """
        Args:
            milvus_host: Milvus 호스트
            milvus_port: Milvus 포트
            collection_name: 컬렉션 이름
            embed_model_name: BGE-M3 모델 경로
            device: 디바이스 (None이면 자동 선택)
        """
        self.milvus_host = milvus_host
        self.milvus_port = milvus_port
        self.collection_name = collection_name
        self.embed_model_name = embed_model_name

        # 디바이스 설정
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        # Milvus 연결
        self.vector_store = MilvusVectorStore(
            host=milvus_host,
            port=milvus_port
        )
        self.vector_store.connect()

        # BGE-M3 모델 (lazy loading)
        self.model = None

    def load_model(self):
        """BGE-M3 모델 로딩"""
        if self.model is None:
            print(f"📥 BGE-M3 모델 로딩 중... (device: {self.device})")
            self.model = BGEM3FlagModel(
                self.embed_model_name,
                use_fp16=True if self.device == "cuda" else False
            )
            print("✅ BGE-M3 모델 로딩 완료")

    def unload_model(self):
        """BGE-M3 모델 언로딩"""
        if self.model is not None:
            print("🔄 BGE-M3 모델 언로딩 중...")
            del self.model
            self.model = None

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            print("✅ BGE-M3 모델 언로딩 완료")

    def search(
        self,
        query: str,
        top_k: int = 20,
        rerank_top_k: int = 5,
        source_type_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        검색 및 재순위

        Args:
            query: 검색 쿼리
            top_k: Dense 검색 상위 k개 (기본값: 20)
            rerank_top_k: 재순위 후 상위 k개 (기본값: 5)
            source_type_filter: 소스 타입 필터 (pdf, image, json)

        Returns:
            재순위된 문서 리스트 (각 문서는 dict)
            [
                {
                    "text": "문서 텍스트",
                    "source_type": "pdf|image|json",
                    "source_path": "파일 경로",
                    "metadata": {...},
                    "score": 0.95,  # 재순위 점수
                    "image_path": "이미지 경로" (있는 경우)
                },
                ...
            ]
        """
        print(f"\n{'='*60}")
        print(f"검색 쿼리: {query}")
        print(f"{'='*60}")

        try:
            # 1. BGE-M3 모델 로딩
            self.load_model()

            # 2. 쿼리 임베딩 (Dense만)
            print(f"\n🔍 쿼리 임베딩 중...")
            query_embedding_dict = self.model.encode(
                [query],
                batch_size=1,
                max_length=8192
            )
            query_vector = query_embedding_dict["dense_vecs"][0]

            # 3. Milvus Dense 검색 (top-20)
            print(f"🔍 Milvus Dense 검색 중... (top-{top_k})")

            # 소스 타입 필터 표현식
            expr = None
            if source_type_filter:
                expr = f'source_type == "{source_type_filter}"'

            search_results = self.vector_store.search(
                query_vector=query_vector.tolist(),
                top_k=top_k,
                expr=expr
            )

            if not search_results:
                print("⚠️  검색 결과가 없습니다.")
                return []

            print(f"✅ {len(search_results)}개 문서 검색 완료")

            # 4. BGE-M3 ColBERT 재순위 (top-5)
            print(f"\n🔄 BGE-M3 ColBERT 재순위 중... (top-{rerank_top_k})")

            # 문서 텍스트 추출
            docs_text = [doc["text"] for doc in search_results]

            # ColBERT 재순위 (BGE-M3의 compute_score 사용)
            rerank_scores = []
            for doc_text in docs_text:
                # BGE-M3 ColBERT 점수 계산
                score_dict = self.model.compute_score(
                    [[query, doc_text]],
                    weights_for_different_modes=[0.0, 1.0, 0.0]  # ColBERT만 사용
                )
                score = score_dict["colbert"][0]
                rerank_scores.append(score)

            # 점수 기준 정렬
            scored_docs = list(zip(search_results, rerank_scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)

            # 상위 rerank_top_k개 선택
            top_docs = scored_docs[:rerank_top_k]

            # 결과 포맷팅
            results = []
            for doc, score in top_docs:
                result = {
                    "text": doc["text"],
                    "source_type": doc["source_type"],
                    "source_path": doc["source_path"],
                    "metadata": doc["metadata"],
                    "score": float(score)
                }

                # 이미지 경로 추가 (이미지 소스 타입이거나 메타데이터에 있는 경우)
                if doc["source_type"] == "image":
                    result["image_path"] = doc["source_path"]
                elif "image_path" in doc["metadata"]:
                    result["image_path"] = doc["metadata"]["image_path"]

                results.append(result)

            print(f"✅ 재순위 완료 ({len(results)}개 문서)")

            # 5. 결과 출력
            print(f"\n{'='*60}")
            print("검색 결과")
            print(f"{'='*60}")
            for i, result in enumerate(results, 1):
                print(f"\n[{i}] 점수: {result['score']:.4f}")
                print(f"소스: {result['source_type']} - {result['source_path']}")
                print(f"텍스트: {result['text'][:100]}...")
                if result.get("image_path"):
                    print(f"이미지: {result['image_path']}")

            return results

        finally:
            # 6. 모델 언로딩 (항상 실행)
            self.unload_model()

    def close(self):
        """리소스 정리"""
        self.unload_model()
        self.vector_store.close()


if __name__ == "__main__":
    """
    테스트 실행 예시
    """
    import sys

    # 검색 쿼리
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "운동 방법을 알려줘"

    print("="*60)
    print("RAG Retriever 테스트")
    print("="*60)
    print(f"쿼리: {query}")

    # Retriever 초기화
    retriever = Retriever()

    # 검색
    results = retriever.search(
        query=query,
        top_k=20,
        rerank_top_k=5
    )

    # 결과 출력
    print("\n" + "="*60)
    print("최종 결과")
    print("="*60)
    for i, result in enumerate(results, 1):
        print(f"\n[{i}] {result['source_type']} - 점수: {result['score']:.4f}")
        print(f"파일: {result['source_path']}")
        print(f"내용: {result['text'][:200]}...")
        if result.get("image_path"):
            print(f"이미지: {result['image_path']}")

    # 정리
    retriever.close()
