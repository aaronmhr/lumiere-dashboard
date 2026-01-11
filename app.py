"""
Lumiere Experiment Dashboard
============================
A Streamlit dashboard for monitoring and analyzing behavioral research data.

2x2 Factorial Design: Product Variety × AR Effects on Shopping Decisions
"""

import streamlit as st

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="Lumiere Dashboard",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished appearance
st.markdown("""
<style>
    /* Import distinctive font */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Global styling */
    .stApp {
        font-family: 'DM Sans', sans-serif;
    }
    
    code, .stCode {
        font-family: 'JetBrains Mono', monospace;
    }
    
    /* Hero section */
    .hero-container {
        background: linear-gradient(135deg, #1a1d24 0%, #2d1f3d 50%, #1a2d3d 100%);
        border-radius: 20px;
        padding: 3rem 2rem;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 107, 107, 0.2);
        position: relative;
        overflow: hidden;
    }
    
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255, 107, 107, 0.05) 0%, transparent 50%);
        animation: pulse 15s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 0.5; }
        50% { transform: scale(1.1); opacity: 0.3; }
    }
    
    .hero-title {
        font-size: 3.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #FF6B6B 0%, #FFE66D 50%, #4ECDC4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        position: relative;
        z-index: 1;
    }
    
    .hero-subtitle {
        font-size: 1.3rem;
        color: #a0a0a0;
        margin-bottom: 1.5rem;
        position: relative;
        z-index: 1;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(145deg, #1e222a 0%, #252a34 100%);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #FF6B6B;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #808080;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Group cards */
    .group-card {
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.5rem 0;
        border-left: 4px solid;
    }
    
    .group-1 { 
        background: rgba(78, 205, 196, 0.1); 
        border-left-color: #4ECDC4; 
    }
    .group-2 { 
        background: rgba(255, 107, 107, 0.1); 
        border-left-color: #FF6B6B; 
    }
    .group-3 { 
        background: rgba(255, 230, 109, 0.1); 
        border-left-color: #FFE66D; 
    }
    .group-4 { 
        background: rgba(155, 89, 182, 0.1); 
        border-left-color: #9B59B6; 
    }
    
    /* Navigation styling */
    .nav-link {
        display: block;
        padding: 1rem 1.5rem;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        margin: 0.5rem 0;
        text-decoration: none;
        color: #FAFAFA;
        transition: all 0.2s ease;
        border: 1px solid transparent;
    }
    
    .nav-link:hover {
        background: rgba(255, 107, 107, 0.1);
        border-color: rgba(255, 107, 107, 0.3);
        transform: translateX(4px);
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0E1117 0%, #1A1D24 100%);
    }
    
    /* Make dataframes look better */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Hero Section
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">✨ Lumiere</div>
        <div class="hero-subtitle">Behavioral Research Experiment Dashboard</div>
        <p style="color: #c0c0c0; max-width: 600px; position: relative; z-index: 1;">
            Analyzing product variety and augmented reality effects on shopping decisions 
            through a 2×2 factorial design study.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Study Design Overview
    st.markdown("## 📋 Study Design")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="group-card group-1">
            <strong style="color: #4ECDC4;">Group 1</strong><br>
            <span style="color: #a0a0a0;">Low Variety • No AR</span><br>
            <small style="color: #606060;">5 products</small>
        </div>
        <div class="group-card group-2">
            <strong style="color: #FF6B6B;">Group 2</strong><br>
            <span style="color: #a0a0a0;">Low Variety • AR Enabled</span><br>
            <small style="color: #606060;">5 products</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="group-card group-3">
            <strong style="color: #FFE66D;">Group 3</strong><br>
            <span style="color: #a0a0a0;">High Variety • No AR</span><br>
            <small style="color: #606060;">15 products</small>
        </div>
        <div class="group-card group-4">
            <strong style="color: #9B59B6;">Group 4</strong><br>
            <span style="color: #a0a0a0;">High Variety • AR Enabled</span><br>
            <small style="color: #606060;">15 products</small>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Design Matrix
    st.markdown("### Factorial Design Matrix")
    
    matrix_col1, matrix_col2, matrix_col3 = st.columns([1, 2, 2])
    
    with matrix_col1:
        st.markdown("##### ")
    with matrix_col2:
        st.markdown("##### 🚫 No AR")
    with matrix_col3:
        st.markdown("##### 📱 AR Enabled")
    
    matrix_col1, matrix_col2, matrix_col3 = st.columns([1, 2, 2])
    
    with matrix_col1:
        st.markdown("**Low Variety**")
    with matrix_col2:
        st.info("**Group 1**\n\n5 products")
    with matrix_col3:
        st.error("**Group 2**\n\n5 products")
    
    matrix_col1, matrix_col2, matrix_col3 = st.columns([1, 2, 2])
    
    with matrix_col1:
        st.markdown("**High Variety**")
    with matrix_col2:
        st.warning("**Group 3**\n\n15 products")
    with matrix_col3:
        st.success("**Group 4**\n\n15 products")
    
    st.markdown("---")
    
    # Quick Navigation
    st.markdown("## 🧭 Dashboard Pages")
    
    nav_col1, nav_col2 = st.columns(2)
    
    with nav_col1:
        st.markdown("""
        ### 📊 Monitoring
        Real-time session tracking, completion rates, and group distribution.
        
        - Total and completed sessions
        - Sessions per group visualization
        - Timeline of session starts
        - Recent sessions table
        - Auto-refresh capability
        """)
        
        st.markdown("""
        ### 📈 Exploration
        Interactive data visualization and pattern discovery.
        
        - Multiple chart types
        - Variable selection
        - Color by experimental conditions
        - Correlation analysis
        """)
    
    with nav_col2:
        st.markdown("""
        ### 🧹 Data Preparation
        Data quality assessment and preprocessing tools.
        
        - Quality reports
        - Group reconstruction
        - Derived variables
        - Filtering controls
        - CSV export
        """)
        
        st.markdown("""
        ### 🔬 Analysis
        Statistical testing and hypothesis evaluation.
        
        - Descriptive statistics
        - ANOVA and factorial analysis
        - Regression modeling
        - Effect size calculations
        """)
    
    st.markdown("---")
    
    # Product Information
    with st.expander("📦 Product ID Reference"):
        pid_col1, pid_col2 = st.columns(2)
        
        with pid_col1:
            st.markdown("""
            **Low Variety Products** (Groups 1 & 2):
            ```
            [1, 6, 10, 11, 14]
            ```
            """)
        
        with pid_col2:
            st.markdown("""
            **High Variety Products** (Groups 3 & 4):
            ```
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
            ```
            
            **High Variety Exclusive** (only in Groups 3 & 4):
            ```
            [2, 3, 4, 5, 7, 8, 9, 12, 13, 15]
            ```
            """)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #606060;'>"
        "Built with Streamlit • Data from Firebase Firestore"
        "</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
