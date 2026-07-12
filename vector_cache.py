# vector_cache.py
# Uses vector embeddings to:
# 1. Find similar previous questions
# 2. Return cached answer if similar enough
# 3. Avoid redundant API calls completely

import numpy as np
import json
import os
from sentence_transformers import SentenceTransformer
from datetime import datetime, timedelta

class VectorCache:
    
    def __init__(
        self,
        cache_file: str = 'cache.json',
        similarity_threshold: float = 0.85,
        cache_expiry_hours: int = 24
    ):
        """
        similarity_threshold:
        0.85 = 85% similar = use cache
        Higher = stricter matching
        Lower = more cache hits
        
        cache_expiry_hours:
        How long to keep cached answers
        """
        
        self.cache_file = cache_file
        self.threshold = similarity_threshold
        self.expiry_hours = cache_expiry_hours
        
        # Load lightweight embedding model
        # all-MiniLM-L6-v2 is only 80MB
        # Fast and accurate enough
        print("📦 Loading embedding model...")
        self.model = SentenceTransformer(
            'all-MiniLM-L6-v2'
        )
        print("✅ Embedding model loaded")
        
        # Load existing cache
        self.cache = self._load_cache()
        
    def _load_cache(self) -> list:
        """Load cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_cache(self):
        """Save cache to file"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def _is_expired(
        self, timestamp: str
    ) -> bool:
        """Check if cache entry is expired"""
        cached_time = datetime.fromisoformat(
            timestamp
        )
        expiry_time = cached_time + timedelta(
            hours=self.expiry_hours
        )
        return datetime.now() > expiry_time
    
    def _cosine_similarity(
        self,
        vec1: list,
        vec2: list
    ) -> float:
        """Calculate similarity between vectors"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def get_embedding(self, text: str) -> list:
        """Convert text to vector embedding"""
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    def find_similar(
        self,
        query: str
    ) -> tuple:
        """
        Find most similar cached question
        Returns (answer, similarity_score)
        or (None, 0) if no match
        """
        
        if not self.cache:
            return None, 0.0
        
        # Get embedding for new query
        query_embedding = self.get_embedding(query)
        
        best_match = None
        best_score = 0.0
        
        # Compare with all cached questions
        valid_cache = []
        
        for entry in self.cache:
            # Skip expired entries
            if self._is_expired(entry['timestamp']):
                continue
            
            valid_cache.append(entry)
            
            # Calculate similarity
            score = self._cosine_similarity(
                query_embedding,
                entry['embedding']
            )
            
            if score > best_score:
                best_score = score
                best_match = entry
        
        # Update cache removing expired
        self.cache = valid_cache
        
        if (best_match
                and best_score >= self.threshold):
            print(
                f"💾 Cache hit! "
                f"Similarity: {best_score:.3f}"
            )
            return best_match['answer'], best_score
        
        return None, best_score
    
    def store(
        self,
        question: str,
        answer: str
    ):
        """Store question-answer in cache"""
        
        embedding = self.get_embedding(question)
        
        entry = {
            'question': question,
            'answer': answer,
            'embedding': embedding,
            'timestamp': datetime.now().isoformat()
        }
        
        self.cache.append(entry)
        
        # Keep cache size manageable
        # Remove oldest if more than 500 entries
        if len(self.cache) > 500:
            self.cache = self.cache[-500:]
        
        self._save_cache()
        print(f"💾 Cached: '{question[:50]}...'")
    
    def clear(self):
        """Clear all cache"""
        self.cache = []
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        print("🗑️ Cache cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        valid = [
            e for e in self.cache
            if not self._is_expired(e['timestamp'])
        ]
        return {
            'total_entries': len(valid),
            'cache_file_size': (
                os.path.getsize(self.cache_file)
                if os.path.exists(self.cache_file)
                else 0
            )
        }


# Global cache instance
# Created once reused everywhere
cache = VectorCache(
    cache_file='qa_cache.json',
    similarity_threshold=0.85,
    cache_expiry_hours=24
)
