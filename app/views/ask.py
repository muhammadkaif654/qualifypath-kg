"""Ask AI: chat-style KG-grounded question answering. Each answer separates graph facts, derived results,
hypothetical scenarios and reasoning, cites its evidence, and can be compared with an LLM-only baseline."""
import time

import pandas as pd
import streamlit as st

import ui
from qualifypath import llm, qa

ui.style()
kg = ui.kg()
rt = ui.retriever()
ui.sidebar(kg)

ui.hero("Ask AI",
        "Ask about the IPL 2026 league stage. Answers are generated only from facts retrieved from the knowledge graph, "
        "and every claim cites its evidence. If the graph has nothing relevant, the assistant says so instead of guessing.",
        ["Question", "Entity linking", "SPARQL + multi-hop retrieval", "Numbered facts", "LLM", "Answer + evidence"])

EXAMPLES = [
    "Can Lucknow Super Giants still qualify for the top 4?",
    "Which fixtures does Rajasthan Royals still have to play?",
    "Which teams has RR beaten and at which venues?",
    "If KKR lose their last match, which teams are certain to finish above them?",
    "Which teams hold the top 4 places and how is the SRH v RR tie decided?",
    "Who is the top run scorer for Rajasthan Royals?",
]
GROUPS = [("Graph facts — stored in the knowledge graph", ["explicit"]),
          ("Derived results — OWL 2 RL inference and rules R1–R7", ["inferred (OWL 2 RL)", "rule-derived"]),
          ("Reasoning paths — multi-hop", ["reasoning path"]),
          ("Hypothetical scenarios — not facts", ["scenario"])]

params = st.query_params
if "chat" not in st.session_state:
    st.session_state.chat = []

c1, c2, c3 = st.columns([4, 1.3, 0.9])
with c1:
    picked = st.pills("Suggested questions", EXAMPLES, key="example", label_visibility="collapsed")
compare = c2.toggle("Compare with LLM-only", value=params.get("compare") == "1",
                    help="Also ask the same model with no graph access, to see the difference.")
if c3.button("Clear chat", use_container_width=True, disabled=not st.session_state.chat):
    st.session_state.chat = []
    st.rerun()

if not llm.has_key():
    st.error("GROQ_API_KEY is not set. Copy `.env.example` to `.env`, add your Groq key and restart the app.")
    st.stop()

typed = st.chat_input("Ask about standings, qualification, fixtures, results, venues…")
question = None
if typed:
    question = typed
elif picked and st.session_state.get("last_pick") != picked:
    question = picked
elif params.get("q") and not st.session_state.get("auto_done"):
    question = params.get("q")
    st.session_state.auto_done = True
st.session_state.last_pick = picked


def render_answer(question, ans, only, latest):
    r = ans.retrieval
    cited_ids = {f.id for f in ans.cited}
    cls = "insufficient" if ans.insufficient else "answer"
    head = "Insufficient graph evidence" if ans.insufficient else "KG-grounded answer"
    pills = (f"<span class='qp-pill {'c' if ans.insufficient else 'q'}'>{head}</span> "
             f"<span class='qp-muted'>{len(r.facts)} facts retrieved · {len(ans.cited)} cited · "
             f"{len(r.results)} multi-hop result(s) · {ans.seconds:.1f}s</span>")
    chips = [f"<span class='qp-chip'>{ui.team_crest(kg.label(t), 20)} {kg.full_name(t)}</span>" for t in r.teams] + \
            [f"<span class='qp-chip'>&nbsp;🏟️ {kg.full_name(v)}</span>" for v in r.venues] + \
            [f"<span class='qp-chip'>&nbsp;# match {m}</span>" for m in r.matches] + \
            [f"<span class='qp-chip'>&nbsp;🎯 {i}</span>" for i in r.intents]
    cols = st.columns(2) if only else [st.container()]
    with cols[0]:
        st.markdown(f"<div class='qp-card {cls}'>{pills}<div style='margin-top:6px'>{' '.join(chips)}</div></div>",
                    unsafe_allow_html=True)
        st.markdown(ui.cite(ans.answer), unsafe_allow_html=True)
        if ans.warning:
            st.error(ans.warning)
    if only:
        with cols[1]:
            st.markdown("<div class='qp-card baseline'><span class='qp-pill n'>LLM only · no graph</span> "
                        "<span class='qp-muted'>same model and settings · no retrieved facts · no evidence</span></div>",
                        unsafe_allow_html=True)
            st.markdown(only.answer)
    if not r.facts:
        st.caption("Nothing in the graph matched this question, so the LLM was not called.")
        return
    t_ev, t_reason, t_ctx, t_meta = st.tabs(["Evidence", "Reasoning chain", "All retrieved facts", "Pipeline"])
    with t_ev:
        for title, kinds in GROUPS:
            items = [f for f in r.facts if f.kind in kinds]
            if items:
                items.sort(key=lambda f: f.id not in cited_ids)
                n_cited = sum(f.id in cited_ids for f in items)
                st.markdown(f"**{title}** <span class='qp-muted'>· {len(items)} retrieved, {n_cited} cited</span>",
                            unsafe_allow_html=True)
                st.markdown("".join(ui.fact_card(f, f.id in cited_ids) for f in items[:10]), unsafe_allow_html=True)
        st.markdown("**Generated text — the LLM's answer**")
        st.markdown(f"<div class='qp-fact'>{ui.badge('generated')}{ui.cite(ans.answer)}</div>", unsafe_allow_html=True)
    with t_reason:
        paths = [p for res in r.results for p in res.paths]
        if paths:
            if latest:
                st.graphviz_chart(ui.path_graph(kg, paths), use_container_width=False)
                st.caption("Edge colour = provenance: green stored · cyan OWL-inferred · purple rule-derived; "
                           "amber ovals are values.")
            for res in r.results:
                st.markdown(f"**{'Scenario — ' if res.scenario else ''}{res.question}**")
                for i, s in enumerate(res.steps, 1):
                    st.markdown(f"<div class='qp-fact'><span class='id'>{i}</span>{s}</div>", unsafe_allow_html=True)
                for p in res.paths[:6]:
                    st.markdown(" ⟶ ".join(f"`{h.text(kg)}`" for h in p))
        else:
            st.info("This answer needed no multi-hop reasoning; it comes from direct SPARQL retrieval.")
    with t_ctx:
        st.dataframe(pd.DataFrame([{"ID": f.id, "Cited": "✔" if f.id in cited_ids else "", "Type": f.kind,
                                    "Source": f.source, "Fact": f.text} for f in r.facts]),
                     use_container_width=True, hide_index=True,
                     column_config={"Fact": st.column_config.TextColumn(width="large")})
    with t_meta:
        st.json({"model": llm.MODEL, "temperature": llm.TEMPERATURE, "max_tokens": llm.MAX_TOKENS,
                 "reasoning_effort": llm.REASONING_EFFORT, "teams": [kg.label(t) for t in r.teams],
                 "venues": [kg.full_name(v) for v in r.venues], "matches": r.matches, "intents": r.intents,
                 "facts_retrieved": len(r.facts), "facts_cited": [f.id for f in ans.cited],
                 "llm_called": bool(r.facts), "llm_seconds": round(ans.seconds, 2)})
        st.caption("System prompt: prompts/grounded_system.txt · LLM-only prompt: prompts/llm_only_system.txt")


if not st.session_state.chat and not question:
    with st.chat_message("assistant", avatar=str(ui.ROOT / "app" / "assets" / "favicon.png")):
        st.markdown("Hi! I answer questions about IPL 2026 using only the knowledge graph. Pick a suggested question or "
                    "type your own. Try one the graph can't answer, such as player stats, to see me refuse to guess.")

history = st.session_state.chat
for i, (q, ans, only) in enumerate(history):
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant", avatar=str(ui.ROOT / "app" / "assets" / "favicon.png")):
        render_answer(q, ans, only, latest=(i == len(history) - 1 and not question))

if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant", avatar=str(ui.ROOT / "app" / "assets" / "favicon.png")):
        with st.status("Answering from the knowledge graph…", expanded=True) as status:
            t0 = time.time()
            st.write("Linking entities and detecting intent…")
            ans = qa.ask_grounded(question)
            r = ans.retrieval
            st.write(f"Retrieved **{len(r.facts)} facts** and **{len(r.results)} multi-hop reasoning result(s)**")
            st.write("Skipped the LLM: nothing in the graph matched" if not r.facts
                     else f"LLM answered in {ans.seconds:.1f}s")
            only = None
            if compare:
                st.write("Asking the same LLM without the graph…")
                only = qa.ask_llm_only(question)
            status.update(label=f"Done in {time.time() - t0:.1f}s", state="complete", expanded=False)
        render_answer(question, ans, only, latest=True)
    history.append((question, ans, only))
