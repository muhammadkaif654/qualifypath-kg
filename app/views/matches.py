"""Match Center: every completed, no-result and scheduled match stored in the graph, with innings scores."""
import streamlit as st

import data
import ui

ui.style()
kg = ui.kg()
ui.sidebar(kg)
ms = data.matches()

ui.hero("Match Center",
        "All 70 league matches in the graph: results with both innings, the no-result and the rain-shortened match, "
        "and the fixtures still to play after match 39.", eyebrow="IPL 2026 · league stage")

teams = list(ui.TEAMS)
c1, c2, c3 = st.columns([1.6, 1.4, 1.2])
kind = c1.segmented_control("Matches", ["Results", "Fixtures", "All"], default="Results", label_visibility="collapsed")
team = c2.selectbox("Team", ["All teams"] + teams, label_visibility="collapsed",
                    format_func=lambda t: t if t == "All teams" else f"{t} · {ui.TEAMS[t][0]}")
venues = sorted({m["city"] for m in ms})
city = c3.selectbox("City", ["All cities"] + venues, label_visibility="collapsed")

sel = [m for m in ms
       if (kind in (None, "All") or (kind == "Results") == (m["kind"] != "scheduled"))
       and (team == "All teams" or team in (m["home"], m["away"]))
       and (city == "All cities" or m["city"] == city)]
if kind == "Results":
    sel = sel[::-1]  # newest first

if team != "All teams":
    w = sum(m["winner"] == team for m in sel)
    l = sum(m["loser"] == team for m in sel)
    nr = sum(m["kind"] == "no result" for m in sel)
    ui.stats([("Matches shown", str(len(sel)), ""), ("Won", str(w), "g"), ("Lost", str(l), ""),
              ("No result", str(nr), "a"), ("Fixtures left", str(sum(m["kind"] == "scheduled" for m in sel)), "c")])

if not sel:
    st.info("No matches for this filter.")
cols = st.columns(3)
for i, m in enumerate(sel):
    cols[i % 3].markdown(data.match_card(m), unsafe_allow_html=True)
st.caption("Scores are the stored innings (runs/wickets and overs faced). Margins are computed from the two innings. "
           "Player-level data is not part of this knowledge graph.")
