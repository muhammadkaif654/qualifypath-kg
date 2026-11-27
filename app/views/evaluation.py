"""Evaluation dashboard: LLM-only vs KG-grounded on 10 CQs, and the multi-hop reasoner vs ground truth."""
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui

ui.style()
kg = ui.kg()
ui.sidebar(kg)
OUT = ui.ROOT / "Results" / "iteration2"

ui.hero("Evaluation",
        "Same LLM and settings in both conditions; correctness judged against verified answers from the graph and "
        "the official points table.",
        ["10 competency questions", "LLM only", "LLM + KG", "Correct?", "Evidence?"])

review = OUT / "cq_evaluation_review.csv"
raw = OUT / "cq_evaluation_raw.json"
if review.exists():
    df = pd.read_csv(review)
elif raw.exists():
    df = pd.DataFrame(json.loads(raw.read_text(encoding="utf-8")))
    df["correct_llm_only"] = df["auto_llm_only"]
    df["correct_kg_grounded"] = df["auto_kg_grounded"]
    st.warning("Showing the automatic first-pass check; the reviewed verdicts are not saved yet.")
else:
    st.info("Run `python scripts/run_cq_evaluation.py` to produce the comparison.")
    st.stop()

a, b = int(df.correct_llm_only.sum()), int(df.correct_kg_grounded.sum())
ev_b = int(df.evidence_kg_grounded.sum())
ui.metrics([("LLM only — correct", f"{a}/10"), ("LLM + KG — correct", f"{b}/10"),
            ("LLM only — evidence", "0/10"), ("LLM + KG — evidence", f"{ev_b}/10"),
            ("Model", str(df.model.iloc[0]).split("/")[-1])])
st.write("")
c1, c2 = st.columns([1, 1.6])
with c1:
    fig = go.Figure()
    fig.add_bar(x=["LLM only", "LLM + KG"], y=[a, b], marker_color=["#94a3b8", "#4f46e5"], text=[a, b],
                textposition="outside")
    fig.update_layout(height=330, yaxis=dict(range=[0, 10.8], title="correct answers (of 10)"),
                      margin=dict(l=10, r=10, t=20, b=10), plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)
with c2:
    view = pd.DataFrame({"CQ": df.cq, "Type": df["type"],
                         "Correct A/B": [f"{'Yes' if x else 'No'} / {'Yes' if y else 'No'}"
                                         for x, y in zip(df.correct_llm_only, df.correct_kg_grounded)],
                         "Evidence A/B": [f"No / {'Yes' if y else 'No'}" for y in df.evidence_kg_grounded]})
    st.dataframe(view, hide_index=True, use_container_width=True, height=330)

st.markdown("#### Answers side by side")
for _, r in df.iterrows():
    ok_a, ok_b = ("✅" if r.correct_llm_only else "❌"), ("✅" if r.correct_kg_grounded else "❌")
    with st.expander(f"{r.cq} · {r['question']}   —   LLM only {ok_a}   ·   LLM + KG {ok_b}"):
        st.markdown(f"**Expected:** {r.expected}")
        if "note" in r and isinstance(r.note, str) and r.note:
            st.caption(f"Review note: {r.note}")
        x, y = st.columns(2)
        x.markdown("<div class='qp-card baseline'><h4>LLM only</h4></div>", unsafe_allow_html=True)
        x.markdown(r.llm_only)
        y.markdown("<div class='qp-card answer'><h4>LLM + knowledge graph</h4></div>", unsafe_allow_html=True)
        y.markdown(ui.cite(r.kg_grounded), unsafe_allow_html=True)

summary = OUT / "multihop_summary.md"
if summary.exists():
    st.markdown("#### Multi-hop reasoner vs independent ground truth")
    st.markdown(summary.read_text(encoding="utf-8").split("\n", 2)[2])
