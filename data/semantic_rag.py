"""Semantic RAG search using FAISS embeddings."""
import os
import json
import sqlite3
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

# Fallback: simple TF-IDF-like approach if sentence-transformers not available
class SimpleEmbedder:
    """Simple embedder using word frequencies as fallback."""
    
    def __init__(self, dim: int = 384):
        self.dim = dim
        self.vocab: dict[str, int] = {}
    
    def encode(self, texts: List[str], normalize_embeddings: bool = True) -> np.ndarray:
        """Generate simple embeddings based on word frequencies."""
        # Build vocabulary from all texts
        all_words = set()
        for text in texts:
            all_words.update(text.lower().split())
        
        # Map words to indices
        for word in all_words:
            if word not in self.vocab:
                self.vocab[word] = len(self.vocab) % self.dim
        
        # Generate embeddings
        embeddings = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            words = text.lower().split()
            for word in words:
                idx = self.vocab.get(word, 0)
                embeddings[i, idx] += 1
            
            # Normalize
            if normalize_embeddings:
                norm = np.linalg.norm(embeddings[i])
                if norm > 0:
                    embeddings[i] /= norm
        
        return embeddings
    
    def get_sentence_embedding_dimension(self) -> int:
        return self.dim


class SemanticRAGStore:
    """Semantic RAG store using FAISS for vector similarity search."""
    
    def __init__(self, db_path: str = "chefchat.db", model_name: str = "all-MiniLM-L6-v2", index_path: str = "rag_index.faiss"):
        self.db_path = db_path
        self.model_name = model_name
        self.index_path = index_path
        self.model = None
        self.index = None
        self.document_ids = []
        self.document_texts = []
        self._init_tables()
        self._load_or_create_index()
    
    def _init_tables(self) -> None:
        """Initialize tables for semantic RAG."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS SemanticChunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento_id INTEGER,
                chunk_text TEXT NOT NULL,
                embedding_id INTEGER,
                metadata TEXT,
                FOREIGN KEY (documento_id) REFERENCES DocumentosRAG(id)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_doc 
            ON SemanticChunks(documento_id)
        """)
        conn.commit()
        conn.close()
    
    def _load_model(self):
        """Load the sentence transformer model or use simple embedder."""
        if self.model is None:
            if HAS_SENTENCE_TRANSFORMERS:
                self.model = SentenceTransformer(self.model_name)
            else:
                self.model = SimpleEmbedder()
    
    def _load_or_create_index(self):
        """Load existing FAISS index or create new one."""
        if not HAS_FAISS:
            return
        
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            # Load document metadata
            meta_path = self.index_path.replace('.faiss', '_meta.json')
            if os.path.exists(meta_path):
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    self.document_ids = meta.get('document_ids', [])
                    self.document_texts = meta.get('document_texts', [])
        else:
            # Create new index
            self._load_model()
            embedding_dim = self.model.get_sentence_embedding_dimension()
            self.index = faiss.IndexFlatIP(embedding_dim)  # Inner product for cosine similarity
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        return chunks
    
    def add_document(self, doc_id: int, text: str, metadata: Optional[Dict] = None) -> int:
        """Add a document to the semantic index."""
        if not HAS_FAISS or not HAS_SENTENCE_TRANSFORMERS:
            return 0
        
        self._load_model()
        chunks = self._chunk_text(text)
        added = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for chunk in chunks:
            # Generate embedding
            embedding = self.model.encode([chunk], normalize_embeddings=True)[0]
            
            # Add to FAISS index
            self.index.add(embedding.reshape(1, -1))
            
            # Save to SQLite
            cursor.execute("""
                INSERT INTO SemanticChunks (documento_id, chunk_text, metadata)
                VALUES (?, ?, ?)
            """, (doc_id, chunk, json.dumps(metadata or {})))
            
            chunk_id = cursor.lastrowid
            self.document_ids.append(chunk_id)
            self.document_texts.append(chunk)
            added += 1
        
        conn.commit()
        conn.close()
        self._save_index()
        return added
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for semantically similar documents."""
        if not HAS_FAISS or not HAS_SENTENCE_TRANSFORMERS or self.index is None or self.index.ntotal == 0:
            return []
        
        self._load_model()
        
        # Generate query embedding
        query_embedding = self.model.encode([query], normalize_embeddings=True)[0]
        
        # Search FAISS index
        distances, indices = self.index.search(query_embedding.reshape(1, -1), top_k)
        
        results = []
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                continue
            
            chunk_id = self.document_ids[idx]
            cursor.execute("""
                SELECT sc.*, dr.nombre as documento_nombre, dr.tipo as documento_tipo
                FROM SemanticChunks sc
                LEFT JOIN DocumentosRAG dr ON sc.documento_id = dr.id
                WHERE sc.id = ?
            """, (chunk_id,))
            
            row = cursor.fetchone()
            if row:
                results.append({
                    "id": row["id"],
                    "chunk_text": row["chunk_text"],
                    "score": float(distances[0][i]),
                    "documento_id": row["documento_id"],
                    "documento_nombre": row["documento_nombre"],
                    "documento_tipo": row["documento_tipo"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                })
        
        conn.close()
        return results
    
    def _save_index(self):
        """Save FAISS index and metadata to disk."""
        if self.index is None:
            return
        
        faiss.write_index(self.index, self.index_path)
        
        meta_path = self.index_path.replace('.faiss', '_meta.json')
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump({
                'document_ids': self.document_ids,
                'document_texts': self.document_texts,
            }, f)
    
    def rebuild_index(self):
        """Rebuild index from SQLite data."""
        if not HAS_FAISS or not HAS_SENTENCE_TRANSFORMERS:
            return
        
        self._load_model()
        
        # Clear existing index
        embedding_dim = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(embedding_dim)
        self.document_ids = []
        self.document_texts = []
        
        # Load all chunks from SQLite
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, chunk_text FROM SemanticChunks")
        rows = cursor.fetchall()
        
        if rows:
            texts = [row["chunk_text"] for row in rows]
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            self.index.add(embeddings)
            self.document_ids = [row["id"] for row in rows]
            self.document_texts = texts
        
        conn.close()
        self._save_index()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "total_vectors": self.index.ntotal if self.index else 0,
            "model": self.model_name,
            "has_faiss": HAS_FAISS,
            "has_sentence_transformers": HAS_SENTENCE_TRANSFORMERS,
        }
