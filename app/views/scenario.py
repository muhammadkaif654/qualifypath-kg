"""Scenario Explorer: pick outcomes for remaining fixtures and recompute points and status. Hypothetical only."""
import streamlit as st

import data
import ui

ui.style()
kg = ui.kg()
ui.sidebar(kg)
ms, rl = data.matches(), data.rules()
fixtures = [m for m in ms if m["kind"] == "scheduled"]

ui.hero("Scenario explorer",
        "Choose results for the remaining fixtures and see the table recompute with the same points rule and the "
        "R4–R6 qualification logic. Everything on this page is a hypothetical scenario — nothing is written to the graph.",
        ["Pick outcomes", "Points rule", "R4–R6 status", "Rank: points › wins › current NRR"])
st.markdown(f"{ui.badge('scenario')}<span class='qp-muted'>Net run rate of unplayed matches is unknown, so ties are "
            f"ranked by the current NRR.</span>", unsafe_allow_html=True)


def preset(team=None):
    for m in fixtures:
        key = f"sc{m['no']}"
        if team is None:
            st.session_state[key] = None
        elif team in (m["home"], m["away"]):
            st.session_state[key] = team


c1, c2, c3 = st.columns([1.4, 1, 1])
fav = c1.selectbox("Team", list(ui.TEAMS), format_func=lambda t: f"{t} · {ui.TEAMS[t][0]}",
                   label_visibility="collapsed")
c2.button(f"{fav} wins every fixture", on_click=preset, args=(fav,), use_container_width=True)
c3.button("Reset all to open", on_click=preset, use_container_width=True)

left, right = st.columns([1, 1.15])
with left:
    ui.title("Remaining fixtures", f"{len(fixtures)} · leave a match unset to keep it open")
    with st.container(height=640, border=False):
        for m in fixtures:
            st.segmented_control(f"Match {m['no']} · {m['date']} · {m['city']}", [m["home"], m["away"], "NR"],
                                 key=f"sc{m['no']}", format_func=lambda o: "No result" if o == "NR" else o)
outcomes = {m["no"]: st.session_state.get(f"sc{m['no']}") for m in fixtures}
outcomes = {k: v for k, v in outcomes.items() if v}
sc = data.scenario(outcomes)

with right:
    ui.title("Projected table", f"{len(outcomes)} of {len(fixtures)} fixtures decided")
    body = ""
    for r in sc.itertuples():
        move = r.Was - r.Pos
        arrow = (f"<span style='color:{ui.GREEN}'>▲{move}</span>" if move > 0 else
                 f"<span style='color:{ui.RED}'>▼{-move}</span>" if move < 0 else "<span class='qp-muted'>–</span>")
        body += (f"<tr class='{'qz' if r.Pos <= rl['places'] else ''} {'cut' if r.Pos == rl['places'] else ''}'>"
                 f"<td class='qp-pos'>{r.Pos}</td><td>{arrow}</td><td>{ui.team_label(r.Team, 24, full=False)}</td>"
                 f"<td>{r.P}</td><td>{r.W}</td><td><b>{r.Pts}</b></td><td>{r.Left}</td><td>{r.Max}</td>"
                 f"<td>{ui.status_pill(r.Status)}</td></tr>")
    st.markdown(f"<div class='qp-panel'><table class='qp-table'><thead><tr><th>#</th><th></th><th>Team</th><th>P</th>"
                f"<th>W</th><th>Pts</th><th>Left</th><th>Max</th><th>Status</th></tr></thead><tbody>{body}</tbody>"
                f"</table></div>", unsafe_allow_html=True)
    changed = sc[sc.Status != data.standings().set_index("Team").loc[sc.Team, "Status"].values]
    if len(changed):
        st.markdown("**Status changes in this scenario:** " + " · ".join(
            f"{ui.team_crest(r.Team, 20)} {r.Team} → {r.Status}" for r in changed.itertuples()), unsafe_allow_html=True)
    else:
        st.caption("No team's status changes yet — decide more fixtures.")
