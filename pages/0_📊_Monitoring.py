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
    
    .filter-active {
        background: rgba(255, 107, 107, 0.1);
        border: 1px solid rgba(255, 107, 107, 0.3);
        border-radius: 8px;
        padding: 0.5rem 1rem;
        margin-bottom: 1rem;
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
        df = create_derived_variables(df)
        
        return df


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply all filters to the dataframe"""
    df_filtered = df.copy()
    
    # Device type filter (include nulls if "Include unknown" or if all options selected)
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
    
    # AR supported filter
    if filters.get("ar_supported") and filters["ar_supported"] != "All" and "ar_supported" in df_filtered.columns:
        if filters["ar_supported"] == "AR Supported":
            df_filtered = df_filtered[df_filtered["ar_supported"] == True]
        elif filters["ar_supported"] == "AR Not Supported":
            df_filtered = df_filtered[df_filtered["ar_supported"] == False]
    
    # Group filter (include nulls if "Include unassigned" is checked)
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


def render_filters(df: pd.DataFrame) -> dict:
    """Render filter controls in sidebar and return filter settings"""
    st.sidebar.markdown("## 🔍 Filters")
    
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
    
    # 4. AR supported filter
    if "ar_supported" in df.columns:
        filters["ar_supported"] = st.sidebar.selectbox(
            "AR Support",
            options=["All", "AR Supported", "AR Not Supported"],
            index=0
        )
    
    # 5. Include unassigned group checkbox
    if "group" in df.columns:
        unassigned_group_count = df["group"].isna().sum()
        if unassigned_group_count > 0:
            filters["include_unknown_group"] = st.sidebar.checkbox(
                f"Include unassigned group ({unassigned_group_count})",
                value=False
            )
        else:
            filters["include_unknown_group"] = False
    
    # 6. Exclude reconstructed groups filter
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
    
    # 7. Debug mode filter (at the bottom)
    if "debug_mode" in df.columns:
        filters["exclude_debug"] = st.sidebar.checkbox(
            "Exclude debug sessions",
            value=True
        )
    
    st.sidebar.markdown("---")
    
    # Reset filters button
    if st.sidebar.button("🔄 Reset Filters"):
        st.rerun()
    
    return filters


def render_filter_summary(df_original: pd.DataFrame, df_filtered: pd.DataFrame, filters: dict):
    """Show active filters and their impact"""
    if len(df_filtered) < len(df_original):
        active_filters = []
        
        if filters.get("device_types") and "device_type" in df_original.columns:
            all_devices = set(df_original["device_type"].dropna().unique())
            if set(filters["device_types"]) != all_devices:
                active_filters.append(f"Devices: {', '.join(filters['device_types'])}")
        
        if filters.get("completion_status") != "All":
            active_filters.append(f"Status: {filters['completion_status']}")
        
        if filters.get("groups") and "group" in df_original.columns:
            all_groups = set(int(g) for g in df_original["group"].dropna().unique())
            if set(filters["groups"]) != all_groups:
                active_filters.append(f"Groups: {', '.join(str(g) for g in filters['groups'])}")
        
        if filters.get("ar_supported") != "All":
            active_filters.append(f"AR: {filters['ar_supported']}")
        
        if filters.get("exclude_debug"):
            debug_count = df_original["debug_mode"].sum() if "debug_mode" in df_original.columns else 0
            if debug_count > 0:
                active_filters.append("Debug excluded")
        
        if active_filters:
            st.markdown(f"""
            <div class="filter-active">
                <strong>🔍 Active Filters:</strong> {' • '.join(active_filters)}<br>
                <small style="color: #808080;">Showing {len(df_filtered)} of {len(df_original)} sessions</small>
            </div>
            """, unsafe_allow_html=True)


def render_metrics(df: pd.DataFrame, df_total: pd.DataFrame):
    """Render key metrics cards"""
    total_sessions = len(df)
    completed_sessions = df["is_completed"].sum() if "is_completed" in df.columns else 0
    completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
    
    # Sessions in last 24 hours (from filtered data)
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
            <div class="big-metric-label">Sessions</div>
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
    
    if "group" not in df.columns:
        st.warning("Group data not available")
        return
    
    if len(df) == 0:
        st.info("No sessions match the current filters")
        return
    
    group_counts = df["group"].value_counts().reset_index()
    group_counts.columns = ["Group", "Count"]
    group_counts = group_counts[group_counts["Group"].notna()]
    
    if len(group_counts) == 0:
        st.info("No group data available for filtered sessions")
        return
    
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
        total = len(df)
        for _, row in group_counts.iterrows():
            group = int(row["Group"])
            count = row["Count"]
            pct = count / total * 100 if total > 0 else 0
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


def render_breakdown_stats(df: pd.DataFrame):
    """Render breakdown statistics for filtered data"""
    st.markdown("### 📊 Breakdown Stats")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if "device_type" in df.columns:
            st.markdown("**By Device:**")
            device_counts = df["device_type"].value_counts()
            for device, count in device_counts.items():
                pct = count / len(df) * 100 if len(df) > 0 else 0
                st.markdown(f"- {device}: **{count}** ({pct:.1f}%)")
    
    with col2:
        if "ar_supported" in df.columns:
            st.markdown("**By AR Support:**")
            ar_counts = df["ar_supported"].value_counts()
            for supported, count in ar_counts.items():
                label = "AR Supported" if supported else "No AR"
                pct = count / len(df) * 100 if len(df) > 0 else 0
                st.markdown(f"- {label}: **{count}** ({pct:.1f}%)")
        
        if "has_survey" in df.columns:
            survey_completed = df["has_survey"].sum()
            survey_pct = survey_completed / len(df) * 100 if len(df) > 0 else 0
            st.markdown(f"**Surveys Completed:** {survey_completed} ({survey_pct:.1f}%)")


def render_timeline(df: pd.DataFrame):
    """Render session timeline chart"""
    st.markdown("### Session Timeline")
    
    if "started_at" not in df.columns or df["started_at"].isna().all():
        st.warning("No timestamp data available")
        return
    
    if len(df) == 0:
        st.info("No sessions match the current filters")
        return
    
    # Aggregate by hour
    df_timeline = df.copy()
    df_timeline["hour"] = df_timeline["started_at"].dt.floor("h")
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


def render_timezone_map(df: pd.DataFrame):
    """Render world map showing countries based on timezone data"""
    st.markdown("### 🌍 Geographic Distribution")
    
    if "timezone" not in df.columns or df["timezone"].isna().all():
        st.info("No timezone data available")
        return
    
    if len(df) == 0:
        st.info("No sessions match the current filters")
        return
    
    # Timezone to ISO 3166-1 alpha-3 country code mapping
    # This covers common timezones - extend as needed
    TIMEZONE_TO_COUNTRY = {
        # Europe
        "Europe/London": "GBR", "Europe/Dublin": "IRL", "Europe/Paris": "FRA",
        "Europe/Berlin": "DEU", "Europe/Madrid": "ESP", "Europe/Rome": "ITA",
        "Europe/Amsterdam": "NLD", "Europe/Brussels": "BEL", "Europe/Vienna": "AUT",
        "Europe/Zurich": "CHE", "Europe/Stockholm": "SWE", "Europe/Oslo": "NOR",
        "Europe/Copenhagen": "DNK", "Europe/Helsinki": "FIN", "Europe/Warsaw": "POL",
        "Europe/Prague": "CZE", "Europe/Budapest": "HUN", "Europe/Athens": "GRC",
        "Europe/Lisbon": "PRT", "Europe/Bucharest": "ROU", "Europe/Sofia": "BGR",
        "Europe/Kiev": "UKR", "Europe/Moscow": "RUS", "Europe/Istanbul": "TUR",
        # Americas
        "America/New_York": "USA", "America/Los_Angeles": "USA", "America/Chicago": "USA",
        "America/Denver": "USA", "America/Phoenix": "USA", "America/Detroit": "USA",
        "America/Toronto": "CAN", "America/Vancouver": "CAN", "America/Montreal": "CAN",
        "America/Mexico_City": "MEX", "America/Sao_Paulo": "BRA", "America/Buenos_Aires": "ARG",
        "America/Santiago": "CHL", "America/Lima": "PER", "America/Bogota": "COL",
        # Asia/Pacific
        "Asia/Tokyo": "JPN", "Asia/Seoul": "KOR", "Asia/Shanghai": "CHN",
        "Asia/Hong_Kong": "HKG", "Asia/Singapore": "SGP", "Asia/Bangkok": "THA",
        "Asia/Jakarta": "IDN", "Asia/Manila": "PHL", "Asia/Kuala_Lumpur": "MYS",
        "Asia/Dubai": "ARE", "Asia/Kolkata": "IND", "Asia/Mumbai": "IND",
        "Asia/Tel_Aviv": "ISR", "Asia/Jerusalem": "ISR",
        "Australia/Sydney": "AUS", "Australia/Melbourne": "AUS", "Australia/Perth": "AUS",
        "Pacific/Auckland": "NZL",
        # Africa
        "Africa/Johannesburg": "ZAF", "Africa/Cairo": "EGY", "Africa/Lagos": "NGA",
        "Africa/Nairobi": "KEN", "Africa/Casablanca": "MAR",
    }
    
    # Count sessions per country
    country_counts = {}
    timezone_counts = df["timezone"].value_counts()
    
    for tz, count in timezone_counts.items():
        if pd.isna(tz):
            continue
        country_code = TIMEZONE_TO_COUNTRY.get(tz)
        if country_code:
            country_counts[country_code] = country_counts.get(country_code, 0) + count
    
    if not country_counts:
        st.info("No recognized timezones found in data")
        # Show raw timezone distribution instead
        with st.expander("View raw timezone data"):
            tz_df = df["timezone"].value_counts().reset_index()
            tz_df.columns = ["Timezone", "Count"]
            st.dataframe(tz_df, use_container_width=True, hide_index=True)
        return
    
    # Create dataframe for map
    map_data = pd.DataFrame([
        {"country": code, "sessions": count}
        for code, count in country_counts.items()
    ])
    
    # Create choropleth map
    fig = px.choropleth(
        map_data,
        locations="country",
        locationmode="ISO-3",
        color="sessions",
        hover_name="country",
        hover_data={"sessions": True, "country": False},
        color_continuous_scale=[
            [0, "rgba(78, 205, 196, 0.2)"],
            [0.5, "rgba(78, 205, 196, 0.6)"],
            [1, "#4ECDC4"]
        ],
        labels={"sessions": "Sessions"},
    )
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FAFAFA", family="DM Sans"),
        geo=dict(
            bgcolor="rgba(0,0,0,0)",
            showframe=False,
            showcoastlines=True,
            coastlinecolor="rgba(255,255,255,0.2)",
            showland=True,
            landcolor="rgba(30, 34, 42, 1)",
            showocean=True,
            oceancolor="rgba(14, 17, 23, 1)",
            showlakes=False,
            showcountries=True,
            countrycolor="rgba(255,255,255,0.1)",
            projection_type="natural earth",
        ),
        margin=dict(t=10, b=10, l=0, r=0),
        coloraxis_colorbar=dict(
            title=dict(text="Sessions", font=dict(color="#FAFAFA")),
            tickfont=dict(color="#FAFAFA"),
        ),
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show country breakdown
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**Top Countries:**")
        sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
        for country, count in sorted_countries[:5]:
            pct = count / len(df) * 100
            st.markdown(f"- {country}: **{count}** ({pct:.1f}%)")
    
    with col2:
        # Show unmapped timezones if any
        unmapped = [tz for tz in timezone_counts.index if pd.notna(tz) and tz not in TIMEZONE_TO_COUNTRY]
        if unmapped:
            with st.expander(f"Unmapped timezones ({len(unmapped)})"):
                for tz in unmapped[:10]:
                    st.text(f"• {tz}: {timezone_counts[tz]}")


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
    
    # Render filters in sidebar and get filter settings
    filters = render_filters(df)
    
    # Apply filters
    df_filtered = apply_filters(df, filters)
    
    # Show filter summary
    render_filter_summary(df, df_filtered, filters)
    
    # Render dashboard components with filtered data
    render_metrics(df_filtered, df)
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        render_group_distribution(df_filtered)
    
    with col2:
        render_breakdown_stats(df_filtered)
    
    st.markdown("---")
    
    render_timeline(df_filtered)
    
    st.markdown("---")
    
    render_timezone_map(df_filtered)
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(30)
        clear_session_cache()
        st.rerun()


if __name__ == "__main__":
    main()
