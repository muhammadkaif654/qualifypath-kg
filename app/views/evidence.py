"""Evidence & Sources: provenance of every layer, the SPARQL competency queries (run live) and the rules R1-R7."""
import pandas as pd
import streamlit as st
from rdflib import Literal, URIRef

import ui

ui.style()
kg = ui.kg()
ui.sidebar(kg)
QDIR = ui.ROOT / "SPARQL_Queries"

ui.hero("Evidence & sources",
        "Where every answer comes from: the stored triples, what OWL 2 RL reasoning adds, what the SPARQL rules derive, "
        "and the competency queries you can run live against the graph.",
        ["Ontology + A-Box (.ttl)", "OWL 2 RL closure", "Rules R1–R7", "SPARQL queries"])

n_exp, n_owl, n_full = len(kg.explicit), len(kg.owl), len(kg.full)
ui.stats([("Explicit triples", f"{n_exp:,}", "g"), ("Inferred · OWL 2 RL", f"{n_owl - n_exp:,}", "c"),
          ("Rule-derived · R1–R7", f"{n_full - n_owl:,}", "a"), ("Total in the graph", f"{n_full:,}", "")])

t_q, t_rules, t_src = st.tabs(["SPARQL competency queries", "Rules R1–R7", "Data sources"])
with t_q:
    files = sorted(QDIR.glob("Q*.rq"))
    pick = st.selectbox("Query", files, format_func=lambda p: p.stem.replace("_", " "), label_visibility="collapsed")
    text = pick.read_text(encoding="utf-8")
    c1, c2 = st.columns([1, 1.25])
    with c1:
        st.code(text, language="sparql")
    with c2:
        try:
            rows = kg.query(text)
            df = pd.DataFrame([{str(k): (kg.label(v) if isinstance(v, URIRef) else
                                         (v.toPython() if isinstance(v, Literal) else v))
                                for k, v in r.asdict().items()} for r in rows])
            st.markdown(f"<span class='qp-pill q'>{len(df)} rows</span> <span class='qp-muted'>run live on the full "
                        f"graph (explicit + OWL 2 RL + rules)</span>", unsafe_allow_html=True)
            st.dataframe(df, hide_index=True, use_container_width=True, height=460)
        except Exception as e:  # show query errors instead of crashing the page
            st.error(f"Query failed: {e}")
with t_rules:
    for ru in sorted((QDIR / "rules").glob("*.ru")):
        with st.expander(ru.stem.replace("_", " "), expanded=ru.stem.startswith("R4")):
            st.code(ru.read_text(encoding="utf-8"), language="sparql")
    st.markdown("**Inference checks** — queries that only return results with reasoning switched on:")
    for f in sorted((QDIR / "inference").glob("*.rq")):
        with st.expander(f.stem.replace("_", " ")):
            st.code(f.read_text(encoding="utf-8"), language="sparql")
with t_src:
    st.markdown("""
| Layer | File | Role |
|---|---|---|
| Ontology (T-Box) | `Ontology/qualifypath.ttl` | 19 classes, 20 object and 26 datatype properties, property chains and restrictions |
| Instance data (A-Box) | `RDF_Knowledge_Graph/ipl2026_abox.ttl` | teams, venues, cities, 70 matches, 76 innings, season rules |
| Reasoning | owlrl `OWLRL_Semantics` (same profile as GraphDB OWL2-RL) | participatesIn, CompletedMatch, playedAtVenue … |
| Rules | `SPARQL_Queries/rules/*.ru` | standings, NRR, max points, status, position |
""")
    st.markdown("The tie-break order (points, then most wins, then net run rate) follows IPL playing condition "
                "16.10.2. The sources for the match data and rules are listed in the project report.")
