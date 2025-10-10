"""Google Cloud Storage connector adapter."""

from __future__ import annotations

from typing import List

from .base_connector import ObjectStorageConnector, ConnectorType, ConnectorMetadata


class GCSConnector(ObjectStorageConnector):
    """Adapter for Google Cloud Storage.
    
    Wraps existing GCS functionality into the standard connector interface.
    """
    
    def __init__(self, **kwargs):
        """Initialize GCS connector.
        
        Args:
            **kwargs: Configuration (bucket, project, credentials)
        """
        super().__init__(**kwargs)
    
    def read_text(self, uri: str, encoding: str = "utf-8") -> str:
        """Read text from GCS object.
        
        Args:
            uri: GCS URI (e.g., "gs://bucket/key")
            encoding: Text encoding
            
        Returns:
            Object contents
        """
        raise NotImplementedError("Use read_jsonl for JSONL files")
    
    def write_text(self, uri: str, content: str, encoding: str = "utf-8") -> None:
        """Write text to GCS object.
        
        Args:
            uri: GCS URI
            content: Content to write
            encoding: Text encoding
        """
        raise NotImplementedError("Use write_jsonl for JSONL files")
    
    def read_jsonl(self, uri: str, encoding: str = "utf-8") -> List[dict]:
        """Read JSONL file from GCS.
        
        Args:
            uri: GCS URI
            encoding: Text encoding
            
        Returns:
            List of JSON objects
        """
        from connectors import gcs
        return gcs.read_jsonl(uri, encoding=encoding)
    
    def write_jsonl(self, uri: str, records: List[dict], encoding: str = "utf-8") -> None:
        """Write JSONL file to GCS.
        
        Args:
            uri: GCS URI
            records: List of JSON objects
            encoding: Text encoding
        """
        from connectors import gcs
        gcs.write_jsonl(uri, records, encoding=encoding)
    
    def exists(self, uri: str) -> bool:
        """Check if GCS object exists.
        
        Args:
            uri: GCS URI
            
        Returns:
            True if exists
        """
        from connectors import gcs
        return gcs.exists(uri)
    
    def delete(self, uri: str) -> None:
        """Delete GCS object.
        
        Args:
            uri: GCS URI
        """
        raise NotImplementedError("Delete not yet implemented for GCS")
    
    def list_objects(self, prefix: str) -> List[str]:
        """List GCS objects with prefix.
        
        Args:
            prefix: URI prefix
            
        Returns:
            List of object URIs
        """
        raise NotImplementedError("List not yet implemented for GCS")
    
    def get_metadata(self) -> ConnectorMetadata:
        """Get connector metadata.
        
        Returns:
            ConnectorMetadata
        """
        return ConnectorMetadata(
            name="gcs",
            connector_type=ConnectorType.OBJECT_STORAGE,
            provider="Google Cloud",
            version="1.0",
            supports_streaming=False,
            supports_batch=True,
        )


__all__ = ["GCSConnector"]

