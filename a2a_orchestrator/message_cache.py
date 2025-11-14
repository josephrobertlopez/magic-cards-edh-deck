"""
A2A Message Cache and Orchestration Layer

Provides:
- Message response caching (avoid re-executing same requests)
- Message bus for pub/sub patterns
- Persistent cache storage
- Cache invalidation strategies
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict


@dataclass
class CachedMessage:
    """Cached A2A message response with metadata."""
    cache_key: str
    request_hash: str
    response_data: Dict[str, Any]
    timestamp: float
    ttl_seconds: int
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        age_seconds = time.time() - self.timestamp
        return age_seconds > self.ttl_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CachedMessage':
        """Create from dictionary."""
        return cls(**data)


class A2AMessageCache:
    """
    Cache layer for A2A message responses.
    
    Features:
    - Content-based hashing (same request = same response)
    - TTL-based expiration
    - LRU eviction when cache is full
    - Persistent storage to disk
    """
    
    def __init__(self, cache_dir: str = ".claude/cache", max_entries: int = 1000):
        """
        Initialize message cache.
        
        Args:
            cache_dir: Directory for cache storage
            max_entries: Maximum cache entries before eviction
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "a2a_message_cache.json"
        self.max_entries = max_entries
        self.cache: Dict[str, CachedMessage] = {}
        self._load_cache()
    
    def _compute_cache_key(self, skill_name: str, payload: Dict[str, Any]) -> str:
        """
        Compute cache key from skill name and payload.
        
        Uses content hashing - same inputs always produce same key.
        """
        # Normalize payload for consistent hashing
        normalized = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"{skill_name}:{payload_hash}"
    
    def get(self, skill_name: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available and not expired.
        
        Args:
            skill_name: Name of skill being called
            payload: Request payload
            
        Returns:
            Cached response data or None if miss/expired
        """
        cache_key = self._compute_cache_key(skill_name, payload)
        
        if cache_key not in self.cache:
            return None
        
        cached = self.cache[cache_key]
        
        # Check expiration
        if cached.is_expired():
            del self.cache[cache_key]
            self._save_cache()
            return None
        
        # Update hit count
        cached.hit_count += 1
        self._save_cache()
        
        return cached.response_data
    
    def put(
        self, 
        skill_name: str, 
        payload: Dict[str, Any], 
        response: Dict[str, Any],
        ttl_seconds: int = 3600
    ):
        """
        Cache a response.
        
        Args:
            skill_name: Name of skill
            payload: Request payload
            response: Response data to cache
            ttl_seconds: Time to live in seconds (default: 1 hour)
        """
        cache_key = self._compute_cache_key(skill_name, payload)
        request_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        
        cached_msg = CachedMessage(
            cache_key=cache_key,
            request_hash=request_hash,
            response_data=response,
            timestamp=time.time(),
            ttl_seconds=ttl_seconds,
            hit_count=0
        )
        
        self.cache[cache_key] = cached_msg
        
        # Evict oldest entries if cache is full
        if len(self.cache) > self.max_entries:
            self._evict_lru()
        
        self._save_cache()
    
    def invalidate(self, skill_name: str, payload: Optional[Dict[str, Any]] = None):
        """
        Invalidate cache entries.
        
        Args:
            skill_name: Skill to invalidate
            payload: If provided, invalidate specific request. Otherwise invalidate all for skill.
        """
        if payload:
            cache_key = self._compute_cache_key(skill_name, payload)
            if cache_key in self.cache:
                del self.cache[cache_key]
        else:
            # Invalidate all entries for this skill
            keys_to_delete = [
                key for key in self.cache.keys() 
                if key.startswith(f"{skill_name}:")
            ]
            for key in keys_to_delete:
                del self.cache[key]
        
        self._save_cache()
    
    def clear(self):
        """Clear entire cache."""
        self.cache.clear()
        self._save_cache()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        total_hits = sum(cached.hit_count for cached in self.cache.values())
        expired_count = sum(1 for cached in self.cache.values() if cached.is_expired())
        
        return {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "expired_entries": expired_count,
            "cache_size_mb": self._get_cache_size_mb()
        }
    
    def _evict_lru(self):
        """Evict least recently used entries."""
        # Sort by timestamp (oldest first)
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda item: item[1].timestamp
        )
        
        # Remove 10% of oldest entries
        num_to_evict = max(1, len(sorted_entries) // 10)
        for cache_key, _ in sorted_entries[:num_to_evict]:
            del self.cache[cache_key]
    
    def _load_cache(self):
        """Load cache from disk."""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
                self.cache = {
                    key: CachedMessage.from_dict(cached_data)
                    for key, cached_data in data.items()
                }
        except Exception as e:
            print(f"⚠️  Failed to load cache: {e}")
            self.cache = {}
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            data = {
                key: cached.to_dict()
                for key, cached in self.cache.items()
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save cache: {e}")
    
    def _get_cache_size_mb(self) -> float:
        """Get cache file size in MB."""
        if self.cache_file.exists():
            return self.cache_file.stat().st_size / (1024 * 1024)
        return 0.0


class A2AMessageBus:
    """
    Message bus for pub/sub orchestration patterns.
    
    Allows skills to subscribe to topics and receive messages
    without direct coupling.
    """
    
    def __init__(self):
        """Initialize message bus."""
        self.subscriptions: Dict[str, List[Any]] = {}
        self.message_log: List[Dict[str, Any]] = []
    
    def subscribe(self, topic: str, handler: Any):
        """
        Subscribe to a message topic.
        
        Args:
            topic: Topic name (e.g., "workflow.complete", "skill.error")
            handler: Async function to handle messages
        """
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        self.subscriptions[topic].append(handler)
    
    async def publish(self, topic: str, message: Dict[str, Any]):
        """
        Publish message to topic.
        
        All subscribers will receive the message asynchronously.
        
        Args:
            topic: Topic name
            message: Message payload
        """
        self.message_log.append({
            "topic": topic,
            "message": message,
            "timestamp": time.time()
        })
        
        if topic in self.subscriptions:
            # Notify all subscribers concurrently
            handlers = self.subscriptions[topic]
            await asyncio.gather(
                *[handler(message) for handler in handlers],
                return_exceptions=True
            )
    
    def get_message_log(self) -> List[Dict[str, Any]]:
        """Get message bus log."""
        return self.message_log
