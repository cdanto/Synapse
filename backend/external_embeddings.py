"""
External Embedding Service for Synapse
Uses cloud APIs instead of heavy local models to stay under 4GB limit
"""

import os
import requests
import json
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ExternalEmbeddingService:
    """Service for getting embeddings from external APIs"""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.cohere_api_key = os.getenv("COHERE_API_KEY")
        self.hf_token = os.getenv("HF_TOKEN")
        
        # Default to OpenAI if available
        if self.openai_api_key:
            self.provider = "openai"
        elif self.cohere_api_key:
            self.provider = "cohere"
        elif self.hf_token:
            self.provider = "huggingface"
        else:
            self.provider = None
            logger.warning("No embedding API keys found. RAG features will be limited.")
    
    def get_embeddings(self, texts: List[str], model: str = None) -> List[List[float]]:
        """Get embeddings for a list of texts"""
        if not texts:
            return []
        
        if self.provider == "openai":
            return self._get_openai_embeddings(texts, model)
        elif self.provider == "cohere":
            return self._get_cohere_embeddings(texts, model)
        elif self.provider == "huggingface":
            return self._get_hf_embeddings(texts, model)
        else:
            # Fallback: return random embeddings (for testing)
            logger.warning("No embedding provider available, using fallback")
            return self._get_fallback_embeddings(texts)
    
    def _get_openai_embeddings(self, texts: List[str], model: str = None) -> List[List[float]]:
        """Get embeddings from OpenAI API"""
        if not model:
            model = "text-embedding-ada-002"
        
        try:
            import openai
            openai.api_key = self.openai_api_key
            
            response = openai.Embedding.create(
                input=texts,
                model=model
            )
            
            return [data.embedding for data in response.data]
            
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            return self._get_fallback_embeddings(texts)
    
    def _get_cohere_embeddings(self, texts: List[str], model: str = None) -> List[List[float]]:
        """Get embeddings from Cohere API"""
        if not model:
            model = "embed-english-v3.0"
        
        try:
            import cohere
            co = cohere.Client(self.cohere_api_key)
            
            response = co.embed(
                texts=texts,
                model=model
            )
            
            return response.embeddings
            
        except Exception as e:
            logger.error(f"Cohere embedding error: {e}")
            return self._get_fallback_embeddings(texts)
    
    def _get_hf_embeddings(self, texts: List[str], model: str = None) -> List[List[float]]:
        """Get embeddings from Hugging Face Inference API"""
        if not model:
            model = "BAAI/bge-base-en-v1.5"
        
        try:
            headers = {"Authorization": f"Bearer {self.hf_token}"}
            
            # HF API expects a single text, so we'll batch them
            all_embeddings = []
            
            for text in texts:
                response = requests.post(
                    f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model}",
                    headers=headers,
                    json={"inputs": text}
                )
                
                if response.status_code == 200:
                    embedding = response.json()
                    if isinstance(embedding, list) and len(embedding) > 0:
                        all_embeddings.append(embedding[0])
                    else:
                        all_embeddings.append(embedding)
                else:
                    logger.error(f"HF API error: {response.status_code}")
                    all_embeddings.append(self._get_fallback_embeddings([text])[0])
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Hugging Face embedding error: {e}")
            return self._get_fallback_embeddings(texts)
    
    def _get_fallback_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Fallback embeddings for when no API is available"""
        import random
        import numpy as np
        
        # Generate consistent random embeddings (same text = same embedding)
        random.seed(42)
        np.random.seed(42)
        
        embeddings = []
        for text in texts:
            # Create a hash-based seed for consistency
            seed = hash(text) % 1000000
            random.seed(seed)
            np.random.seed(seed)
            
            # Generate 384-dimensional embedding (standard size)
            embedding = np.random.normal(0, 1, 384).tolist()
            embeddings.append(embedding)
        
        return embeddings
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current embedding provider"""
        return {
            "provider": self.provider,
            "available": self.provider is not None,
            "models": {
                "openai": ["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"],
                "cohere": ["embed-english-v3.0", "embed-multilingual-v3.0"],
                "huggingface": ["BAAI/bge-base-en-v1.5", "sentence-transformers/all-MiniLM-L6-v2"]
            }
        }

# Global instance
embedding_service = ExternalEmbeddingService()
