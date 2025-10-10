"""CLI commands for usage quota management."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .enforcer import get_quota_enforcer
from .reset import UsageResetter


def cmd_usage(args: argparse.Namespace) -> int:
    """Show usage for tenant."""
    enforcer = get_quota_enforcer()
    usage = enforcer.get_usage(args.tenant_id, period=args.period)
    
    print(f"Tenant: {usage.tenant_id}")
    print(f"Period: {usage.period}")
    print(f"Plan: {usage.plan_type}")
    print(f"Usage: {usage.usage_count:,}")
    
    if usage.monthly_quota:
        print(f"Quota: {usage.monthly_quota:,}")
        pct = (usage.usage_count / usage.monthly_quota) * 100
        print(f"Percentage: {pct:.1f}%")
        
        if usage.quota_exceeded:
            print("⚠️  QUOTA EXCEEDED")
        elif usage.quota_warning:
            print("⚠️  Approaching quota limit")
    else:
        print("Quota: Unlimited")
    
    return 0


def cmd_set_plan(args: argparse.Namespace) -> int:
    """Set tenant plan."""
    enforcer = get_quota_enforcer()
    enforcer.set_tenant_plan(
        args.tenant_id,
        args.plan,
        monthly_quota=args.quota
    )
    
    usage = enforcer.get_usage(args.tenant_id)
    print(f"✅ Updated tenant {args.tenant_id}")
    print(f"   Plan: {usage.plan_type}")
    print(f"   Quota: {usage.monthly_quota:,}" if usage.monthly_quota else "   Quota: Unlimited")
    
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    """Reset tenant usage."""
    enforcer = get_quota_enforcer()
    
    if args.all:
        resetter = UsageResetter()
        stats = resetter.check_and_reset_all()
        print(f"✅ Reset {stats['reset_count']} tenants")
        print(f"   Period: {stats['current_period']}")
        print(f"   Kept: {stats['kept_count']} (already current)")
    else:
        enforcer.reset_usage(args.tenant_id, period=args.period)
        print(f"✅ Reset usage for tenant {args.tenant_id}")
    
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List all tenants with usage."""
    import sqlite3
    
    db_path = Path("history.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            u.tenant_id,
            u.period,
            u.usage_count,
            p.plan_type,
            p.monthly_quota
        FROM tenant_usage u
        LEFT JOIN tenant_plans p ON u.tenant_id = p.tenant_id
        ORDER BY u.usage_count DESC
    """)
    
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        print("No usage data found")
        return 0
    
    print(f"{'Tenant ID':<30} {'Period':<10} {'Plan':<12} {'Usage':>10} {'Quota':>10} {'%':>6}")
    print("-" * 90)
    
    for row in rows:
        tenant_id = row["tenant_id"]
        period = row["period"]
        plan_type = row["plan_type"] or "free"
        usage = row["usage_count"]
        quota = row["monthly_quota"]
        
        quota_str = f"{quota:,}" if quota else "∞"
        pct_str = f"{(usage/quota)*100:.1f}%" if quota else "-"
        
        print(f"{tenant_id:<30} {period:<10} {plan_type:<12} {usage:>10,} {quota_str:>10} {pct_str:>6}")
    
    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Usage Quota Management CLI"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # usage command
    usage_parser = subparsers.add_parser("usage", help="Show usage for tenant")
    usage_parser.add_argument("tenant_id", help="Tenant ID")
    usage_parser.add_argument("--period", help="Period (YYYY-MM)")
    usage_parser.set_defaults(func=cmd_usage)
    
    # set-plan command
    plan_parser = subparsers.add_parser("set-plan", help="Set tenant plan")
    plan_parser.add_argument("tenant_id", help="Tenant ID")
    plan_parser.add_argument("plan", help="Plan type (free, starter, pro, enterprise)")
    plan_parser.add_argument("--quota", type=int, help="Custom monthly quota")
    plan_parser.set_defaults(func=cmd_set_plan)
    
    # reset command
    reset_parser = subparsers.add_parser("reset", help="Reset tenant usage")
    reset_parser.add_argument("--tenant-id", help="Tenant ID")
    reset_parser.add_argument("--period", help="Period (YYYY-MM)")
    reset_parser.add_argument("--all", action="store_true", help="Reset all tenants")
    reset_parser.set_defaults(func=cmd_reset)
    
    # list command
    list_parser = subparsers.add_parser("list", help="List all tenants with usage")
    list_parser.set_defaults(func=cmd_list)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

