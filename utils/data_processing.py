"""Data processing utilities for Lumiere Dashboard"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional
from .firebase_client import firestore_timestamp_to_datetime
from .group_reconstruction import merge_group_fields


def sessions_to_dataframe(sessions: list[dict]) -> pd.DataFrame:
    """
    Convert raw session documents to a pandas DataFrame.
    
    Args:
        sessions: List of session dictionaries from Firestore
    
    Returns:
        DataFrame with flattened session data
    """
    if not sessions:
        return pd.DataFrame()
    
    rows = []
    for session in sessions:
        row = {
            "session_id": session.get("session_id"),
            "doc_id": session.get("_doc_id"),
            "started_at": firestore_timestamp_to_datetime(session.get("started_at")),
            "completed_at": firestore_timestamp_to_datetime(session.get("completed_at")),
            "consented_at": firestore_timestamp_to_datetime(session.get("consented_at")),
            "consented": session.get("consented", False),
            "debug_mode": session.get("debug_mode", False),
            "device_type": session.get("device_type"),
            "ar_supported": session.get("ar_supported"),
            "locale": session.get("locale"),
            "timezone": session.get("timezone"),
            "pid": session.get("pid"),
            "group": session.get("group"),
            "group_reconstructed": session.get("group_reconstructed"),
            "group_assigned_at": firestore_timestamp_to_datetime(
                session.get("group_assigned_at")
            ),
            "group_assignment_status": session.get("group_assignment_status"),
            "final_cart": session.get("final_cart", []),
            "final_cart_count": session.get("final_cart_count", 0),
            "events": session.get("events", []),
        }
        
        # Flatten survey data
        survey = session.get("survey", {}) or {}
        row["survey_submitted_at"] = firestore_timestamp_to_datetime(
            survey.get("submitted_at")
        )
        
        survey_final = survey.get("survey_final", {}) or {}
        row["has_survey_final"] = len(survey_final) > 0
        for key, value in survey_final.items():
            row[f"survey_{key}"] = value
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Convert timestamps to datetime
    timestamp_cols = ["started_at", "completed_at", "consented_at", 
                      "group_assigned_at", "survey_submitted_at"]
    for col in timestamp_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit="s", errors="coerce")
    
    # Merge group fields (use 'group' if present, else 'group_reconstructed')
    df = merge_group_fields(df)
    
    return df


def create_derived_variables(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create derived variables for analysis.
    
    Args:
        df: DataFrame from sessions_to_dataframe
    
    Returns:
        DataFrame with additional derived columns
    """
    df = df.copy()
    
    # Variety condition: Low (groups 1,2) or High (groups 3,4)
    df["variety"] = df["group"].apply(
        lambda g: "low" if g in [1, 2] else ("high" if g in [3, 4] else None)
    )
    
    # AR condition: Yes (groups 2,4) or No (groups 1,3)
    df["ar_enabled"] = df["group"].apply(
        lambda g: True if g in [2, 4] else (False if g in [1, 3] else None)
    )
    
    # Session duration in seconds
    df["session_duration_sec"] = (
        df["completed_at"] - df["started_at"]
    ).dt.total_seconds()
    
    # Time to complete survey (from start)
    df["time_to_survey_sec"] = (
        df["survey_submitted_at"] - df["started_at"]
    ).dt.total_seconds()
    
    # Extract metrics from events
    event_metrics = df["events"].apply(extract_event_metrics)
    event_metrics_df = pd.DataFrame(event_metrics.tolist())
    
    for col in event_metrics_df.columns:
        df[col] = event_metrics_df[col].values
    
    # Is completed (has survey_final object with data)
    df["is_completed"] = df["has_survey_final"].fillna(False)
    
    # Has survey (same as is_completed)
    df["has_survey"] = df["has_survey_final"].fillna(False)
    
    return df


def extract_event_metrics(events: list) -> dict:
    """
    Extract metrics from event list.
    
    Args:
        events: List of event dictionaries
    
    Returns:
        Dictionary of computed metrics
    """
    if not events:
        return {
            "total_ar_time_sec": 0,
            "ar_session_count": 0,
            "unique_products_viewed": 0,
            "cart_additions": 0,
            "cart_removals": 0,
            "page_views": 0,
            "avg_ar_duration_sec": None,
            "total_ar_rotations": 0,
            "total_ar_zooms": 0,
            "time_on_gallery_sec": None,
            "time_on_detail_sec": None,
            "scrolled_to_bottom": False,
        }
    
    metrics = {
        "total_ar_time_sec": 0,
        "ar_session_count": 0,
        "unique_products_viewed": 0,
        "cart_additions": 0,
        "cart_removals": 0,
        "page_views": 0,
        "total_ar_rotations": 0,
        "total_ar_zooms": 0,
        "scrolled_to_bottom": False,
    }
    
    products_viewed = set()
    ar_durations = []
    gallery_start = None
    gallery_time = 0
    detail_start = None
    detail_time = 0
    last_page = None
    
    for event in events:
        event_type = event.get("e", "")
        timestamp = event.get("t", 0)
        
        # Page views and timing
        if event_type == "view_page":
            metrics["page_views"] += 1
            page = event.get("p")
            
            # Calculate time on previous page
            if last_page == "gallery" and gallery_start is not None:
                gallery_time += timestamp - gallery_start
            elif last_page == "detail" and detail_start is not None:
                detail_time += timestamp - detail_start
            
            # Start timing new page
            if page == "gallery":
                gallery_start = timestamp
            elif page == "detail":
                detail_start = timestamp
            else:
                gallery_start = None
                detail_start = None
            
            last_page = page
        
        # Product views
        if event_type == "view":
            product_id = event.get("p")
            if product_id:
                try:
                    products_viewed.add(int(product_id))
                except (ValueError, TypeError):
                    pass
        
        # AR events
        if event_type == "ar_end":
            metrics["ar_session_count"] += 1
            duration = event.get("d", 0)
            if duration:
                ar_durations.append(duration / 1000)  # Convert to seconds
                metrics["total_ar_time_sec"] += duration / 1000
            metrics["total_ar_rotations"] += event.get("rotations", 0)
            metrics["total_ar_zooms"] += event.get("zooms", 0)
        
        # Cart actions
        if event_type in ("cart_add_detail", "cart_add_gallery"):
            metrics["cart_additions"] += 1
        if event_type == "cart_remove":
            metrics["cart_removals"] += 1
        
        # Scroll
        if event_type == "scroll_to_bottom":
            metrics["scrolled_to_bottom"] = True
    
    metrics["unique_products_viewed"] = len(products_viewed)
    metrics["avg_ar_duration_sec"] = (
        np.mean(ar_durations) if ar_durations else None
    )
    metrics["time_on_gallery_sec"] = gallery_time / 1000 if gallery_time > 0 else None
    metrics["time_on_detail_sec"] = detail_time / 1000 if detail_time > 0 else None
    
    return metrics


def filter_sessions(
    df: pd.DataFrame,
    exclude_debug: bool = True,
    exclude_incomplete: bool = False,
    exclude_pids: Optional[list[str]] = None,
    min_session_duration: Optional[float] = None,
    max_session_duration: Optional[float] = None,
) -> pd.DataFrame:
    """
    Filter sessions based on criteria.
    
    Args:
        df: DataFrame to filter
        exclude_debug: Exclude sessions with debug_mode=True
        exclude_incomplete: Exclude sessions without completed_at
        exclude_pids: List of PIDs to exclude (test accounts)
        min_session_duration: Minimum session duration in seconds
        max_session_duration: Maximum session duration in seconds
    
    Returns:
        Filtered DataFrame
    """
    mask = pd.Series([True] * len(df), index=df.index)
    
    if exclude_debug and "debug_mode" in df.columns:
        mask &= ~df["debug_mode"].fillna(False)
    
    if exclude_incomplete and "completed_at" in df.columns:
        mask &= df["completed_at"].notna()
    
    if exclude_pids and "pid" in df.columns:
        mask &= ~df["pid"].isin(exclude_pids)
    
    if min_session_duration is not None and "session_duration_sec" in df.columns:
        mask &= df["session_duration_sec"] >= min_session_duration
    
    if max_session_duration is not None and "session_duration_sec" in df.columns:
        mask &= df["session_duration_sec"] <= max_session_duration
    
    return df[mask].copy()


def get_data_quality_report(df: pd.DataFrame) -> dict:
    """
    Generate a data quality report.
    
    Args:
        df: DataFrame to analyze
    
    Returns:
        Dictionary with quality metrics
    """
    report = {
        "total_rows": len(df),
        "columns": {},
        "issues": [],
    }
    
    # Key columns to check
    key_columns = [
        "session_id", "group", "started_at", "completed_at",
        "pid", "device_type", "final_cart_count", "session_duration_sec"
    ]
    
    for col in key_columns:
        if col not in df.columns:
            report["columns"][col] = {"present": False}
            report["issues"].append(f"Missing column: {col}")
            continue
        
        col_data = df[col]
        missing = col_data.isna().sum()
        missing_pct = (missing / len(df) * 100) if len(df) > 0 else 0
        
        col_report = {
            "present": True,
            "missing_count": int(missing),
            "missing_percent": round(missing_pct, 1),
            "dtype": str(col_data.dtype),
        }
        
        if pd.api.types.is_numeric_dtype(col_data):
            col_report["min"] = col_data.min()
            col_report["max"] = col_data.max()
            col_report["mean"] = col_data.mean()
            col_report["std"] = col_data.std()
            
            # Check for outliers (beyond 3 std)
            if col_report["std"] and col_report["std"] > 0:
                z_scores = np.abs((col_data - col_report["mean"]) / col_report["std"])
                outliers = (z_scores > 3).sum()
                col_report["outliers_count"] = int(outliers)
        
        report["columns"][col] = col_report
        
        if missing_pct > 10:
            report["issues"].append(f"High missing rate ({missing_pct:.1f}%) for {col}")
    
    # Check for duplicate session IDs
    if "session_id" in df.columns:
        duplicates = df["session_id"].duplicated().sum()
        if duplicates > 0:
            report["duplicate_sessions"] = int(duplicates)
            report["issues"].append(f"Found {duplicates} duplicate session IDs")
    
    # Check group distribution
    if "group" in df.columns:
        group_counts = df["group"].value_counts()
        report["group_distribution"] = group_counts.to_dict()
        
        # Check for imbalanced groups
        if len(group_counts) > 0:
            min_count = group_counts.min()
            max_count = group_counts.max()
            if max_count > min_count * 2:
                report["issues"].append("Imbalanced group distribution detected")
    
    return report


def export_to_csv(df: pd.DataFrame, include_events: bool = False) -> str:
    """
    Export DataFrame to CSV string.
    
    Args:
        df: DataFrame to export
        include_events: Whether to include events column (large)
    
    Returns:
        CSV string
    """
    export_df = df.copy()
    
    # Remove complex columns
    columns_to_drop = []
    if not include_events:
        columns_to_drop.extend(["events", "final_cart"])
    
    for col in columns_to_drop:
        if col in export_df.columns:
            export_df = export_df.drop(columns=[col])
    
    return export_df.to_csv(index=False)
