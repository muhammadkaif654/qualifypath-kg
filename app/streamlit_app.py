"""
QualifyPath-KG application entry point.

Run from the project folder:  streamlit run app/streamlit_app.py
Pages: Ask (KG-grounded Q&A) · Multi-hop reasoner · Knowledge graph explorer · Evaluation
URL parameters for direct links: /?q=<question>&compare=1 , /reasoner?task=...&a=LSG , /explorer?team=RR
"""
import sys
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

st.set_page_config(page_title="QualifyPath-KG", page_icon="🏏", layout="wide", initial_sidebar_state="expanded")

pages = [
    st.Page("views/ask.py", title="Ask the graph", icon="💬", url_path="ask", default=True),
    st.Page("views/reasoner.py", title="Multi-hop reasoner", icon="🧭", url_path="reasoner"),
    st.Page("views/explorer.py", title="Knowledge graph explorer", icon="🕸️", url_path="explorer"),
    st.Page("views/evaluation.py", title="Evaluation", icon="📊", url_path="evaluation"),
]
st.navigation(pages).run()
