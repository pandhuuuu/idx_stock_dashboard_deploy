import streamlit as st
import os
import sys

# Menambahkan path folder saat ini agar import sub-folder (seperti 'app') terdeteksi
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="MarketLens", layout="wide", page_icon="🧿")

from app.ui import dashboard

if __name__ == "__main__":
    # We will wrap dashboard logic in a render function shortly,
    # but for now, importing dashboard executes its top-level code.
    pass
