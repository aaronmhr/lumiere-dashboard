"""Group handling utilities for Lumiere Dashboard"""

import pandas as pd

# Product ID sets for reference
LOW_VARIETY_PRODUCTS = {1, 6, 10, 11, 14}
HIGH_VARIETY_PRODUCTS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15}
HIGH_VARIETY_EXCLUSIVE = {2, 3, 4, 5, 7, 8, 9, 12, 13, 15}

# Group definitions
# Group 1: Low variety, No AR
# Group 2: Low variety, Yes AR
# Group 3: High variety, No AR
# Group 4: High variety, Yes AR


def merge_group_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge group fields from Firebase into a single 'group' column.
    Uses 'group' if present, otherwise falls back to 'group_reconstructed'.
    
    Args:
        df: DataFrame with 'group' and/or 'group_reconstructed' columns
    
    Returns:
        DataFrame with unified 'group' column
    """
    df = df.copy()
    
    if "group" in df.columns and "group_reconstructed" in df.columns:
        # Use group if present, otherwise use group_reconstructed
        df["group"] = df["group"].fillna(df["group_reconstructed"])
    elif "group_reconstructed" in df.columns and "group" not in df.columns:
        # Only group_reconstructed exists
        df["group"] = df["group_reconstructed"]
    # If only 'group' exists, keep it as is
    
    return df
