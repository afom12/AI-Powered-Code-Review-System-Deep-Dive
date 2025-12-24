"""Code embedding utilities for similarity search"""

from typing import List, Optional
import numpy as np
import os


class CodeEmbedder:
    """
    Generates embeddings for code snippets.
    Uses sentence-transformers for code similarity.
    """
    
    def __init__(self, model_name: Optional[str] = None, use_local: bool = False):
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.use_local = use_local or os.getenv("USE_LOCAL_MODELS", "false").lower() == "true"
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model"""
        try:
            if self.use_local:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name)
                self.embedding_size = self.model.get_sentence_embedding_dimension()
            else:
                # Fallback to placeholder if models not available
                self.model = None
                self.embedding_size = 384  # all-MiniLM-L6-v2 default size
        except ImportError:
            print("Warning: sentence-transformers not available. Using placeholder embeddings.")
            self.model = None
            self.embedding_size = 384
        except Exception as e:
            print(f"Warning: Failed to load embedding model: {e}. Using placeholder.")
            self.model = None
            self.embedding_size = 384
    
    def embed_code(self, code: str) -> np.ndarray:
        """
        Generate embedding for code snippet.
        
        Args:
            code: Code snippet to embed
            
        Returns:
            Embedding vector
        """
        if self.model is not None:
            try:
                # Truncate code if too long (models have token limits)
                max_length = 512
                if len(code) > max_length:
                    code = code[:max_length]
                
                embedding = self.model.encode(code, convert_to_numpy=True)
                return embedding
            except Exception as e:
                print(f"Error generating embedding: {e}")
        
        # Fallback to placeholder
        return np.random.rand(self.embedding_size).astype(np.float32)
    
    def embed_batch(self, code_snippets: List[str]) -> np.ndarray:
        """Generate embeddings for multiple code snippets"""
        if self.model is not None:
            try:
                # Truncate long snippets
                truncated = [s[:512] if len(s) > 512 else s for s in code_snippets]
                embeddings = self.model.encode(truncated, convert_to_numpy=True)
                return embeddings
            except Exception as e:
                print(f"Error generating batch embeddings: {e}")
        
        # Fallback to placeholder
        return np.array([self.embed_code(code) for code in code_snippets])
    
    def embed_pr_content(self, title: str, description: str, file_paths: List[str], code_snippets: List[str]) -> np.ndarray:
        """
        Generate embedding for entire PR content.
        Combines title, description, file paths, and code snippets.
        """
        # Combine all text content
        content_parts = []
        if title:
            content_parts.append(f"Title: {title}")
        if description:
            content_parts.append(f"Description: {description[:500]}")  # Limit description length
        if file_paths:
            content_parts.append(f"Files: {', '.join(file_paths[:20])}")  # Limit to 20 files
        
        # Add code snippets (limit to prevent too long input)
        for snippet in code_snippets[:5]:  # Limit to 5 snippets
            if snippet:
                content_parts.append(f"Code: {snippet[:200]}")  # Limit snippet length
        
        combined_text = "\n".join(content_parts)
        return self.embed_code(combined_text)
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings"""
        # Normalize embeddings
        embedding1 = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
        embedding2 = embedding2 / (np.linalg.norm(embedding2) + 1e-8)
        
        dot_product = np.dot(embedding1, embedding2)
        return float(np.clip(dot_product, -1.0, 1.0))


