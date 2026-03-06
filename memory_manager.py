"""
Memory Management - Two-tier memory architecture
Short-term (fast) and long-term (persistent) memory for efficient data retrieval
"""

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import OrderedDict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DistributedMemory:
    """
    Redis-backed memory for distributed swarms.
    Acts as shared long-term memory across multiple Jarvis-OS instances.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", prefix: str = "jarvis:"):
        """
        Initialize Redis connection.
        
        Args:
            redis_url: Redis connection string
            prefix: Key prefix for isolation
        """
        self.prefix = prefix
        try:
            import redis
            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.redis.ping() # test connection
        except ImportError:
            logger.error("Redis package not installed. Run: pip install redis")
            self.redis = None
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None
            
    def _full_key(self, key: str) -> str:
        return f"{self.prefix}{key}"
        
    def set(self, key: str, value: Any, ttl: Optional[float] = None, priority: int = 0):
        if not self.redis:
            return
            
        import time
        entry = {
            "key": key,
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl,
            "access_count": 0,
            "priority": priority,
            "metadata": {}
        }
        
        try:
            # We must serialize value
            serialized = json.dumps(entry, default=str)
            if ttl:
                self.redis.setex(self._full_key(key), int(ttl), serialized)
            else:
                self.redis.set(self._full_key(key), serialized)
        except Exception as e:
            logger.error(f"Failed to save to Redis distributed memory: {e}")

    def get(self, key: str) -> Optional[Any]:
        if not self.redis:
            return None
            
        try:
            data = self.redis.get(self._full_key(key))
            if not data:
                return None
            
            entry_dict = json.loads(data)
            
            # Reconstruct MemoryEntry just to check rules
            import time
            ttl = entry_dict.get("ttl")
            if ttl and (time.time() - entry_dict["timestamp"]) > ttl:
                self.delete(key)
                return None
            
            # Increment access count
            entry_dict["access_count"] = entry_dict.get("access_count", 0) + 1
            if ttl:
                self.redis.setex(self._full_key(key), int(ttl), json.dumps(entry_dict, default=str))
            else:
                self.redis.set(self._full_key(key), json.dumps(entry_dict, default=str))
                
            return entry_dict["value"]
        except Exception as e:
            logger.error(f"Failed to retrieve from Redis distributed memory: {e}")
            return None

    def delete(self, key: str) -> bool:
        if not self.redis:
            return False
        return bool(self.redis.delete(self._full_key(key)))

    def clear(self):
        if not self.redis:
            return
        keys = self.redis.keys(f"{self.prefix}*")
        if keys:
            self.redis.delete(*keys)

    def size(self) -> int:
        if not self.redis:
            return 0
        return len(self.redis.keys(f"{self.prefix}*"))


@dataclass
class MemoryEntry:
    """A single memory entry"""
    key: str
    value: Any
    timestamp: float
    ttl: Optional[float] = None  # Time to live in seconds
    access_count: int = 0
    priority: int = 0  # Higher = more important
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl is None:
            return False
        import time
        return (time.time() - self.timestamp) > self.ttl


class ShortTermMemory:
    """
    Fast, limited-size in-memory cache
    Uses LRU (Least Recently Used) eviction policy
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize short-term memory
        
        Args:
            max_size: Maximum number of entries
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, MemoryEntry] = OrderedDict()
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        priority: int = 0,
    ):
        """Store a value"""
        import time
        
        entry = MemoryEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            ttl=ttl,
            priority=priority,
        )
        
        # Remove expired entries
        self._cleanup_expired()
        
        # If at capacity, remove lowest priority LRU entry
        if len(self.cache) >= self.max_size:
            # Sort by priority then by access count
            min_key = min(
                self.cache.keys(),
                key=lambda k: (
                    self.cache[k].priority,
                    self.cache[k].access_count,
                )
            )
            del self.cache[min_key]
        
        # Add/update entry
        self.cache[key] = entry
        # Move to end (most recently used)
        self.cache.move_to_end(key)
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value"""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        
        if entry.is_expired():
            del self.cache[key]
            return None
        
        # Update access count and move to end
        entry.access_count += 1
        self.cache.move_to_end(key)
        
        return entry.value
    
    def delete(self, key: str) -> bool:
        """Delete an entry"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self):
        """Clear all entries"""
        self.cache.clear()
    
    def size(self) -> int:
        """Get current size"""
        return len(self.cache)
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        keys_to_delete = [
            k for k, v in self.cache.items()
            if v.is_expired()
        ]
        for key in keys_to_delete:
            del self.cache[key]


class LongTermMemory:
    """
    Persistent memory for long-term storage
    Simplified file-based storage
    """
    
    def __init__(self, storage_file: str = "memory.json"):
        """
        Initialize long-term memory
        
        Args:
            storage_file: Path to storage file
        """
        self.storage_file = storage_file
        self.data: Dict[str, MemoryEntry] = {}
        self._load()
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        priority: int = 0,
    ):
        """Store a value"""
        import time
        
        entry = MemoryEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            ttl=ttl,
            priority=priority,
        )
        
        self.data[key] = entry
        self._save()
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value"""
        if key not in self.data:
            return None
        
        entry = self.data[key]
        
        if entry.is_expired():
            del self.data[key]
            self._save()
            return None
        
        entry.access_count += 1
        self._save()
        
        return entry.value
    
    def delete(self, key: str) -> bool:
        """Delete an entry"""
        if key in self.data:
            del self.data[key]
            self._save()
            return True
        return False
    
    def clear(self):
        """Clear all entries"""
        self.data.clear()
        self._save()
    
    def size(self) -> int:
        """Get current size"""
        return len(self.data)
    
    def _save(self):
        """Save to disk"""
        try:
            with open(self.storage_file, 'w') as f:
                data_dict = {
                    k: {
                        'key': v.key,
                        'value': v.value,
                        'timestamp': v.timestamp,
                        'ttl': v.ttl,
                        'access_count': v.access_count,
                        'priority': v.priority,
                        'metadata': v.metadata,
                    }
                    for k, v in self.data.items()
                }
                json.dump(data_dict, f, default=str, indent=2)
        except Exception as e:
            logger.error(f"Failed to save long-term memory: {e}")
    
    def _load(self):
        """Load from disk"""
        try:
            with open(self.storage_file, 'r') as f:
                data_dict = json.load(f)
                for key, data in data_dict.items():
                    self.data[key] = MemoryEntry(
                        key=data['key'],
                        value=data['value'],
                        timestamp=data['timestamp'],
                        ttl=data.get('ttl'),
                        access_count=data.get('access_count', 0),
                        priority=data.get('priority', 0),
                        metadata=data.get('metadata', {}),
                    )
        except FileNotFoundError:
            pass  # File will be created on first save
        except Exception as e:
            logger.error(f"Failed to load long-term memory: {e}")


class MemoryManager:
    """
    Manager for two-tier memory system
    Coordinates between short-term and long-term memory
    """
    
    def __init__(
        self,
        short_term_size: int = 1000,
        long_term_file: str = "memory.json",
        redis_url: Optional[str] = None,
    ):
        """
        Initialize memory manager
        
        Args:
            short_term_size: Short-term memory capacity
            long_term_file: Long-term memory storage file
            redis_url: Redis URL for distributed scaling across agents
        """
        self.short_term = ShortTermMemory(short_term_size)
        if redis_url:
            self.long_term = DistributedMemory(redis_url)
        else:
            self.long_term = LongTermMemory(long_term_file)
        self.stats = {
            "short_term_hits": 0,
            "long_term_hits": 0,
            "misses": 0,
        }
    
    def store(
        self,
        key: str,
        value: Any,
        persistent: bool = False,
        ttl: Optional[float] = None,
        priority: int = 0,
    ):
        """
        Store a value in memory
        
        Args:
            key: Memory key
            value: Value to store
            persistent: If True, also store in long-term
            ttl: Time to live in seconds
            priority: Priority level for eviction
        """
        self.short_term.set(key, value, ttl, priority)
        
        if persistent:
            self.long_term.set(key, value, ttl, priority)
    
    def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from memory
        Tries short-term first, then long-term
        """
        # Try short-term
        value = self.short_term.get(key)
        if value is not None:
            self.stats["short_term_hits"] += 1
            return value
        
        # Try long-term
        value = self.long_term.get(key)
        if value is not None:
            self.stats["long_term_hits"] += 1
            # Store in short-term for future access
            self.short_term.set(key, value)
            return value
        
        self.stats["misses"] += 1
        return None
    
    def delete(self, key: str) -> bool:
        """Delete from both memories"""
        short_deleted = self.short_term.delete(key)
        long_deleted = self.long_term.delete(key)
        return short_deleted or long_deleted
    
    def clear_all(self):
        """Clear all memories"""
        self.short_term.clear()
        self.long_term.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        total_accesses = (
            self.stats["short_term_hits"] +
            self.stats["long_term_hits"] +
            self.stats["misses"]
        )
        
        return {
            "short_term_size": self.short_term.size(),
            "long_term_size": self.long_term.size(),
            "short_term_hits": self.stats["short_term_hits"],
            "long_term_hits": self.stats["long_term_hits"],
            "misses": self.stats["misses"],
            "hit_rate": (
                (self.stats["short_term_hits"] + self.stats["long_term_hits"]) /
                total_accesses
                if total_accesses > 0 else 0
            ),
        }
