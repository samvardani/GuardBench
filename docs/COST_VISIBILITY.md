# Real-Time Cost Visibility

This document describes the real-time cost visibility system that provides tenants with transparent,up-to-date information about their usage and costs based on their pricing plan.

## Overview

The cost visibility system calculates and displays real-time usage costs based on consumption and pricing tiers. This transparency helps customers manage their usage, prevents billing surprises, and improves trust.

## Features

✅ **Real-Time Cost Calculation**: Instant cost updates based on current usage  
✅ **Multiple Pricing Tiers**: Free, Starter, Professional, Enterprise plans  
✅ **Free Tier Support**: 10,000 evaluations/month free tier  
✅ **Usage Tracking**: Automatic per-tenant usage tracking  
✅ **Beautiful Dashboard**: Interactive UI with usage bars and metrics  
✅ **Cost Breakdown**: Detailed breakdown of free vs. billable usage  
✅ **Alerts**: Visual warnings when approaching or exceeding limits  
✅ **Multi-Tenant**: Isolated cost tracking per tenant  
✅ **API Endpoints**: Programmatic access to cost data  

## Pricing Tiers

### Free Tier

- **Price**: $0.001 per evaluation
- **Free Tier**: 10,000 evaluations/month
- **Monthly Minimum**: $0
- **Best For**: Individual developers, testing, small projects

### Starter Tier

- **Price**: $0.0008 per evaluation
- **Free Tier**: None
- **Monthly Minimum**: $49
- **Best For**: Small teams, production apps with moderate usage

### Professional Tier

- **Price**: $0.0005 per evaluation
- **Free Tier**: None
- **Monthly Minimum**: $199
- **Best For**: Growing companies, high-volume applications

### Enterprise Tier

- **Price**: $0.0003 per evaluation
- **Free Tier**: None
- **Monthly Minimum**: $999
- **Best For**: Large organizations, very high volume

## Cost Calculation

### Within Free Tier

```python
if usage <= 10000:
    cost = $0.00
```

**Example**: 8,000 evaluations → $0.00

### Over Free Tier

```python
if usage > 10000:
    billable_usage = usage - 10000
    cost = billable_usage * price_per_eval
```

**Example**: 12,000 evaluations → (12000 - 10000) × $0.001 = $2.00

### Paid Tiers (No Free Tier)

```python
cost = max(usage * price_per_eval, monthly_minimum)
```

**Example (Starter)**: 5,000 evaluations → max($4.00, $49.00) = $49.00

## API Endpoints

### GET /billing/cost

Get current month cost breakdown for tenant.

**Query Parameters**:
- `tenant_id` (str): Tenant identifier

**Response**:
```json
{
  "tenant_id": "tenant-123",
  "current_month": "2025-01",
  "total_usage": 12000,
  "free_tier_usage": 10000,
  "billable_usage": 2000,
  "unit_cost": 0.001,
  "total_cost": 2.0,
  "pricing_tier": "free",
  "free_tier_limit": 10000,
  "monthly_minimum": 0.0,
  "cost_formatted": "$2.00"
}
```

**Example**:
```bash
curl "http://localhost:8001/billing/cost?tenant_id=public"
```

### GET /billing/usage

Get current month usage information.

**Response**:
```json
{
  "tenant_id": "tenant-123",
  "current_usage": 8000,
  "free_tier_limit": 10000,
  "remaining": 2000,
  "percentage": 80.0,
  "is_over_limit": false
}
```

### GET /billing/pricing

Get pricing information for tenant.

**Response**:
```json
{
  "tenant_id": "tenant-123",
  "pricing_tier": "free",
  "price_per_eval": 0.001,
  "free_tier_limit": 10000,
  "monthly_minimum": 0.0,
  "price_formatted": "$0.0010",
  "monthly_minimum_formatted": "$0.00"
}
```

### GET /billing/dashboard

Serve the interactive cost visibility dashboard UI.

Visit: http://localhost:8001/billing/dashboard

## Dashboard UI

### Features

**Summary Display**:
- Large cost amount display
- Pricing tier badge
- Usage alerts (approaching/over limit)

**Usage Bar**:
- Visual progress bar showing usage percentage
- Color-coded (green → yellow → red)
- Percentage display

**Usage Stats**:
- Total evaluations
- Free tier used
- Billable usage
- Free tier remaining

**Pricing Details**:
- Current tier
- Price per evaluation
- Free tier limit
- Monthly minimum

### Screenshots

```
┌────────────────────────────────────────────────┐
│            💳 Cost Visibility                  │
│      Real-time usage and cost tracking         │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│  ✅ Within Free Tier!                          │
│  You're using the free tier. 2,000 remaining   │
├────────────────────────────────────────────────┤
│                                                 │
│                   $0.00                         │
│            Current Month Cost                   │
│               [FREE tier]                       │
│                                                 │
│         Usage This Month                        │
│  ████████████████░░░░  80.0%                   │
│                                                 │
│  ┌──────────┬──────────┬──────────┬──────────┐│
│  │  8,000   │  8,000   │    0     │  2,000   ││
│  │  Total   │  Free    │Billable  │Remaining ││
│  └──────────┴──────────┴──────────┴──────────┘│
│                                                 │
│  📋 Pricing Details                            │
│  Tier: free                                     │
│  Price per Evaluation: $0.0010                  │
│  Free Tier Limit: 10,000 evaluations/month     │
│                                                 │
│               [🔄 Refresh]                      │
└────────────────────────────────────────────────┘
```

## Usage

### Track Usage (Automatic)

Usage is tracked automatically when evaluations are performed:

```python
from billing import get_cost_calculator

calculator = get_cost_calculator()

# After each evaluation
calculator.track_usage("tenant-123", count=1)
```

### Calculate Cost

```python
from billing import get_cost_calculator

calculator = get_cost_calculator()

# Get cost breakdown
cost = calculator.calculate_cost("tenant-123")

print(f"Usage: {cost.total_usage}")
print(f"Cost: ${cost.total_cost:.2f}")
print(f"Billable: {cost.billable_usage} evaluations")
```

### Set Pricing Plan

```python
from billing import get_cost_calculator, get_pricing_plan

calculator = get_cost_calculator()

# Upgrade to starter plan
plan = get_pricing_plan("starter")
calculator.set_pricing_plan_for_tenant("tenant-123", plan)
```

## Configuration

### Environment Variables

```bash
# Pricing tier (default: free)
export PRICING_TIER=free

# Custom pricing (overrides defaults)
export PRICE_PER_EVAL=0.001
export FREE_TIER_LIMIT=10000
export MONTHLY_MINIMUM=0.0
```

### Example Configurations

**Free Tier** (Default):
```bash
export PRICING_TIER=free
# 10k free evaluations, then $0.001 each
```

**Starter Plan**:
```bash
export PRICING_TIER=starter
# $0.0008 per evaluation, $49 monthly minimum
```

**Custom Pricing**:
```bash
export PRICING_TIER=free
export PRICE_PER_EVAL=0.0005
export FREE_TIER_LIMIT=25000
# 25k free evaluations, then $0.0005 each
```

## Integration Examples

### With Evaluation Pipeline

```python
from billing import get_cost_calculator

calculator = get_cost_calculator()

def evaluate_content(content, tenant_id):
    # Perform evaluation
    result = safety_guard.score(content)
    
    # Track usage
    calculator.track_usage(tenant_id, count=1)
    
    # Check cost
    cost = calculator.calculate_cost(tenant_id)
    
    # Warn if approaching limit
    if cost.total_usage >= cost.free_tier_limit * 0.9:
        logger.warning(f"Tenant {tenant_id} approaching free tier limit")
    
    return result
```

### With API Middleware

```python
from fastapi import Request
from billing import get_cost_calculator

calculator = get_cost_calculator()

@app.middleware("http")
async def track_usage_middleware(request: Request, call_next):
    response = await call_next(request)
    
    # Track usage after successful evaluation
    if request.url.path == "/score" and response.status_code == 200:
        tenant_id = request.state.tenant_id
        calculator.track_usage(tenant_id)
    
    return response
```

## Testing

Run cost visibility tests:

```bash
pytest tests/test_cost_visibility.py -v
```

**24 comprehensive tests** covering:
- ✅ Pricing plan creation and validation
- ✅ Usage cost calculations
- ✅ Cost calculator operations
- ✅ Within free tier scenarios
- ✅ Over free tier scenarios
- ✅ Multiple pricing tiers
- ✅ Monthly minimums
- ✅ High usage scenarios
- ✅ Multi-tenant isolation
- ✅ API endpoints
- ✅ Dashboard UI

### Test Examples

**Within Free Tier**:
```python
def test_within_free_tier():
    calculator = CostCalculator()
    calculator.track_usage("tenant-1", count=8000)
    
    cost = calculator.calculate_cost("tenant-1")
    
    assert cost.total_usage == 8000
    assert cost.total_cost == 0.0
```

**Over Free Tier**:
```python
def test_over_free_tier():
    calculator = CostCalculator()
    calculator.track_usage("tenant-1", count=12000)
    
    cost = calculator.calculate_cost("tenant-1")
    
    assert cost.billable_usage == 2000
    assert cost.total_cost == 2.0  # 2000 × $0.001
```

## Best Practices

1. **Show Cost Prominently**: Display cost on dashboard homepage
2. **Set Alerts**: Warn users at 80%, 90%, 100% of free tier
3. **Update Frequently**: Refresh cost display after each evaluation
4. **Provide History**: Show historical usage and costs
5. **Explain Pricing**: Clear documentation of pricing tiers
6. **Support Upgrade**: Easy path to upgrade to paid tiers
7. **Prevent Surprises**: Alert before charging

## Troubleshooting

### Cost Not Updating

**Check usage tracking**:
```python
from billing import get_cost_calculator

calculator = get_cost_calculator()
usage = calculator.get_usage("tenant-123")
print(f"Current usage: {usage}")
```

**Manually recalculate**:
```python
cost = calculator.calculate_cost("tenant-123")
print(f"Cost: ${cost.total_cost:.2f}")
```

### Dashboard Not Loading

**Check template path**:
```bash
ls -la templates/billing/cost_dashboard.html
```

**Check route**:
```bash
curl http://localhost:8001/billing/dashboard
```

### Incorrect Cost Calculation

**Verify pricing plan**:
```python
plan = calculator.get_pricing_plan_for_tenant("tenant-123")
print(f"Tier: {plan.tier}")
print(f"Price: ${plan.price_per_eval:.4f}")
print(f"Free tier: {plan.free_tier_limit}")
```

## Security

- **Multi-Tenant Isolation**: Each tenant sees only their own costs
- **No Cost Manipulation**: Usage tracking is server-side only
- **Audit Trail**: All usage is logged
- **Read-Only Display**: Users cannot modify costs

## Related Documentation

- [Pricing Plans](PRICING.md)
- [Usage Statistics](USAGE_STATISTICS.md)
- [Quota Enforcement](QUOTA.md)
- [Billing FAQ](BILLING_FAQ.md)

## Support

For cost visibility issues:
1. Check database tables exist: `tenant_usage`, `tenant_pricing`
2. Verify API endpoints respond: `/billing/cost`
3. Check pricing tier configuration
4. Review usage tracking calls
5. Test with curl/API client

