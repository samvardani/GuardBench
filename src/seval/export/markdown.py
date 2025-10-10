"""Markdown report renderer."""

from __future__ import annotations

from typing import Any, Dict, List


def render_markdown_report(report_data: Dict[str, Any]) -> str:
    """Render report as Markdown.
    
    Args:
        report_data: Report dictionary
        
    Returns:
        Markdown string
    """
    sections = []
    
    # Header
    metadata = report_data.get("metadata", {})
    sections.append(f"""# Safety Evaluation Report

**Report ID**: {metadata.get('report_id', 'N/A')}  
**Generated**: {metadata.get('generated_at', 'N/A')}  
**Policy Version**: {metadata.get('policy_version', 'N/A')}  
**Git Commit**: {metadata.get('git_commit', 'N/A')}  
**Dataset**: {metadata.get('dataset_path', 'N/A')} ({metadata.get('total_samples', 0)} samples)

---
""")
    
    # Executive Summary
    kpis = report_data.get("kpis", {})
    sections.append(f"""## Executive Summary

### Key Performance Indicators

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Precision** | {kpis.get('precision', 0):.1%} | ≥95% | {'✅' if kpis.get('precision', 0) >= 0.95 else '⚠️'} |
| **Recall** | {kpis.get('recall', 0):.1%} | ≥95% | {'✅' if kpis.get('recall', 0) >= 0.95 else '⚠️'} |
| **FNR** (Miss Rate) | {kpis.get('fnr', 0):.1%} | ≤5% | {'✅' if kpis.get('fnr', 0) <= 0.05 else '⚠️'} |
| **FPR** (False Alarm) | {kpis.get('fpr', 0):.1%} | ≤5% | {'✅' if kpis.get('fpr', 0) <= 0.05 else '⚠️'} |
| **Blocked Rate** | {kpis.get('blocked_rate', 0):.1%} | - | ℹ️ |

### Latency Performance

| Percentile | Value | Target | Status |
|------------|-------|--------|--------|
| **P50** | {kpis.get('latency_p50_ms', 0):.0f}ms | ≤50ms | {'✅' if kpis.get('latency_p50_ms', 0) <= 50 else '⚠️'} |
| **P95** | {kpis.get('latency_p95_ms', 0):.0f}ms | ≤100ms | {'✅' if kpis.get('latency_p95_ms', 0) <= 100 else '⚠️'} |
| **P99** | {kpis.get('latency_p99_ms', 0):.0f}ms | ≤200ms | {'✅' if kpis.get('latency_p99_ms', 0) <= 200 else '⚠️'} |

---
""")
    
    # Improvement Plan
    improvements = report_data.get("improvement_plan", [])
    if improvements:
        sections.append("## Improvement Plan\n\n")
        
        for priority in ["high", "medium", "low"]:
            priority_items = [item for item in improvements if item.get("priority") == priority]
            if priority_items:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
                sections.append(f"### {priority_icon} {priority.title()} Priority\n\n")
                
                for item in priority_items:
                    sections.append(f"""**{item.get('category', 'General')}**

*Issue*: {item.get('issue', 'N/A')}

*Recommendation*: {item.get('recommendation', 'N/A')}

---
""")
    else:
        sections.append("## Improvement Plan\n\nNo improvements needed at this time. ✅\n\n---\n")
    
    # Risks
    risks = report_data.get("risks", [])
    if risks:
        sections.append("## Risk Assessment\n\n")
        
        for risk_level in ["high", "medium", "low"]:
            level_risks = [r for r in risks if r.get("risk_level") == risk_level]
            if level_risks:
                risk_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk_level, "⚪")
                sections.append(f"### {risk_icon} {risk_level.title()} Risk\n\n")
                
                for risk in level_risks:
                    sections.append(f"""**{risk.get('category', 'General')}**

{risk.get('description', 'N/A')}

*Mitigation*: {risk.get('mitigation', 'TBD')}

---
""")
    else:
        sections.append("## Risk Assessment\n\nNo significant risks identified. ✅\n\n---\n")
    
    # Market Data
    market_data = report_data.get("market_data", {})
    if market_data:
        sections.append("## Market Data\n\n")
        sections.append("*Note: External market data requires additional research.*\n\n")
        
        for key, value in market_data.items():
            if isinstance(value, dict):
                val = value.get("value", "TBD")
                source = value.get("source", "unknown")
                note = value.get("note", "")
                
                sections.append(f"- **{key.replace('_', ' ').title()}**: {val} *(source: {source})*\n")
                if note:
                    sections.append(f"  - {note}\n")
        
        sections.append("\n---\n")
    
    # References
    references = report_data.get("references", [])
    if references:
        sections.append("## References\n\n")
        
        for ref in references:
            title = ref.get("title", "Untitled")
            url = ref.get("url", "#")
            ref_type = ref.get("type", "internal")
            
            sections.append(f"- **{title}** [{ref_type}]({url})\n")
        
        sections.append("\n---\n")
    
    # Footer
    sections.append(f"""
*This report was automatically generated from evaluation results.*  
*For questions or issues, please refer to the documentation.*
""")
    
    return "".join(sections)

