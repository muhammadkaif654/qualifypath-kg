"""Qualification Predictor: what each team needs, from the multi-hop reasoner (CQ4-CQ8). Mathematical, not probabilistic."""
import streamlit as st

import data
import ui
from qualifypath.kg import TEAM

ui.style()
kg = ui.kg()
R = ui.reasoner()
ui.sidebar(kg)
df, rl = data.standings(), data.rules()

ui.hero("Qualification predictor",
        "Exactly how many wins each team needs — worked out by multi-hop reasoning over standings, remaining fixtures "
        "and the season's qualification rule. It is mathematical certainty, not a probability model.",
        ["Team", "standingOf → points, max", "participatesIn → fixtures", "hasQualificationRule → places",
         "Wins needed"])

teams = list(df.Team)
default = st.query_params.get("team", "LSG")
team = st.selectbox("Team", teams, index=teams.index(default) if default in teams else 0,
                    format_func=lambda t: f"{t} · {ui.TEAMS[t][0]}", label_visibility="collapsed")
st.query_params["team"] = team
q = R.qualification(TEAM[team])
it = q.items
row = df[df.Team == team].iloc[0]

st.markdown(f"<div class='qp-panel qp-fade' style='display:flex;align-items:center;gap:16px;flex-wrap:wrap'>"
            f"{ui.team_crest(team, 64)}<div style='flex:1'><div style='font-size:1.35rem;font-weight:800'>"
            f"{ui.TEAMS[team][0]}</div><div class='qp-muted'>#{row.Pos} · {row.W}-{row.L}-{row.NR} · NRR "
            f"{row.NRR:+.3f} · form {data.form_html(team)}</div></div>{ui.status_pill(it['status'])}</div>",
            unsafe_allow_html=True)
st.write("")
safe, alive, rem = it["safe_wins"], it["alive_wins"], it["remaining"]
ui.stats([("Points", str(it["points"]), ""), ("Matches left", str(rem), "c"), ("Max reachable", str(it["max"]), ""),
          ("Wins to stay alive", "—" if alive is None else str(alive), "a"),
          ("Wins to guarantee top 4", "none" if safe is None else str(safe), "g")])

ui.title("Wins ladder", f"final points for every number of wins from the {rem} remaining matches")
rungs = []
for w in range(rem + 1):
    if alive is None or w < alive:
        cls, note = "e", "eliminated"
    elif safe is not None and w >= safe:
        cls, note = "q", "guaranteed"
    else:
        cls, note = "c", "depends on others"
    rungs.append(f"<div class='qp-rung {cls}'><div class='w'>{w} W</div><div class='p'>{it['points'] + w * rl['win']} pts"
                 f"</div><div class='p'>{note}</div></div>")
st.markdown(f"<div class='qp-ladder qp-fade'>{''.join(rungs)}</div>", unsafe_allow_html=True)
st.caption("Red: other teams already have more points than this total, so it cannot be enough. Green: too few teams "
           "can still reach this total, so it is enough whatever else happens. Amber: depends on other results, "
           "head-to-heads and net run rate.")

c1, c2 = st.columns([1.1, 1])
with c1:
    ui.title("Reasoning chain", "multi-hop, no LLM")
    for i, s in enumerate(q.steps, 1):
        st.markdown(f"<div class='qp-fact'><span class='id'>{i}</span>{s}</div>", unsafe_allow_html=True)
    if it["out_of_reach"]:
        st.markdown("Already out of reach on points: " + " ".join(ui.team_crest(t, 24) for t in it["out_of_reach"]),
                    unsafe_allow_html=True)
with c2:
    ui.title("Remaining fixtures", "direct rivals still in contention are highlighted")
    rivals = {o: gap for _, o, _, gap in R.rivals(TEAM[team]).items}
    fx = R.remaining_fixtures(TEAM[team]).items
    for n, opp, date, city in fx:
        tag = (f"<span class='qp-pill c'>rival · gap {rivals[opp]} pts</span>" if opp in rivals else "")
        st.markdown(f"<div class='qp-fact' style='display:flex;align-items:center;gap:10px'>"
                    f"<span class='qp-muted' style='width:58px'>M{n}</span>{ui.team_crest(opp, 26)}"
                    f"<span style='flex:1'><b>v {opp}</b> <span class='qp-muted'>· {date} · {city}</span></span>{tag}</div>",
                    unsafe_allow_html=True)
    if not fx:
        st.caption("No fixtures left.")

with st.expander("Graph path behind this answer"):
    st.graphviz_chart(ui.path_graph(kg, q.paths), use_container_width=False)
    st.caption("Edge colour = provenance: green stored · cyan OWL-inferred · purple rule-derived.")
st.page_link("views/scenario.py", label="Try outcomes in the Scenario Explorer", icon=":material/tune:")
