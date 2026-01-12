"""
🔬 Analysis Page
================
Statistical testing and hypothesis evaluation.
"""

import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Analysis | Lumiere",
    page_icon="🔬",
    layout="wide",
)

# Try to import statsmodels (optional for advanced analysis)
try:
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    from statsmodels.stats.anova import anova_lm
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

# Import utilities
from utils.firebase_client import get_firestore_client, fetch_sessions
from utils.data_processing import sessions_to_dataframe, create_derived_variables, filter_sessions

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    .stApp { font-family: 'DM Sans', sans-serif; }
    
    .stat-result {
        background: linear-gradient(145deg, #1e222a 0%, #252a34 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #FF6B6B;
    }
    
    .stat-significant {
        border-left-color: #2ecc71;
    }
    
    .stat-not-significant {
        border-left-color: #808080;
    }
    
    .effect-size {
        background: rgba(78, 205, 196, 0.1);
        border-radius: 8px;
        padding: 0.5rem 1rem;
        display: inline-block;
        margin: 0.25rem;
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
            index=1,  # Default to Completed for analysis
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
    exclude_cols = ["group", "group", "group_reconstructed"]
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return [c for c in numeric_cols if c not in exclude_cols]


def cohens_d(group1, group2):
    """Calculate Cohen's d effect size"""
    n1, n2 = len(group1), len(group2)
    var1, var2 = group1.var(), group2.var()
    
    # Pooled standard deviation
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    
    if pooled_std == 0:
        return 0
    
    return (group1.mean() - group2.mean()) / pooled_std


def interpret_cohens_d(d):
    """Interpret Cohen's d magnitude"""
    d = abs(d)
    if d < 0.2:
        return "negligible"
    elif d < 0.5:
        return "small"
    elif d < 0.8:
        return "medium"
    else:
        return "large"


def eta_squared(ss_between, ss_total):
    """Calculate eta-squared effect size"""
    if ss_total == 0:
        return 0
    return ss_between / ss_total


def interpret_eta_squared(eta_sq):
    """Interpret eta-squared magnitude"""
    if eta_sq < 0.01:
        return "negligible"
    elif eta_sq < 0.06:
        return "small"
    elif eta_sq < 0.14:
        return "medium"
    else:
        return "large"


def render_descriptive_stats(df: pd.DataFrame, dv: str):
    """Render descriptive statistics table by group"""
    st.markdown("### 📊 Descriptive Statistics")
    
    stats_data = []
    
    for group in sorted(df["group"].dropna().unique()):
        group_data = df[df["group"] == group][dv].dropna()
        
        stats_data.append({
            "Group": int(group),
            "N": len(group_data),
            "Mean": f"{group_data.mean():.3f}",
            "SD": f"{group_data.std():.3f}",
            "Median": f"{group_data.median():.3f}",
            "Min": f"{group_data.min():.3f}",
            "Max": f"{group_data.max():.3f}",
            "Skewness": f"{group_data.skew():.3f}",
        })
    
    # Add overall
    overall_data = df[dv].dropna()
    stats_data.append({
        "Group": "Overall",
        "N": len(overall_data),
        "Mean": f"{overall_data.mean():.3f}",
        "SD": f"{overall_data.std():.3f}",
        "Median": f"{overall_data.median():.3f}",
        "Min": f"{overall_data.min():.3f}",
        "Max": f"{overall_data.max():.3f}",
        "Skewness": f"{overall_data.skew():.3f}",
    })
    
    st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)
    
    # Visualization
    fig = go.Figure()
    
    for group in sorted(df["group"].dropna().unique()):
        group_data = df[df["group"] == group][dv].dropna()
        fig.add_trace(go.Box(
            y=group_data,
            name=f"Group {int(group)}",
            marker_color=GROUP_COLORS.get(int(group), "#808080"),
            boxmean=True,
        ))
    
    fig.update_layout(**PLOTLY_TEMPLATE)
    fig.update_layout(
        title=f"Distribution of {dv} by Group",
        yaxis=dict(title=dv, gridcolor="rgba(255,255,255,0.05)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        showlegend=False,
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_one_way_anova(df: pd.DataFrame, dv: str):
    """Render one-way ANOVA comparing all 4 groups"""
    st.markdown("### 🧪 One-Way ANOVA (4 Groups)")
    
    groups = []
    for group in sorted(df["group"].dropna().unique()):
        group_data = df[df["group"] == group][dv].dropna()
        if len(group_data) > 0:
            groups.append(group_data)
    
    if len(groups) < 2:
        st.warning("Need at least 2 groups with data for ANOVA")
        return
    
    # Perform ANOVA
    f_stat, p_value = stats.f_oneway(*groups)
    
    # Calculate effect size (eta-squared)
    all_data = pd.concat(groups)
    grand_mean = all_data.mean()
    ss_total = ((all_data - grand_mean) ** 2).sum()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    eta_sq = eta_squared(ss_between, ss_total)
    
    # Display results
    significance = "stat-significant" if p_value < 0.05 else "stat-not-significant"
    
    st.markdown(f"""
    <div class="stat-result {significance}">
        <h4>One-Way ANOVA Results</h4>
        <p><strong>F-statistic:</strong> {f_stat:.3f}</p>
        <p><strong>p-value:</strong> {p_value:.4f} {'✅ Significant' if p_value < 0.05 else '❌ Not significant'}</p>
        <p><strong>η² (eta-squared):</strong> {eta_sq:.3f} ({interpret_eta_squared(eta_sq)} effect)</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Post-hoc tests if significant
    if p_value < 0.05 and STATSMODELS_AVAILABLE:
        st.markdown("#### Post-hoc: Tukey HSD")
        
        # Prepare data for Tukey
        df_tukey = df[["group", dv]].dropna()
        
        try:
            tukey = pairwise_tukeyhsd(df_tukey[dv], df_tukey["group"], alpha=0.05)
            
            tukey_df = pd.DataFrame(data=tukey._results_table.data[1:], 
                                   columns=tukey._results_table.data[0])
            st.dataframe(tukey_df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"Could not perform Tukey HSD: {e}")


def render_factorial_anova(df: pd.DataFrame, dv: str):
    """Render 2x2 factorial ANOVA (variety × AR)"""
    st.markdown("### 🔬 2×2 Factorial ANOVA (Variety × AR)")
    
    if not STATSMODELS_AVAILABLE:
        st.warning("statsmodels package required for factorial ANOVA. Install with: `pip install statsmodels`")
        return
    
    # Prepare data
    df_anova = df[["variety", "ar_enabled", dv]].dropna()
    df_anova["ar_enabled"] = df_anova["ar_enabled"].astype(str)
    
    if len(df_anova) < 10:
        st.warning("Insufficient data for factorial ANOVA")
        return
    
    try:
        # Fit model
        formula = f"{dv} ~ C(variety) * C(ar_enabled)"
        model = ols(formula, data=df_anova).fit()
        anova_table = anova_lm(model, typ=2)
        
        # Display ANOVA table
        st.markdown("#### ANOVA Table")
        
        anova_display = anova_table.copy()
        anova_display.columns = ["Sum Sq", "df", "F", "p-value"]
        anova_display["Sig"] = anova_display["p-value"].apply(
            lambda p: "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))
        )
        
        st.dataframe(anova_display.round(4), use_container_width=True)
        
        # Effect sizes
        ss_total = anova_table["sum_sq"].sum()
        
        st.markdown("#### Effect Sizes (η²)")
        
        effects = []
        for effect in ["C(variety)", "C(ar_enabled)", "C(variety):C(ar_enabled)"]:
            if effect in anova_table.index:
                ss = anova_table.loc[effect, "sum_sq"]
                eta_sq = ss / ss_total
                p_val = anova_table.loc[effect, "PR(>F)"]
                
                effect_name = effect.replace("C(", "").replace(")", "").replace(":", " × ")
                
                effects.append({
                    "Effect": effect_name,
                    "η²": f"{eta_sq:.4f}",
                    "Interpretation": interpret_eta_squared(eta_sq),
                    "p-value": f"{p_val:.4f}",
                    "Significant": "Yes" if p_val < 0.05 else "No"
                })
        
        st.dataframe(pd.DataFrame(effects), use_container_width=True, hide_index=True)
        
        # Interaction plot
        st.markdown("#### Interaction Plot")
        
        interaction_data = df_anova.groupby(["variety", "ar_enabled"])[dv].mean().reset_index()
        
        fig = px.line(
            interaction_data,
            x="variety",
            y=dv,
            color="ar_enabled",
            markers=True,
            color_discrete_map={"True": "#FF6B6B", "False": "#4ECDC4"},
            labels={"ar_enabled": "AR Enabled"},
        )
        
        fig.update_layout(**PLOTLY_TEMPLATE)
        fig.update_layout(
            xaxis=dict(title="Variety Condition", gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(title=f"Mean {dv}", gridcolor="rgba(255,255,255,0.05)"),
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error in factorial ANOVA: {e}")


def render_t_tests(df: pd.DataFrame, dv: str):
    """Render independent t-tests for key comparisons"""
    st.markdown("### 📐 Independent t-Tests")
    
    comparisons = [
        ("variety", "low", "high", "Low vs High Variety"),
        ("ar_enabled", True, False, "AR vs No AR"),
    ]
    
    results = []
    
    for col, val1, val2, label in comparisons:
        if col not in df.columns:
            continue
        
        group1 = df[df[col] == val1][dv].dropna()
        group2 = df[df[col] == val2][dv].dropna()
        
        if len(group1) < 2 or len(group2) < 2:
            continue
        
        # Levene's test for equality of variances
        levene_stat, levene_p = stats.levene(group1, group2)
        equal_var = levene_p > 0.05
        
        # t-test
        t_stat, p_value = stats.ttest_ind(group1, group2, equal_var=equal_var)
        
        # Effect size
        d = cohens_d(group1, group2)
        
        results.append({
            "Comparison": label,
            "Group 1 (M ± SD)": f"{group1.mean():.2f} ± {group1.std():.2f}",
            "Group 2 (M ± SD)": f"{group2.mean():.2f} ± {group2.std():.2f}",
            "t": f"{t_stat:.3f}",
            "p": f"{p_value:.4f}",
            "Cohen's d": f"{d:.3f}",
            "Effect": interpret_cohens_d(d),
            "Sig": "Yes" if p_value < 0.05 else "No"
        })
    
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
    else:
        st.info("No comparisons available")


def render_regression(df: pd.DataFrame, dv: str, ivs: list[str]):
    """Render linear regression analysis"""
    st.markdown("### 📈 Linear Regression")
    
    if not STATSMODELS_AVAILABLE:
        st.warning("statsmodels package required for regression. Install with: `pip install statsmodels`")
        return
    
    if not ivs:
        st.info("Select independent variables to run regression")
        return
    
    # Prepare data
    cols_needed = [dv] + ivs
    df_reg = df[cols_needed].dropna()
    
    # Convert categorical to dummy variables
    df_dummies = pd.get_dummies(df_reg, columns=[c for c in ivs if df_reg[c].dtype == 'object'], drop_first=True)
    
    if len(df_dummies) < len(ivs) + 2:
        st.warning("Insufficient data for regression")
        return
    
    try:
        # Fit model
        X = df_dummies.drop(columns=[dv])
        X = sm.add_constant(X)
        y = df_dummies[dv]
        
        model = sm.OLS(y, X).fit()
        
        # Model summary
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("R²", f"{model.rsquared:.3f}")
        with col2:
            st.metric("Adjusted R²", f"{model.rsquared_adj:.3f}")
        with col3:
            st.metric("F-statistic", f"{model.fvalue:.3f} (p={model.f_pvalue:.4f})")
        
        # Coefficients table
        st.markdown("#### Coefficients")
        
        coef_df = pd.DataFrame({
            "Variable": model.params.index,
            "Coefficient": model.params.values,
            "Std Error": model.bse.values,
            "t-value": model.tvalues.values,
            "p-value": model.pvalues.values,
            "95% CI Lower": model.conf_int()[0].values,
            "95% CI Upper": model.conf_int()[1].values,
        })
        
        coef_df["Sig"] = coef_df["p-value"].apply(
            lambda p: "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))
        )
        
        st.dataframe(coef_df.round(4), use_container_width=True, hide_index=True)
        
        # Coefficient plot
        fig = go.Figure()
        
        # Exclude constant from plot
        plot_df = coef_df[coef_df["Variable"] != "const"].copy()
        
        fig.add_trace(go.Bar(
            y=plot_df["Variable"],
            x=plot_df["Coefficient"],
            orientation="h",
            marker_color=["#2ecc71" if p < 0.05 else "#808080" for p in plot_df["p-value"]],
            error_x=dict(
                type="data",
                symmetric=False,
                array=plot_df["95% CI Upper"] - plot_df["Coefficient"],
                arrayminus=plot_df["Coefficient"] - plot_df["95% CI Lower"],
            )
        ))
        
        fig.add_vline(x=0, line_dash="dash", line_color="#808080")
        
        fig.update_layout(**PLOTLY_TEMPLATE)
        fig.update_layout(
            title="Regression Coefficients (95% CI)",
            xaxis=dict(title="Coefficient", gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error in regression: {e}")


def main():
    st.title("🔬 Analysis")
    st.markdown("Statistical testing and hypothesis evaluation")
    
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading data..."):
        df = load_data()
    
    if df is None:
        st.error("Failed to connect to database.")
        return
    
    if df.empty:
        st.info("No sessions found.")
        return
    
    # Variable selection first (Analysis Settings)
    st.sidebar.markdown("### 📊 Analysis Settings")
    
    numeric_cols = get_numeric_columns(df)
    
    dv = st.sidebar.selectbox(
        "Dependent Variable",
        options=numeric_cols,
        index=numeric_cols.index("session_duration_sec") if "session_duration_sec" in numeric_cols else 0
    )
    
    st.sidebar.markdown("---")
    
    # Render filters
    filters = render_filters(df)
    
    # Apply filters
    df_filtered = apply_filters(df, filters)
    
    if df_filtered.empty:
        st.warning("No sessions match the current filters.")
        return
    
    st.success(f"Analyzing {len(df_filtered)} sessions (filtered from {len(df)} total)")
    
    # Create tabs for different analyses
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Descriptive",
        "🧪 One-Way ANOVA",
        "🔬 Factorial ANOVA",
        "📐 t-Tests",
        "📈 Regression"
    ])
    
    with tab1:
        render_descriptive_stats(df_filtered, dv)
    
    with tab2:
        render_one_way_anova(df_filtered, dv)
    
    with tab3:
        render_factorial_anova(df_filtered, dv)
    
    with tab4:
        render_t_tests(df_filtered, dv)
    
    with tab5:
        st.markdown("Select independent variables for regression:")
        
        potential_ivs = ["variety", "ar_enabled", "unique_products_viewed", 
                        "total_ar_time_sec", "ar_session_count", "scrolled_to_bottom"]
        potential_ivs = [iv for iv in potential_ivs if iv in df_filtered.columns and iv != dv]
        
        selected_ivs = st.multiselect(
            "Independent Variables",
            options=potential_ivs,
            default=["variety", "ar_enabled"] if all(v in potential_ivs for v in ["variety", "ar_enabled"]) else potential_ivs[:2]
        )
        
        render_regression(df_filtered, dv, selected_ivs)
    
    # Statistical notes
    st.markdown("---")
    with st.expander("📖 Statistical Notes"):
        st.markdown("""
        **Interpretation Guidelines:**
        
        - **p < 0.05**: Statistically significant at α = 0.05
        - **Cohen's d**: 0.2 = small, 0.5 = medium, 0.8 = large
        - **η² (eta-squared)**: 0.01 = small, 0.06 = medium, 0.14 = large
        
        **Analysis Notes:**
        
        - Use the sidebar filters to control which sessions are included in the analysis
        - By default, debug sessions are excluded and only completed sessions are shown
        - All tests assume α = 0.05 significance level
        """)


if __name__ == "__main__":
    main()
