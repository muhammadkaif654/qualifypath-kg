"""Knowledge graph explorer: league table from rules R1-R7, qualification race and team neighbourhoods."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from qualifypath.kg import QP, TEAM

ui.style()
kg = ui.kg()
R = ui.reasoner()
ui.sidebar(kg)

ui.hero("Knowledge graph explorer",
        "The standings, qualification status and team neighbourhoods are all read from the graph — "
        "standings are derived by SPARQL rules R1–R7, never stored.",
        ["Stored results", "OWL 2 RL", "Rules R1–R3 points/NRR", "R4–R6 status", "R7 position"])

rows = kg.query("""SELECT ?team ?name ?pos ?pts ?w ?l ?nr ?nrr ?mx ?status WHERE {
  ?se qp:standingOf ?t ; qp:position ?pos ; qp:points ?pts ; qp:won ?w ; qp:lost ?l ; qp:noResult ?nr ;
      qp:netRunRate ?nrr ; qp:maxReachablePoints ?mx ; a ?c .
  ?c rdfs:subClassOf qp:StandingEntry ; rdfs:label ?status . FILTER(?c != qp:StandingEntry)
  ?t qp:shortName ?team ; rdfs:label ?name } ORDER BY ?pos""")
table = pd.DataFrame([{"Pos": int(r.pos), "Team": str(r.team), "Name": str(r.name), "Pts": int(r.pts),
                       "W": int(r.w), "L": int(r.l), "NR": int(r.nr), "NRR": float(r.nrr),
                       "Max reachable": int(r.mx), "Status (R4–R6)": str(r.status).replace(" standing", "")}
                      for r in rows])

left, right = st.columns([1.15, 1])
with left:
    st.markdown("#### League table after match 39")
    st.caption("Ranked by points, then most wins, then net run rate (IPL rule 16.10.2). Top 4 qualify.")
    st.dataframe(table.style.apply(lambda r: ["background-color:#eef2ff" if r.Pos <= 4 else "" for _ in r], axis=1)
                 .format({"NRR": "{:+.3f}"}), hide_index=True, use_container_width=True, height=400)
with right:
    st.markdown("#### Qualification race")
    fig = go.Figure()
    fig.add_bar(y=table.Team, x=table.Pts, name="Points now", orientation="h", marker_color="#4f46e5")
    fig.add_bar(y=table.Team, x=table["Max reachable"] - table.Pts, name="Still reachable", orientation="h",
                marker_color="#c7d2fe")
    fourth = int(table.Pts.iloc[3])
    fig.add_vline(x=fourth, line_dash="dash", line_color="#dc2626",
                  annotation_text=f"4th place now: {fourth}", annotation_position="top")
    fig.update_layout(barmode="stack", height=400, margin=dict(l=10, r=10, t=30, b=10),
                      yaxis=dict(autorange="reversed"), legend=dict(orientation="h", y=-0.12),
                      plot_bgcolor="white", xaxis_title="points")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("#### Team neighbourhood")
teams = [kg.label(t) for t in kg.teams()]
team = st.segmented_control("Team", teams, default=st.query_params.get("team", "RR"))
if team:
    T = TEAM[team]
    row = table[table.Team == team].iloc[0]
    ui.metrics([("Position", str(row.Pos)), ("Points", str(row.Pts)), ("Record", f"{row.W}-{row.L}-{row.NR}"),
                ("NRR", f"{row.NRR:+.3f}"), ("Max reachable", str(row["Max reachable"])),
                ("Status", row["Status (R4–R6)"])])
    st.write("")
    beaten, fixtures, venues = R.teams_beaten(T), R.remaining_fixtures(T), R.venues_played(T)
    c1, c2 = st.columns([1, 1.4])
    with c1:
        st.markdown("**Results**")
        g = kg.full
        res_rows = []
        for m in sorted(g.objects(T, QP.participatesIn), key=kg.match_number):
            n = kg.match_number(m)
            if (m, QP.hasWinner, None) in g:
                won = (m, QP.hasWinner, T) in g
                opp = kg.label(g.value(m, QP.hasLoser if won else QP.hasWinner))
                res_rows.append({"Match": n, "Opponent": opp, "Result": "Won" if won else "Lost"})
            elif (m, QP.scheduledAt, None) in g:
                opp = next(kg.label(t) for t in g.objects(m, QP.hasParticipant) if t != T)
                res_rows.append({"Match": n, "Opponent": opp, "Result": "Scheduled"})
            else:
                opp = next(kg.label(t) for t in g.objects(m, QP.hasParticipant) if t != T)
                res_rows.append({"Match": n, "Opponent": opp, "Result": "No result"})
        st.dataframe(pd.DataFrame(res_rows), hide_index=True, use_container_width=True, height=420)
    with c2:
        st.markdown("**Neighbourhood graph** — team → matches → opponent and city")
        colour = {"Won": "#059669", "Lost": "#dc2626", "Scheduled": "#94a3b8", "No result": "#d97706"}
        dot = ['digraph G { rankdir=LR; bgcolor="transparent"; nodesep=0.12; ranksep=0.9;',
               'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#cbd5e1", '
               'fillcolor="#f8fafc"]; edge [color="#94a3b8", arrowsize=0.6];',
               f'T [label="{team}", fillcolor="#4f46e5", fontcolor="white", color="#4f46e5", fontsize=16, shape=circle];']
        opps, cities = set(), set()
        for rr in res_rows:
            m = f'M{rr["Match"]}'
            mnode = next(mm for mm in g.objects(T, QP.participatesIn) if kg.match_number(mm) == rr["Match"])
            v = g.value(mnode, QP.playedAt) or g.value(mnode, QP.scheduledAt)
            city = kg.label(g.value(v, QP.locatedIn))
            dot.append(f'{m} [label="Match {rr["Match"]}\\n{rr["Result"]}", fillcolor="{colour[rr["Result"]]}", '
                       f'fontcolor="white", color="{colour[rr["Result"]]}"];')
            dot.append(f'T -> {m} [label="participatesIn", fontsize=8, fontcolor="#2563eb", color="#2563eb"];')
            opps.add(rr["Opponent"])
            cities.add(city)
            dot.append(f'{m} -> "o_{rr["Opponent"]}"; {m} -> "c_{city}" [style=dashed];')
        for o in opps:
            dot.append(f'"o_{o}" [label="{o}", fillcolor="#e0e7ff", color="#6366f1"];')
        for c in cities:
            dot.append(f'"c_{c}" [label="📍 {c}", fillcolor="#fef3c7", color="#d97706"];')
        dot.append("}")
        st.graphviz_chart("\n".join(dot), use_container_width=True)
        st.caption("Green = won · red = lost · grey = scheduled · solid arrow → opponent · dashed arrow → city. "
                   "participatesIn is inferred (inverse of hasParticipant / sub-properties hasWinner, hasLoser).")
