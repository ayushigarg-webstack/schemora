def check_loan_eligibility(credit_score: int, annual_income: float, debt_amount: float) -> str:
    """Evaluates loan eligibility based on financial metrics."""
    debt_to_income = debt_amount / annual_income if annual_income > 0 else 1.0
    
    if credit_score >= 750:
        if debt_to_income < 0.35:
            decision = "Approved - Prime Tier"
        else:
            decision = "Approved - Standard Tier (High DTI)"
    elif credit_score >= 650:
        if debt_to_income < 0.25:
            decision = "Approved - Standard Tier"
        else:
            decision = "Requires Manual Review"
    else:
        decision = "Rejected - Insufficient Credit Score"
        
    return decision

# Example execution
result = check_loan_eligibility(760, 85000.0, 15000.0)
