"""Tests for unified billing system."""

from __future__ import annotations

import pytest
import sqlite3
import tempfile
from pathlib import Path

from billing import (
    compute_cost,
    CostResult,
    BillingCalculator,
    get_billing_calculator,
    PricingTier,
    PricingConfig,
    get_pricing_config
)


class TestPricingConfig:
    """Test centralized pricing configuration."""
    
    def test_pricing_config_defaults(self):
        """Test default pricing configuration."""
        config = PricingConfig()
        
        assert config.free_tier_limit == 10000
        assert config.free_price_per_eval == 0.001
        assert config.starter_monthly_minimum == 49.0
    
    def test_get_tier_config_free(self):
        """Test getting free tier config."""
        config = PricingConfig()
        tier_config = config.get_tier_config(PricingTier.FREE)
        
        assert tier_config["price_per_eval"] == 0.001
        assert tier_config["free_tier_limit"] == 10000
        assert tier_config["monthly_minimum"] == 0.0
    
    def test_get_tier_config_starter(self):
        """Test getting starter tier config."""
        config = PricingConfig()
        tier_config = config.get_tier_config(PricingTier.STARTER)
        
        assert tier_config["price_per_eval"] == 0.0008
        assert tier_config["free_tier_limit"] == 0
        assert tier_config["monthly_minimum"] == 49.0


class TestPureComputeCost:
    """Test pure compute_cost() function - single source of truth."""
    
    def test_compute_cost_within_free_tier(self):
        """Test cost within free tier."""
        result = compute_cost(usage=8000, tier=PricingTier.FREE)
        
        assert result.total_usage == 8000
        assert result.free_tier_usage == 8000
        assert result.billable_usage == 0
        assert result.subtotal == 0.0
        assert result.total_cost == 0.0
    
    def test_compute_cost_at_free_tier_limit(self):
        """Test cost at exact free tier limit (10,000)."""
        result = compute_cost(usage=10000, tier=PricingTier.FREE)
        
        assert result.total_usage == 10000
        assert result.free_tier_usage == 10000
        assert result.billable_usage == 0
        assert result.total_cost == 0.0  # Exactly at limit = $0.00
    
    def test_compute_cost_one_over_free_tier(self):
        """Test cost at 10,001 (one over free tier)."""
        result = compute_cost(usage=10001, tier=PricingTier.FREE)
        
        assert result.total_usage == 10001
        assert result.free_tier_usage == 10000
        assert result.billable_usage == 1
        assert result.subtotal == 0.001  # 1 × $0.001
        assert result.total_cost == 0.001  # $0.001
    
    def test_compute_cost_over_free_tier(self):
        """Test cost over free tier."""
        result = compute_cost(usage=12000, tier=PricingTier.FREE)
        
        assert result.total_usage == 12000
        assert result.free_tier_usage == 10000
        assert result.billable_usage == 2000
        assert result.subtotal == 2.0  # 2000 × $0.001
        assert result.total_cost == 2.0
    
    def test_compute_cost_starter_below_minimum(self):
        """Test starter tier with usage below monthly minimum."""
        result = compute_cost(usage=5000, tier=PricingTier.STARTER)
        
        assert result.total_usage == 5000
        assert result.billable_usage == 5000  # No free tier
        assert result.subtotal == 4.0  # 5000 × $0.0008
        assert result.total_cost == 49.0  # Monthly minimum applied
    
    def test_compute_cost_starter_above_minimum(self):
        """Test starter tier with usage above monthly minimum."""
        result = compute_cost(usage=100000, tier=PricingTier.STARTER)
        
        assert result.total_usage == 100000
        assert result.billable_usage == 100000
        assert result.subtotal == 80.0  # 100000 × $0.0008
        assert result.total_cost == 80.0  # Above minimum, use subtotal
    
    def test_compute_cost_zero_usage(self):
        """Test zero usage."""
        result = compute_cost(usage=0, tier=PricingTier.FREE)
        
        assert result.total_usage == 0
        assert result.total_cost == 0.0
    
    def test_compute_cost_high_usage(self):
        """Test high usage (1 million)."""
        result = compute_cost(usage=1000000, tier=PricingTier.FREE)
        
        assert result.total_usage == 1000000
        assert result.billable_usage == 990000  # 1M - 10k
        assert result.total_cost == 990.0  # 990k × $0.001


class TestBillingCalculator:
    """Test BillingCalculator with database."""
    
    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database."""
        db_path = tmp_path / "test_billing.db"
        return db_path
    
    @pytest.fixture
    def calculator(self, temp_db):
        """Create calculator with isolated temp db."""
        return BillingCalculator(db_path=temp_db)
    
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
        """Test tracking multiple increments."""
        calculator.track_usage("tenant-1", count=50)
        calculator.track_usage("tenant-1", count=30)
        calculator.track_usage("tenant-1", count=20)
        
        usage = calculator.get_usage("tenant-1")
        
        assert usage == 100
    
    def test_get_usage_no_data(self, calculator):
        """Test getting usage with no data."""
        usage = calculator.get_usage("tenant-unknown")
        
        assert usage == 0
    
    def test_set_tier(self, calculator):
        """Test setting pricing tier."""
        calculator.set_tier("tenant-1", PricingTier.STARTER)
        
        tier = calculator.get_tier("tenant-1")
        
        assert tier == PricingTier.STARTER
    
    def test_get_tier_default(self, calculator):
        """Test getting default tier (FREE)."""
        tier = calculator.get_tier("tenant-unknown")
        
        assert tier == PricingTier.FREE
    
    def test_calculate_cost_integration(self, calculator):
        """Test calculate_cost using unified function."""
        # Track usage
        calculator.track_usage("tenant-1", count=12000)
        
        # Calculate cost
        cost = calculator.calculate_cost("tenant-1")
        
        # Uses compute_cost() internally - single source of truth
        assert cost.total_usage == 12000
        assert cost.billable_usage == 2000
        assert cost.total_cost == 2.0
    
    def test_multi_tenant_isolation(self, calculator):
        """Test multi-tenant isolation."""
        calculator.track_usage("tenant-1", count=5000)
        calculator.track_usage("tenant-2", count=8000)
        
        cost1 = calculator.calculate_cost("tenant-1")
        cost2 = calculator.calculate_cost("tenant-2")
        
        assert cost1.total_usage == 5000
        assert cost2.total_usage == 8000


class TestBoundaryScenarios:
    """Test boundary cases - critical for correctness."""
    
    @pytest.fixture
    def calculator(self, tmp_path):
        """Create calculator with isolated temp db."""
        db_path = tmp_path / "test_billing.db"
        return BillingCalculator(db_path=db_path)
    
    def test_exactly_10000_evaluations(self, calculator):
        """Test exactly at free tier limit."""
        calculator.track_usage("tenant-1", count=10000)
        
        cost = calculator.calculate_cost("tenant-1")
        
        # Exactly at limit = $0.00
        assert cost.total_usage == 10000
        assert cost.free_tier_usage == 10000
        assert cost.billable_usage == 0
        assert cost.total_cost == 0.0
    
    def test_10001_evaluations(self, calculator):
        """Test 10,001 evaluations (one over limit)."""
        calculator.track_usage("tenant-1", count=10001)
        
        cost = calculator.calculate_cost("tenant-1")
        
        # One over = $0.001
        assert cost.total_usage == 10001
        assert cost.free_tier_usage == 10000
        assert cost.billable_usage == 1
        assert cost.subtotal == 0.001
        assert cost.total_cost == 0.001
    
    def test_9999_evaluations(self, calculator):
        """Test 9,999 evaluations (one under limit)."""
        calculator.track_usage("tenant-1", count=9999)
        
        cost = calculator.calculate_cost("tenant-1")
        
        # Under limit = $0.00
        assert cost.total_usage == 9999
        assert cost.total_cost == 0.0


class TestAPI:
    """Test billing API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from service.api import app
        
        return TestClient(app)
    
    @pytest.fixture
    def setup_data(self, tmp_path):
        """Setup test data with isolated database."""
        db_path = tmp_path / "test_api.db"
        calculator = BillingCalculator(db_path=db_path)
        
        # Track usage
        calculator.track_usage("public", count=8000)
        
        # Temporarily replace global calculator
        import billing.calculator
        original_calculator = billing.calculator._global_calculator
        billing.calculator._global_calculator = calculator
        
        yield calculator
        
        # Restore
        billing.calculator._global_calculator = original_calculator
    
    def test_get_cost_endpoint(self, client, setup_data):
        """Test GET /billing/cost endpoint."""
        response = client.get("/billing/cost?tenant_id=public")
        
        assert response.status_code == 200
        
        # Check headers
        assert "X-Billing-Plan" in response.headers
        assert "X-Billable-Usage" in response.headers
        assert "X-Total-Cost" in response.headers
        
        # Check data
        data = response.json()
        
        assert data["tenant_id"] == "public"
        assert data["total_usage"] == 8000
        assert data["billable_usage"] == 0
        assert data["total_cost"] == 0.0
        assert data["cost_formatted"] == "$0.00"
    
    def test_get_usage_endpoint(self, client, setup_data):
        """Test GET /billing/usage endpoint."""
        response = client.get("/billing/usage?tenant_id=public")
        
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["tenant_id"] == "public"
        assert data["current_usage"] == 8000
        assert data["free_tier_limit"] == 10000
        assert data["remaining"] == 2000
        assert data["percentage"] == 80.0
        assert data["is_over_limit"] is False
    
    def test_get_pricing_endpoint(self, client):
        """Test GET /billing/pricing endpoint."""
        response = client.get("/billing/pricing?tenant_id=public")
        
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["pricing_tier"] == "free"
        assert data["price_per_eval"] == 0.001
        assert data["free_tier_limit"] == 10000


class TestUnifiedPricing:
    """Test that all components use the same pricing source."""
    
    @pytest.fixture
    def calculator(self, tmp_path):
        """Create calculator with isolated temp db."""
        db_path = tmp_path / "test_unified.db"
        return BillingCalculator(db_path=db_path)
    
    def test_api_matches_pure_function(self, calculator):
        """Test that API uses same calculation as pure function."""
        # Track usage
        calculator.track_usage("tenant-1", count=12000)
        
        # Calculate via API (uses compute_cost internally)
        api_result = calculator.calculate_cost("tenant-1")
        
        # Calculate via pure function directly
        pure_result = compute_cost(usage=12000, tier=PricingTier.FREE)
        
        # Should match exactly
        assert api_result.total_usage == pure_result.total_usage
        assert api_result.billable_usage == pure_result.billable_usage
        assert api_result.total_cost == pure_result.total_cost
    
    def test_headers_match_api_values(self, tmp_path):
        """Test that billing headers match API cost values."""
        from fastapi.testclient import TestClient
        from service.api import app
        
        # Setup
        db_path = tmp_path / "test_headers.db"
        calculator = BillingCalculator(db_path=db_path)
        calculator.track_usage("public", count=12000)
        
        # Replace global
        import billing.calculator
        original = billing.calculator._global_calculator
        billing.calculator._global_calculator = calculator
        
        try:
            client = TestClient(app)
            response = client.get("/billing/cost?tenant_id=public")
            
            assert response.status_code == 200
            
            data = response.json()
            
            # Headers should match API values
            assert response.headers["X-Billable-Usage"] == str(data["billable_usage"])
            assert response.headers["X-Total-Cost"] == data["cost_formatted"]
        
        finally:
            billing.calculator._global_calculator = original


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

