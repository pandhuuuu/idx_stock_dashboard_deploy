import streamlit as st

st.set_page_config(page_title="MarketLens", layout="wide", page_icon="🧿")

from app.ui import dashboard

if __name__ == "__main__":
    # We will wrap dashboard logic in a render function shortly,
    # but for now, importing dashboard executes its top-level code.
    pass
