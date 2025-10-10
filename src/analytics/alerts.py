"""Alert system for anomaly notifications."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from .anomaly_detector import Anomaly

logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:
    httpx = None


class AlertSystem:
    """Sends alerts for detected anomalies."""
    
    def __init__(
        self,
        slack_webhook_url: Optional[str] = None,
        email_enabled: bool = False,
        log_enabled: bool = True
    ):
        """Initialize alert system.
        
        Args:
            slack_webhook_url: Slack webhook URL
            email_enabled: Enable email alerts
            log_enabled: Enable log alerts
        """
        self.slack_webhook_url = slack_webhook_url
        self.email_enabled = email_enabled
        self.log_enabled = log_enabled
        
        logger.info(
            f"AlertSystem initialized: slack={bool(slack_webhook_url)}, "
            f"email={email_enabled}, log={log_enabled}"
        )
    
    def send_alert(self, anomaly: Anomaly) -> None:
        """Send alert for anomaly.
        
        Args:
            anomaly: Detected anomaly
        """
        if self.log_enabled:
            self._log_alert(anomaly)
        
        if self.slack_webhook_url:
            self._send_slack_alert(anomaly)
        
        if self.email_enabled:
            self._send_email_alert(anomaly)
    
    def _log_alert(self, anomaly: Anomaly) -> None:
        """Log alert."""
        severity_emoji = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🚨",
            "critical": "🔥"
        }
        
        emoji = severity_emoji.get(anomaly.severity.value, "⚠️")
        logger.warning(f"{emoji} ANOMALY ALERT: {anomaly}")
    
    def _send_slack_alert(self, anomaly: Anomaly) -> None:
        """Send Slack alert.
        
        Args:
            anomaly: Detected anomaly
        """
        if httpx is None:
            logger.warning("httpx not installed - cannot send Slack alert")
            return
        
        if not self.slack_webhook_url:
            return
        
        try:
            # Format message
            color = self._get_alert_color(anomaly.severity.value)
            
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"🚨 Anomaly Detected: {anomaly.type.value}",
                        "text": str(anomaly),
                        "fields": [
                            {
                                "title": "Metric",
                                "value": anomaly.metric_name,
                                "short": True
                            },
                            {
                                "title": "Severity",
                                "value": anomaly.severity.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Current Value",
                                "value": f"{anomaly.current_value:.2f}",
                                "short": True
                            },
                            {
                                "title": "Expected Value",
                                "value": f"{anomaly.expected_value:.2f}",
                                "short": True
                            },
                        ],
                        "footer": "Safety-Eval-Mini Anomaly Detection",
                        "ts": int(anomaly.timestamp)
                    }
                ]
            }
            
            if anomaly.tenant_id:
                payload["attachments"][0]["fields"].append({
                    "title": "Tenant",
                    "value": anomaly.tenant_id,
                    "short": True
                })
            
            # Send
            with httpx.Client(timeout=5.0) as client:
                response = client.post(self.slack_webhook_url, json=payload)
                response.raise_for_status()
            
            logger.info(f"Slack alert sent for {anomaly.type.value}")
        
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def _send_email_alert(self, anomaly: Anomaly) -> None:
        """Send email alert.
        
        Args:
            anomaly: Detected anomaly
        """
        # Placeholder for email integration
        logger.info(f"Email alert would be sent for {anomaly.type.value}")
        # TODO: Implement email sending (SMTP or service like SendGrid)
    
    def _get_alert_color(self, severity: str) -> str:
        """Get color for alert severity.
        
        Args:
            severity: Severity level
            
        Returns:
            Color hex code
        """
        colors = {
            "low": "#36a64f",      # Green
            "medium": "#ff9900",   # Orange
            "high": "#ff0000",     # Red
            "critical": "#8b0000"  # Dark red
        }
        
        return colors.get(severity, "#ff9900")


def create_alert_system() -> AlertSystem:
    """Create alert system from environment configuration.
    
    Returns:
        AlertSystem instance
    """
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    email_enabled = os.getenv("EMAIL_ALERTS_ENABLED", "0") == "1"
    log_enabled = os.getenv("LOG_ALERTS_ENABLED", "1") == "1"
    
    return AlertSystem(
        slack_webhook_url=slack_webhook_url,
        email_enabled=email_enabled,
        log_enabled=log_enabled
    )


__all__ = ["AlertSystem", "create_alert_system"]

