#!/usr/bin/env python3
"""
AEGIS Federation API Endpoints
RESTful API for antibody sharing across deployments
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.aegis.federation import FederationNetwork, Antibody

# Create router
router = APIRouter(prefix="/federation", tags=["AEGIS Federation"])

# Initialize federation network
federation = FederationNetwork(node_id="api_node")


# Pydantic models
class AntibodySubmission(BaseModel):
    pattern: str = Field(..., description="Regex pattern for detection")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    category: str = Field(..., description="Category (violence, harassment, etc.)")
    seen_count: int = Field(default=1, ge=1, description="Number of times pattern was seen")
    false_positive_count: int = Field(default=0, ge=0, description="Number of false positives")
    false_negative_count: int = Field(default=0, ge=0, description="Number of false negatives")


class VoteRequest(BaseModel):
    antibody_id: str = Field(..., description="Antibody ID to vote on")
    reason: Optional[str] = Field(None, description="Reason for downvote (false_positive, false_negative)")


class SyncRequest(BaseModel):
    node_id: str = Field(..., description="Source node ID")
    antibodies: List[Dict[str, Any]] = Field(..., description="Antibodies to sync")
    timestamp: Optional[str] = Field(None, description="Sync timestamp")


# Endpoints
@router.post("/intel-exchange", summary="Submit new antibody to federation")
async def submit_antibody(submission: AntibodySubmission):
    """
    Submit a new antibody pattern to the federation network.
    
    **Privacy:** Only the regex pattern and metadata are shared, no raw text.
    
    **Reputation:** Antibodies are tracked and scored based on accuracy.
    """
    try:
        result = federation.submit_antibody(
            pattern=submission.pattern,
            confidence=submission.confidence,
            category=submission.category,
            seen_count=submission.seen_count,
            false_positive_count=submission.false_positive_count,
            false_negative_count=submission.false_negative_count
        )
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upvote", summary="Upvote an antibody (worked well)")
async def upvote_antibody(vote: VoteRequest):
    """
    Upvote an antibody that worked well in your deployment.
    
    This increases the antibody's reputation score.
    """
    try:
        result = federation.upvote_antibody(vote.antibody_id)
        
        if result['status'] == 'error':
            raise HTTPException(status_code=404, detail=result['message'])
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/downvote", summary="Downvote an antibody (false positive or ineffective)")
async def downvote_antibody(vote: VoteRequest):
    """
    Downvote an antibody that caused false positives or was ineffective.
    
    This decreases the antibody's reputation score.
    """
    try:
        result = federation.downvote_antibody(
            vote.antibody_id,
            reason=vote.reason or "false_positive"
        )
        
        if result['status'] == 'error':
            raise HTTPException(status_code=404, detail=result['message'])
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/antibodies", summary="Get validated antibodies")
async def get_antibodies(
    category: Optional[str] = None,
    min_reputation: float = 0.6,
    limit: int = 100
):
    """
    Get validated antibodies from the federation.
    
    **Filters:**
    - category: Filter by category (violence, harassment, etc.)
    - min_reputation: Minimum reputation score (0.0-1.0)
    - limit: Maximum number of results
    """
    try:
        antibodies = federation.get_validated_antibodies(
            min_reputation=min_reputation,
            category=category
        )
        
        # Limit results
        antibodies = antibodies[:limit]
        
        return {
            "success": True,
            "count": len(antibodies),
            "antibodies": [
                {
                    "antibody_id": ab.antibody_id,
                    "pattern": ab.pattern,
                    "confidence": ab.confidence,
                    "category": ab.category,
                    "reputation_score": ab.reputation_score,
                    "seen_count": ab.seen_count,
                    "upvotes": ab.upvotes,
                    "downvotes": ab.downvotes,
                    "created_at": ab.created_at,
                    "source_node": ab.source_node
                }
                for ab in antibodies
            ],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/antibodies/{antibody_id}", summary="Get antibody details")
async def get_antibody(antibody_id: str):
    """Get detailed information about a specific antibody."""
    try:
        if antibody_id not in federation.antibodies:
            raise HTTPException(status_code=404, detail="Antibody not found")
        
        ab = federation.antibodies[antibody_id]
        
        return {
            "success": True,
            "antibody": {
                "antibody_id": ab.antibody_id,
                "pattern": ab.pattern,
                "confidence": ab.confidence,
                "category": ab.category,
                "reputation_score": ab.reputation_score,
                "seen_count": ab.seen_count,
                "false_positive_count": ab.false_positive_count,
                "false_negative_count": ab.false_negative_count,
                "upvotes": ab.upvotes,
                "downvotes": ab.downvotes,
                "created_at": ab.created_at,
                "source_node": ab.source_node,
                "is_expired": ab.is_expired()
            },
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync", summary="Sync antibodies from another node (Gossip Protocol)")
async def sync_with_node(sync_request: SyncRequest):
    """
    Sync antibodies with another node using gossip protocol.
    
    **Privacy:** Only patterns and metadata are shared, never raw text.
    
    **Validation:** Low-reputation antibodies are rejected.
    """
    try:
        result = federation.sync_with_node({
            'node_id': sync_request.node_id,
            'antibodies': sync_request.antibodies
        })
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export", summary="Export antibodies for sharing")
async def export_antibodies(min_reputation: float = 0.6):
    """
    Export validated antibodies for sharing with other nodes.
    
    Use this endpoint to pull antibodies from this node.
    """
    try:
        export = federation.export_antibodies_for_sync(min_reputation=min_reputation)
        
        return {
            "success": True,
            "data": export,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", summary="Get federation statistics")
async def get_statistics():
    """Get overall federation network statistics."""
    try:
        stats = federation.get_statistics()
        
        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prune", summary="Prune expired/low-reputation antibodies")
async def prune_antibodies(threshold: float = 0.3):
    """
    Remove expired antibodies and those with very low reputation.
    
    **Maintenance:** Run this periodically to keep the federation clean.
    """
    try:
        expired_count = federation.prune_expired_antibodies()
        low_rep_count = federation.prune_low_reputation_antibodies(threshold)
        
        return {
            "success": True,
            "pruned": {
                "expired": expired_count,
                "low_reputation": low_rep_count,
                "total": expired_count + low_rep_count
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", summary="Federation health check")
async def health_check():
    """Check if federation network is operational."""
    try:
        stats = federation.get_statistics()
        
        return {
            "status": "healthy",
            "node_id": federation.node_id,
            "total_antibodies": stats['total_antibodies'],
            "active_antibodies": stats['active_antibodies'],
            "avg_reputation": stats['avg_reputation'],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }












