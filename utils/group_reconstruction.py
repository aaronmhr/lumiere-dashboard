"""Group reconstruction logic for sessions with missing group field"""

from typing import Optional
import pandas as pd

# Product ID sets for group determination
LOW_VARIETY_PRODUCTS = {1, 6, 10, 11, 14}
HIGH_VARIETY_PRODUCTS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15}
HIGH_VARIETY_EXCLUSIVE = {2, 3, 4, 5, 7, 8, 9, 12, 13, 15}

# Group definitions
# Group 1: Low variety, No AR
# Group 2: Low variety, Yes AR
# Group 3: High variety, No AR
# Group 4: High variety, Yes AR


def get_reconstruction_signals(events: list[dict]) -> dict:
    """
    Extract signals from events that help determine group assignment.
    
    Args:
        events: List of event dictionaries from session
    
    Returns:
        Dictionary of signals with confidence indicators
    """
    signals = {
        "has_ar_events": False,
        "ar_event_count": 0,
        "has_high_variety_exclusive": False,
        "high_variety_exclusive_products": set(),
        "unique_products_viewed": set(),
        "scroll_time_after_gallery": None,
        "gallery_view_time": None,
        "scroll_to_bottom_time": None,
        "group_from_event": None,
    }
    
    if not events:
        return signals
    
    for event in events:
        event_type = event.get("e", "")
        timestamp = event.get("t", 0)
        
        # Check for AR events (definitive for AR groups)
        if event_type in ("ar_start", "ar_end"):
            signals["has_ar_events"] = True
            signals["ar_event_count"] += 1
        
        # Check for group_assigned event
        if event_type == "group_assigned":
            signals["group_from_event"] = event.get("v")
        
        # Track gallery view time
        if event_type == "view_page" and event.get("p") == "gallery":
            signals["gallery_view_time"] = timestamp
        
        # Track scroll to bottom time
        if event_type == "scroll_to_bottom":
            signals["scroll_to_bottom_time"] = timestamp
        
        # Track viewed products
        if event_type == "view":
            product_id = event.get("p")
            if product_id:
                try:
                    pid = int(product_id)
                    signals["unique_products_viewed"].add(pid)
                    if pid in HIGH_VARIETY_EXCLUSIVE:
                        signals["has_high_variety_exclusive"] = True
                        signals["high_variety_exclusive_products"].add(pid)
                except (ValueError, TypeError):
                    pass
        
        # Also check cart actions for product IDs
        if event_type in ("cart_add_detail", "cart_add_gallery", "cart_remove"):
            product_id = event.get("p")
            if product_id:
                try:
                    pid = int(product_id)
                    signals["unique_products_viewed"].add(pid)
                    if pid in HIGH_VARIETY_EXCLUSIVE:
                        signals["has_high_variety_exclusive"] = True
                        signals["high_variety_exclusive_products"].add(pid)
                except (ValueError, TypeError):
                    pass
    
    # Calculate scroll timing
    if signals["gallery_view_time"] is not None and signals["scroll_to_bottom_time"] is not None:
        signals["scroll_time_after_gallery"] = (
            signals["scroll_to_bottom_time"] - signals["gallery_view_time"]
        ) / 1000  # Convert to seconds
    
    return signals


def reconstruct_group(signals: dict) -> tuple[Optional[int], str, float]:
    """
    Reconstruct group assignment from signals.
    
    Args:
        signals: Dictionary from get_reconstruction_signals
    
    Returns:
        Tuple of (group_number, method_used, confidence)
        - group_number: 1-4 or None if cannot determine
        - method_used: Description of reconstruction method
        - confidence: 0.0-1.0 confidence score
    """
    # If we have the group from event, use that (most reliable)
    if signals["group_from_event"] is not None:
        return signals["group_from_event"], "group_assigned_event", 1.0
    
    has_ar = signals["has_ar_events"]
    has_high_variety = signals["has_high_variety_exclusive"]
    product_count = len(signals["unique_products_viewed"])
    scroll_time = signals["scroll_time_after_gallery"]
    
    # Definitive: AR events + high variety exclusive products
    if has_ar and has_high_variety:
        return 4, "ar_events + high_variety_products", 1.0
    
    # Definitive: AR events + low variety only
    if has_ar and not has_high_variety:
        # Could be Group 2, but might just not have viewed exclusive products
        if product_count > 0:
            return 2, "ar_events + no_high_variety_products", 0.9
        return 2, "ar_events_only", 0.7
    
    # Definitive: High variety exclusive products + no AR
    if has_high_variety and not has_ar:
        return 3, "high_variety_products + no_ar", 1.0
    
    # Use product count as indicator
    if product_count > 5:
        return 3, "product_count_exceeds_5", 0.8
    
    # Use scroll timing as indicator (< 3 seconds = low variety)
    if scroll_time is not None:
        if scroll_time < 3.0:
            return 1, "fast_scroll_time", 0.6
        elif scroll_time > 6.0:
            return 3, "slow_scroll_time", 0.5
    
    # Cannot determine with confidence
    return None, "insufficient_signals", 0.0


def reconstruct_groups(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add reconstructed group information to dataframe.
    
    Args:
        df: DataFrame with 'events' and optionally 'group' columns
    
    Returns:
        DataFrame with additional columns:
        - group_reconstructed: Reconstructed group number
        - group_final: Original group if present, else reconstructed
        - reconstruction_method: How group was determined
        - reconstruction_confidence: Confidence score
    """
    df = df.copy()
    
    results = []
    for _, row in df.iterrows():
        events = row.get("events", []) or []
        original_group = row.get("group")
        
        signals = get_reconstruction_signals(events)
        reconstructed, method, confidence = reconstruct_group(signals)
        
        results.append({
            "group_reconstructed": reconstructed,
            "group_final": original_group if pd.notna(original_group) else reconstructed,
            "reconstruction_method": method if pd.isna(original_group) else "original",
            "reconstruction_confidence": confidence if pd.isna(original_group) else 1.0,
            "reconstruction_signals": signals,
        })
    
    result_df = pd.DataFrame(results)
    
    for col in result_df.columns:
        df[col] = result_df[col].values
    
    return df
