"""
📈 Exploration Page
===================
Interactive data visualization and pattern discovery.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page configuration
st.set_page_config(
    page_title="Exploration | Lumiere",
    page_icon="📈",
    layout="wide",
)

# Import utilities
from utils.firebase_client import get_firestore_client, fetch_sessions
from utils.data_processing import sessions_to_dataframe, create_derived_variables

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    .stApp { font-family: 'DM Sans', sans-serif; }
    
    .chart-container {
        background: linear-gradient(145deg, #1e222a 0%, #252a34 100%);
        border-radius: 16px;
        padding: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
</style>
""", unsafe_allow_html=True)

# Color scheme
GROUP_COLORS = {
    1: "#4ECDC4",
    2: "#FF6B6B",
    3: "#FFE66D",
    4: "#9B59B6",
}

VARIETY_COLORS = {
    "low": "#4ECDC4",
    "high": "#FFE66D",
}

AR_COLORS = {
    True: "#FF6B6B",
    False: "#4ECDC4",
}

PLOTLY_TEMPLATE = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#FAFAFA", "family": "DM Sans"},
}


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


def render_filters(df: pd.DataFrame) -> dict:
    """Render filter controls in sidebar and return filter settings"""
    st.sidebar.markdown("### 🔍 Filters")
    
    filters = {}
    
    # 1. Device type filter
    if "device_type" in df.columns:
        device_options = sorted(df["device_type"].dropna().unique().tolist())
        filters["device_types"] = st.sidebar.multiselect(
            "Device Type",
            options=device_options,
            default=device_options,
            help="Select device types to include"
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
            format_func=lambda x: f"Group {x}",
            help="Select groups to include"
        )
    
    # 3. Completion status filter
    if "is_completed" in df.columns:
        filters["completion_status"] = st.sidebar.selectbox(
            "Completion Status",
            options=["All", "Completed", "In Progress"],
            index=0,
            help="Filter by session completion"
        )
    
    # 4. Include unassigned group checkbox
    if "group" in df.columns:
        unassigned_group_count = df["group"].isna().sum()
        if unassigned_group_count > 0:
            filters["include_unknown_group"] = st.sidebar.checkbox(
                f"Include unassigned group ({unassigned_group_count})",
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
    
    return filters


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply all filters to the dataframe"""
    df_filtered = df.copy()
    
    # Device type filter
    if filters.get("device_types") is not None and "device_type" in df_filtered.columns:
        include_unknown_device = filters.get("include_unknown_device", True)
        if include_unknown_device:
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
    
    # Debug mode filter
    if filters.get("exclude_debug") and "debug_mode" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["debug_mode"] != True]
    
    # Group filter
    if filters.get("groups") is not None and "group" in df_filtered.columns:
        include_unknown_group = filters.get("include_unknown_group", True)
        if include_unknown_group:
            df_filtered = df_filtered[
                df_filtered["group"].isin(filters["groups"]) | 
                df_filtered["group"].isna()
            ]
        else:
            df_filtered = df_filtered[df_filtered["group"].isin(filters["groups"])]
    
    # Exclude reconstructed groups filter
    if filters.get("exclude_reconstructed") and "group_reconstructed" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["group_reconstructed"].isna()]
    
    return df_filtered


def get_numeric_columns(df: pd.DataFrame) -> list[str]:
    """Get list of numeric columns suitable for analysis"""
    exclude_cols = [
        "group", "group_reconstructed", 
        "total_ar_rotations", "total_ar_zooms"
    ]
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return [c for c in numeric_cols if c not in exclude_cols]


def get_categorical_columns(df: pd.DataFrame) -> list[str]:
    """Get list of categorical columns"""
    exclude_cols = ["group", "group_reconstructed"]
    cat_cols = df.select_dtypes(include=["object", "bool", "category"]).columns.tolist()
    # Also include columns with few unique values
    for col in df.columns:
        if col not in cat_cols and df[col].nunique() <= 10:
            cat_cols.append(col)
    return [c for c in list(set(cat_cols)) if c not in exclude_cols]


def render_histogram(df: pd.DataFrame, x_var: str, color_var: str = None):
    """Render histogram"""
    if color_var and color_var != "None":
        if color_var == "group":
            color_map = {str(k): v for k, v in GROUP_COLORS.items()}
            df_plot = df.copy()
            df_plot[color_var] = df_plot[color_var].astype(str)
        elif color_var == "variety":
            color_map = VARIETY_COLORS
            df_plot = df
        elif color_var == "ar_enabled":
            color_map = {str(k): v for k, v in AR_COLORS.items()}
            df_plot = df.copy()
            df_plot[color_var] = df_plot[color_var].astype(str)
        else:
            color_map = None
            df_plot = df
        
        fig = px.histogram(
            df_plot, x=x_var, color=color_var,
            color_discrete_map=color_map,
            barmode="overlay",
            opacity=0.7,
        )
    else:
        fig = px.histogram(df, x=x_var, color_discrete_sequence=["#FF6B6B"])
    
    fig.update_layout(**PLOTLY_TEMPLATE)
    fig.update_layout(
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        bargap=0.1,
    )
    
    return fig


def render_box_plot(df: pd.DataFrame, x_var: str, y_var: str, color_var: str = None):
    """Render box plot"""
    if color_var and color_var != "None":
        if color_var == "group":
            color_map = {str(k): v for k, v in GROUP_COLORS.items()}
            df_plot = df.copy()
            df_plot[color_var] = df_plot[color_var].astype(str)
        elif color_var == "variety":
            color_map = VARIETY_COLORS
            df_plot = df
        else:
            color_map = None
            df_plot = df
        
        fig = px.box(df_plot, x=x_var, y=y_var, color=color_var,
                    color_discrete_map=color_map)
    else:
        fig = px.box(df, x=x_var, y=y_var, color_discrete_sequence=["#FF6B6B"])
    
    fig.update_layout(**PLOTLY_TEMPLATE)
    fig.update_layout(
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    
    return fig


def render_scatter(df: pd.DataFrame, x_var: str, y_var: str, color_var: str = None):
    """Render scatter plot"""
    if color_var and color_var != "None":
        if color_var == "group":
            color_map = {str(k): v for k, v in GROUP_COLORS.items()}
            df_plot = df.copy()
            df_plot[color_var] = df_plot[color_var].astype(str)
        elif color_var == "variety":
            color_map = VARIETY_COLORS
            df_plot = df
        else:
            color_map = None
            df_plot = df
        
        fig = px.scatter(df_plot, x=x_var, y=y_var, color=color_var,
                        color_discrete_map=color_map, opacity=0.7)
    else:
        fig = px.scatter(df, x=x_var, y=y_var, color_discrete_sequence=["#FF6B6B"],
                        opacity=0.7)
    
    fig.update_layout(**PLOTLY_TEMPLATE)
    fig.update_layout(
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    
    return fig


def render_bar_chart(df: pd.DataFrame, x_var: str, y_var: str = None, color_var: str = None):
    """Render bar chart"""
    if y_var and y_var != "None":
        # Aggregate data
        agg_df = df.groupby(x_var)[y_var].mean().reset_index()
        
        if color_var and color_var != "None":
            agg_df = df.groupby([x_var, color_var])[y_var].mean().reset_index()
            
            if color_var == "group":
                color_map = {str(k): v for k, v in GROUP_COLORS.items()}
                agg_df[color_var] = agg_df[color_var].astype(str)
            else:
                color_map = None
            
            fig = px.bar(agg_df, x=x_var, y=y_var, color=color_var,
                        color_discrete_map=color_map, barmode="group")
        else:
            fig = px.bar(agg_df, x=x_var, y=y_var, 
                        color_discrete_sequence=["#FF6B6B"])
    else:
        # Count plot
        count_df = df[x_var].value_counts().reset_index()
        count_df.columns = [x_var, "count"]
        
        fig = px.bar(count_df, x=x_var, y="count",
                    color_discrete_sequence=["#FF6B6B"])
    
    fig.update_layout(**PLOTLY_TEMPLATE)
    fig.update_layout(
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        bargap=0.2,
    )
    
    return fig


def render_violin(df: pd.DataFrame, x_var: str, y_var: str, color_var: str = None):
    """Render violin plot"""
    if color_var and color_var != "None":
        if color_var == "group":
            color_map = {str(k): v for k, v in GROUP_COLORS.items()}
            df_plot = df.copy()
            df_plot[color_var] = df_plot[color_var].astype(str)
        else:
            color_map = None
            df_plot = df
        
        fig = px.violin(df_plot, x=x_var, y=y_var, color=color_var,
                       color_discrete_map=color_map, box=True)
    else:
        fig = px.violin(df, x=x_var, y=y_var, color_discrete_sequence=["#FF6B6B"],
                       box=True)
    
    fig.update_layout(**PLOTLY_TEMPLATE)
    fig.update_layout(
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    
    return fig


def render_correlation_matrix(df: pd.DataFrame, columns: list[str]):
    """Render correlation heatmap"""
    if len(columns) < 2:
        st.warning("Select at least 2 numeric variables for correlation matrix")
        return None
    
    corr_df = df[columns].corr()
    
    fig = px.imshow(
        corr_df,
        labels=dict(color="Correlation"),
        color_continuous_scale=[
            [0, "#4ECDC4"],
            [0.5, "#1A1D24"],
            [1, "#FF6B6B"]
        ],
        aspect="auto",
        text_auto=".2f",
    )
    
    fig.update_layout(**PLOTLY_TEMPLATE)
    fig.update_layout(
        xaxis=dict(tickangle=45),
    )
    
    return fig


def main():
    st.title("📈 Exploration")
    st.markdown("Interactive data visualization and pattern discovery")
    
    # Load data
    with st.spinner("Loading data..."):
        df = load_data()
    
    if df is None:
        st.error("Failed to connect to database.")
        return
    
    if df.empty:
        st.info("No sessions found in database.")
        return
    
    # Get column lists
    numeric_cols = get_numeric_columns(df)
    categorical_cols = get_categorical_columns(df)
    
    # Sidebar chart controls (on top)
    st.sidebar.markdown("### 📊 Chart Settings")
    
    chart_type = st.sidebar.selectbox(
        "Chart Type",
        ["Histogram", "Box Plot", "Scatter", "Bar Chart", "Violin Plot", "Correlation Matrix"]
    )
    
    color_options = ["None", "variety", "ar_enabled"] + [c for c in categorical_cols if c not in ["variety", "ar_enabled"]]
    color_options = list(dict.fromkeys(color_options))  # Remove duplicates
    
    color_var = st.sidebar.selectbox("Color By", color_options)
    
    st.sidebar.markdown("---")
    
    # Render filters in sidebar (below chart settings)
    filters = render_filters(df)
    
    # Apply filters
    df_filtered = apply_filters(df, filters)
    
    # Update column lists from filtered data
    numeric_cols = get_numeric_columns(df_filtered)
    categorical_cols = get_categorical_columns(df_filtered)
    
    # Show filter status
    if len(df_filtered) < len(df):
        st.info(f"Showing {len(df_filtered)} of {len(df)} sessions (filtered)")
    else:
        st.success(f"Showing all {len(df)} sessions")
    
    st.markdown("---")
    
    # Chart-specific controls and rendering
    if chart_type == "Histogram":
        st.markdown("### Histogram")
        
        x_var = st.selectbox("Variable", numeric_cols, key="hist_x")
        
        fig = render_histogram(df_filtered, x_var, color_var if color_var != "None" else None)
        st.plotly_chart(fig, use_container_width=True)
        
        # Stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Mean", f"{df_filtered[x_var].mean():.2f}")
        with col2:
            st.metric("Median", f"{df_filtered[x_var].median():.2f}")
        with col3:
            st.metric("Std Dev", f"{df_filtered[x_var].std():.2f}")
        with col4:
            st.metric("N", f"{df_filtered[x_var].notna().sum()}")
    
    elif chart_type == "Box Plot":
        st.markdown("### Box Plot")
        
        col1, col2 = st.columns(2)
        with col1:
            x_var = st.selectbox("X (Category)", categorical_cols, key="box_x")
        with col2:
            y_var = st.selectbox("Y (Numeric)", numeric_cols, key="box_y")
        
        fig = render_box_plot(df_filtered, x_var, y_var, color_var if color_var != "None" else None)
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_type == "Scatter":
        st.markdown("### Scatter Plot")
        
        col1, col2 = st.columns(2)
        with col1:
            x_var = st.selectbox("X Variable", numeric_cols, key="scatter_x")
        with col2:
            y_var = st.selectbox("Y Variable", numeric_cols, key="scatter_y",
                                index=min(1, len(numeric_cols)-1))
        
        fig = render_scatter(df_filtered, x_var, y_var, color_var if color_var != "None" else None)
        st.plotly_chart(fig, use_container_width=True)
        
        # Show correlation
        if x_var != y_var:
            corr = df_filtered[[x_var, y_var]].corr().iloc[0, 1]
            st.metric("Pearson Correlation", f"{corr:.3f}")
    
    elif chart_type == "Bar Chart":
        st.markdown("### Bar Chart")
        
        col1, col2 = st.columns(2)
        with col1:
            x_var = st.selectbox("X (Category)", categorical_cols, key="bar_x")
        with col2:
            y_options = ["None (Count)"] + numeric_cols
            y_var_sel = st.selectbox("Y (Numeric, optional)", y_options, key="bar_y")
            y_var = None if y_var_sel == "None (Count)" else y_var_sel
        
        fig = render_bar_chart(df_filtered, x_var, y_var, color_var if color_var != "None" else None)
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_type == "Violin Plot":
        st.markdown("### Violin Plot")
        
        col1, col2 = st.columns(2)
        with col1:
            x_var = st.selectbox("X (Category)", categorical_cols, key="violin_x")
        with col2:
            y_var = st.selectbox("Y (Numeric)", numeric_cols, key="violin_y")
        
        fig = render_violin(df_filtered, x_var, y_var, color_var if color_var != "None" else None)
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_type == "Correlation Matrix":
        st.markdown("### Correlation Matrix")
        
        # Default selection of interesting variables
        default_vars = ["session_duration_sec", "total_ar_time_sec", "unique_products_viewed",
                       "cart_additions", "final_cart_count", "ar_session_count"]
        default_vars = [v for v in default_vars if v in numeric_cols]
        
        selected_vars = st.multiselect(
            "Select Variables",
            options=numeric_cols,
            default=default_vars[:6] if default_vars else numeric_cols[:6]
        )
        
        if selected_vars:
            fig = render_correlation_matrix(df_filtered, selected_vars)
            if fig:
                st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
