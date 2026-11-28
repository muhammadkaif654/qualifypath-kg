"""Overview: tournament snapshot, leaders, qualification race and latest results — all read from the graph."""
import plotly.graph_objects as go
import streamlit as st

import data
import ui

ui.style()
kg = ui.kg()
ui.sidebar(kg)
df, ms, rl = data.standings(), data.matches(), data.rules()

ui.hero("Tournament overview",
        f"IPL 2026 league stage after match {rl['cutoff']}. Standings, qualification status and every number below "
        "are derived from the knowledge graph by OWL 2 RL reasoning and SPARQL rules R1–R7.",
        eyebrow="IPL 2026 · Snapshot after match 39")

done = [m for m in ms if m["kind"] != "scheduled"]
left = [m for m in ms if m["kind"] == "scheduled"]
counts = df.Status.value_counts()
ui.stats([("Matches played", str(len(done)), ""), ("Fixtures left", str(len(left)), "c"),
          ("Qualified", str(counts.get("qualified", 0)), "g"), ("In contention", str(counts.get("in contention", 0)), "a"),
          ("Eliminated", str(counts.get("eliminated", 0)), ""), ("Graph triples", f"{len(kg.full):,}", "c")])

lead, fourth = df.iloc[0], df.iloc[rl["places"] - 1]
best_nrr = df.sort_values("NRR", ascending=False).iloc[0]
c1, c2, c3 = st.columns(3)
for col, head, t, line in [
    (c1, "Table leader", lead.Team, f"{lead.Pts} pts · {lead.W}-{lead.L}-{lead.NR} · NRR {lead.NRR:+.3f}"),
    (c2, f"Holding the last spot (#{rl['places']})", fourth.Team, f"{fourth.Pts} pts · NRR {fourth.NRR:+.3f}"),
    (c3, "Best net run rate", best_nrr.Team, f"NRR {best_nrr.NRR:+.3f} · {best_nrr.Pts} pts"),
]:
    col.markdown(f"<div class='qp-panel qp-fade'><div class='qp-muted' style='text-transform:uppercase;"
                 f"letter-spacing:.08em;font-size:.7rem'>{head}</div><div style='display:flex;align-items:center;"
                 f"gap:12px;margin-top:8px'>{ui.team_crest(t, 46)}<div><div style='font-weight:800;font-size:1.05rem'>"
                 f"{ui.TEAMS[t][0]}</div><div class='qp-muted'>{line}</div></div></div>"
                 f"<div style='margin-top:10px'>{data.form_html(t)} <span class='qp-muted'>last 5</span></div></div>",
                 unsafe_allow_html=True)

left_col, right_col = st.columns([1.25, 1])
with left_col:
    ui.title("Qualification race", "points now vs maximum still reachable")
    colours = [ui.TEAMS[t][2] if t in ("GT", "SRH") else ui.TEAMS[t][1] for t in df.Team]
    fig = go.Figure()
    fig.add_bar(y=df.Team, x=df.Pts, name="Points now", orientation="h", marker_color=colours,
                hovertemplate="%{y}: %{x} pts<extra></extra>")
    fig.add_bar(y=df.Team, x=df.Max - df.Pts, name="Still reachable", orientation="h",
                marker=dict(color="rgba(148,163,184,.16)", line=dict(color=colours, width=1.4)),
                customdata=df.Max, hovertemplate="%{y}: up to %{customdata} pts<extra></extra>")
    fig.add_vline(x=int(fourth.Pts), line_dash="dot", line_color=ui.GREEN,
                  annotation_text=f"#{rl['places']} now: {fourth.Pts}", annotation_font_color=ui.GREEN)
    fig.update_layout(barmode="stack", height=430, margin=dict(l=6, r=6, t=26, b=6), yaxis=dict(autorange="reversed"),
                      legend=dict(orientation="h", y=-0.1), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(16,26,42,.7)", font=dict(family="Inter"), xaxis_title="points")
    st.plotly_chart(fig, use_container_width=True)
with right_col:
    ui.title("Top of the table", f"top {rl['places']} qualify for the playoffs")
    rows = "".join(
        f"<tr class='{'qz' if r.Pos <= rl['places'] else ''} {'cut' if r.Pos == rl['places'] else ''}'>"
        f"<td class='qp-pos'>{r.Pos}</td><td>{ui.team_label(r.Team, 24, full=False)}</td><td><b>{r.Pts}</b></td>"
        f"<td>{r.NRR:+.3f}</td><td>{ui.status_pill(r.Status)}</td></tr>" for r in df.head(6).itertuples())
    st.markdown(f"<div class='qp-panel'><table class='qp-table'><thead><tr><th>#</th><th>Team</th><th>Pts</th>"
                f"<th>NRR</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></div>", unsafe_allow_html=True)
    st.page_link("views/points.py", label="Full points table", icon=":material/arrow_forward:")

a, b = st.columns(2)
with a:
    ui.title("Latest results")
    for m in done[-3:][::-1]:
        st.markdown(data.match_card(m), unsafe_allow_html=True)
with b:
    ui.title("Next fixtures")
    for m in left[:3]:
        st.markdown(data.match_card(m), unsafe_allow_html=True)
st.page_link("views/matches.py", label="All matches in the Match Center", icon=":material/arrow_forward:")
st.caption("Status uses rules R4–R6 on points only, so it is conservative: no team is marked qualified or eliminated "
           "until it is mathematically certain.")
