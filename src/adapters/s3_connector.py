"""S3 connector adapter."""

from __future__ import annotations

from typing import List

from .base_connector import ObjectStorageConnector, ConnectorType, ConnectorMetadata


class S3Connector(ObjectStorageConnector):
    """Adapter for S3-compatible object storage.
    
    Wraps existing S3 functionality into the standard connector interface.
    """
    
    def __init__(self, **kwargs):
        """Initialize S3 connector.
        
        Args:
            **kwargs: Configuration (bucket, region, credentials)
        """
        super().__init__(**kwargs)
    
    def read_text(self, uri: str, encoding: str = "utf-8") -> str:
        """Read text from S3 object.
        
        Args:
            uri: S3 URI (e.g., "s3://bucket/key")
            encoding: Text encoding
            
        Returns:
            Object contents
        """
        from connectors import s3
        
        # For now, delegate to existing s3 module
        # In full implementation, would parse URI and use boto3 directly
        raise NotImplementedError("Use read_jsonl for JSONL files")
    
    def write_text(self, uri: str, content: str, encoding: str = "utf-8") -> None:
        """Write text to S3 object.
        
        Args:
            uri: S3 URI
            content: Content to write
            encoding: Text encoding
        """
        raise NotImplementedError("Use write_jsonl for JSONL files")
    
    def read_jsonl(self, uri: str, encoding: str = "utf-8") -> List[dict]:
        """Read JSONL file from S3.
        
        Args:
            uri: S3 URI
            encoding: Text encoding
            
        Returns:
            List of JSON objects
        """
        from connectors import s3
        return s3.read_jsonl(uri, encoding=encoding)
    
    def write_jsonl(self, uri: str, records: List[dict], encoding: str = "utf-8") -> None:
        """Write JSONL file to S3.
        
        Args:
            uri: S3 URI
            records: List of JSON objects
            encoding: Text encoding
        """
        from connectors import s3
        s3.write_jsonl(uri, records, encoding=encoding)
    
    def exists(self, uri: str) -> bool:
        """Check if S3 object exists.
        
        Args:
            uri: S3 URI
            
        Returns:
            True if exists
        """
        from connectors import s3
        return s3.exists(uri)
    
    def delete(self, uri: str) -> None:
        """Delete S3 object.
        
        Args:
            uri: S3 URI
        """
        raise NotImplementedError("Delete not yet implemented for S3")
    
    def list_objects(self, prefix: str) -> List[str]:
        """List S3 objects with prefix.
        
        Args:
            prefix: S3 URI prefix
            
        Returns:
            List of object URIs
        """
        raise NotImplementedError("List not yet implemented for S3")
    
    def get_metadata(self) -> ConnectorMetadata:
        """Get connector metadata.
        
        Returns:
            ConnectorMetadata
        """
        return ConnectorMetadata(
            name="s3",
            connector_type=ConnectorType.OBJECT_STORAGE,
            provider="AWS S3",
            version="1.0",
            supports_streaming=False,
            supports_batch=True,
        )


__all__ = ["S3Connector"]

