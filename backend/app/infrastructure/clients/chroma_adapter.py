# app/infrastructure/clients/chroma_adapter.py
import os
from typing import List, Dict, Optional
import chromadb
from google import genai

from app.ports.vector_store import VectorStoreRepository
from app.infrastructure.settings.config import settings


class ChromaVectorStoreRepository(VectorStoreRepository):
    def __init__(self, persist_directory: Optional[str] = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Falta la variable de entorno GEMINI_API_KEY")

        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIRECTORY
        
        # Cliente oficial de Google GenAI para generar embeddings
        self.genai_client = genai.Client(api_key=api_key)
        self.embedding_model = "gemini-embedding-2"

        # Cliente Nativo de ChromaDB
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=chromadb.Settings(anonymized_telemetry=False)
            )
        except Exception:
            try:
                from chromadb.api.shared_system_client import SharedSystemClient
                SharedSystemClient._identifier_to_system.clear()
            except Exception:
                pass
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=chromadb.Settings(anonymized_telemetry=False)
            )

        self.collection = self.chroma_client.get_or_create_collection(
            name="escuela_summaries",
            metadata={"hnsw:space": "cosine"}
        )

    def _generate_embedding(self, text: str) -> List[float]:
        response = self.genai_client.models.embed_content(
            model=self.embedding_model,
            contents=text
        )
        return response.embeddings[0].values

    def add_summary(self, summary_id: int, target_date: str, group_name: str, summary_text: str) -> None:
        embedding_vector = self._generate_embedding(summary_text)
        doc_id = f"summary_{summary_id}"
        
        self.collection.upsert(
            ids=[doc_id],
            embeddings=[embedding_vector],
            documents=[summary_text],
            metadatas=[{
                "summary_id": summary_id,
                "target_date": target_date,
                "group_name": group_name
            }]
        )

    def search_similar(self, query: str, group_name: Optional[str] = None, limit: int = 4) -> List[Dict]:
        query_vector = self._generate_embedding(query)
        where_filter = None
        if group_name and group_name.strip():
            where_filter = {"group_name": group_name.strip()}

        res = self.collection.query(
            query_embeddings=[query_vector],
            n_results=limit,
            where=where_filter
        )

        results = []
        if res and res.get("documents") and len(res["documents"]) > 0:
            documents = res["documents"][0]
            metadatas = res["metadatas"][0] if res.get("metadatas") else [{}] * len(documents)
            distances = res["distances"][0] if res.get("distances") else [0.0] * len(documents)

            for doc_content, meta, dist in zip(documents, metadatas, distances):
                results.append({
                    "content": doc_content,
                    "metadata": meta,
                    "score": float(dist)
                })

        return results
