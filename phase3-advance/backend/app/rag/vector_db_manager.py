"""
Vector Database Manager - Core Milvus Integration
Self-contained: no LangChain dependency. Uses direct HTTP for embeddings.
"""
import os, re
from typing import List, Dict, Any, Optional
from loguru import logger
import httpx

from pymilvus import (
    connections, Collection, CollectionSchema, FieldSchema, DataType,
    utility, MilvusException
)


class RecursiveChineseTextSplitter:
    """Standalone recursive text splitter for Chinese text (no LangChain dependency)."""

    def __init__(self, chunk_size=500, chunk_overlap=50,
                 separators=None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]

    def split_text(self, text: str) -> List[str]:
        """Split text into chunks recursively."""
        if not text:
            return []
        return self._split_recursive(text, self.separators)

    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        if not separators:
            return self._split_by_size(text)
        sep = separators[0]
        remaining = separators[1:]

        if sep == "":
            return self._split_by_size(text)

        splits = text.split(sep)
        chunks = []
        current = ""
        for part in splits:
            candidate = (current + sep + part).strip(sep) if current else part
            if len(candidate) > self.chunk_size:
                if current:
                    chunks.append(current)
                if len(part) > self.chunk_size and remaining:
                    sub_chunks = self._split_recursive(part, remaining)
                    chunks.extend(sub_chunks)
                elif len(part) > self.chunk_size:
                    sub = self._split_by_size(part)
                    chunks.extend(sub)
                else:
                    current = part
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks

    def _split_by_size(self, text: str) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(text[start:end])
            start += self.chunk_size - self.chunk_overlap
        return chunks


class DashScopeEmbeddings:
    """Direct HTTP embedding via DashScope API (no LangChain)."""

    def __init__(self, api_key: str = None, model: str = "text-embedding-v1"):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def embed_query(self, text: str) -> List[float]:
        embeddings = self.embed_documents([text])
        return embeddings[0] if embeddings else [0.0] * 1536

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Batch embed documents."""
        if not texts:
            return []
        try:
            response = httpx.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                },
                timeout=30.0,
            )
            if response.status_code == 200:
                data = response.json()
                return [item["embedding"] for item in data.get("data", [])]
            else:
                logger.error(f"Embedding API error: {response.status_code} {response.text[:200]}")
        except Exception as e:
            logger.error(f"Embedding request failed: {e}")
        return [[0.0] * 1536] * len(texts)


class VectorDBManager:
    """Manages vector database for RAG knowledge base.
    Priority: Milvus (Docker) → ChromaDB (embedded, no Docker)."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        collection_name: str = "agent_rag",
        embedding_model: str = "text-embedding-v1",
        embedding_dim: int = 1536,
    ):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.collection = None
        self.connected = False
        self.backend = "unknown"  # milvus, chromadb, none

        self.text_splitter = RecursiveChineseTextSplitter(chunk_size=500, chunk_overlap=50)
        api_key = os.getenv("DASHSCOPE_API_KEY", "sk-46f3e548c7774726b1c6a94da442a496")
        self.embeddings = DashScopeEmbeddings(api_key=api_key, model=embedding_model)

        # Try Milvus first, fall back to ChromaDB
        if self._try_connect_milvus():
            self.backend = "milvus"
            if self.connected:
                self._init_milvus_collection()
        else:
            logger.info("[RAG_DEBUG] Milvus unavailable → trying ChromaDB (embedded, no Docker)")
            if self._init_chromadb():
                self.backend = "chromadb"
            else:
                self.backend = "none"
                logger.warning("[RAG_DEBUG] ⚠️ Both Milvus and ChromaDB unavailable. RAG disabled.")

    def _try_connect_milvus(self) -> bool:
        """Try connecting to Milvus. Returns True if port is open (even if connection fails later)."""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            if result != 0:
                logger.info(f"[MILVUS_DEBUG] Port {self.port} closed — Milvus not running")
                return False

            connections.connect(alias="default", host=self.host, port=self.port, timeout=5)
            self.connected = True
            logger.info(f"[MILVUS_DEBUG] ✅ Connected to Milvus at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.warning(f"[MILVUS_DEBUG] Connection failed: {e}")
            self.connected = False
            return True  # port was open but connection failed → don't try ChromaDB

    def _init_milvus_collection(self):
        try:
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                self.collection.load()
                logger.info(f"[MILVUS_DEBUG] 📚 Loaded collection: {self.collection_name}")
            else:
                fields = [
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=5000),
                    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=500),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
                ]
                schema = CollectionSchema(fields, description="RAG knowledge base")
                self.collection = Collection(self.collection_name, schema)
                index_params = {"metric_type": "IP", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
                self.collection.create_index("embedding", index_params)
                self.collection.load()
                logger.info(f"[MILVUS_DEBUG] ✅ Created collection: {self.collection_name}")
        except Exception as e:
            logger.warning(f"[MILVUS_DEBUG] Collection init failed: {e}")
            self.collection = None

    def _init_chromadb(self) -> bool:
        """Initialize ChromaDB as fallback (pure Python, no Docker)."""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self._chroma_client = chromadb.Client(ChromaSettings(
                anonymized_telemetry=False,
                is_persistent=True,
                persist_directory="./workspace/chroma_db",
            ))
            # Get or create collection
            try:
                self._chroma_collection = self._chroma_client.get_collection(self.collection_name)
                logger.info(f"[RAG_DEBUG] ✅ ChromaDB loaded existing collection: {self.collection_name}")
            except:
                self._chroma_collection = self._chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"[RAG_DEBUG] ✅ ChromaDB created new collection: {self.collection_name}")
            self.connected = True
            logger.info(f"[RAG_DEBUG] ✅ RAG backend: ChromaDB (embedded) at ./workspace/chroma_db")
            return True
        except ImportError:
            logger.warning("[RAG_DEBUG] ⚠️ chromadb not installed. Run: pip install chromadb")
            return False
        except Exception as e:
            logger.warning(f"[RAG_DEBUG] ⚠️ ChromaDB init failed: {e}")
            return False



    def add_documents(self, documents: List[str], source: str = "upload") -> int:
        if not self.connected:
            return 0
        all_chunks = []
        for doc in documents:
            if doc and doc.strip():
                chunks = self.text_splitter.split_text(doc)
                all_chunks.extend(chunks)
        if not all_chunks:
            return 0
        try:
            if self.backend == "chromadb":
                embeddings_list = self.embeddings.embed_documents(all_chunks)
                ids = [f"{source}_{i}_{hash(c[-30:])}" for i, c in enumerate(all_chunks)]
                self._chroma_collection.add(
                    embeddings=embeddings_list,
                    documents=all_chunks,
                    metadatas=[{"source": source}] * len(all_chunks),
                    ids=ids,
                )
                logger.info(f"📝 ChromaDB: Inserted {len(all_chunks)} chunks from '{source}'")
                return len(all_chunks)
            elif self.backend == "milvus" and self.collection:
                embeddings_list = self.embeddings.embed_documents(all_chunks)
                sources = [source] * len(all_chunks)
                data = [all_chunks, sources, embeddings_list]
                mr = self.collection.insert(data)
                self.collection.flush()
                logger.info(f"📝 Milvus: Inserted {len(mr.primary_keys)} chunks from '{source}'")
                return len(mr.primary_keys)
        except Exception as e:
            logger.error(f"Failed to insert documents: {e}")
        return 0

    def search(self, query: str, top_k: int = 5, threshold: float = 0.5) -> List[Dict[str, Any]]:
        if not self.connected:
            return []
        try:
            if self.backend == "chromadb":
                query_embedding = self.embeddings.embed_query(query)
                results = self._chroma_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                )
                hits = []
                if results and results.get("documents") and results["documents"][0]:
                    for i, doc in enumerate(results["documents"][0]):
                        score = 1.0 - (results.get("distances", [[1.0]])[0][i] if results.get("distances") else 0.0)
                        meta = results.get("metadatas", [[{}]])[0][i] if results.get("metadatas") else {}
                        if score >= threshold:
                            hits.append({
                                "content": doc,
                                "source": meta.get("source", "unknown") if isinstance(meta, dict) else "unknown",
                                "score": round(score, 4),
                            })
                logger.info(f"🔍 ChromaDB search returned {len(hits)} results")
                return hits
            elif self.backend == "milvus" and self.collection:
                query_embedding = self.embeddings.embed_query(query)
                search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
                results = self.collection.search(
                    data=[query_embedding], anns_field="embedding",
                    param=search_params, limit=top_k, output_fields=["content", "source"],
                )
                hits = []
                for hit in results[0]:
                    score = hit.distance
                    if score >= threshold:
                        hits.append({
                            "content": hit.entity.get("content", ""),
                            "source": hit.entity.get("source", ""),
                            "score": round(score, 4),
                        })
                logger.info(f"🔍 Milvus search returned {len(hits)} results")
                return hits
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
        return []

    def delete_by_source(self, source: str) -> int:
        if not self.connected:
            return 0
        try:
            if self.backend == "chromadb":
                # ChromaDB delete by metadata filter
                results = self._chroma_collection.get(where={"source": source})
                if results and results.get("ids"):
                    self._chroma_collection.delete(ids=results["ids"])
                    count = len(results["ids"])
                    logger.info(f"🗑️ ChromaDB: Deleted {count} records for source '{source}'")
                    return count
                return 0
            elif self.backend == "milvus" and self.collection:
                expr = f'source == "{source}"'
                count = self.collection.delete(expr)
                self.collection.flush()
                logger.info(f"🗑️ Milvus: Deleted {count} records for source '{source}'")
                return count
        except Exception as e:
            logger.error(f"Delete failed: {e}")
        return 0

    def get_stats(self) -> Dict[str, Any]:
        if not self.connected:
            return {"connected": False, "collection": self.collection_name, "backend": self.backend, "total_chunks": 0}
        try:
            if self.backend == "chromadb":
                return {"connected": True, "collection": self.collection_name, "backend": "chromadb", "total_chunks": self._chroma_collection.count()}
            elif self.backend == "milvus" and self.collection:
                return {"connected": True, "collection": self.collection_name, "backend": "milvus", "total_chunks": self.collection.num_entities}
        except:
            pass
        return {"connected": True, "collection": self.collection_name, "backend": self.backend, "total_chunks": 0}

    def close(self):
        try:
            connections.disconnect("default")
        except:
            pass
