"""
RAG (Retrieval-Augmented Generation) extension for knowledge base searching.

Provides semantic search over vectorized knowledge base chunks using FAISS indexing.
Handles embedding generation, similarity search, and answer formatting.
"""

from typing import TypedDict
from pathlib import Path


class RAGResponse(TypedDict):
    """Response structure for RAG search queries."""
    answer: str
    source: str
    confidence: float


def rag_search(question: str) -> RAGResponse:
    """
    Search the knowledge base for relevant information using semantic similarity.
    
    Loads a FAISS vector index, embeds the input question, performs similarity search
    on the top-3 most similar chunks, and formats results into a coherent answer.
    
    Args:
        question: The user's question to search for in the knowledge base.
    
    Returns:
        RAGResponse containing:
        - answer: Formatted response text from knowledge base chunks or fallback message
        - source: Always "rag" for this function
        - confidence: Top chunk similarity score (0.0-1.0), or 0.0 if no match found
    
    Raises:
        No exceptions are raised; all errors are handled gracefully with fallback response.
    """
    import numpy as np
    
    try:
        # Import FAISS and embedding model
        import faiss
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        return {
            "answer": "I couldn't find information about that in our knowledge base.",
            "source": "rag",
            "confidence": 0.0
        }
    
    index_path = Path("vector-store/index.faiss")
    
    # Handle missing index file
    if not index_path.exists():
        return {
            "answer": "I couldn't find information about that in our knowledge base.",
            "source": "rag",
            "confidence": 0.0
        }
    
    try:
        # Load the FAISS index
        index = faiss.read_index(str(index_path))
        
        # Load the embedding model (same model used during indexing)
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Embed the question
        question_embedding = model.encode([question], convert_to_numpy=True)
        
        # Search for top-3 most similar chunks
        distances, indices = index.search(question_embedding, k=3)
        
        # Extract similarity scores (convert distance to similarity)
        # FAISS returns distances, so similarity = 1 / (1 + distance)
        similarities = 1.0 / (1.0 + distances[0])
        top_similarity = float(similarities[0])
        
        # Check if top match meets confidence threshold
        if top_similarity < 0.5:
            return {
                "answer": "I couldn't find information about that in our knowledge base.",
                "source": "rag",
                "confidence": 0.0
            }
        
        # Load chunk metadata to reconstruct answers
        metadata_path = Path("vector-store/metadata.pkl")
        if not metadata_path.exists():
            return {
                "answer": "I couldn't find information about that in our knowledge base.",
                "source": "rag",
                "confidence": 0.0
            }
        
        import pickle
        with open(metadata_path, 'rb') as f:
            chunks = pickle.load(f)
        
        # Format the top-3 chunks into a coherent answer
        relevant_chunks = [chunks[int(idx)] for idx in indices[0] if int(idx) < len(chunks)]
        
        if not relevant_chunks:
            return {
                "answer": "I couldn't find information about that in our knowledge base.",
                "source": "rag",
                "confidence": 0.0
            }
        
        # Join chunks with natural formatting
        answer = " ".join(chunk.strip() for chunk in relevant_chunks if chunk)
        
        return {
            "answer": answer,
            "source": "rag",
            "confidence": top_similarity
        }
    
    except (FileNotFoundError, OSError, KeyError, IndexError, pickle.UnpicklingError):
        # Gracefully handle any file or data structure errors
        return {
            "answer": "I couldn't find information about that in our knowledge base.",
            "source": "rag",
            "confidence": 0.0
        }
    except Exception:
        # Catch any other unexpected errors
        return {
            "answer": "I couldn't find information about that in our knowledge base.",
            "source": "rag",
            "confidence": 0.0
        }
