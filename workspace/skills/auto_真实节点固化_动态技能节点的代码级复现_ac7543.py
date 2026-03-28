"""
Module: auto_skill_materialization_financial_audit.py

This module implements a concrete skill node for 'Financial Anomaly Detection' 
to demonstrate the materialization of a cognitive skill into executable code.

It simulates the extraction and validation of specific financial anomalies 
(e.g., Benford's Law deviations) from ledger data, fulfilling the requirements 
of skill ID 'ac7543'.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

# Configuration for logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FinancialAuditSkill")

@dataclass
class AuditResult:
    """
    Data structure representing the result of the anomaly detection skill.
    
    Attributes:
        is_compliant (bool): True if the data passes the validation checks.
        anomaly_score (float): A calculated score representing deviation from the norm.
        details (Dict[str, Any]): Additional details about the detected anomalies.
    """
    is_compliant: bool
    anomaly_score: float
    details: Dict[str, Any]

class FinancialDataValidationError(ValueError):
    """Custom exception for errors during financial data validation."""
    pass

def _validate_data_schema(df: pd.DataFrame, required_columns: List[str]) -> None:
    """
    [Helper Function] Validates that the DataFrame contains the required columns.
    
    Args:
        df (pd.DataFrame): The input data frame.
        required_columns (List[str]): List of column names that must exist.
        
    Raises:
        FinancialDataValidationError: If any required column is missing.
    """
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        error_msg = f"Missing required columns: {missing_cols}"
        logger.error(error_msg)
        raise FinancialDataValidationError(error_msg)
    logger.info("Data schema validation passed.")

def calculate_benford_deviation(amounts: pd.Series) -> Tuple[float, Dict[str, float]]:
    """
    [Core Function 1] Calculates the deviation of transaction amounts from Benford's Law.
    
    Benford's Law predicts the frequency of the leading digit in many natural datasets.
    Significant deviations can indicate manipulation or fraud.
    
    Args:
        amounts (pd.Series): A pandas Series of numerical transaction amounts.
        
    Returns:
        Tuple[float, Dict[str, float]]: 
            - A deviation score (0.0 means perfect match).
            - A dictionary of observed vs expected frequencies.
            
    Raises:
        ValueError: If input data is empty or contains non-positive numbers where inappropriate.
    """
    logger.info("Starting Benford's Law analysis...")
    
    # Data Cleaning: Filter out zero/negative values for leading digit analysis
    clean_amounts = amounts[amounts > 0].dropna()
    if len(clean_amounts) < 50:
        logger.warning("Sample size too small for reliable Benford analysis.")
        return 1.0, {"error": "Insufficient data"}

    # Extract leading digits
    first_digits = clean_amounts.astype(str).str.replace(r'\.', '').str[0].astype(int)
    
    # Calculate observed frequencies
    observed_counts = first_digits.value_counts().sort_index()
    total_count = len(first_digits)
    observed_freq = observed_counts / total_count
    
    # Expected Benford frequencies
    benford_freq = {d: np.log10(1 + (1 / d)) for d in range(1, 10)}
    
    # Calculate Chi-Square-like deviation score
    deviation_score = 0.0
    freq_comparison = {}
    
    for d in range(1, 10):
        exp = benford_freq.get(d, 0)
        obs = observed_freq.get(d, 0) if d in observed_freq.index else 0.0
        
        # Sum of squared errors
        deviation_score += (obs - exp) ** 2
        freq_comparison[f"digit_{d}"] = {"expected": round(exp, 4), "observed": round(obs, 4)}

    logger.info(f"Benford analysis complete. Deviation score: {deviation_score:.4f}")
    return round(deviation_score, 4), freq_comparison

def detect_duplicate_transactions(
    df: pd.DataFrame, 
    amount_col: str = 'amount', 
    date_col: str = 'transaction_date', 
    tolerance_days: int = 3
) -> List[Dict[str, Any]]:
    """
    [Core Function 2] Identifies potential duplicate transactions based on amount and proximity of date.
    
    Args:
        df (pd.DataFrame): Financial ledger data.
        amount_col (str): Column name for transaction amounts.
        date_col (str): Column name for transaction dates.
        tolerance_days (int): Maximum days between transactions to consider them potential duplicates.
        
    Returns:
        List[Dict[str, Any]]: A list of records flagged as potential duplicates.
    """
    logger.info("Scanning for duplicate transactions...")
    _validate_data_schema(df, [amount_col, date_col])
    
    # Ensure datetime format
    try:
        df[date_col] = pd.to_datetime(df[date_col])
    except Exception as e:
        logger.error(f"Date parsing error: {e}")
        raise FinancialDataValidationError(f"Invalid date format in column {date_col}")

    potential_duplicates = []
    
    # Group by amount to find same-value transactions
    grouped = df.groupby(amount_col)
    
    for amount, group in grouped:
        if len(group) > 1:
            # Sort by date
            sorted_group = group.sort_values(by=date_col)
            
            # Compare dates
            for i in range(len(sorted_group) - 1):
                current_row = sorted_group.iloc[i]
                next_row = sorted_group.iloc[i+1]
                
                time_diff = (next_row[date_col] - current_row[date_col]).days
                
                if time_diff <= tolerance_days:
                    record = {
                        "type": "POTENTIAL_DUPLICATE",
                        "amount": float(amount),
                        "transaction_id_1": current_row.get('transaction_id', 'N/A'),
                        "transaction_id_2": next_row.get('transaction_id', 'N/A'),
                        "days_apart": time_diff
                    }
                    potential_duplicates.append(record)
                    
    logger.info(f"Found {len(potential_duplicates)} potential duplicate pairs.")
    return potential_duplicates

def execute_audit_skill(df: pd.DataFrame) -> AuditResult:
    """
    Main orchestrator function that materializes the 'Financial Audit' skill.
    
    It combines statistical analysis (Benford) and pattern matching (Duplicates)
    to produce a comprehensive audit result.
    
    Args:
        df (pd.DataFrame): The input financial dataset.
        
    Returns:
        AuditResult: The final object containing pass/fail status and metrics.
        
    Example:
        >>> data = {
        ...     'transaction_id': range(1, 101),
        ...     'amount': np.random.uniform(100, 10000, 100),
        ...     'transaction_date': pd.date_range(start='2023-01-01', periods=100)
        ... }
        >>> df = pd.DataFrame(data)
        >>> result = execute_audit_skill(df)
        >>> print(result.is_compliant)
        True
    """
    logger.info("Initializing Skill Node: Financial Audit Materialization")
    
    if df.empty:
        logger.error("Input DataFrame is empty.")
        return AuditResult(is_compliant=False, anomaly_score=1.0, details={"error": "Empty input"})

    try:
        # 1. Run Benford's Law Analysis
        benford_score, benford_details = calculate_benford_deviation(df['amount'])
        
        # 2. Run Duplicate Detection
        duplicates = detect_duplicate_transactions(df)
        
        # 3. Aggregate Results
        # Threshold: Benford deviation > 0.1 is suspicious, or > 0 duplicates found
        is_compliant = (benford_score < 0.1) and (len(duplicates) == 0)
        
        details = {
            "benford_analysis": benford_details,
            "duplicate_flags": duplicates,
            "total_records_analyzed": len(df)
        }
        
        logger.info(f"Audit Skill Execution Complete. Compliant: {is_compliant}")
        
        return AuditResult(
            is_compliant=is_compliant,
            anomaly_score=benford_score + (len(duplicates) * 0.05), # Weighted scoring
            details=details
        )
        
    except Exception as e:
        logger.critical(f"Critical failure during skill execution: {str(e)}", exc_info=True)
        return AuditResult(
            is_compliant=False, 
            anomaly_score=1.0, 
            details={"critical_error": str(e)}
        )

if __name__ == "__main__":
    # Generate synthetic financial data for demonstration
    np.random.seed(42)
    n_rows = 1000
    
    # Generate amounts roughly following Benford's law for a 'Good' dataset
    # (Using a simple log-normal distribution as a proxy)
    amounts_good = np.random.lognormal(mean=3, sigma=1.5, size=n_rows)
    dates_good = pd.date_range(start='2022-01-01', periods=n_rows, freq='D')
    
    df_good = pd.DataFrame({
        'transaction_id': range(1, n_rows + 1),
        'amount': amounts_good,
        'transaction_date': dates_good
    })
    
    print("--- Running Audit Skill on Clean Data ---")
    result_good = execute_audit_skill(df_good)
    print(f"Status: {'PASSED' if result_good.is_compliant else 'FAILED'}")
    print(f"Score: {result_good.anomaly_score}")
    
    print("\n--- Running Audit Skill on Anomalous Data (Duplicates Injected) ---")
    # Inject duplicates
    df_bad = df_good.copy()
    df_bad = pd.concat([df_bad, df_bad.sample(10)], ignore_index=True)
    
    result_bad = execute_audit_skill(df_bad)
    print(f"Status: {'PASSED' if result_bad.is_compliant else 'FAILED'}")
    print(f"Score: {result_bad.anomaly_score}")
    print(f"Flags found: {len(result_bad.details.get('duplicate_flags', []))}")