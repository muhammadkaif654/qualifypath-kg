"""
QualifyPath-KG application entry point.

Run from the project folder:  streamlit run app/streamlit_app.py
Sections: Tournament (Overview, Points Table, Match Center) · Intelligence (Qualification Predictor,
Scenario Explorer, Ask AI, Multi-hop Reasoner) · Knowledge Graph (Graph Explorer, Evidence & Sources, Evaluation) ·
Project (About).
Direct links: /ask?q=<question>&compare=1 · /predictor?team=LSG · /reasoner?task=...&a=LSG · add &nosplash=1 to skip the intro
"""
import sys
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

st.set_page_config(page_title="QualifyPath-KG · IPL 2026 qualification intelligence",
                   page_icon=str(HERE / "assets" / "favicon.png"), layout="wide", initial_sidebar_state="auto")

import ui  # noqa: E402

ui.style()
ui.splash()  # blue cricket intro, once per browser session (?nosplash=1 skips it)
st.logo(str(HERE / "assets" / "wordmark.svg"), size="large", icon_image=str(HERE / "assets" / "logo.svg"))

V = "views/"
pages = {
    "Tournament": [
        st.Page(V + "overview.py", title="Overview", icon=":material/space_dashboard:", default=True),
        st.Page(V + "points.py", title="Points Table", icon=":material/leaderboard:", url_path="points"),
        st.Page(V + "matches.py", title="Match Center", icon=":material/sports_cricket:", url_path="matches"),
    ],
    "Intelligence": [
        st.Page(V + "predictor.py", title="Qualification Predictor", icon=":material/military_tech:",
                url_path="predictor"),
        st.Page(V + "scenario.py", title="Scenario Explorer", icon=":material/tune:", url_path="scenario"),
        st.Page(V + "ask.py", title="Ask AI", icon=":material/forum:", url_path="ask"),
        st.Page(V + "reasoner.py", title="Multi-hop Reasoner", icon=":material/route:", url_path="reasoner"),
    ],
    "Knowledge Graph": [
        st.Page(V + "graph.py", title="Graph Explorer", icon=":material/hub:", url_path="graph"),
        st.Page(V + "evidence.py", title="Evidence & Sources", icon=":material/fact_check:", url_path="evidence"),
        st.Page(V + "evaluation.py", title="Evaluation", icon=":material/analytics:", url_path="evaluation"),
    ],
    "Project": [
        st.Page(V + "about.py", title="About", icon=":material/info:", url_path="about"),
    ],
}
st.navigation(pages).run()
