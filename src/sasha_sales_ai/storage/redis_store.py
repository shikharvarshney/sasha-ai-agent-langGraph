"""Redis-based state storage for lead management"""

import json
import logging
from typing import Optional, Any
from datetime import datetime

import redis

logger = logging.getLogger("sasha_sales_ai.storage.redis_store")


class RedisStateStore:
    """Redis-based state storage for leads.
    
    Provides persistent storage for FlowState objects using Redis hashes.
    Each lead is stored as a JSON string with key pattern: {prefix}lead:{lead_id}
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "sasha:",
    ):
        """Initialize Redis state store.
        
        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all Redis keys
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.lead_prefix = f"{key_prefix}lead:"
        
        # Create Redis connection
        self._redis: Optional[redis.Redis] = None
        self._connect()
        
        logger.info(f"RedisStateStore initialized with prefix '{key_prefix}'")
    
    def _connect(self) -> None:
        """Establish Redis connection."""
        try:
            self._redis = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # Test connection
            self._redis.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    @property
    def redis(self) -> redis.Redis:
        """Get Redis client, reconnecting if necessary."""
        if self._redis is None:
            self._connect()
        return self._redis
    
    def _lead_key(self, lead_id: str) -> str:
        """Generate Redis key for a lead.
        
        Args:
            lead_id: Lead identifier
            
        Returns:
            Full Redis key
        """
        return f"{self.lead_prefix}{lead_id}"
    
    def get(self, lead_id: str) -> Optional[dict[str, Any]]:
        """Get state for a lead.
        
        Args:
            lead_id: Lead identifier
            
        Returns:
            State dictionary or None if not found
        """
        try:
            data = self.redis.get(self._lead_key(lead_id))
            if data:
                return json.loads(data)
            return None
        except redis.RedisError as e:
            logger.error(f"Redis error getting lead {lead_id}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for lead {lead_id}: {e}")
            return None
    
    def set(self, lead_id: str, state: dict[str, Any]) -> None:
        """Save state for a lead.
        
        Args:
            lead_id: Lead identifier
            state: State dictionary to save
        """
        try:
            # Add metadata
            state_with_meta = dict(state)
            state_with_meta["_updated_at"] = datetime.now().isoformat()
            
            # Serialize and store
            self.redis.set(
                self._lead_key(lead_id),
                json.dumps(state_with_meta, default=str)
            )
            logger.debug(f"Saved state for lead {lead_id}")
        except redis.RedisError as e:
            logger.error(f"Redis error saving lead {lead_id}: {e}")
            raise
    
    def delete(self, lead_id: str) -> bool:
        """Delete state for a lead.
        
        Args:
            lead_id: Lead identifier
            
        Returns:
            True if deleted, False if not found
        """
        try:
            result = self.redis.delete(self._lead_key(lead_id))
            if result:
                logger.debug(f"Deleted state for lead {lead_id}")
            return result > 0
        except redis.RedisError as e:
            logger.error(f"Redis error deleting lead {lead_id}: {e}")
            raise
    
    def exists(self, lead_id: str) -> bool:
        """Check if a lead exists.
        
        Args:
            lead_id: Lead identifier
            
        Returns:
            True if exists
        """
        try:
            return self.redis.exists(self._lead_key(lead_id)) > 0
        except redis.RedisError as e:
            logger.error(f"Redis error checking lead {lead_id}: {e}")
            raise
    
    def list_all(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        """List all leads, optionally filtered by status.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of lead summaries
        """
        leads = []
        try:
            # Use SCAN to iterate through keys (production-safe)
            for key in self.redis.scan_iter(f"{self.lead_prefix}*"):
                try:
                    data = self.redis.get(key)
                    if data:
                        state = json.loads(data)
                        
                        # Apply status filter
                        if status and state.get("status") != status:
                            continue
                        
                        leads.append({
                            "lead_id": state.get("lead_id"),
                            "status": state.get("status"),
                            "email_from": state.get("email_from"),
                            "email_subject": state.get("email_subject"),
                            "total_amount": state.get("total_amount"),
                            "updated_at": state.get("_updated_at"),
                        })
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Error parsing lead data from {key}: {e}")
                    continue
                    
        except redis.RedisError as e:
            logger.error(f"Redis error listing leads: {e}")
            raise
        
        return leads
    
    def get_by_status(self, status: str) -> list[dict[str, Any]]:
        """Get all leads with a specific status.
        
        Args:
            status: Status to filter by
            
        Returns:
            List of lead summaries
        """
        return self.list_all(status=status)
    
    def count(self) -> int:
        """Count total number of leads.
        
        Returns:
            Number of leads stored
        """
        try:
            count = 0
            for _ in self.redis.scan_iter(f"{self.lead_prefix}*"):
                count += 1
            return count
        except redis.RedisError as e:
            logger.error(f"Redis error counting leads: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check Redis connection health.
        
        Returns:
            True if healthy
        """
        try:
            self.redis.ping()
            return True
        except redis.RedisError:
            return False
    
    def flush_all_leads(self) -> int:
        """Delete all leads (use with caution!).
        
        Returns:
            Number of leads deleted
        """
        try:
            count = 0
            for key in self.redis.scan_iter(f"{self.lead_prefix}*"):
                self.redis.delete(key)
                count += 1
            logger.warning(f"Flushed {count} leads from Redis")
            return count
        except redis.RedisError as e:
            logger.error(f"Redis error flushing leads: {e}")
            raise


# Global instance
_redis_store: Optional[RedisStateStore] = None


def get_redis_store(
    redis_url: Optional[str] = None,
    key_prefix: Optional[str] = None,
) -> RedisStateStore:
    """Get or create global Redis store instance.
    
    Args:
        redis_url: Optional Redis URL (uses config if not provided)
        key_prefix: Optional key prefix (uses config if not provided)
        
    Returns:
        RedisStateStore instance
    """
    global _redis_store
    
    if _redis_store is None:
        from ..config import get_settings
        settings = get_settings()
        
        _redis_store = RedisStateStore(
            redis_url=redis_url or settings.redis_url,
            key_prefix=key_prefix or settings.redis_key_prefix,
        )
    
    return _redis_store

