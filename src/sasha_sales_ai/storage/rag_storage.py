"""RAG storage for context retrieval"""

import logging
from typing import Optional, Any
from datetime import datetime

logger = logging.getLogger("sasha_sales_ai.storage.rag")


class RAGStorage:
    """Simple RAG storage for lead context and history"""
    
    def __init__(self):
        """Initialize the RAG storage"""
        # In-memory storage (would be a vector DB in production)
        self._lead_history: dict[str, list[dict[str, Any]]] = {}
        self._product_info: dict[str, dict[str, Any]] = {}
        self._customer_info: dict[str, dict[str, Any]] = {}
    
    def store_lead_interaction(
        self,
        lead_id: str,
        interaction_type: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Store a lead interaction for later retrieval.
        
        Args:
            lead_id: Lead identifier
            interaction_type: Type of interaction (email_in, email_out, note, etc.)
            content: Content of the interaction
            metadata: Optional additional metadata
        """
        if lead_id not in self._lead_history:
            self._lead_history[lead_id] = []
        
        self._lead_history[lead_id].append({
            "type": interaction_type,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        })
        
        logger.debug(f"Stored interaction for lead {lead_id}: {interaction_type}")
    
    def get_lead_history(
        self,
        lead_id: str,
        limit: int = 10,
        interaction_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Retrieve lead interaction history.
        
        Args:
            lead_id: Lead identifier
            limit: Maximum number of interactions to return
            interaction_type: Optional filter by interaction type
        
        Returns:
            List of interaction records
        """
        history = self._lead_history.get(lead_id, [])
        
        if interaction_type:
            history = [h for h in history if h["type"] == interaction_type]
        
        # Return most recent first
        return list(reversed(history[-limit:]))
    
    def get_thread_context(self, lead_id: str) -> str:
        """Get formatted thread history for context.
        
        Args:
            lead_id: Lead identifier
        
        Returns:
            Formatted thread history string
        """
        history = self.get_lead_history(lead_id, limit=20)
        
        if not history:
            return ""
        
        formatted = []
        for interaction in history:
            type_label = {
                "email_in": "Customer",
                "email_out": "Sasha AI",
                "note": "Note",
            }.get(interaction["type"], interaction["type"])
            
            formatted.append(f"[{type_label}] {interaction['content'][:500]}")
        
        return "\n\n---\n\n".join(formatted)
    
    def store_customer_info(
        self,
        email: str,
        info: dict[str, Any],
    ) -> None:
        """Store customer information.
        
        Args:
            email: Customer email (key)
            info: Customer information dictionary
        """
        if email not in self._customer_info:
            self._customer_info[email] = {}
        
        self._customer_info[email].update(info)
        self._customer_info[email]["updated_at"] = datetime.now().isoformat()
        
        logger.debug(f"Updated customer info for {email}")
    
    def get_customer_info(self, email: str) -> Optional[dict[str, Any]]:
        """Get stored customer information.
        
        Args:
            email: Customer email
        
        Returns:
            Customer information dictionary or None
        """
        return self._customer_info.get(email)
    
    def store_product_info(
        self,
        product_type: str,
        info: dict[str, Any],
    ) -> None:
        """Store product information.
        
        Args:
            product_type: Product type identifier
            info: Product information dictionary
        """
        self._product_info[product_type] = {
            **info,
            "updated_at": datetime.now().isoformat(),
        }
        
        logger.debug(f"Updated product info for {product_type}")
    
    def get_product_info(self, product_type: str) -> Optional[dict[str, Any]]:
        """Get stored product information.
        
        Args:
            product_type: Product type identifier
        
        Returns:
            Product information dictionary or None
        """
        return self._product_info.get(product_type)
    
    def search_similar_leads(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for similar leads based on content.
        
        In production, this would use vector similarity search.
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of similar lead records
        """
        # Simple keyword matching (would be vector search in production)
        query_lower = query.lower()
        results = []
        
        for lead_id, history in self._lead_history.items():
            score = 0
            for interaction in history:
                content_lower = interaction["content"].lower()
                # Count keyword matches
                for word in query_lower.split():
                    if word in content_lower:
                        score += 1
            
            if score > 0:
                results.append({
                    "lead_id": lead_id,
                    "score": score,
                    "latest_interaction": history[-1] if history else None,
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def clear_lead(self, lead_id: str) -> bool:
        """Clear all stored data for a lead.
        
        Args:
            lead_id: Lead identifier
        
        Returns:
            True if data was cleared, False if lead not found
        """
        if lead_id in self._lead_history:
            del self._lead_history[lead_id]
            logger.info(f"Cleared data for lead {lead_id}")
            return True
        return False


# Global storage instance
_storage: Optional[RAGStorage] = None


def get_rag_storage() -> RAGStorage:
    """Get or create the RAG storage instance.
    
    Returns:
        RAGStorage instance
    """
    global _storage
    if _storage is None:
        _storage = RAGStorage()
    return _storage

