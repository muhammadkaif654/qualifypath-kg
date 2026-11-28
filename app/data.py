"""Read-only views over the knowledge graph for the UI (standings, matches, scenarios). No backend logic changes:
everything comes from the graph, the SPARQL rules R1-R7 and the multi-hop reasoner."""
from __future__ import annotations

import re

import pandas as pd
import streamlit as st
from rdflib import RDF, RDFS

import ui
from qualifypath.kg import QP, SEASON_ID, TEAM


def _overs(balls: int) -> str:
    return f"{balls // 6}" + (f".{balls % 6}" if balls % 6 else "")


@st.cache_data(show_spinner=False)
def standings() -> pd.DataFrame:
    rows = ui.kg().query("""SELECT ?team ?name ?pos ?pts ?w ?l ?nr ?nrr ?mx ?status WHERE {
      ?se qp:standingOf ?t ; qp:position ?pos ; qp:points ?pts ; qp:won ?w ; qp:lost ?l ; qp:noResult ?nr ;
          qp:netRunRate ?nrr ; qp:maxReachablePoints ?mx ; a ?c .
      ?c rdfs:subClassOf qp:StandingEntry ; rdfs:label ?status . FILTER(?c != qp:StandingEntry)
      ?t qp:shortName ?team ; rdfs:label ?name } ORDER BY ?pos""")
    df = pd.DataFrame([{"Pos": int(r.pos), "Team": str(r.team), "Name": str(r.name), "P": int(r.w) + int(r.l) + int(r.nr),
                        "W": int(r.w), "L": int(r.l), "NR": int(r.nr), "Pts": int(r.pts), "NRR": float(r.nrr),
                        "Max": int(r.mx), "Status": str(r.status).replace(" standing", "").replace("-", " ").lower()}
                       for r in rows])
    df["Left"] = (df.Max - df.Pts) // rules()["win"]
    return df


@st.cache_data(show_spinner=False)
def rules() -> dict:
    kg = ui.kg()
    return {"win": kg.season_rule(QP.pointsForWin), "nr": kg.season_rule(QP.pointsForNoResult),
            "loss": kg.season_rule(QP.pointsForLoss), "places": kg.season_rule(QP.qualifyingPlaces),
            "overs": int(kg.value(SEASON_ID, QP.oversQuota)), "cutoff": kg.season_rule(QP.cutoffMatchNumber)}


@st.cache_data(show_spinner=False)
def matches() -> list[dict]:
    kg = ui.kg()
    g = kg.full
    out = []
    for m in set(g.subjects(QP.matchNumber, None)):
        label = str(g.value(m, RDFS.label) or "")
        pair = re.search(r":\s*(\w+)\s+v\s+(\w+)", label)
        home, away = (pair.group(1), pair.group(2)) if pair else ("?", "?")
        if (m, RDF.type, QP.ScheduledMatch) in g:
            kind = "scheduled"
        elif (m, RDF.type, QP.NoResultMatch) in g:
            kind = "no result"
        else:
            kind = "completed"
        venue = g.value(m, QP.playedAt) or g.value(m, QP.scheduledAt)
        innings = []
        for inn in sorted(g.objects(m, QP.hasInnings), key=lambda i: int(g.value(i, QP.inningsNumber))):
            balls = int(g.value(inn, QP.ballsFaced))
            innings.append({"team": kg.label(g.value(inn, QP.battingTeam)), "runs": int(g.value(inn, QP.runs)),
                            "wkts": int(g.value(inn, QP.wicketsLost)), "overs": _overs(balls),
                            "all_out": str(g.value(inn, QP.allOut)).lower() == "true"})
        winner, loser = g.value(m, QP.hasWinner), g.value(m, QP.hasLoser)
        out.append({"no": kg.match_number(m), "date": str(g.value(m, QP.matchDate)), "home": home, "away": away,
                    "kind": kind, "venue": kg.full_name(venue) if venue else "", "city":
                    kg.label(g.value(venue, QP.locatedIn)) if venue else "", "innings": innings,
                    "winner": kg.label(winner) if winner else None, "loser": kg.label(loser) if loser else None,
                    "overs_per_side": int(g.value(m, QP.oversPerSide)) if g.value(m, QP.oversPerSide) else None,
                    "uri": str(m)})
    return sorted(out, key=lambda x: x["no"])


def margin(m: dict) -> str:
    """Result line derived from the two stored innings (runs / wickets margin)."""
    if m["kind"] == "no result":
        return "No result · 1 point each"
    if m["kind"] == "scheduled":
        return f"Scheduled · {m['date']}"
    inn = m["innings"]
    if len(inn) == 2:
        first, second = inn
        if second["team"] == m["winner"]:
            return f"{m['winner']} won by {10 - second['wkts']} wicket{'s' if 10 - second['wkts'] != 1 else ''}"
        return f"{m['winner']} won by {first['runs'] - second['runs']} runs"
    return f"{m['winner']} won"


def form(team: str, n: int = 5) -> list[str]:
    res = []
    for m in matches():
        if team in (m["home"], m["away"]) and m["kind"] != "scheduled":
            res.append("W" if m["winner"] == team else "L" if m["winner"] else "N")
    return res[-n:]


def form_html(team: str, n: int = 5) -> str:
    col = {"W": ui.GREEN, "L": ui.RED, "N": ui.AMBER}
    return "".join(f"<span title='{'Won' if r == 'W' else 'Lost' if r == 'L' else 'No result'}' "
                   f"style='display:inline-block;width:18px;height:18px;line-height:18px;border-radius:5px;"
                   f"margin-right:3px;font-size:.66rem;font-weight:800;text-align:center;color:#080E19;"
                   f"background:{col[r]}'>{r}</span>" for r in form(team, n))


def match_card(m: dict) -> str:
    def row(team):
        inn = next((i for i in m["innings"] if i["team"] == team), None)
        score = (f"{inn['runs']}/{inn['wkts']}" if not inn["all_out"] else f"{inn['runs']}") + \
                f" <span class='qp-muted'>({inn['overs']})</span>" if inn else "<span class='qp-muted'>—</span>"
        cls = "won" if m["winner"] == team else "lost" if m["winner"] else ""
        return (f"<div class='row {cls}'><span class='tm'>{ui.team_crest(team, 24)}{ui.TEAMS.get(team, (team,))[0]}"
                f"</span><span class='sc'>{score}</span></div>")
    res_cls = {"scheduled": "s", "no result": "n"}.get(m["kind"], "")
    note = f" · reduced to {m['overs_per_side']} overs a side" if m["overs_per_side"] else ""
    return (f"<div class='qp-match qp-fade'><div class='meta'><span>Match {m['no']} · {m['date']}</span>"
            f"<span>{m['venue']}, {m['city']}</span></div>{row(m['home'])}{row(m['away'])}"
            f"<div class='res {res_cls}'>{margin(m)}{note}</div></div>")


# ------------------------------------------------------------------ hypothetical scenarios
def scenario(outcomes: dict[int, str]) -> pd.DataFrame:
    """Recompute the table for chosen outcomes of scheduled fixtures (winner short name or 'NR').
    Ranking: points, then wins, then the CURRENT net run rate (unknown for unplayed matches).
    Status: the same R4-R6 logic on points, with every unchosen fixture still open."""
    rl = rules()
    df = standings().set_index("Team").copy()
    left = df.Left.copy()
    for m in matches():
        if m["kind"] != "scheduled" or m["no"] not in outcomes:
            continue
        pick = outcomes[m["no"]]
        for t in (m["home"], m["away"]):
            left[t] -= 1
        if pick == "NR":
            df.loc[[m["home"], m["away"]], "Pts"] += rl["nr"]
            df.loc[[m["home"], m["away"]], "NR"] += 1
        else:
            loser = m["away"] if pick == m["home"] else m["home"]
            df.loc[pick, "Pts"] += rl["win"]
            df.loc[pick, "W"] += 1
            df.loc[loser, "L"] += 1
    df["Left"] = left
    df["Max"] = df.Pts + df.Left * rl["win"]
    df["P"] = df.W + df.L + df.NR
    status = {}
    for t in df.index:
        out_of_reach = sum((df.Pts > df.loc[t, "Max"]) & (df.index != t))
        can_catch = sum((df.Max >= df.loc[t, "Pts"]) & (df.index != t))
        status[t] = ("eliminated" if out_of_reach >= rl["places"] else
                     "qualified" if can_catch < rl["places"] else "in contention")
    df["Status"] = pd.Series(status)
    df = df.reset_index().sort_values(["Pts", "W", "NRR"], ascending=False).reset_index(drop=True)
    df["Was"] = df.Pos
    df["Pos"] = range(1, len(df) + 1)
    return df


def team_uri(short: str):
    return TEAM[short]
