import streamlit as st

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {
            --primary: #2563eb;
            --bg-dark: #0f172a;
            --card-bg: #1e293b;
            --text-main: #e2e8f0;
            --text-dim: #94a3b8;
        }

        .stApp {
            background-color: var(--bg-dark);
            color: var(--text-main);
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #020617;
            border-right: 1px solid #1e293b;
        }

        /* Card Styling */
        div.stMetric {
            background-color: var(--card-bg);
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #334155;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }

        /* Button Styling */
        .stButton>button {
            background-color: var(--primary);
            color: white;
            border-radius: 8px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 600;
            transition: all 0.2s;
        }

        .stButton>button:hover {
            background-color: #1d4ed8;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }

        /* Custom Font */
        h1, h2, h3, p, span, div {
            font-family: 'Space Grotesk', sans-serif !important;
        }

        code {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* Hide Streamlit Branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)
