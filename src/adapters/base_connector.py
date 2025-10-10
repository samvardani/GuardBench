"""Base adapter interface for data connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ConnectorType(Enum):
    """Types of connectors."""
    
    OBJECT_STORAGE = "object_storage"  # S3, GCS, Azure Blob
    MESSAGE_QUEUE = "message_queue"    # Kafka, RabbitMQ, SQS
    DATABASE = "database"               # PostgreSQL, MySQL, MongoDB
    CACHE = "cache"                     # Redis, Memcached


@dataclass
class ConnectorMetadata:
    """Metadata about a connector."""
    
    name: str
    connector_type: ConnectorType
    provider: str
    version: Optional[str] = None
    supports_streaming: bool = False
    supports_batch: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "connector_type": self.connector_type.value,
            "provider": self.provider,
            "version": self.version,
            "supports_streaming": self.supports_streaming,
            "supports_batch": self.supports_batch,
        }


class BaseConnector(ABC):
    """Abstract base class for data connectors.
    
    Provides a uniform interface for interacting with different data storage
    and messaging systems (S3, GCS, Azure Blob, Kafka, etc.).
    """
    
    def __init__(self, **kwargs: Any):
        """Initialize connector.
        
        Args:
            **kwargs: Configuration parameters (credentials, endpoints, etc.)
        """
        self.config = kwargs
    
    @abstractmethod
    def get_metadata(self) -> ConnectorMetadata:
        """Get connector metadata.
        
        Returns:
            ConnectorMetadata describing this connector
        """
        pass
    
    def initialize(self) -> None:
        """Optional initialization/setup.
        
        Override to perform any setup needed before operations.
        """
        pass
    
    def health_check(self) -> bool:
        """Check if connector is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        return True


class ObjectStorageConnector(BaseConnector):
    """Abstract base for object storage connectors (S3, GCS, Azure Blob)."""
    
    @abstractmethod
    def read_text(self, uri: str, encoding: str = "utf-8") -> str:
        """Read text from object.
        
        Args:
            uri: Object URI (e.g., "s3://bucket/key")
            encoding: Text encoding
            
        Returns:
            Object contents as string
        """
        pass
    
    @abstractmethod
    def write_text(self, uri: str, content: str, encoding: str = "utf-8") -> None:
        """Write text to object.
        
        Args:
            uri: Object URI
            content: Content to write
            encoding: Text encoding
        """
        pass
    
    @abstractmethod
    def read_jsonl(self, uri: str, encoding: str = "utf-8") -> List[dict]:
        """Read JSONL file.
        
        Args:
            uri: Object URI
            encoding: Text encoding
            
        Returns:
            List of JSON objects
        """
        pass
    
    @abstractmethod
    def write_jsonl(self, uri: str, records: List[dict], encoding: str = "utf-8") -> None:
        """Write JSONL file.
        
        Args:
            uri: Object URI
            records: List of JSON objects
            encoding: Text encoding
        """
        pass
    
    @abstractmethod
    def exists(self, uri: str) -> bool:
        """Check if object exists.
        
        Args:
            uri: Object URI
            
        Returns:
            True if exists
        """
        pass
    
    @abstractmethod
    def delete(self, uri: str) -> None:
        """Delete object.
        
        Args:
            uri: Object URI
        """
        pass
    
    @abstractmethod
    def list_objects(self, prefix: str) -> List[str]:
        """List objects with prefix.
        
        Args:
            prefix: URI prefix
            
        Returns:
            List of object URIs
        """
        pass


class MessageQueueConnector(BaseConnector):
    """Abstract base for message queue connectors (Kafka, SQS, etc.)."""
    
    @abstractmethod
    def send(self, topic: str, message: dict) -> None:
        """Send message to topic/queue.
        
        Args:
            topic: Topic or queue name
            message: Message payload
        """
        pass
    
    @abstractmethod
    def send_batch(self, topic: str, messages: List[dict]) -> None:
        """Send batch of messages.
        
        Args:
            topic: Topic or queue name
            messages: List of message payloads
        """
        pass


__all__ = [
    "BaseConnector",
    "ObjectStorageConnector",
    "MessageQueueConnector",
    "ConnectorType",
    "ConnectorMetadata",
]

