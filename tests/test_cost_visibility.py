"""Tests for cost visibility and billing system."""

from __future__ import annotations

import os
import pytest
import sqlite3
import tempfile
from pathlib import Path

from billing import (
    CostCalculator,
    PricingPlan,
    PricingTier,
    UsageCost,
    get_pricing_plan
)


class TestPricingPlan:
    """Test PricingPlan dataclass."""
    
    def test_pricing_plan_creation(self):
        """Test creating pricing plan."""
        plan = PricingPlan(
            tier=PricingTier.FREE,
            price_per_eval=0.001,
            free_tier_limit=10000
        )
        
        assert plan.tier == PricingTier.FREE
        assert plan.price_per_eval == 0.001
        assert plan.free_tier_limit == 10000
    
    def test_pricing_plan_validation(self):
        """Test pricing plan validation."""
        with pytest.raises(ValueError):
            PricingPlan(
                tier=PricingTier.FREE,
                price_per_eval=-0.001,  # Negative price
                free_tier_limit=10000
            )
        
        with pytest.raises(ValueError):
            PricingPlan(
                tier=PricingTier.FREE,
                price_per_eval=0.001,
                free_tier_limit=-100  # Negative limit
            )
    
    def test_get_pricing_plan_default(self):
        """Test getting default pricing plan."""
        plan = get_pricing_plan()
        
        assert plan.tier == PricingTier.FREE
        assert plan.price_per_eval == 0.001
        assert plan.free_tier_limit == 10000
    
    def test_get_pricing_plan_starter(self):
        """Test getting starter plan."""
        plan = get_pricing_plan("starter")
        
        assert plan.tier == PricingTier.STARTER
        assert plan.price_per_eval == 0.0008
        assert plan.free_tier_limit == 0
        assert plan.monthly_minimum == 49.0


class TestUsageCost:
    """Test UsageCost dataclass."""
    
    def test_usage_cost_creation(self):
        """Test creating usage cost."""
        cost = UsageCost(
            tenant_id="tenant-1",
            current_month="2025-01",
            total_usage=8000,
            free_tier_usage=8000,
            billable_usage=0,
            unit_cost=0.001,
            total_cost=0.0,
            pricing_tier="free",
            free_tier_limit=10000,
            monthly_minimum=0.0
        )
        
        assert cost.tenant_id == "tenant-1"
        assert cost.total_usage == 8000
        assert cost.total_cost == 0.0
    
    def test_usage_cost_to_dict(self):
        """Test converting usage cost to dict."""
        cost = UsageCost(
            tenant_id="tenant-1",
            current_month="2025-01",
            total_usage=12000,
            free_tier_usage=10000,
            billable_usage=2000,
            unit_cost=0.001,
            total_cost=2.0,
            pricing_tier="free",
            free_tier_limit=10000,
            monthly_minimum=0.0
        )
        
        data = cost.to_dict()
        
        assert data["tenant_id"] == "tenant-1"
        assert data["total_usage"] == 12000
        assert data["billable_usage"] == 2000
        assert data["total_cost"] == 2.0
        assert data["cost_formatted"] == "$2.00"


class TestCostCalculator:
    """Test CostCalculator."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        yield db_path
        
        # Cleanup
        db_path.unlink(missing_ok=True)
    
    @pytest.fixture
    def calculator(self, temp_db):
        """Create calculator with temp db."""
        return CostCalculator(db_path=temp_db)
    
    def test_calculator_creation(self, calculator):
        """Test creating calculator."""
        assert calculator is not None
        assert calculator.db_path.exists()
    
    def test_track_usage(self, calculator):
        """Test tracking usage."""
        calculator.track_usage("tenant-1", count=100)
        
        usage = calculator.get_usage("tenant-1")
        
        assert usage == 100
    
    def test_track_usage_multiple(self, calculator):
        """Test tracking multiple usage increments."""
        calculator.track_usage("tenant-1", count=50)
        calculator.track_usage("tenant-1", count=30)
        calculator.track_usage("tenant-1", count=20)
        
        usage = calculator.get_usage("tenant-1")
        
        assert usage == 100
    
    def test_get_usage_no_data(self, calculator):
        """Test getting usage with no data."""
        usage = calculator.get_usage("tenant-unknown")
        
        assert usage == 0
    
    def test_calculate_cost_within_free_tier(self, calculator):
        """Test cost calculation within free tier."""
        # Track 8000 evaluations (under 10000 limit)
        calculator.track_usage("tenant-1", count=8000)
        
        # Calculate cost
        cost = calculator.calculate_cost("tenant-1")
        
        assert cost.total_usage == 8000
        assert cost.free_tier_usage == 8000
        assert cost.billable_usage == 0
        assert cost.total_cost == 0.0
    
    def test_calculate_cost_at_free_tier_limit(self, calculator):
        """Test cost calculation at exact free tier limit."""
        # Track exactly 10000 evaluations
        calculator.track_usage("tenant-1", count=10000)
        
        # Calculate cost
        cost = calculator.calculate_cost("tenant-1")
        
        assert cost.total_usage == 10000
        assert cost.free_tier_usage == 10000
        assert cost.billable_usage == 0
        assert cost.total_cost == 0.0
    
    def test_calculate_cost_over_free_tier(self, calculator):
        """Test cost calculation over free tier."""
        # Track 12000 evaluations (2000 over limit)
        calculator.track_usage("tenant-1", count=12000)
        
        # Calculate cost
        cost = calculator.calculate_cost("tenant-1")
        
        assert cost.total_usage == 12000
        assert cost.free_tier_usage == 10000
        assert cost.billable_usage == 2000
        # 2000 * $0.001 = $2.00
        assert cost.total_cost == 2.0
    
    def test_calculate_cost_no_free_tier(self, calculator):
        """Test cost calculation with no free tier."""
        # Set starter plan (no free tier)
        plan = get_pricing_plan("starter")
        calculator.set_pricing_plan_for_tenant("tenant-1", plan)
        
        # Track 5000 evaluations
        calculator.track_usage("tenant-1", count=5000)
        
        # Calculate cost
        cost = calculator.calculate_cost("tenant-1")
        
        assert cost.total_usage == 5000
        assert cost.free_tier_usage == 0
        assert cost.billable_usage == 5000
        # 5000 * $0.0008 = $4.00, but monthly minimum is $49
        assert cost.total_cost == 49.0  # Monthly minimum applied
    
    def test_calculate_cost_high_usage(self, calculator):
        """Test cost calculation with high usage."""
        # Track 1 million evaluations
        calculator.track_usage("tenant-1", count=1000000)
        
        # Calculate cost
        cost = calculator.calculate_cost("tenant-1")
        
        assert cost.total_usage == 1000000
        assert cost.billable_usage == 990000  # 1M - 10k free tier
        # 990000 * $0.001 = $990.00
        assert cost.total_cost == 990.0
    
    def test_set_pricing_plan(self, calculator):
        """Test setting pricing plan for tenant."""
        plan = PricingPlan(
            tier=PricingTier.PROFESSIONAL,
            price_per_eval=0.0005,
            free_tier_limit=0,
            monthly_minimum=199.0
        )
        
        calculator.set_pricing_plan_for_tenant("tenant-1", plan)
        
        retrieved_plan = calculator.get_pricing_plan_for_tenant("tenant-1")
        
        assert retrieved_plan.tier == PricingTier.PROFESSIONAL
        assert retrieved_plan.price_per_eval == 0.0005
    
    def test_multi_tenant_isolation(self, calculator):
        """Test multi-tenant isolation."""
        # Track for tenant-1
        calculator.track_usage("tenant-1", count=5000)
        
        # Track for tenant-2
        calculator.track_usage("tenant-2", count=8000)
        
        # Verify isolation
        cost1 = calculator.calculate_cost("tenant-1")
        cost2 = calculator.calculate_cost("tenant-2")
        
        assert cost1.total_usage == 5000
        assert cost2.total_usage == 8000


class TestCostAPI:
    """Test cost visibility API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from service.api import app
        
        return TestClient(app)
    
    @pytest.fixture
    def setup_usage(self, temp_db):
        """Setup test usage data."""
        calculator = CostCalculator(db_path=temp_db)
        
        # Track usage for testing
        calculator.track_usage("public", count=8000)
        
        yield calculator
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for API tests."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        yield db_path
        
        db_path.unlink(missing_ok=True)
    
    def test_get_cost_endpoint(self, client, setup_usage):
        """Test GET /billing/cost endpoint."""
        response = client.get("/billing/cost?tenant_id=public")
        
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["tenant_id"] == "public"
        assert data["total_usage"] >= 8000
        assert "total_cost" in data
        assert "cost_formatted" in data
    
    def test_get_usage_endpoint(self, client, setup_usage):
        """Test GET /billing/usage endpoint."""
        response = client.get("/billing/usage?tenant_id=public")
        
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["tenant_id"] == "public"
        assert "current_usage" in data
        assert "free_tier_limit" in data
        assert "remaining" in data
        assert "percentage" in data
    
    def test_get_pricing_endpoint(self, client):
        """Test GET /billing/pricing endpoint."""
        response = client.get("/billing/pricing?tenant_id=public")
        
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["tenant_id"] == "public"
        assert "pricing_tier" in data
        assert "price_per_eval" in data
        assert "free_tier_limit" in data
    
    def test_cost_dashboard_endpoint(self, client):
        """Test GET /billing/dashboard endpoint."""
        response = client.get("/billing/dashboard")
        
        assert response.status_code == 200
        assert "Cost Visibility" in response.text


class TestCostCalculationScenarios:
    """Test various cost calculation scenarios."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator with temp db."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        calc = CostCalculator(db_path=db_path)
        
        yield calc
        
        db_path.unlink(missing_ok=True)
    
    def test_boundary_10001_evaluations(self, calculator):
        """Test cost at 10001 evaluations (just over free tier)."""
        calculator.track_usage("tenant-1", count=10001)
        
        cost = calculator.calculate_cost("tenant-1")
        
        assert cost.billable_usage == 1
        # 1 * $0.001 = $0.001
        assert cost.total_cost == 0.001
    
    def test_zero_usage(self, calculator):
        """Test cost with zero usage."""
        cost = calculator.calculate_cost("tenant-1")
        
        assert cost.total_usage == 0
        assert cost.total_cost == 0.0
    
    def test_pricing_tiers_comparison(self, calculator):
        """Test different pricing tiers."""
        usage_count = 50000
        
        # Free tier
        calculator.track_usage("tenant-free", count=usage_count)
        cost_free = calculator.calculate_cost("tenant-free")
        # 50000 - 10000 = 40000 * $0.001 = $40
        assert cost_free.total_cost == 40.0
        
        # Starter tier
        plan_starter = get_pricing_plan("starter")
        calculator.set_pricing_plan_for_tenant("tenant-starter", plan_starter)
        calculator.track_usage("tenant-starter", count=usage_count)
        cost_starter = calculator.calculate_cost("tenant-starter")
        # 50000 * $0.0008 = $40, but monthly minimum is $49
        assert cost_starter.total_cost == 49.0  # Monthly minimum applied
        
        # Professional tier with high usage (above minimum)
        plan_pro = get_pricing_plan("professional")
        calculator.set_pricing_plan_for_tenant("tenant-pro", plan_pro)
        calculator.track_usage("tenant-pro", count=500000)  # Higher usage
        cost_pro = calculator.calculate_cost("tenant-pro")
        # 500000 * $0.0005 = $250 (above $199 minimum)
        assert cost_pro.total_cost == 250.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

