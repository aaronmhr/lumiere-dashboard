"""
🧹 Data Preparation Page
========================
Data quality assessment, group reconstruction, and export tools.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Data Prep | Lumiere",
    page_icon="🧹",
    layout="wide",
)

# Import utilities
from utils.firebase_client import get_firestore_client, fetch_sessions
from utils.data_processing import (
    sessions_to_dataframe,
    create_derived_variables,
    filter_sessions,
    get_data_quality_report,
    export_to_csv,
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    .stApp { font-family: 'DM Sans', sans-serif; }
    
    .quality-card {
        background: linear-gradient(145deg, #1e222a 0%, #252a34 100%);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid;
    }
    
    .quality-good { border-left-color: #2ecc71; }
    .quality-warn { border-left-color: #f1c40f; }
    .quality-bad { border-left-color: #e74c3c; }
    
    .derived-var {
        background: rgba(78, 205, 196, 0.1);
        border: 1px solid rgba(78, 205, 196, 0.2);
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.25rem 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data():
    """Load and process session data"""
    db = get_firestore_client()
    if db is None:
        return None
    
    sessions = fetch_sessions(db)
    if not sessions:
        return pd.DataFrame()
    
    df = sessions_to_dataframe(sessions)
    df = create_derived_variables(df)
    
    return df


def render_quality_report(df: pd.DataFrame):
    """Render data quality report"""
    st.markdown("### 📋 Data Quality Report")
    
    report = get_data_quality_report(df)
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Rows", report["total_rows"])
    
    with col2:
        issue_count = len(report.get("issues", []))
        st.metric("Issues Found", issue_count)
    
    with col3:
        columns_checked = len(report.get("columns", {}))
        st.metric("Columns Checked", columns_checked)
    
    # Issues list
    if report.get("issues"):
        st.markdown("#### ⚠️ Issues Detected")
        for issue in report["issues"]:
            st.warning(issue)
    else:
        st.success("✅ No critical issues detected")
    
    # Column details
    st.markdown("#### Column Analysis")
    
    col_data = []
    for col_name, col_info in report.get("columns", {}).items():
        if not col_info.get("present", False):
            continue
        
        col_data.append({
            "Column": col_name,
            "Type": col_info.get("dtype", "unknown"),
            "Missing": f"{col_info.get('missing_count', 0)} ({col_info.get('missing_percent', 0):.1f}%)",
            "Min": col_info.get("min", "-"),
            "Max": col_info.get("max", "-"),
            "Mean": f"{col_info.get('mean', 0):.2f}" if col_info.get("mean") else "-",
            "Outliers": col_info.get("outliers_count", "-"),
        })
    
    if col_data:
        st.dataframe(pd.DataFrame(col_data), use_container_width=True, hide_index=True)
    
    # Group distribution
    if "group_distribution" in report:
        st.markdown("#### Group Distribution")
        dist = report["group_distribution"]
        dist_df = pd.DataFrame([
            {"Group": int(k) if pd.notna(k) else "Unknown", "Count": v}
            for k, v in dist.items()
        ])
        st.dataframe(dist_df, use_container_width=True, hide_index=True)


def render_group_info(df: pd.DataFrame):
    """Render group information summary"""
    st.markdown("### 📊 Group Summary")
    
    if "group" not in df.columns:
        st.warning("No group data available")
        return
    
    # Count sessions per group
    group_counts = df["group"].value_counts().sort_index()
    missing_group = df["group"].isna().sum()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Sessions with Group", len(df) - missing_group)
    
    with col2:
        st.metric("Sessions Missing Group", missing_group)
    
    # Group breakdown
    st.markdown("#### Sessions per Group")
    
    group_data = []
    for group in [1, 2, 3, 4]:
        count = group_counts.get(group, 0)
        variety = "Low" if group in [1, 2] else "High"
        ar = "Yes" if group in [2, 4] else "No"
        group_data.append({
            "Group": group,
            "Variety": variety,
            "AR": ar,
            "Count": count,
            "Percentage": f"{count / len(df) * 100:.1f}%" if len(df) > 0 else "0%"
        })
    
    st.dataframe(pd.DataFrame(group_data), use_container_width=True, hide_index=True)


def render_derived_variables(df: pd.DataFrame):
    """Show derived variables"""
    st.markdown("### 📊 Derived Variables")
    
    derived_vars = [
        ("variety", "Experimental condition: 'low' (Groups 1,2) or 'high' (Groups 3,4)"),
        ("ar_enabled", "AR condition: True (Groups 2,4) or False (Groups 1,3)"),
        ("session_duration_sec", "Total session duration in seconds"),
        ("total_ar_time_sec", "Sum of all AR session durations"),
        ("unique_products_viewed", "Count of distinct products viewed"),
        ("ar_session_count", "Number of AR sessions initiated"),
        ("cart_additions", "Number of items added to cart"),
        ("is_completed", "Whether session was completed"),
        ("has_survey", "Whether survey was submitted"),
    ]
    
    for var_name, description in derived_vars:
        if var_name in df.columns:
            non_null = df[var_name].notna().sum()
            pct = non_null / len(df) * 100
            
            st.markdown(f"""
            <div class="derived-var">
                <code>{var_name}</code><br>
                <small style="color: #808080;">{description}</small><br>
                <small style="color: #4ECDC4;">{non_null} values ({pct:.1f}% coverage)</small>
            </div>
            """, unsafe_allow_html=True)


def render_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render filter controls and return filtered dataframe"""
    st.markdown("### 🔍 Filter Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        exclude_debug = st.checkbox("Exclude debug sessions", value=True)
        exclude_incomplete = st.checkbox("Exclude incomplete sessions", value=False)
    
    with col2:
        # Duration filters
        min_duration = st.number_input("Min duration (sec)", min_value=0, value=0)
        max_duration = st.number_input("Max duration (sec)", min_value=0, value=0, 
                                       help="Set to 0 for no maximum")
    
    # Test PIDs to exclude
    exclude_pids_text = st.text_area(
        "PIDs to exclude (one per line)",
        placeholder="test_user_1\ntest_user_2",
        height=100
    )
    exclude_pids = [p.strip() for p in exclude_pids_text.split("\n") if p.strip()]
    
    # Apply filters
    df_filtered = filter_sessions(
        df,
        exclude_debug=exclude_debug,
        exclude_incomplete=exclude_incomplete,
        exclude_pids=exclude_pids if exclude_pids else None,
        min_session_duration=min_duration if min_duration > 0 else None,
        max_session_duration=max_duration if max_duration > 0 else None,
    )
    
    # Show filter results
    removed = len(df) - len(df_filtered)
    st.info(f"Filtered: {len(df_filtered)} sessions remaining ({removed} removed)")
    
    return df_filtered


def render_export(df: pd.DataFrame):
    """Render export controls"""
    st.markdown("### 💾 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        include_events = st.checkbox("Include events column", value=False,
                                    help="Warning: This can make the file very large")
    
    with col2:
        filename = st.text_input("Filename", value=f"lumiere_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    if st.button("📥 Generate CSV", type="primary"):
        csv_data = export_to_csv(df, include_events=include_events)
        
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
        )
        
        st.success(f"CSV ready with {len(df)} rows")


def main():
    st.title("🧹 Data Preparation")
    st.markdown("Data quality assessment, cleaning, and export tools")
    
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading data..."):
        df = load_data()
    
    if df is None:
        st.error("Failed to connect to database. Please check your Firebase configuration.")
        return
    
    if df.empty:
        st.info("No sessions found in database.")
        return
    
    st.success(f"Loaded {len(df)} sessions")
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Quality Report", 
        "📊 Group Summary", 
        "🔍 Filters & Variables",
        "💾 Export"
    ])
    
    with tab1:
        render_quality_report(df)
    
    with tab2:
        render_group_info(df)
    
    with tab3:
        st.markdown("---")
        df_filtered = render_filters(df)
        st.markdown("---")
        render_derived_variables(df_filtered)
    
    with tab4:
        # Use filtered data if filters tab was used
        df_to_export = df_filtered if 'df_filtered' in dir() else df
        render_export(df_to_export)
    
    # Data preview at bottom
    st.markdown("---")
    st.markdown("### 👀 Data Preview")
    
    # Select columns to show
    all_cols = df.columns.tolist()
    default_cols = ["session_id", "group", "variety", "ar_enabled", 
                   "session_duration_sec", "is_completed", "device_type"]
    default_cols = [c for c in default_cols if c in all_cols]
    
    selected_cols = st.multiselect(
        "Select columns to display",
        options=all_cols,
        default=default_cols
    )
    
    if selected_cols:
        st.dataframe(df[selected_cols].head(50), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
