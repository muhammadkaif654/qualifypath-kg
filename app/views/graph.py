"""Graph Explorer: interactive view of the knowledge graph (zoom, pan, click a node to inspect its triples)."""
import html

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from rdflib import RDF, Literal, URIRef

import ui
from qualifypath.kg import QP, TEAM

ui.style()
kg = ui.kg()
ui.sidebar(kg)
g = kg.full

ui.hero("Knowledge graph explorer",
        "Explore the instance graph: teams, matches, venues, cities and the rule-derived standing entries. Scroll to "
        "zoom, drag to pan and click any node to see every triple about it, labelled stored, inferred or rule-derived.",
        ["Teams", "participatesIn", "Matches", "playedAt / scheduledAt", "Venues", "locatedIn", "Cities"])

TYPES = {"Team": ui.GREEN, "Completed match": ui.CYAN, "Scheduled match": "#64748B", "No-result match": ui.AMBER,
         "Venue": ui.LIME, "City": "#F472B6", "Standing entry": "#A78BFA"}
EDGES = [QP.participatesIn, QP.playedAt, QP.scheduledAt, QP.locatedIn, QP.homeVenue, QP.standingOf]


def kind(n):
    if (n, RDF.type, QP.Team) in g:
        return "Team"
    if (n, RDF.type, QP.ScheduledMatch) in g:
        return "Scheduled match"
    if (n, RDF.type, QP.NoResultMatch) in g:
        return "No-result match"
    if (n, RDF.type, QP.CompletedMatch) in g:
        return "Completed match"
    if (n, RDF.type, QP.Venue) in g:
        return "Venue"
    if (n, RDF.type, QP.City) in g:
        return "City"
    if (n, RDF.type, QP.StandingEntry) in g:
        return "Standing entry"
    return None


teams = list(ui.TEAMS)
c1, c2, c3 = st.columns([1.2, 1.6, 1.2])
scope = c1.segmented_control("Scope", ["One team", "Whole league"], default="One team", label_visibility="collapsed")
focus = c2.selectbox("Team", teams, index=teams.index(st.query_params.get("team", "RR"))
                     if st.query_params.get("team", "RR") in teams else 0,
                     format_func=lambda t: f"{t} · {ui.TEAMS[t][0]}", label_visibility="collapsed",
                     disabled=scope == "Whole league")
c3.caption("Filter node types below · click a legend item to hide it")
shown = st.pills("Node types", list(TYPES), selection_mode="multi", default=list(TYPES), label_visibility="collapsed")


@st.cache_data(show_spinner=False)
def build(scope, focus, shown):
    G = nx.Graph()
    edges = []
    for p in EDGES:
        for s, o in g.subject_objects(p):
            ks, ko = kind(s), kind(o)
            if ks in shown and ko in shown:
                edges.append((s, o, str(p).rsplit("#", 1)[-1]))
    if scope == "One team":
        T = TEAM[focus]
        ms = set(g.objects(T, QP.participatesIn))
        keep = {T} | ms | set(g.subjects(QP.standingOf, T)) | set(g.objects(T, QP.homeVenue))
        keep |= {o for m in ms for o in g.objects(m, QP.hasParticipant)}
        keep |= {v for m in ms for v in list(g.objects(m, QP.playedAt)) + list(g.objects(m, QP.scheduledAt))}
        keep |= {c for v in list(keep) for c in g.objects(v, QP.locatedIn)}
        edges = [e for e in edges if e[0] in keep and e[1] in keep
                 and not (e[2] == "participatesIn" and e[1] not in ms)]
    for s, o, p in edges:
        G.add_edge(str(s), str(o), p=p)
    pos = nx.spring_layout(G, seed=7, k=1.6 / max(len(G), 1) ** 0.5, iterations=120)
    nodes = [{"id": n, "x": float(xy[0]), "y": float(xy[1]), "kind": kind(URIRef(n)), "label": kg.label(URIRef(n)),
              "deg": G.degree(n)} for n, xy in pos.items()]
    lines = [(pos[a][0], pos[a][1], pos[b][0], pos[b][1]) for a, b in G.edges()]
    return nodes, lines


if not shown:
    st.info("Pick at least one node type.")
    st.stop()
nodes, lines = build(scope, focus, tuple(shown))
fig = go.Figure()
ex, ey = [], []
for x0, y0, x1, y1 in lines:
    ex += [x0, x1, None]
    ey += [y0, y1, None]
fig.add_scatter(x=ex, y=ey, mode="lines", line=dict(color="rgba(148,163,184,.22)", width=1), hoverinfo="skip",
                showlegend=False)
for k, colour in TYPES.items():
    pts = [n for n in nodes if n["kind"] == k]
    if not pts:
        continue
    big = k == "Team"
    fig.add_scatter(
        x=[n["x"] for n in pts], y=[n["y"] for n in pts], mode="markers+text" if big or k == "City" else "markers",
        name=f"{k} ({len(pts)})", text=[n["label"] for n in pts], textposition="top center",
        textfont=dict(color=ui.WHITE, size=12 if big else 10), customdata=[n["id"] for n in pts],
        marker=dict(size=[(26 if big else 9) + min(n["deg"], 14) * (0.4 if big else 0.5) for n in pts],
                    color=[ui.TEAMS[n["label"]][1] if big and n["label"] in ui.TEAMS else colour for n in pts],
                    line=dict(color=colour if big else "rgba(8,14,25,.9)", width=2.5 if big else 1)),
        hovertemplate="<b>%{text}</b><br>" + k + "<extra></extra>")
fig.update_layout(height=620, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)",
                  plot_bgcolor="rgba(16,26,42,.55)", clickmode="event+select",
                  xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"), font=dict(family="Inter"),
                  legend=dict(orientation="h", y=1.04, x=0, bgcolor="rgba(0,0,0,0)"))
ui.stats([("Nodes shown", str(len(nodes)), "c"), ("Edges shown", str(len(lines)), ""),
          ("Graph triples (all layers)", f"{len(g):,}", "g")])
event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points",
                        key=f"kg_{scope}_{focus}_{len(shown)}", config={"scrollZoom": True, "displaylogo": False})

picked = None
pts = (event or {}).get("selection", {}).get("points", []) if event else []
if pts and pts[0].get("customdata"):
    picked = pts[0]["customdata"]
ids = sorted((n["id"] for n in nodes), key=lambda i: (list(TYPES).index(next(n["kind"] for n in nodes if n["id"] == i)),
                                                      kg.label(URIRef(i))))
names = {n["id"]: f"{n['label']} · {n['kind']}" for n in nodes}
default_id = picked or str(TEAM[focus] if scope == "One team" else TEAM["RR"])
choice = st.selectbox("Inspect node", ids, index=ids.index(default_id) if default_id in ids else 0,
                      format_func=names.get, key=f"inspect_{picked}",
                      help="Click a node in the graph, or pick one here.")
picked = URIRef(choice)

ui.title(f"Node: {html.escape(kg.full_name(picked))}", kind(picked) or "")
rows = []
for p, o in g.predicate_objects(picked):
    if isinstance(o, URIRef) and str(o).startswith("http://www.w3.org/2002/07/owl#"):
        continue
    rows.append({"Direction": "→ out", "Predicate": kg.label(p), "Value": kg.label(o) if not isinstance(o, Literal)
                 else str(o), "Provenance": kg.provenance(picked, p, o)})
for s, p in g.subject_predicates(picked):
    rows.append({"Direction": "← in", "Predicate": kg.label(p), "Value": kg.label(s),
                 "Provenance": kg.provenance(s, p, picked)})
tri = pd.DataFrame(rows).drop_duplicates()
if len(tri):
    counts = tri.Provenance.value_counts()
    st.markdown(" ".join(f"{ui.badge(k)}"
                         f"<span class='qp-muted'>{v} &nbsp;</span>" for k, v in counts.items()), unsafe_allow_html=True)
    prov = st.segmented_control("Provenance", list(counts.index), selection_mode="multi", default=list(counts.index),
                                label_visibility="collapsed", key="prov_filter")
    st.dataframe(tri[tri.Provenance.isin(prov or [])].sort_values(["Provenance", "Direction", "Predicate"]),
                 hide_index=True, use_container_width=True, height=380)
st.caption("owl:sameAs / owl:Thing style reflexive inferences are hidden. Explicit = stored in the .ttl files; "
           "inferred = OWL 2 RL closure; rule-derived = SPARQL Update rules R1–R7.")
