"""
Vector Retriever - Semantic search with LLM answer generation.
Searches Milvus for relevant context, formats it, and calls LLM to generate answer.
"""
import os
from typing import List, Dict, Any, Optional
from loguru import logger
from openai import OpenAI
from app.rag.vector_db_manager import VectorDBManager
from app.rag.document_loader import DocumentLoader


class VectorRetriever:
    """
    Retrieves relevant documents from Milvus and generates LLM answers.
    Priority: Milvus RAG → web search (handled by data_layer)
    """

    def __init__(self, vector_db: VectorDBManager, similarity_threshold: float = 0.5):
        self.vector_db = vector_db
        self.threshold = similarity_threshold
        self.loader = DocumentLoader()

        # LLM client for answer generation (DashScope qwen-plus)
        api_key = os.getenv("DASHSCOPE_API_KEY", "sk-46f3e548c7774726b1c6a94da442a496")
        self.llm = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.llm_model = os.getenv("LLM_MODEL", "qwen-plus")

    def query(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Full RAG query: search Milvus → build context → generate answer.

        Args:
            question: User question
            top_k: Number of chunks to retrieve

        Returns:
            Dict with {answer, sources, chunks_used, from_kb: bool}
        """
        # Step 1: Search Milvus
        chunks = self.vector_db.search(question, top_k=top_k, threshold=self.threshold)

        result = {
            "answer": "",
            "sources": [],
            "chunks_used": len(chunks),
            "from_kb": len(chunks) > 0,
        }

        if not chunks:
            result["answer"] = ""
            return result

        # Step 2: Extract unique sources
        seen_sources = set()
        for c in chunks:
            src = c.get("source", "unknown")
            if src not in seen_sources:
                result["sources"].append({"source": src, "score": c.get("score", 0)})
                seen_sources.add(src)

        # Step 3: Build context for LLM
        context = self._build_context(chunks)
        result["answer"] = self._generate_answer(question, context, chunks)

        logger.info(f"🎯 RAG query complete: {len(chunks)} chunks → {len(result['answer'])} char answer")
        return result

    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved chunks."""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            content = chunk.get("content", "").strip()
            source = chunk.get("source", "未知来源")
            if content:
                parts.append(f"[参考资料{i} - 来源: {source}]\n{content}")
        return "\n\n---\n\n".join(parts)

    def _generate_answer(
        self, question: str, context: str, chunks: List[Dict[str, Any]]
    ) -> str:
        """Generate answer using LLM with RAG context."""
        system_prompt = (
            "你是知识库问答助手。请基于提供的参考资料回答用户问题。\n\n"
            "规则：\n"
            "- 如果参考资料与问题相关，严格基于资料内容回答\n"
            "- 如果参考资料与问题无关，使用你的通用知识回答\n"
            "- 回答要结构化：使用 ### 小标题、**加粗**、- 列表\n"
            "- 引用参考资料时标注来源\n"
            "- 不要编造参考资料中没有的信息\n"
            "- 用中文回复"
        )

        user_prompt = f"参考资料：\n{context}\n\n用户问题：{question}"

        try:
            response = self.llm.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM answer generation failed: {e}")

            # Fallback: return context directly
            if chunks:
                best = chunks[0].get("content", "")[:500]
                return f"### 知识库检索结果\n\n{best}\n\n*（AI 回答生成失败，以上为最相关内容）*"
            return "抱歉，无法生成回答。请检查 API 配置。"

    def upload_document(self, file_path: str) -> Dict[str, Any]:
        """
        Load a document from file, embed it, and store in Milvus.

        Args:
            file_path: Path to the document

        Returns:
            Dict with {success, filename, chunks_inserted, error}
        """
        result = {"success": False, "filename": "", "chunks_inserted": 0, "error": ""}

        # Step 1: Load document text
        doc = self.loader.load(file_path)
        if doc.get("error"):
            result["error"] = doc["error"]
            return result

        texts = doc.get("texts", [])
        if not texts:
            result["error"] = "No text content extracted from document"
            return result

        # Step 2: Store in Milvus
        source = doc.get("filename", "upload")
        count = self.vector_db.add_documents(texts, source=source)

        result["success"] = count > 0
        result["filename"] = source
        result["chunks_inserted"] = count
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return self.vector_db.get_stats()