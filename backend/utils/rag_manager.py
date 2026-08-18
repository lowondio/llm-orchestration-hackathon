import os
import sqlite3
import json
import uuid
import datetime
import io
import numpy as np
import requests
from typing import List, Dict, Any, Optional

# Constants
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rag_embeddings.db")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")

class RagManager:
    @staticmethod
    def init_db():
        """Initialize SQLite database for chunks and metadata"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                node_id TEXT,
                filename TEXT,
                file_path TEXT,
                file_size INTEGER,
                uploaded_at TEXT
            )
        """)
        
        # Create chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                node_id TEXT,
                file_id TEXT,
                chunk_index INTEGER,
                text TEXT,
                embedding TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Create uploads folder if not exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    @staticmethod
    def get_openai_embedding(text: str) -> Optional[List[float]]:
        """Fetch embedding for a single text query from OpenAI API"""
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key or api_key.startswith("dummy") or api_key == "test":
            return None
            
        try:
            url = "https://api.openai.com/v1/embeddings"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "input": text,
                "model": "text-embedding-3-small"
            }
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            print(f"[RagManager] OpenAI Embeddings API error: {e}")
            return None

    @staticmethod
    def get_openai_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
        """Fetch embeddings for a batch of texts from OpenAI API"""
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key or api_key.startswith("dummy") or api_key == "test":
            return [None] * len(texts)
            
        try:
            url = "https://api.openai.com/v1/embeddings"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            # Limit batch size to 2048 as per OpenAI limits, but our uploads will be small
            payload = {
                "input": texts,
                "model": "text-embedding-3-small"
            }
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            # Construct embeddings list in original order
            embeddings = [item["embedding"] for item in data["data"]]
            return embeddings
        except Exception as e:
            print(f"[RagManager] OpenAI Embeddings batch API error: {e}")
            return [None] * len(texts)

    @staticmethod
    def extract_text(file_bytes: bytes, filename: str) -> str:
        """Extract text from TXT or PDF file"""
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.txt':
            return file_bytes.decode('utf-8', errors='ignore')
        elif ext == '.pdf':
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Only PDF and TXT are supported.")

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
        """Split text into overlapping character chunks"""
        if not text:
            return []
        
        # Normalize whitespace
        text = " ".join(text.split())
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            # Move start pointer forward
            start += (chunk_size - chunk_overlap)
            
            # Prevent infinite loop or very small trailing chunks
            if start >= text_len or (chunk_size - chunk_overlap) <= 0:
                break
                
        return chunks

    @classmethod
    def add_file(cls, node_id: str, filename: str, file_bytes: bytes, chunk_size: int = 500, chunk_overlap: int = 50) -> Dict[str, Any]:
        """Parse file, generate chunks, compute embeddings, and store in SQLite"""
        cls.init_db()
        
        # Save file to disk
        node_upload_dir = os.path.join(UPLOAD_DIR, f"rag_{node_id}")
        os.makedirs(node_upload_dir, exist_ok=True)
        
        # Clean filename to avoid path traversal
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(node_upload_dir, safe_filename)
        
        with open(file_path, "wb") as f:
            f.write(file_bytes)
            
        file_size = len(file_bytes)
        file_id = str(uuid.uuid4())
        uploaded_at = datetime.datetime.utcnow().isoformat()
        
        # Extract text and chunk
        text = cls.extract_text(file_bytes, safe_filename)
        chunks = cls.chunk_text(text, chunk_size, chunk_overlap)
        
        if not chunks:
            # Clean up if empty
            if os.path.exists(file_path):
                os.remove(file_path)
            raise ValueError("No text could be extracted from the file.")
            
        # Get embeddings
        embeddings = cls.get_openai_embeddings_batch(chunks)
        
        # Save to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Insert file record
            cursor.execute(
                "INSERT INTO files (id, node_id, filename, file_path, file_size, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
                (file_id, node_id, safe_filename, file_path, file_size, uploaded_at)
            )
            
            # Insert chunk records
            for idx, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
                chunk_id = str(uuid.uuid4())
                emb_json = json.dumps(emb) if emb is not None else ""
                cursor.execute(
                    "INSERT INTO chunks (id, node_id, file_id, chunk_index, text, embedding) VALUES (?, ?, ?, ?, ?, ?)",
                    (chunk_id, node_id, file_id, idx, chunk_text, emb_json)
                )
                
            conn.commit()
        except Exception as e:
            conn.rollback()
            # Clean up file
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e
        finally:
            conn.close()
            
        return {
            "id": file_id,
            "filename": safe_filename,
            "size": file_size,
            "chunks_count": len(chunks),
            "uploaded_at": uploaded_at
        }

    @staticmethod
    def delete_file(node_id: str, file_id: str) -> bool:
        """Delete file and its associated chunks from DB and disk"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Find file path
        cursor.execute("SELECT file_path FROM files WHERE id = ? AND node_id = ?", (file_id, node_id))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False
            
        file_path = row[0]
        
        try:
            # Delete database records
            cursor.execute("DELETE FROM chunks WHERE file_id = ? AND node_id = ?", (file_id, node_id))
            cursor.execute("DELETE FROM files WHERE id = ? AND node_id = ?", (file_id, node_id))
            conn.commit()
            
            # Delete physical file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Remove directory if empty
            node_upload_dir = os.path.dirname(file_path)
            if os.path.exists(node_upload_dir) and not os.listdir(node_upload_dir):
                os.rmdir(node_upload_dir)
                
            return True
        except Exception as e:
            conn.rollback()
            print(f"[RagManager] Error deleting file: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def list_files(node_id: str) -> List[Dict[str, Any]]:
        """List all files uploaded for a given RAG node"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, filename, file_size, uploaded_at FROM files WHERE node_id = ? ORDER BY uploaded_at DESC",
            (node_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "filename": r[1],
                "size": r[2],
                "uploaded_at": r[3]
            }
            for r in rows
        ]

    @classmethod
    def search(cls, node_id: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Perform vector search or fallback keyword search over node chunks"""
        cls.init_db()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all chunks for this node
        cursor.execute("SELECT id, file_id, text, embedding FROM chunks WHERE node_id = ?", (node_id,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return []
            
        # Parse query embedding
        query_emb = cls.get_openai_embedding(query)
        
        # Check if we can perform Vector Search
        has_vector_search = query_emb is not None and all(bool(r[3]) for r in rows)
        
        results = []
        
        if has_vector_search:
            # Real Vector search
            q_vec = np.array(query_emb)
            q_norm = np.linalg.norm(q_vec)
            
            for chunk_id, file_id, text, emb_json in rows:
                try:
                    c_vec = np.array(json.loads(emb_json))
                    c_norm = np.linalg.norm(c_vec)
                    
                    if q_norm > 0 and c_norm > 0:
                        similarity = float(np.dot(q_vec, c_vec) / (q_norm * c_norm))
                    else:
                        similarity = 0.0
                        
                    results.append({
                        "text": text,
                        "score": similarity,
                        "file_id": file_id
                    })
                except Exception as e:
                    # Fallback on parse error
                    pass
            
            # Sort by similarity desc
            results.sort(key=lambda x: x["score"], reverse=True)
            
        else:
            # Fallback TF-IDF keyword search
            # Tokenize query
            query_words = [w.strip().lower() for w in query.split() if len(w.strip()) > 1]
            if not query_words:
                query_words = [query.lower()]
                
            # Compute document frequency (DF) of each query word
            df = {}
            for word in query_words:
                df[word] = sum(1 for r in rows if word in r[2].lower())
                
            num_docs = len(rows)
            
            for chunk_id, file_id, text, _ in rows:
                text_lower = text.lower()
                score = 0.0
                
                for word in query_words:
                    if word in text_lower:
                        # TF: count of word in chunk
                        tf = text_lower.count(word)
                        # IDF with smoothing
                        word_df = df.get(word, 0)
                        idf = np.log((num_docs + 1) / (word_df + 1)) + 1
                        score += tf * idf
                        
                if score > 0:
                    results.append({
                        "text": text,
                        "score": float(score),
                        "file_id": file_id
                    })
                    
            # Sort by score desc
            results.sort(key=lambda x: x["score"], reverse=True)
            
            # If no keyword matches at all, return all chunks as context
            # so the LLM can still see the document content
            if not results:
                for chunk_id, file_id, text, _ in rows:
                    results.append({
                        "text": text,
                        "score": 0.0,
                        "file_id": file_id
                    })
            
        # Return top K results
        return results[:top_k]

# Initialize tables on import
RagManager.init_db()
