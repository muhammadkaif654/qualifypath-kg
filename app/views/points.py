"""Points table: standings derived by rules R1-R7 with qualification status, form and tie-break notes."""
import streamlit as st

import data
import ui

ui.style()
kg = ui.kg()
ui.sidebar(kg)
df, rl = data.standings(), data.rules()

ui.hero("Points table",
        "Never stored — every row is derived: R1–R3 compute points, net run rate and the maximum reachable points, "
        "R4–R6 classify qualification status and R7 ranks by points, then most wins, then net run rate (IPL 16.10.2).",
        ["Stored results", "OWL 2 RL", "R1–R3 points · NRR · max", "R4–R6 status", "R7 position"],
        eyebrow=f"IPL 2026 · after match {rl['cutoff']}")

c1, c2 = st.columns([3, 1.2])
with c2:
    view = st.segmented_control("Show", ["All teams", "Top 4", "Chasing pack"], default="All teams",
                                label_visibility="collapsed")
with c1:
    st.markdown(f"<span class='qp-pill q'>Qualified</span> <span class='qp-pill c'>In contention</span> "
                f"<span class='qp-pill e'>Eliminated</span> <span class='qp-muted'>&nbsp; Green bar = current top "
                f"{rl['places']} · dashed line = qualification cut</span>", unsafe_allow_html=True)

show = df if view in (None, "All teams") else df[df.Pos <= rl["places"]] if view == "Top 4" else df[df.Pos > rl["places"]]
head = "".join(f"<th class='{c}'>{h}</th>" for h, c in [
    ("#", ""), ("Team", ""), ("P", ""), ("W", ""), ("L", ""), ("NR", "hide-sm"), ("Pts", ""), ("NRR", ""),
    ("Left", "hide-sm"), ("Max", "hide-sm"), ("Form", "hide-sm"), ("Status", "")])
body = "".join(
    f"<tr class='{'qz' if r.Pos <= rl['places'] else ''} {'cut' if r.Pos == rl['places'] else ''}'>"
    f"<td class='qp-pos'>{r.Pos}</td><td>{ui.team_label(r.Team, 28)}</td><td>{r.P}</td><td>{r.W}</td><td>{r.L}</td>"
    f"<td class='hide-sm'>{r.NR}</td><td><b style='font-size:1.02rem'>{r.Pts}</b></td>"
    f"<td style='color:{ui.GREEN if r.NRR >= 0 else ui.RED}'>{r.NRR:+.3f}</td><td class='hide-sm'>{r.Left}</td>"
    f"<td class='hide-sm'>{r.Max}</td><td class='hide-sm'>{data.form_html(r.Team)}</td>"
    f"<td>{ui.status_pill(r.Status)}</td></tr>" for r in show.itertuples())
st.markdown(f"<div class='qp-panel qp-fade' style='overflow-x:auto'><table class='qp-table'><thead><tr>{head}</tr></thead>"
            f"<tbody>{body}</tbody></table></div>", unsafe_allow_html=True)

ui.title("Tie-breaks in the current table", "teams level on points")
ties = [g for _, g in df.groupby("Pts") if len(g) > 1]
if not ties:
    st.caption("No teams are level on points.")
for g in sorted(ties, key=lambda g: g.Pos.min()):
    g = g.sort_values("Pos")
    by_wins = g.W.nunique() > 1
    order = " ahead of ".join(f"**{t}**" for t in g.Team)
    reason = ("more wins" if by_wins else "higher net run rate (wins are equal)")
    detail = " · ".join(f"{r.Team}: {r.W} W, NRR {r.NRR:+.3f}" for r in g.itertuples())
    st.markdown(f"- {g.Pts.iloc[0]} points: {order}, on {reason}. <span class='qp-muted'>{detail}</span>",
                unsafe_allow_html=True)

with st.expander("How each column is derived from the graph"):
    st.markdown(f"""
- **P, W, L, NR** — counted from `qp:hasWinner`, `qp:hasLoser` and `qp:NoResultMatch` (rule R1); `participatesIn` and
  `CompletedMatch` are inferred by OWL 2 RL.
- **Pts** — W × {rl['win']} + NR × {rl['nr']} (season points rule).
- **NRR** — runs scored ÷ overs faced − runs conceded ÷ overs bowled, from the stored innings (rule R2; a team bowled
  out is charged the full quota).
- **Left / Max** — remaining scheduled fixtures, and points + left × {rl['win']} (rule R3).
- **Status** — R4 eliminated if {rl['places']}+ teams already have more points than this team can reach; R5 qualified
  if fewer than {rl['places']} teams can still reach its points; otherwise R6 in contention.
- **#** — R7: points, then most wins, then NRR.""")
