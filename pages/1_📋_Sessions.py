"""
📋 Sessions Page
================
View all sessions from newest to oldest.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Sessions | Lumiere",
    page_icon="📋",
    layout="wide",
)

# Import utilities
from utils.firebase_client import get_firestore_client, fetch_sessions, clear_session_cache
from utils.data_processing import sessions_to_dataframe, create_derived_variables

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    .stApp { font-family: 'DM Sans', sans-serif; }
    
    .session-count {
        background: linear-gradient(145deg, #1e222a 0%, #252a34 100%);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
        display: inline-block;
    }
    
    .session-count-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #4ECDC4;
    }
    
    .session-count-label {
        font-size: 0.8rem;
        color: #808080;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# Group colors for display
GROUP_COLORS = {
    1: "#4ECDC4",
    2: "#FF6B6B", 
    3: "#FFE66D",
    4: "#9B59B6",
}


def load_data():
    """Load and process session data"""
    with st.spinner("Loading sessions..."):
        db = get_firestore_client()
        if db is None:
            return None
        
        sessions = fetch_sessions(db)
        if not sessions:
            return pd.DataFrame()
        
        df = sessions_to_dataframe(sessions)
        df = create_derived_variables(df)
        
        return df


def render_filters(df: pd.DataFrame) -> dict:
    """Render filter controls in sidebar"""
    st.sidebar.markdown("## 🔍 Filters")
    
    filters = {}
    
    # 0. Search by session ID or PID (page-specific filter)
    search_term = st.sidebar.text_input(
        "Search (Session ID or PID)",
        placeholder="Enter search term...",
        help="Search by session ID or participant ID"
    )
    filters["search"] = search_term.strip() if search_term else None
    
    # 1. Device type filter
    if "device_type" in df.columns:
        device_options = sorted(df["device_type"].dropna().unique().tolist())
        filters["device_types"] = st.sidebar.multiselect(
            "Device Type",
            options=device_options,
            default=device_options
        )
        unknown_device_count = df["device_type"].isna().sum()
        if unknown_device_count > 0:
            filters["include_unknown_device"] = True  # Will be set by checkbox later
        else:
            filters["include_unknown_device"] = True
    
    # 2. Group filter
    if "group" in df.columns:
        group_options = sorted([int(g) for g in df["group"].dropna().unique()])
        filters["groups"] = st.sidebar.multiselect(
            "Groups",
            options=group_options,
            default=group_options,
            format_func=lambda x: f"Group {x}"
        )
    
    # 3. Completion status filter
    if "is_completed" in df.columns:
        filters["completion_status"] = st.sidebar.selectbox(
            "Completion Status",
            options=["All", "Completed", "In Progress"],
            index=0
        )
    
    # 4. Include unassigned group checkbox
    if "group" in df.columns:
        unassigned_count = df["group"].isna().sum()
        if unassigned_count > 0:
            filters["include_unknown_group"] = st.sidebar.checkbox(
                f"Include unassigned group ({unassigned_count})",
                value=False
            )
        else:
            filters["include_unknown_group"] = False
    
    # 5. Exclude reconstructed groups filter
    if "group_reconstructed" in df.columns:
        reconstructed_count = df["group_reconstructed"].notna().sum()
        if reconstructed_count > 0:
            filters["exclude_reconstructed"] = st.sidebar.checkbox(
                f"Exclude reconstructed groups ({reconstructed_count})",
                value=False
            )
        else:
            filters["exclude_reconstructed"] = False
    else:
        filters["exclude_reconstructed"] = False
    
    # 6. Debug mode filter (at the bottom)
    if "debug_mode" in df.columns:
        filters["exclude_debug"] = st.sidebar.checkbox(
            "Exclude debug sessions",
            value=True
        )
    
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🔄 Refresh Data"):
        clear_session_cache()
        st.rerun()
    
    return filters


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply filters to dataframe"""
    df_filtered = df.copy()
    
    # Search filter
    if filters.get("search"):
        search = filters["search"].lower()
        mask = (
            df_filtered["session_id"].astype(str).str.lower().str.contains(search, na=False) |
            df_filtered["pid"].astype(str).str.lower().str.contains(search, na=False)
        )
        df_filtered = df_filtered[mask]
    
    # Device type filter
    if filters.get("device_types") is not None and "device_type" in df_filtered.columns:
        include_unknown = filters.get("include_unknown_device", True)
        if include_unknown:
            df_filtered = df_filtered[
                df_filtered["device_type"].isin(filters["device_types"]) |
                df_filtered["device_type"].isna()
            ]
        else:
            df_filtered = df_filtered[df_filtered["device_type"].isin(filters["device_types"])]
    
    # Completion status filter
    if filters.get("completion_status") != "All" and "is_completed" in df_filtered.columns:
        if filters["completion_status"] == "Completed":
            df_filtered = df_filtered[df_filtered["is_completed"] == True]
        elif filters["completion_status"] == "In Progress":
            df_filtered = df_filtered[df_filtered["is_completed"] == False]
    
    # Group filter
    if filters.get("groups") is not None and "group" in df_filtered.columns:
        include_unknown = filters.get("include_unknown_group", True)
        if include_unknown:
            df_filtered = df_filtered[
                df_filtered["group"].isin(filters["groups"]) |
                df_filtered["group"].isna()
            ]
        else:
            df_filtered = df_filtered[df_filtered["group"].isin(filters["groups"])]
    
    # Debug mode filter
    if filters.get("exclude_debug") and "debug_mode" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["debug_mode"] != True]
    
    # Exclude reconstructed groups filter
    if filters.get("exclude_reconstructed") and "group_reconstructed" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["group_reconstructed"].isna()]
    
    return df_filtered


def format_sessions_table(df: pd.DataFrame) -> pd.DataFrame:
    """Format dataframe for display"""
    # Sort by started_at descending (newest first)
    df_sorted = df.sort_values("started_at", ascending=False).copy()
    
    # Select columns for display
    display_cols = [
        "session_id", "pid", "started_at", "group", "device_type", 
        "is_completed", "session_duration_sec", "final_cart_count",
        "ar_supported", "debug_mode"
    ]
    available_cols = [c for c in display_cols if c in df_sorted.columns]
    df_display = df_sorted[available_cols].copy()
    
    # Format columns
    if "started_at" in df_display.columns:
        df_display["started_at"] = df_display["started_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    
    if "session_duration_sec" in df_display.columns:
        def format_duration(seconds):
            if pd.isna(seconds):
                return "-"
            total_seconds = int(seconds)
            minutes = total_seconds // 60
            secs = total_seconds % 60
            if minutes > 0:
                return f"{minutes}min {secs}s"
            else:
                return f"{secs}s"
        df_display["session_duration_sec"] = df_display["session_duration_sec"].apply(format_duration)
    
    if "is_completed" in df_display.columns:
        df_display["is_completed"] = df_display["is_completed"].apply(
            lambda x: "✅" if x else "⏳"
        )
    
    if "ar_supported" in df_display.columns:
        df_display["ar_supported"] = df_display["ar_supported"].apply(
            lambda x: "📱" if x else "🚫" if x == False else "-"
        )
    
    if "debug_mode" in df_display.columns:
        df_display["debug_mode"] = df_display["debug_mode"].apply(
            lambda x: "🔧" if x else ""
        )
    
    if "group" in df_display.columns:
        df_display["group"] = df_display["group"].apply(
            lambda x: int(x) if pd.notna(x) else "-"
        )
    
    # Rename columns for display
    column_names = {
        "session_id": "Session ID",
        "pid": "Participant ID",
        "started_at": "Started At",
        "group": "Group",
        "device_type": "Device",
        "is_completed": "Status",
        "session_duration_sec": "Duration",
        "final_cart_count": "Cart Items",
        "ar_supported": "AR",
        "debug_mode": "Debug",
    }
    df_display = df_display.rename(columns=column_names)
    
    return df_display


def main():
    st.title("📋 Sessions")
    st.markdown("View all experiment sessions")
    
    # Load data
    df = load_data()
    
    if df is None:
        st.error("Failed to connect to database. Please check your Firebase configuration.")
        return
    
    if df.empty:
        st.info("No sessions found in database.")
        return
    
    # Render filters
    filters = render_filters(df)
    
    # Apply filters
    df_filtered = apply_filters(df, filters)
    
    # Session count header
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="session-count">
            <div class="session-count-value">{len(df_filtered)}</div>
            <div class="session-count-label">Sessions</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        completed = df_filtered["is_completed"].sum() if "is_completed" in df_filtered.columns else 0
        st.markdown(f"""
        <div class="session-count">
            <div class="session-count-value" style="color: #2ecc71;">{completed}</div>
            <div class="session-count-label">Completed</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        in_progress = len(df_filtered) - completed
        st.markdown(f"""
        <div class="session-count">
            <div class="session-count-value" style="color: #f1c40f;">{in_progress}</div>
            <div class="session-count-label">In Progress</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        if len(df_filtered) < len(df):
            st.markdown(f"""
            <div class="session-count">
                <div class="session-count-value" style="color: #808080;">{len(df)}</div>
                <div class="session-count-label">Total (unfiltered)</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Column selection
    with st.expander("🔧 Customize Columns"):
        all_cols = df.columns.tolist()
        
        # Remove complex columns from options
        exclude_from_selection = ["events", "final_cart", "reconstruction_signals"]
        selectable_cols = [c for c in all_cols if c not in exclude_from_selection]
        
        default_cols = [
            "session_id", "pid", "started_at", "group", "device_type",
            "is_completed", "session_duration_sec", "final_cart_count"
        ]
        default_cols = [c for c in default_cols if c in selectable_cols]
        
        selected_cols = st.multiselect(
            "Select columns to display",
            options=selectable_cols,
            default=default_cols
        )
    
    # Render table
    if len(df_filtered) == 0:
        st.info("No sessions match the current filters")
    else:
        # Use selected columns if customized, otherwise use default formatting
        if selected_cols:
            df_display = df_filtered.sort_values("started_at", ascending=False)[selected_cols].copy()
            
            # Format datetime columns
            for col in df_display.columns:
                if pd.api.types.is_datetime64_any_dtype(df_display[col]):
                    df_display[col] = df_display[col].dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Format duration column
            if "session_duration_sec" in df_display.columns:
                def format_duration(seconds):
                    if pd.isna(seconds):
                        return "-"
                    total_seconds = int(seconds)
                    minutes = total_seconds // 60
                    secs = total_seconds % 60
                    if minutes > 0:
                        return f"{minutes}min {secs}s"
                    else:
                        return f"{secs}s"
                df_display["session_duration_sec"] = df_display["session_duration_sec"].apply(format_duration)
            
            st.dataframe(df_display, use_container_width=True, hide_index=True, height=600)
        else:
            df_display = format_sessions_table(df_filtered)
            st.dataframe(df_display, use_container_width=True, hide_index=True, height=600)
    


if __name__ == "__main__":
    main()
