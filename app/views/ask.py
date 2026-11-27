"""Ask: KG-grounded question answering with evidence, reasoning paths and an optional LLM-only baseline."""
import time

import pandas as pd
import streamlit as st

import ui
from qualifypath import llm, qa

ui.style()
kg = ui.kg()
rt = ui.retriever()
ui.sidebar(kg)

ui.hero("Ask the knowledge graph",
        "Answers are generated only from facts retrieved from the IPL 2026 knowledge graph — every claim cites its evidence.",
        ["Your question", "Entity linking", "SPARQL + multi-hop retrieval", "Numbered facts", "LLM", "Answer + evidence"])
ui.metrics([("Teams", "10"), ("Completed matches", "39"), ("Scheduled fixtures", "31"),
            ("Explicit triples", f"{len(kg.explicit):,}"), ("Inferred + rule triples", f"{len(kg.full) - len(kg.explicit):,}"),
            ("LLM", llm.MODEL.split("/")[-1])])
st.write("")

EXAMPLES = [
    "Can Lucknow Super Giants still qualify for the top 4?",
    "Which fixtures does Rajasthan Royals still have to play?",
    "Which teams has RR beaten and at which venues?",
    "If KKR lose their last match, which teams are certain to finish above them?",
    "Which teams hold the top 4 places and how is the SRH v RR tie decided?",
    "Who is the top run scorer for Rajasthan Royals?",
]
params = st.query_params
picked = st.pills("Try an example", EXAMPLES, key="example")
with st.form("ask", border=False):
    c1, c2, c3 = st.columns([6, 1.4, 1])
    question = c1.text_input("Question", value=picked or params.get("q", ""), label_visibility="collapsed",
                             placeholder="e.g. Can Lucknow Super Giants still qualify for the top 4?")
    compare = c2.toggle("Compare LLM-only", value=params.get("compare") == "1")
    submitted = c3.form_submit_button("Ask  ➜", type="primary", use_container_width=True)

if not llm.has_key():
    st.error("GROQ_API_KEY is not set. Copy `.env.example` to `.env`, add your Groq key and restart the app.")
    st.stop()

auto = params.get("q") and question == params.get("q") and "last" not in st.session_state
if (submitted or auto or (picked and st.session_state.get("last_q") != picked)) and question:
    with st.status("Answering from the knowledge graph…", expanded=True) as status:
        t0 = time.time()
        st.write("🔎 Linking entities and detecting intent…")
        ans = qa.ask_grounded(question)
        r = ans.retrieval
        st.write(f"📚 Retrieved **{len(r.facts)} facts** and **{len(r.results)} multi-hop reasoning result(s)**")
        st.write(f"🤖 {'Skipped the LLM: nothing in the graph matched' if not r.facts else f'LLM answered in {ans.seconds:.1f}s'}")
        only = None
        if compare:
            st.write("⚖️ Asking the same LLM without the graph…")
            only = qa.ask_llm_only(question)
        status.update(label=f"Done in {time.time() - t0:.1f}s", state="complete", expanded=False)
    st.session_state.last = (question, ans, only)
    st.session_state.last_q = question

if "last" not in st.session_state:
    st.info("Ask a question above, or pick an example. Try one the graph cannot answer to see how the app refuses to guess.")
    st.stop()

question, ans, only = st.session_state.last
r = ans.retrieval
cols = st.columns(2) if only else [st.container()]
with cols[0]:
    cls = "insufficient" if ans.insufficient else "answer"
    title = "⚠️ Insufficient graph evidence" if ans.insufficient else "✅ KG-grounded answer"
    st.markdown(f"<div class='qp-card {cls}'><h4>{title}</h4>"
                f"<div class='qp-muted'>{ui.badge('generated')} Q: {question}</div></div>", unsafe_allow_html=True)
    st.markdown(ui.cite(ans.answer), unsafe_allow_html=True)
    if ans.warning:
        st.error(ans.warning)
    chips = [f"<span class='qp-chip'>👥 {kg.label(t)}</span>" for t in r.teams] + \
            [f"<span class='qp-chip'>🏟️ {kg.full_name(v)}</span>" for v in r.venues] + \
            [f"<span class='qp-chip'>#️⃣ match {m}</span>" for m in r.matches] + \
            [f"<span class='qp-chip'>🎯 {i}</span>" for i in r.intents]
    st.markdown(" ".join(chips) or "<span class='qp-muted'>No entities or intents recognised</span>",
                unsafe_allow_html=True)
if only:
    with cols[1]:
        st.markdown(f"<div class='qp-card baseline'><h4>🧠 LLM only (no graph)</h4>"
                    f"<div class='qp-muted'>Same model and settings · no retrieved facts · no evidence</div></div>",
                    unsafe_allow_html=True)
        st.markdown(only.answer)

if ans.cited:
    st.markdown("#### 📎 Supporting evidence cited by the answer")
    st.markdown("".join(ui.fact_card(f, True) for f in ans.cited), unsafe_allow_html=True)

tab_graph, tab_ctx, tab_split, tab_meta = st.tabs(
    ["🕸️ Reasoning graph", "📚 Retrieved context", "🧩 Explicit · inferred · generated", "⚙️ Pipeline details"])
with tab_graph:
    paths = [p for res in r.results for p in res.paths]
    if paths:
        st.caption("Entities and values (amber) on the multi-hop paths; edge colour = provenance "
                   "(green explicit · blue OWL-inferred · purple rule-derived).")
        st.graphviz_chart(ui.path_graph(kg, paths), use_container_width=False)
        for res in r.results:
            with st.expander(("🧪 " if res.scenario else "🧭 ") + res.question + (" — scenario" if res.scenario else "")):
                for s in res.steps:
                    st.markdown(f"- {s}")
                for p in res.paths[:10]:
                    st.markdown(" ⟶ ".join(f"`{h.text(kg)}`" for h in p))
    else:
        st.info("This answer needed no multi-hop reasoning; it comes from direct SPARQL retrieval.")
with tab_ctx:
    if r.facts:
        kinds = sorted({f.kind for f in r.facts})
        sel = st.segmented_control("Filter by evidence type", kinds, selection_mode="multi", default=kinds)
        cited_ids = {f.id for f in ans.cited}
        st.dataframe(pd.DataFrame([{"ID": f.id, "Cited": "✔" if f.id in cited_ids else "", "Type": f.kind,
                                    "Source": f.source, "Fact": f.text} for f in r.facts if f.kind in (sel or [])]),
                     use_container_width=True, hide_index=True,
                     column_config={"Fact": st.column_config.TextColumn(width="large")})
    else:
        st.info("Nothing in the graph matched this question, so the LLM was not called.")
with tab_split:
    groups = [("Explicit knowledge — stored in the graph", ["explicit"]),
              ("Inferred knowledge — OWL 2 RL reasoning and rules R1–R7", ["inferred (OWL 2 RL)", "rule-derived"]),
              ("Multi-hop reasoning paths", ["reasoning path"]),
              ("Hypothetical scenarios — not facts", ["scenario"])]
    cited_ids = {f.id for f in ans.cited}
    for title, kinds in groups:
        items = [f for f in r.facts if f.kind in kinds]
        if items:
            st.markdown(f"**{title}** ({len(items)})")
            st.markdown("".join(ui.fact_card(f, f.id in cited_ids) for f in items[:12]), unsafe_allow_html=True)
    st.markdown("**Generated text — the LLM's answer**")
    st.markdown(f"<div class='qp-fact'>{ui.badge('generated')}{ui.cite(ans.answer)}</div>", unsafe_allow_html=True)
with tab_meta:
    st.json({"model": llm.MODEL, "temperature": llm.TEMPERATURE, "max_tokens": llm.MAX_TOKENS,
             "reasoning_effort": llm.REASONING_EFFORT, "teams": [kg.label(t) for t in r.teams],
             "venues": [kg.full_name(v) for v in r.venues], "matches": r.matches, "intents": r.intents,
             "facts_retrieved": len(r.facts), "facts_cited": [f.id for f in ans.cited],
             "llm_called": bool(r.facts), "llm_seconds": round(ans.seconds, 2)})
    st.caption("System prompt: prompts/grounded_system.txt · LLM-only prompt: prompts/llm_only_system.txt")
