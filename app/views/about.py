"""About: what QualifyPath-KG is, how it works and who built it."""
import streamlit as st

import ui
from qualifypath import llm

ui.style()
kg = ui.kg()
ui.sidebar(kg)

ui.hero("About QualifyPath-KG",
        "A knowledge-graph reasoner for cricket qualification: it represents the IPL 2026 league stage as an OWL "
        "ontology and RDF graph, infers standings and qualification status with OWL 2 RL and SPARQL rules, answers "
        "multi-hop questions with explicit paths, and grounds an LLM in that evidence.",
        eyebrow="AI-3001 Knowledge Representation & Reasoning")

ui.stats([("OWL classes", "19", ""), ("Explicit triples", f"{len(kg.explicit):,}", "g"),
          ("Inferred + rule triples", f"{len(kg.full) - len(kg.explicit):,}", "c"),
          ("Multi-hop accuracy", "150/150", "g"), ("CQs answered · KG vs LLM-only", "10 vs 0", "a")])

arch = ui.ROOT / "Visualization" / "architecture.png"
if arch.exists():
    ui.title("Architecture")
    st.image(str(arch), use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    ui.title("How it works")
    st.markdown(f"""
1. **Ontology and data** — teams, matches, innings, venues and season rules as RDF.
2. **OWL 2 RL reasoning** — infers participation, completed matches and venues played (property chains, sub-properties).
3. **Rules R1–R7** — SPARQL Update rules derive points, net run rate, maximum points, status and position.
4. **Multi-hop reasoner** — walks connected relations and returns every intermediate hop with its provenance.
5. **Grounded LLM** — `{llm.MODEL}` via Groq answers only from numbered retrieved facts and cites them.
""")
with c2:
    ui.title("Design choices")
    st.markdown("""
- **Team insignia** — official IPL logos are trademarks we are not licensed to use, so each team has a consistent
  shield in its colours.
- **No probabilities** — the predictor reports mathematical certainty (eliminated · depends · guaranteed), because the
  graph holds no data that could justify a probability.
- **No player data** — players are not modelled in the graph, so the assistant refuses player questions instead of
  guessing.
- **Scenarios are labelled** — what-if results are never mixed with stored or inferred facts.
""")

ui.title("Team")
cols = st.columns(3)
for col, (name, roll, part) in zip(cols, [
    ("Muhammad Kaif", "24I-0071", "Retriever, KG-grounded Q&A, application and report"),
    ("Talha Habib", "24I-0029", "Multi-hop reasoner (Option C) and its evaluation"),
    ("Haseebullah Gondal", "24I-0086", "Prompts, LLM-only vs KG evaluation and explainability"),
]):
    col.markdown(f"<div class='qp-panel'><div style='font-weight:800'>{name}</div><div class='qp-muted'>{roll}</div>"
                 f"<div style='margin-top:6px;font-size:.88rem'>{part}</div></div>", unsafe_allow_html=True)
st.caption("Instructor: Ms. Mehreen Javaid · Repository: github.com/muhammadkaif654/qualifypath-kg")
