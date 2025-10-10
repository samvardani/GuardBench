"""Benchmark leaderboard for guard performance comparison."""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result from a benchmark evaluation."""
    
    dataset_name: str
    guard_name: str
    guard_version: Optional[str] = None
    guard_config: Optional[Dict[str, Any]] = None
    run_id: Optional[str] = None
    tenant_id: str = "public"
    
    # Metrics
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    fnr: float = 0.0
    fpr: float = 0.0
    
    # Confusion matrix
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0
    
    # Performance
    avg_latency_ms: int = 0
    p50_latency_ms: int = 0
    p90_latency_ms: int = 0
    p99_latency_ms: int = 0
    
    # Metadata
    dataset_size: int = 0
    categories: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    is_public: bool = False
    
    id: Optional[int] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "dataset_name": self.dataset_name,
            "guard_name": self.guard_name,
            "guard_version": self.guard_version,
            "guard_config": self.guard_config,
            "run_id": self.run_id,
            "tenant_id": self.tenant_id,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "fnr": self.fnr,
            "fpr": self.fpr,
            "tp": self.tp,
            "fp": self.fp,
            "tn": self.tn,
            "fn": self.fn,
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p90_latency_ms": self.p90_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "dataset_size": self.dataset_size,
            "categories": self.categories,
            "languages": self.languages,
            "is_public": self.is_public,
            "created_at": self.created_at,
        }


@dataclass
class LeaderboardEntry:
    """Entry in the leaderboard with rank."""
    
    rank: int
    result: BenchmarkResult
    score: float  # Primary metric used for ranking
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = self.result.to_dict()
        data["rank"] = self.rank
        data["score"] = self.score
        return data


class Leaderboard:
    """Benchmark leaderboard manager."""
    
    def __init__(self, db_path: Path = Path("history.db")):
        """Initialize leaderboard.
        
        Args:
            db_path: Database path
        """
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self) -> None:
        """Initialize database tables."""
        try:
            from .schema import init_benchmark_tables
            
            conn = sqlite3.connect(self.db_path)
            init_benchmark_tables(conn)
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to initialize benchmark tables: {e}")
    
    def add_result(self, result: BenchmarkResult) -> int:
        """Add benchmark result to leaderboard.
        
        Args:
            result: Benchmark result
            
        Returns:
            Result ID
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            cur = conn.cursor()
            
            # Serialize config and lists
            config_json = json.dumps(result.guard_config) if result.guard_config else None
            categories_str = ",".join(result.categories) if result.categories else None
            languages_str = ",".join(result.languages) if result.languages else None
            
            cur.execute("""
                INSERT INTO benchmark_results (
                    dataset_name, guard_name, guard_version, guard_config, run_id, tenant_id,
                    precision, recall, f1_score, fnr, fpr,
                    tp, fp, tn, fn,
                    avg_latency_ms, p50_latency_ms, p90_latency_ms, p99_latency_ms,
                    dataset_size, categories, languages, is_public
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.dataset_name,
                result.guard_name,
                result.guard_version,
                config_json,
                result.run_id,
                result.tenant_id,
                result.precision,
                result.recall,
                result.f1_score,
                result.fnr,
                result.fpr,
                result.tp,
                result.fp,
                result.tn,
                result.fn,
                result.avg_latency_ms,
                result.p50_latency_ms,
                result.p90_latency_ms,
                result.p99_latency_ms,
                result.dataset_size,
                categories_str,
                languages_str,
                int(result.is_public),
            ))
            
            conn.commit()
            result_id = cur.lastrowid
            
            logger.info(f"Added benchmark result: {result.guard_name} on {result.dataset_name} (F1={result.f1_score:.3f})")
            
            return result_id
        
        finally:
            conn.close()
    
    def get_leaderboard(
        self,
        dataset_name: Optional[str] = None,
        tenant_id: Optional[str] = None,
        metric: str = "f1_score",
        limit: int = 100,
        public_only: bool = False
    ) -> List[LeaderboardEntry]:
        """Get leaderboard entries.
        
        Args:
            dataset_name: Optional dataset filter
            tenant_id: Optional tenant filter
            metric: Metric to rank by (f1_score, precision, recall)
            limit: Max entries to return
            public_only: If True, only return public results
            
        Returns:
            List of leaderboard entries with ranks
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Build query
            query = "SELECT * FROM benchmark_results WHERE 1=1"
            params = []
            
            if dataset_name:
                query += " AND dataset_name = ?"
                params.append(dataset_name)
            
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            
            if public_only:
                query += " AND is_public = 1"
            
            # Order by metric descending
            query += f" ORDER BY {metric} DESC, created_at DESC LIMIT ?"
            params.append(limit)
            
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            
            # Build entries with ranks
            entries = []
            for rank, row in enumerate(rows, 1):
                # Parse JSON fields
                config = json.loads(row["guard_config"]) if row["guard_config"] else None
                categories = row["categories"].split(",") if row["categories"] else []
                languages = row["languages"].split(",") if row["languages"] else []
                
                result = BenchmarkResult(
                    id=row["id"],
                    dataset_name=row["dataset_name"],
                    guard_name=row["guard_name"],
                    guard_version=row["guard_version"],
                    guard_config=config,
                    run_id=row["run_id"],
                    tenant_id=row["tenant_id"],
                    precision=row["precision"],
                    recall=row["recall"],
                    f1_score=row["f1_score"],
                    fnr=row["fnr"],
                    fpr=row["fpr"],
                    tp=row["tp"],
                    fp=row["fp"],
                    tn=row["tn"],
                    fn=row["fn"],
                    avg_latency_ms=row["avg_latency_ms"],
                    p50_latency_ms=row["p50_latency_ms"],
                    p90_latency_ms=row["p90_latency_ms"],
                    p99_latency_ms=row["p99_latency_ms"],
                    dataset_size=row["dataset_size"],
                    categories=categories,
                    languages=languages,
                    is_public=bool(row["is_public"]),
                    created_at=row["created_at"],
                )
                
                # Get score value for this metric
                score = getattr(result, metric, 0.0)
                
                entry = LeaderboardEntry(
                    rank=rank,
                    result=result,
                    score=score
                )
                
                entries.append(entry)
            
            return entries
        
        finally:
            conn.close()
    
    def get_datasets(self) -> List[str]:
        """Get list of available benchmark datasets.
        
        Returns:
            List of dataset names
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT dataset_name FROM benchmark_results ORDER BY dataset_name")
            rows = cur.fetchall()
            
            return [row[0] for row in rows]
        
        finally:
            conn.close()
    
    def get_dataset_info(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a benchmark dataset.
        
        Args:
            dataset_name: Dataset name
            
        Returns:
            Dataset info or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM benchmark_datasets WHERE dataset_name = ?",
                (dataset_name,)
            )
            row = cur.fetchone()
            
            if not row:
                return None
            
            return {
                "dataset_name": row["dataset_name"],
                "description": row["description"],
                "size": row["size"],
                "categories": row["categories"].split(",") if row["categories"] else [],
                "languages": row["languages"].split(",") if row["languages"] else [],
                "source_url": row["source_url"],
                "is_official": bool(row["is_official"]),
            }
        
        finally:
            conn.close()
    
    def register_dataset(
        self,
        dataset_name: str,
        description: str,
        size: int,
        categories: List[str],
        languages: List[str],
        source_url: Optional[str] = None,
        is_official: bool = False
    ) -> None:
        """Register a benchmark dataset.
        
        Args:
            dataset_name: Dataset name
            description: Description
            size: Number of samples
            categories: Categories covered
            languages: Languages covered
            source_url: Optional source URL
            is_official: If True, marked as official benchmark
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            categories_str = ",".join(categories)
            languages_str = ",".join(languages)
            
            conn.execute("""
                INSERT OR REPLACE INTO benchmark_datasets 
                (dataset_name, description, size, categories, languages, source_url, is_official)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                dataset_name,
                description,
                size,
                categories_str,
                languages_str,
                source_url,
                int(is_official)
            ))
            
            conn.commit()
            logger.info(f"Registered benchmark dataset: {dataset_name}")
        
        finally:
            conn.close()


# Global leaderboard instance
_global_leaderboard: Optional[Leaderboard] = None


def get_leaderboard() -> Leaderboard:
    """Get global leaderboard instance.
    
    Returns:
        Leaderboard instance
    """
    global _global_leaderboard
    
    if _global_leaderboard is None:
        _global_leaderboard = Leaderboard()
    
    return _global_leaderboard


__all__ = ["Leaderboard", "BenchmarkResult", "LeaderboardEntry", "get_leaderboard"]

