"""Azure Blob Storage connector adapter."""

from __future__ import annotations

from typing import List

from .base_connector import ObjectStorageConnector, ConnectorType, ConnectorMetadata


class AzureBlobConnector(ObjectStorageConnector):
    """Adapter for Azure Blob Storage.
    
    Wraps existing Azure Blob functionality into the standard connector interface.
    """
    
    def __init__(self, **kwargs):
        """Initialize Azure Blob connector.
        
        Args:
            **kwargs: Configuration (account, key, container)
        """
        super().__init__(**kwargs)
    
    def read_text(self, uri: str, encoding: str = "utf-8") -> str:
        """Read text from Azure Blob.
        
        Args:
            uri: Blob URI
            encoding: Text encoding
            
        Returns:
            Blob contents
        """
        raise NotImplementedError("Use read_jsonl for JSONL files")
    
    def write_text(self, uri: str, content: str, encoding: str = "utf-8") -> None:
        """Write text to Azure Blob.
        
        Args:
            uri: Blob URI
            content: Content to write
            encoding: Text encoding
        """
        raise NotImplementedError("Use write_jsonl for JSONL files")
    
    def read_jsonl(self, uri: str, encoding: str = "utf-8") -> List[dict]:
        """Read JSONL file from Azure Blob.
        
        Args:
            uri: Blob URI
            encoding: Text encoding
            
        Returns:
            List of JSON objects
        """
        from connectors import azure
        return azure.read_jsonl(uri, encoding=encoding)
    
    def write_jsonl(self, uri: str, records: List[dict], encoding: str = "utf-8") -> None:
        """Write JSONL file to Azure Blob.
        
        Args:
            uri: Blob URI
            records: List of JSON objects
            encoding: Text encoding
        """
        from connectors import azure
        azure.write_jsonl(uri, records, encoding=encoding)
    
    def exists(self, uri: str) -> bool:
        """Check if blob exists.
        
        Args:
            uri: Blob URI
            
        Returns:
            True if exists
        """
        from connectors import azure
        return azure.exists(uri)
    
    def delete(self, uri: str) -> None:
        """Delete blob.
        
        Args:
            uri: Blob URI
        """
        raise NotImplementedError("Delete not yet implemented for Azure Blob")
    
    def list_objects(self, prefix: str) -> List[str]:
        """List blobs with prefix.
        
        Args:
            prefix: URI prefix
            
        Returns:
            List of blob URIs
        """
        raise NotImplementedError("List not yet implemented for Azure Blob")
    
    def get_metadata(self) -> ConnectorMetadata:
        """Get connector metadata.
        
        Returns:
            ConnectorMetadata
        """
        return ConnectorMetadata(
            name="azure_blob",
            connector_type=ConnectorType.OBJECT_STORAGE,
            provider="Microsoft Azure",
            version="1.0",
            supports_streaming=False,
            supports_batch=True,
        )


__all__ = ["AzureBlobConnector"]

