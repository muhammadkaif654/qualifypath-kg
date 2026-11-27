"""Multi-hop reasoner (Option C) without the LLM: every answer with its intermediate entities and paths."""
import streamlit as st

import ui
from qualifypath.kg import TEAM

ui.style()
kg = ui.kg()
R = ui.reasoner()
ui.sidebar(kg)
teams = [kg.label(t) for t in kg.teams()]
params = st.query_params

ui.hero("Multi-hop KG reasoning",
        "Option C · answers are found by walking connected relationships; every hop shows whether it is stored, "
        "OWL-inferred or rule-derived. No LLM is involved on this page.",
        ["Start entity", "Relation 1", "Intermediate entity", "Relation 2", "…", "Answer + full path"])

TASKS = {
    "Qualification analysis (CQ5–CQ7)": ("one", lambda a, b: R.qualification(TEAM[a])),
    "Remaining fixtures (CQ4)": ("one", lambda a, b: R.remaining_fixtures(TEAM[a])),
    "Direct rivals (CQ8)": ("one", lambda a, b: R.rivals(TEAM[a])),
    "What if it loses its last match (CQ10, scenario)": ("one", lambda a, b: R.what_if_lose_last(TEAM[a])),
    "Teams beaten and where (CQ11)": ("one", lambda a, b: R.teams_beaten(TEAM[a])),
    "Venues played — inferred chain (CQ13)": ("one", lambda a, b: R.venues_played(TEAM[a])),
    "Chains of wins from A to B": ("two", lambda a, b: R.win_chains(TEAM[a], TEAM[b])),
    "Shortest connecting paths A to B": ("two", lambda a, b: R.find_paths(TEAM[a], TEAM[b])),
}
names = list(TASKS)
c1, c2, c3 = st.columns([2.2, 1, 1])
task = c1.selectbox("Reasoning task", names, index=names.index(params["task"]) if params.get("task") in names else 0)
a = c2.selectbox("Team A", teams, index=teams.index(params.get("a", "LSG")) if params.get("a", "LSG") in teams else 0)
pair = TASKS[task][0] == "two"
b = c3.selectbox("Team B", teams, index=teams.index(params.get("b", "KKR")) if params.get("b", "KKR") in teams else 0,
                 disabled=not pair)

res = TASKS[task][1](a, b)
hops = [h for p in res.paths for h in p]
prov = {k: sum(h.provenance.startswith(k) for h in hops) for k in ("explicit", "inferred", "rule-derived")}
ui.metrics([("Reasoning paths", str(len(res.paths))), ("Hops", str(len(hops))),
            ("Explicit hops", str(prov["explicit"])), ("OWL-inferred hops", str(prov["inferred"])),
            ("Rule-derived hops", str(prov["rule-derived"]))])
st.write("")
cls = "insufficient" if res.scenario else "answer"
tag = ui.badge("scenario") + " hypothetical — not a stored or inferred fact" if res.scenario else ui.badge("reasoning path")
st.markdown(f"<div class='qp-card {cls}'><h4>{res.question}</h4><div class='qp-muted'>{tag}</div>"
            f"<p style='margin:8px 0 0 0;font-size:1.02rem'>{res.answer}</p></div>", unsafe_allow_html=True)

left, right = st.columns([1, 1.35])
with left:
    if res.steps:
        st.markdown("#### Reasoning steps")
        for i, s in enumerate(res.steps, 1):
            st.markdown(f"**{i}.** {s}")
    st.markdown(f"#### Paths ({len(res.paths)})")
    for p in res.paths[:12]:
        st.markdown("<div class='qp-fact'>" + " ⟶ ".join(
            f"<code>{h.text(kg)}</code> {ui.badge(h.provenance)}" for h in p) + "</div>", unsafe_allow_html=True)
with right:
    st.markdown("#### Path graph")
    if res.paths:
        st.graphviz_chart(ui.path_graph(kg, res.paths), use_container_width=True)
        st.caption("Green = explicit · blue = OWL-inferred · purple = rule-derived · amber nodes = values")
    else:
        st.info("No path found.")

summary = ui.ROOT / "Results" / "iteration2" / "multihop_summary.md"
if summary.exists():
    with st.expander("📏 Evaluation against independent ground truth (scripts/evaluate_multihop.py)"):
        st.markdown(summary.read_text(encoding="utf-8"))
