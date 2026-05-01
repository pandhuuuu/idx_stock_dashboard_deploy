import streamlit as st

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        /* Base Styling */
        h1, h2, h3, p, span, div {
            font-family: 'Space Grotesk', sans-serif !important;
        }
        code {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* Summary Cards (Upgrade 2) */
        .sum-card {
            background: #0d1117;
            border: 1px solid #1e2a3a;
            border-radius: 12px;
            padding: 20px;
            text-align: left;
            transition: transform 0.2s;
        }
        .sum-card:hover { transform: translateY(-2px); }
        .sum-card-label { color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
        .sum-card-value { font-size: 28px; font-weight: 800; margin: 8px 0; font-family: 'JetBrains Mono', monospace; }
        .sum-card-sub { color: #475569; font-size: 11px; margin-bottom: 12px; }
        .sum-bar-track { background: #1e2a3a; height: 4px; border-radius: 10px; overflow: hidden; }
        .sum-bar-fill { height: 100%; border-radius: 10px; }

        /* Sector Heatmap (Upgrade 3) */
        .sector-heat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 12px;
            margin-top: 10px;
        }
        .sector-heat-cell {
            padding: 16px;
            border-radius: 12px;
            border: 1px solid transparent;
            text-align: center;
        }
        .sector-heat-name { font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; }
        .sector-heat-pct { font-size: 18px; font-weight: 800; font-family: 'JetBrains Mono', monospace; }
        .sector-heat-sub { font-size: 10px; font-weight: 600; margin-top: 4px; }

        /* Confidence Meter (Upgrade 4) */
        .conf-bar-track { background: #1e2a3a; height: 6px; border-radius: 10px; margin: 8px 0 4px 0; overflow: hidden; }
        .conf-bar-fill { height: 100%; border-radius: 10px; }

        /* Live Alert Feed (Upgrade 5) */
        .alert-feed-row {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 0;
            border-bottom: 1px solid #1e2a3a;
        }
        .alert-feed-row:last-child { border-bottom: none; }
        .alert-dot { width: 8px; height: 8px; border-radius: 50%; }
        .alert-feed-ticker { font-weight: 700; color: #e2e8f0; min-width: 50px; font-family: 'JetBrains Mono', monospace; }
        .alert-feed-msg { color: #94a3b8; font-size: 12px; flex: 1; }
        .alert-feed-badge { font-size: 9px; font-weight: 800; padding: 2px 8px; border-radius: 4px; }
        .alert-feed-time { color: #475569; font-size: 10px; font-family: 'JetBrains Mono', monospace; }

        /* RSI Rank Bar (Upgrade 6) */
        .rsi-row {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }
        .rsi-ticker-label { min-width: 50px; font-size: 12px; font-weight: 700; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; }
        .rsi-track { flex: 1; background: #1e2a3a; height: 8px; border-radius: 10px; overflow: hidden; position: relative; }
        .rsi-fill { height: 100%; border-radius: 10px; }
        .rsi-value { min-width: 40px; text-align: right; font-size: 11px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
        .rsi-zone { min-width: 70px; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }

        /* Custom scrollbar */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: #475569; }

        /* Hide Default elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)
