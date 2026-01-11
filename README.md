# ✨ Lumiere Experiment Dashboard

A Streamlit dashboard for monitoring and analyzing behavioral research data from a 2×2 factorial study on product variety and AR effects on shopping decisions.

## 📋 Study Design

| Group | Variety | AR | Products |
|-------|---------|-----|----------|
| 1 | Low | No | 5 |
| 2 | Low | Yes | 5 |
| 3 | High | No | 15 |
| 4 | High | Yes | 15 |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Firebase project with Firestore database
- Firebase service account credentials

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd lumiere-dashboard
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Firebase credentials**
   
   Copy the example secrets file:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   
   Edit `.streamlit/secrets.toml` with your Firebase service account credentials:
   ```toml
   [firebase]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "your-private-key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "firebase-adminsdk-xxxxx@your-project-id.iam.gserviceaccount.com"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
   ```

5. **Run the dashboard**
   ```bash
   streamlit run app.py
   ```

## 📱 Dashboard Pages

### 📊 Monitoring
Real-time session tracking and experiment progress.
- Total/completed sessions and completion rate
- Sessions per group visualization
- Timeline of session starts
- Recent sessions table
- Auto-refresh capability (30-second intervals)

### 🧹 Data Preparation
Data quality assessment and preprocessing tools.
- Comprehensive quality report (missing values, outliers)
- Group reconstruction for sessions missing group field
- Derived variables creation
- Filtering controls (exclude debug, incomplete, test PIDs)
- CSV export with customizable options

### 📈 Exploration
Interactive data visualization and pattern discovery.
- Multiple chart types: Histogram, Box Plot, Scatter, Bar, Violin
- Variable selection for X/Y axes
- Color by experimental conditions (group, variety, AR)
- Correlation matrix heatmap
- Interactive Plotly charts

### 🔬 Analysis
Statistical testing and hypothesis evaluation.
- Descriptive statistics by group
- One-way ANOVA (4 groups) with post-hoc tests
- 2×2 Factorial ANOVA (variety × AR interaction)
- Independent t-tests for pairwise comparisons
- Linear regression builder
- Effect size calculations (Cohen's d, η²)

## ☁️ Deploy to Streamlit Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Add secrets in Streamlit Cloud dashboard:
   - Go to App Settings → Secrets
   - Paste your `secrets.toml` content

## 🗂️ Project Structure

```
lumiere-dashboard/
├── .streamlit/
│   ├── config.toml           # Streamlit theme config
│   └── secrets.toml          # Firebase creds (GITIGNORED)
├── app.py                     # Home page
├── pages/
│   ├── 1_📊_Monitoring.py
│   ├── 2_🧹_Data_Prep.py
│   ├── 3_📈_Exploration.py
│   └── 4_🔬_Analysis.py
├── utils/
│   ├── __init__.py
│   ├── firebase_client.py    # Firestore connection
│   ├── data_processing.py    # Load & transform data
│   └── group_reconstruction.py
├── requirements.txt
├── .gitignore
└── README.md
```

## 🔧 Group Reconstruction Logic

For sessions missing the `group` field, the dashboard can reconstruct groups using:

1. **AR events** (definitive): `ar_start` or `ar_end` present → Group 2 or 4
2. **Product IDs** (definitive): High-variety exclusive products viewed → Group 3 or 4
3. **Scroll timing** (indicator): Fast scroll after gallery → Low variety (Groups 1/2)
4. **Product count** (definitive): > 5 unique products → High variety (Groups 3/4)

## 📊 Data Schema

Expected Firestore document structure in `sessions` collection:

```json
{
  "session_id": "string",
  "started_at": { "_seconds": 123, "_nanoseconds": 456 },
  "completed_at": { "_seconds": 123, "_nanoseconds": 456 },
  "consented": true,
  "debug_mode": false,
  "device_type": "android|ios|web",
  "ar_supported": true,
  "pid": "prolific_id",
  "group": 1-4,
  "final_cart": [{ "product_id": 1, "quantity": 1 }],
  "survey": {
    "submitted_at": { "_seconds": 123, "_nanoseconds": 456 },
    "survey_final": { ... }
  },
  "events": [
    { "t": 0, "e": "view_page", "p": "gallery" },
    { "t": 5000, "e": "ar_start", "p": "5" }
  ]
}
```

## 🎨 Customization

### Theme
Edit `.streamlit/config.toml` to customize colors:

```toml
[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#1A1D24"
textColor = "#FAFAFA"
```

### Group Colors
Group colors are defined in each page file:

```python
GROUP_COLORS = {
    1: "#4ECDC4",  # Teal
    2: "#FF6B6B",  # Coral
    3: "#FFE66D",  # Yellow
    4: "#9B59B6",  # Purple
}
```

## 📝 License

MIT License - feel free to use and modify for your research.

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.
