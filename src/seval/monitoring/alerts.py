"""Alert system for threshold violations."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SlackAlerter:
    """Sends alerts to Slack webhook when thresholds exceeded."""
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        cooldown_seconds: int = 300
    ):
        """Initialize Slack alerter.
        
        Args:
            webhook_url: Slack webhook URL (or from SLACK_WEBHOOK_URL env var)
            cooldown_seconds: Minimum time between alerts for same category
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.cooldown_seconds = cooldown_seconds
        self._last_alert: Dict[str, float] = {}
        
        if self.webhook_url:
            logger.info("SlackAlerter initialized with webhook")
        else:
            logger.info("SlackAlerter initialized without webhook (alerts disabled)")
    
    def _should_alert(self, category: str) -> bool:
        """Check if enough time has passed since last alert for category.
        
        Args:
            category: Content category
            
        Returns:
            True if alert should be sent
        """
        if category not in self._last_alert:
            return True
        
        elapsed = time.time() - self._last_alert[category]
        return elapsed >= self.cooldown_seconds
    
    def send_alert(
        self,
        category: str,
        message: str,
        metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send alert to Slack.
        
        Args:
            category: Content category
            message: Alert message
            metrics: Optional metrics to include
            
        Returns:
            True if alert was sent successfully
        """
        if not self.webhook_url:
            logger.debug(f"Slack webhook not configured, skipping alert: {message}")
            return False
        
        if not self._should_alert(category):
            logger.debug(f"Alert cooldown active for {category}, skipping")
            return False
        
        try:
            import httpx
            
            # Build Slack message
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 Safety Alert: {category}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                }
            ]
            
            # Add metrics if provided
            if metrics:
                fields = []
                for key, value in metrics.items():
                    fields.append({
                        "type": "mrkdwn",
                        "text": f"*{key}:* {value}"
                    })
                
                blocks.append({
                    "type": "section",
                    "fields": fields
                })
            
            payload = {
                "blocks": blocks
            }
            
            # Send to Slack
            response = httpx.post(
                self.webhook_url,
                json=payload,
                timeout=5.0
            )
            
            if response.status_code == 200:
                self._last_alert[category] = time.time()
                logger.info(f"Slack alert sent for {category}")
                return True
            else:
                logger.error(f"Slack webhook returned {response.status_code}: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def check_thresholds(self, summary: Dict[str, Any], thresholds: Dict[str, float]) -> None:
        """Check if metrics exceed thresholds and send alerts.
        
        Args:
            summary: Metrics summary from MetricsCollector
            thresholds: Dictionary of threshold values
        """
        # Check overall blocked rate
        blocked_threshold = thresholds.get("blocked_rate", 0.5)
        if summary["blocked_rate"] > blocked_threshold:
            self.send_alert(
                "overall",
                f"Overall blocked rate ({summary['blocked_rate']:.1%}) exceeds threshold ({blocked_threshold:.1%})",
                {
                    "Total Requests": summary["total_requests"],
                    "Blocked": summary["blocked_count"],
                    "QPS": summary["qps"]
                }
            )
        
        # Check per-category thresholds
        for category, cat_stats in summary.get("categories", {}).items():
            cat_threshold = thresholds.get(f"{category}_blocked_rate", 0.7)
            
            if cat_stats["blocked_rate"] > cat_threshold:
                self.send_alert(
                    category,
                    f"Category *{category}* blocked rate ({cat_stats['blocked_rate']:.1%}) exceeds threshold ({cat_threshold:.1%})",
                    {
                        "Requests": cat_stats["count"],
                        "Blocked": cat_stats["blocked"],
                        "Avg Score": f"{cat_stats['avg_score']:.2f}"
                    }
                )


# Global alerter
_global_alerter: Optional[SlackAlerter] = None


def get_global_alerter() -> SlackAlerter:
    """Get or create global Slack alerter.
    
    Returns:
        Global SlackAlerter instance
    """
    global _global_alerter
    if _global_alerter is None:
        _global_alerter = SlackAlerter()
    return _global_alerter

