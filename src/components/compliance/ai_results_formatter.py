"""
Formatter for AI compliance results to make them more readable
"""

import pandas as pd
from typing import List, Dict, Any

def format_ai_results_as_cards(df: pd.DataFrame) -> str:
    """
    Convert dataframe results to readable card format
    
    Args:
        df: DataFrame with AI detection results
        
    Returns:
        Formatted markdown string
    """
    if df.empty:
        return "### ✅ No discrepancies detected"
    
    # Check if it's a status message
    if 'Status' in df.columns:
        return f"### {df.iloc[0]['Status']}"
    
    # Format as cards
    markdown = "## 🔍 AI Compliance Analysis Results\n\n"
    
    # Group by severity if available
    if 'Severity' in df.columns:
        high_issues = df[df['Severity'] == 'HIGH']
        medium_issues = df[df['Severity'] == 'MEDIUM'] 
        low_issues = df[df['Severity'] == 'LOW']
        
        # Summary
        markdown += f"""
### 📊 Summary
- **🔴 High Severity:** {len(high_issues)} issues
- **🟡 Medium Severity:** {len(medium_issues)} issues  
- **🟢 Low Severity:** {len(low_issues)} issues
- **Total Issues:** {len(df)} discrepancies detected

---
"""
        
        # High severity issues first
        if not high_issues.empty:
            markdown += "### 🔴 **HIGH SEVERITY ISSUES**\n\n"
            for _, row in high_issues.iterrows():
                markdown += format_single_issue_card(row, "high")
        
        # Medium severity
        if not medium_issues.empty:
            markdown += "### 🟡 **MEDIUM SEVERITY ISSUES**\n\n"
            for _, row in medium_issues.iterrows():
                markdown += format_single_issue_card(row, "medium")
        
        # Low severity
        if not low_issues.empty:
            markdown += "### 🟢 **LOW SEVERITY ISSUES**\n\n"
            for _, row in low_issues.iterrows():
                markdown += format_single_issue_card(row, "low")
    else:
        # No severity column, show all as cards
        for _, row in df.iterrows():
            markdown += format_single_issue_card(row)
    
    return markdown

def format_single_issue_card(row: pd.Series, severity: str = "medium") -> str:
    """
    Format a single issue as a card
    
    Args:
        row: DataFrame row with issue details
        severity: Issue severity level
        
    Returns:
        Formatted markdown card
    """
    # Determine card style based on severity
    border_color = {
        "high": "#ff4444",
        "medium": "#ff9800",
        "low": "#4caf50"
    }.get(severity, "#2196f3")
    
    # Extract fields with defaults
    transaction_id = row.get('Transaction ID', 'Unknown')
    merchant = row.get('Merchant', 'Unknown')
    tx_type = row.get('Type', 'Unknown')
    issue_type = row.get('Issue Type', 'Unknown')
    description = row.get('Description', 'No description')
    expected = row.get('Expected', 'N/A')
    actual = row.get('Actual', 'N/A')
    variance = row.get('Variance', 'N/A')
    contract_ref = row.get('Contract Ref', 'N/A')
    confidence = row.get('AI Confidence', 'Medium')
    timestamp = row.get('Timestamp', 'Unknown')
    
    card = f"""
<div style="border-left: 4px solid {border_color}; background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 8px;">

**Transaction:** `{transaction_id}` | **Merchant:** {merchant} | **Type:** {tx_type}

**Issue:** {issue_type}  
**Description:** {description}

| Metric | Value |
|--------|-------|
| **Expected** | {expected} |
| **Actual** | {actual} |
| **Variance** | {variance} |
| **Contract Reference** | {contract_ref} |
| **AI Confidence** | {confidence} |
| **Detected At** | {timestamp} |

</div>
"""
    return card

def format_comparison_table(transactions: List[Dict], discrepancies: List[Dict]) -> str:
    """
    Create a comparison table showing transactions vs discrepancies
    
    Args:
        transactions: List of all transactions
        discrepancies: List of detected discrepancies
        
    Returns:
        Formatted markdown table
    """
    markdown = """
## 📊 Transaction Analysis Comparison

| Metric | Value |
|--------|-------|
| **Total Transactions Analyzed** | {} |
| **Discrepancies Found** | {} |
| **Compliance Rate** | {:.1f}% |
| **Most Common Issue** | {} |
| **Highest Risk Merchant** | {} |
""".format(
        len(transactions),
        len(discrepancies),
        (1 - len(discrepancies) / len(transactions)) * 100 if transactions else 100,
        get_most_common_issue(discrepancies),
        get_highest_risk_merchant(discrepancies)
    )
    
    return markdown

def get_most_common_issue(discrepancies: List[Dict]) -> str:
    """Get the most common issue type"""
    if not discrepancies:
        return "None"
    
    issue_counts = {}
    for disc in discrepancies:
        issue_type = disc.get('Issue Type', 'Unknown')
        issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
    
    return max(issue_counts, key=issue_counts.get)

def get_highest_risk_merchant(discrepancies: List[Dict]) -> str:
    """Get merchant with most discrepancies"""
    if not discrepancies:
        return "None"
    
    merchant_counts = {}
    for disc in discrepancies:
        merchant = disc.get('Merchant', 'Unknown')
        merchant_counts[merchant] = merchant_counts.get(merchant, 0) + 1
    
    return max(merchant_counts, key=merchant_counts.get)

def create_summary_dashboard(df: pd.DataFrame) -> str:
    """
    Create a summary dashboard for the AI results
    
    Args:
        df: DataFrame with AI detection results
        
    Returns:
        Formatted markdown dashboard
    """
    if df.empty:
        return """
## 📊 AI Compliance Dashboard

### ✅ System Status: All Clear
No discrepancies detected in recent transactions.

**Last Check:** Just now  
**Monitoring Status:** Active  
**AI Model:** Gemini 2.0 Flash
"""
    
    total = len(df)
    high = len(df[df['Severity'] == 'HIGH']) if 'Severity' in df.columns else 0
    medium = len(df[df['Severity'] == 'MEDIUM']) if 'Severity' in df.columns else 0
    low = len(df[df['Severity'] == 'LOW']) if 'Severity' in df.columns else 0
    
    # Calculate financial impact
    total_variance = 0
    if 'Variance' in df.columns:
        for val in df['Variance']:
            try:
                # Extract numeric value from string like "$1.234"
                if isinstance(val, str) and '$' in val:
                    total_variance += float(val.replace('$', '').replace(',', ''))
            except:
                pass
    
    dashboard = f"""
## 📊 AI Compliance Dashboard

### ⚠️ Issues Detected

<div style="display: flex; gap: 20px; margin: 20px 0;">
    <div style="flex: 1; padding: 20px; background: #ffebee; border-radius: 8px; text-align: center;">
        <h3 style="color: #c62828;">🔴 HIGH</h3>
        <h1 style="color: #c62828; margin: 0;">{high}</h1>
    </div>
    <div style="flex: 1; padding: 20px; background: #fff3e0; border-radius: 8px; text-align: center;">
        <h3 style="color: #f57c00;">🟡 MEDIUM</h3>
        <h1 style="color: #f57c00; margin: 0;">{medium}</h1>
    </div>
    <div style="flex: 1; padding: 20px; background: #e8f5e9; border-radius: 8px; text-align: center;">
        <h3 style="color: #2e7d32;">🟢 LOW</h3>
        <h1 style="color: #2e7d32; margin: 0;">{low}</h1>
    </div>
</div>

### 💰 Financial Impact
**Total Variance:** ${total_variance:,.2f}

### 🎯 Key Metrics
- **Total Issues:** {total}
- **Detection Method:** AI + RAG + Database Context
- **Confidence Level:** High (using multiple data sources)

### 🔄 Next Steps
1. Review HIGH severity issues immediately
2. Investigate root causes of fee mismatches
3. Update contract terms if needed
4. Generate detailed report for audit trail
"""
    
    return dashboard