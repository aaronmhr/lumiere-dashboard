"""
📊 Monitoring Page
==================
Real-time session tracking and experiment progress monitoring.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="Monitoring | Lumiere",
    page_icon="📊",
    layout="wide",
)

# Import utilities
from utils.firebase_client import get_firestore_client, fetch_sessions, clear_session_cache
from utils.data_processing import sessions_to_dataframe, create_derived_variables
from utils.group_reconstruction import reconstruct_groups

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    .stApp { font-family: 'DM Sans', sans-serif; }
    
    .big-metric {
        background: linear-gradient(145deg, #1e222a 0%, #252a34 100%);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .big-metric-value {
        font-size: 3rem;
        font-weight: 700;
        line-height: 1.2;
    }
    
    .big-metric-label {
        font-size: 0.85rem;
        color: #808080;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.5rem;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    .status-live {
        background: rgba(46, 204, 113, 0.2);
        color: #2ecc71;
        border: 1px solid rgba(46, 204, 113, 0.3);
    }
    
    .status-paused {
        background: rgba(241, 196, 15, 0.2);
        color: #f1c40f;
        border: 1px solid rgba(241, 196, 15, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Color scheme for groups (consistent across dashboard)
GROUP_COLORS = {
    1: "#4ECDC4",  # Teal - Group 1 (Low variety, No AR)
    2: "#FF6B6B",  # Coral - Group 2 (Low variety, AR)
    3: "#FFE66D",  # Yellow - Group 3 (High variety, No AR)
    4: "#9B59B6",  # Purple - Group 4 (High variety, AR)
}

GROUP_NAMES = {
    1: "Low Variety • No AR",
    2: "Low Variety • AR",
    3: "High Variety • No AR",
    4: "High Variety • AR",
}


def load_data():
    """Load and process session data"""
    with st.spinner("Loading data from Firestore..."):
        db = get_firestore_client()
        if db is None:
            return None
        
        sessions = fetch_sessions(db)
        if not sessions:
            st.warning("No sessions found in database.")
            return pd.DataFrame()
        
        df = sessions_to_dataframe(sessions)
        df = reconstruct_groups(df)
        df = create_derived_variables(df)
        
        return df


def render_metrics(df: pd.DataFrame):
    """Render key metrics cards"""
    total_sessions = len(df)
    completed_sessions = df["is_completed"].sum() if "is_completed" in df.columns else 0
    completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
    
    # Sessions in last 24 hours
    if "started_at" in df.columns:
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_sessions = (df["started_at"] > recent_cutoff).sum()
    else:
        recent_sessions = 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="big-metric">
            <div class="big-metric-value" style="color: #4ECDC4;">{total_sessions}</div>
            <div class="big-metric-label">Total Sessions</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="big-metric">
            <div class="big-metric-value" style="color: #2ecc71;">{completed_sessions}</div>
            <div class="big-metric-label">Completed</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="big-metric">
            <div class="big-metric-value" style="color: #FF6B6B;">{completion_rate:.1f}%</div>
            <div class="big-metric-label">Completion Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="big-metric">
            <div class="big-metric-value" style="color: #FFE66D;">{recent_sessions}</div>
            <div class="big-metric-label">Last 24h</div>
        </div>
        """, unsafe_allow_html=True)


def render_group_distribution(df: pd.DataFrame):
    """Render group distribution pie chart"""
    st.markdown("### Sessions by Group")
    
    if "group_final" not in df.columns:
        st.warning("Group data not available")
        return
    
    group_counts = df["group_final"].value_counts().reset_index()
    group_counts.columns = ["Group", "Count"]
    group_counts = group_counts[group_counts["Group"].notna()]
    group_counts["Group"] = group_counts["Group"].astype(int)
    group_counts["Label"] = group_counts["Group"].map(GROUP_NAMES)
    group_counts["Color"] = group_counts["Group"].map(GROUP_COLORS)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        fig = px.pie(
            group_counts,
            values="Count",
            names="Label",
            color="Group",
            color_discrete_map={g: GROUP_COLORS[g] for g in GROUP_COLORS},
            hole=0.4,
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#FAFAFA", family="DM Sans"),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            ),
            margin=dict(t=20, b=60, l=20, r=20),
        )
        fig.update_traces(
            textposition="inside",
            textinfo="value+percent",
            textfont_size=14,
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Group breakdown table
        for _, row in group_counts.iterrows():
            group = int(row["Group"])
            count = row["Count"]
            pct = count / len(df) * 100
            color = GROUP_COLORS.get(group, "#808080")
            
            st.markdown(f"""
            <div style="
                background: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1);
                border-left: 4px solid {color};
                padding: 0.75rem 1rem;
                border-radius: 8px;
                margin: 0.5rem 0;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: {color}; font-weight: 600;">Group {group}</span>
                    <span style="color: #FAFAFA;">{count} ({pct:.1f}%)</span>
                </div>
                <small style="color: #808080;">{GROUP_NAMES.get(group, '')}</small>
            </div>
            """, unsafe_allow_html=True)


def render_timeline(df: pd.DataFrame):
    """Render session timeline chart"""
    st.markdown("### Session Timeline")
    
    if "started_at" not in df.columns or df["started_at"].isna().all():
        st.warning("No timestamp data available")
        return
    
    # Aggregate by hour
    df_timeline = df.copy()
    df_timeline["hour"] = df_timeline["started_at"].dt.floor("H")
    hourly_counts = df_timeline.groupby("hour").size().reset_index(name="sessions")
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=hourly_counts["hour"],
        y=hourly_counts["sessions"],
        mode="lines+markers",
        line=dict(color="#FF6B6B", width=2),
        marker=dict(size=8, color="#FF6B6B"),
        fill="tozeroy",
        fillcolor="rgba(255, 107, 107, 0.1)",
        name="Sessions",
    ))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FAFAFA", family="DM Sans"),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.05)",
            title="Time",
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.05)",
            title="Sessions per Hour",
        ),
        margin=dict(t=20, b=40, l=60, r=20),
        hovermode="x unified",
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_recent_sessions(df: pd.DataFrame):
    """Render recent sessions table"""
    st.markdown("### Recent Sessions")
    
    # Sort by started_at descending
    df_recent = df.sort_values("started_at", ascending=False).head(20)
    
    # Select and format columns for display
    display_cols = ["session_id", "started_at", "group_final", "device_type", "is_completed", "session_duration_sec"]
    available_cols = [c for c in display_cols if c in df_recent.columns]
    
    df_display = df_recent[available_cols].copy()
    
    # Format columns
    if "started_at" in df_display.columns:
        df_display["started_at"] = df_display["started_at"].dt.strftime("%Y-%m-%d %H:%M")
    
    if "session_duration_sec" in df_display.columns:
        df_display["session_duration_sec"] = df_display["session_duration_sec"].apply(
            lambda x: f"{x/60:.1f} min" if pd.notna(x) else "-"
        )
    
    if "is_completed" in df_display.columns:
        df_display["is_completed"] = df_display["is_completed"].apply(
            lambda x: "✅" if x else "⏳"
        )
    
    # Rename columns for display
    column_names = {
        "session_id": "Session ID",
        "started_at": "Started",
        "group_final": "Group",
        "device_type": "Device",
        "is_completed": "Status",
        "session_duration_sec": "Duration",
    }
    df_display = df_display.rename(columns=column_names)
    
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
    )


def main():
    st.title("📊 Monitoring")
    st.markdown("Real-time experiment progress and session tracking")
    
    # Auto-refresh controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        auto_refresh = st.toggle("Auto-refresh (30s)", value=False)
    
    with col2:
        if st.button("🔄 Refresh Now"):
            clear_session_cache()
            st.rerun()
    
    with col3:
        last_updated = datetime.now().strftime("%H:%M:%S")
        st.markdown(f"<small style='color: #808080;'>Updated: {last_updated}</small>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Load data
    df = load_data()
    
    if df is None:
        st.error("Failed to connect to database. Please check your Firebase configuration.")
        st.info("Make sure `.streamlit/secrets.toml` contains valid Firebase credentials.")
        return
    
    if df.empty:
        st.info("No sessions found. Waiting for data...")
        if auto_refresh:
            time.sleep(30)
            clear_session_cache()
            st.rerun()
        return
    
    # Render dashboard components
    render_metrics(df)
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        render_group_distribution(df)
    
    with col2:
        # Additional metrics
        st.markdown("### Quick Stats")
        
        if "device_type" in df.columns:
            device_counts = df["device_type"].value_counts()
            st.markdown("**Device Types:**")
            for device, count in device_counts.items():
                st.markdown(f"- {device}: {count}")
        
        if "ar_supported" in df.columns:
            ar_support = df["ar_supported"].value_counts()
            st.markdown("**AR Support:**")
            for supported, count in ar_support.items():
                label = "Supported" if supported else "Not Supported"
                st.markdown(f"- {label}: {count}")
        
        if "has_survey" in df.columns:
            survey_completed = df["has_survey"].sum()
            st.markdown(f"**Surveys Completed:** {survey_completed}")
    
    st.markdown("---")
    
    render_timeline(df)
    
    st.markdown("---")
    
    render_recent_sessions(df)
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(30)
        clear_session_cache()
        st.rerun()


if __name__ == "__main__":
    main()
