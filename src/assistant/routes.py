"""Safety Copilot API routes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Import at runtime to avoid circular dependency
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from service.api import AuthContext
from .service import get_copilot, AssistantQuery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["Safety Copilot"])


class QueryRequest(BaseModel):
    """Request to query the assistant."""
    
    question: str = Field(..., min_length=1, max_length=500, description="User question")
    run_id: Optional[str] = Field(default=None, description="Optional run ID for context")
    category: Optional[str] = Field(default=None, description="Optional category context")
    language: Optional[str] = Field(default=None, description="Optional language context")


class QueryResponse(BaseModel):
    """Response from the assistant."""
    
    answer: str
    query: str
    latency_ms: int
    model: str
    tokens_used: Optional[int] = None


@router.post("/query", response_model=QueryResponse)
async def query_assistant(
    request: QueryRequest,
    ctx: Optional["AuthContext"] = None
) -> QueryResponse:
    """Query the Safety Copilot assistant.
    
    Args:
        request: Query request
        ctx: Optional auth context
        
    Returns:
        Assistant response
    """
    # Get tenant ID
    tenant_id = ctx.tenant_id if ctx else "public"
    
    # Get copilot
    try:
        copilot = get_copilot()
    except Exception as e:
        logger.error(f"Failed to initialize copilot: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Safety Copilot not available. Ensure OPENAI_API_KEY is set."
        )
    
    # Create query
    query = AssistantQuery(
        question=request.question,
        run_id=request.run_id,
        category=request.category,
        language=request.language,
    )
    
    # Query assistant
    try:
        response = copilot.query(query, tenant_id=tenant_id)
        
        return QueryResponse(
            answer=response.answer,
            query=response.query,
            latency_ms=response.latency_ms,
            model=response.model,
            tokens_used=response.tokens_used,
        )
    
    except Exception as e:
        logger.exception(f"Error querying assistant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )


@router.get("/health")
async def assistant_health() -> Dict[str, Any]:
    """Check assistant health.
    
    Returns:
        Health status
    """
    try:
        copilot = get_copilot()
        healthy = copilot.health_check()
        
        return {
            "status": "healthy" if healthy else "unhealthy",
            "model": copilot.model,
        }
    
    except Exception as e:
        return {
            "status": "unavailable",
            "error": str(e),
        }


@router.get("/info")
async def assistant_info() -> Dict[str, Any]:
    """Get assistant information.
    
    Returns:
        Assistant info
    """
    return {
        "name": "Safety Copilot",
        "version": "1.0",
        "description": "AI assistant for safety evaluation analysis",
        "capabilities": [
            "Explain evaluation results",
            "Describe safety categories and policies",
            "Explain metrics (precision, recall, FNR, FPR)",
            "Suggest improvements",
            "Answer general safety questions",
        ],
        "supported_contexts": [
            "run_id: Specific evaluation run",
            "category: Safety category",
            "language: Content language",
        ],
    }


@router.get("/chat", response_class=HTMLResponse)
async def chat_ui() -> HTMLResponse:
    """Serve the chat UI.
    
    Returns:
        HTML chat interface
    """
    # Load template
    template_path = Path(__file__).resolve().parents[2] / "templates" / "assistant" / "chat.html"
    
    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat UI template not found"
        )
    
    return HTMLResponse(template_path.read_text())


__all__ = ["router"]

