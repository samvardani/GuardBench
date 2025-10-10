"""Kafka connector adapter."""

from __future__ import annotations

from typing import List

from .base_connector import MessageQueueConnector, ConnectorType, ConnectorMetadata


class KafkaConnector(MessageQueueConnector):
    """Adapter for Kafka message queue.
    
    Wraps existing Kafka functionality into the standard connector interface.
    """
    
    def __init__(
        self,
        brokers: str = "localhost:9092",
        **kwargs
    ):
        """Initialize Kafka connector.
        
        Args:
            brokers: Kafka broker addresses (comma-separated)
            **kwargs: Additional configuration
        """
        super().__init__(brokers=brokers, **kwargs)
        self.brokers = brokers
        
        # Initialize producer
        from connectors.kafka import Producer
        self.producer = Producer(brokers=brokers)
    
    def send(self, topic: str, message: dict) -> None:
        """Send message to Kafka topic.
        
        Args:
            topic: Topic name
            message: Message payload
        """
        self.producer.send_json(topic, message)
    
    def send_batch(self, topic: str, messages: List[dict]) -> None:
        """Send batch of messages.
        
        Args:
            topic: Topic name
            messages: List of messages
        """
        for message in messages:
            self.send(topic, message)
    
    def get_metadata(self) -> ConnectorMetadata:
        """Get connector metadata.
        
        Returns:
            ConnectorMetadata
        """
        return ConnectorMetadata(
            name="kafka",
            connector_type=ConnectorType.MESSAGE_QUEUE,
            provider="Apache Kafka",
            version="1.0",
            supports_streaming=True,
            supports_batch=True,
        )


__all__ = ["KafkaConnector"]

