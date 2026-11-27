"""
QualifyPath-KG — build the IPL 2026 A-Box (instance data) from the Kaggle CSVs.

Usage (from the project folder):
    python RDF_Knowledge_Graph/build_kg.py

Inputs : Dataset/raw/matches.csv, deliveries.csv, venues.csv, points_table.csv
Outputs: RDF_Knowledge_Graph/ipl2026_abox.ttl          (the A-Box, Turtle)
         Dataset/processed/league_matches_clean.csv    (cleaned table, one row per league match)
         Results/validation_standings_vs_official.csv  (our standings vs the official table)

Requires: rdflib  (pip install rdflib)
"""
import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "Dataset" / "raw"

# --------------------------------------------------------------------------
# Season configuration (rules come from the IPL playing conditions)
# --------------------------------------------------------------------------
SEASON_ID = "IPL-2026"
SEASON_YEAR = 2026
LEAGUE_MATCHES = 70          # matches 71-74 are playoffs, outside the league-stage model
CUTOFF = 39                  # snapshot: matches.csv and points_table.csv stop after match 39
OVERS_QUOTA = 20
POINTS_WIN, POINTS_LOSS, POINTS_NO_RESULT = 2, 0, 1
QUALIFYING_PLACES = 4
# Applied in order when teams are level on points: IPL rulebook clause 16.10.2
# (16.10.2.1 most wins, 16.10.2.2 higher net run rate), as reported by CricTracker, 17 May 2024.
TIE_BREAKS = [(1, "Most wins"), (2, "Net run rate")]

TEAMS = {
    "CSK": "Chennai Super Kings",
    "DC": "Delhi Capitals",
    "GT": "Gujarat Titans",
    "KKR": "Kolkata Knight Riders",
    "LSG": "Lucknow Super Giants",
    "MI": "Mumbai Indians",
    "PBKS": "Punjab Kings",
    "RCB": "Royal Challengers Bengaluru",
    "RR": "Rajasthan Royals",
    "SRH": "Sunrisers Hyderabad",
}

# Canonical venues. The same ground is spelled up to three ways across the files,
# so each venue is recognised by a distinctive keyword (regex on the lower-cased name).
VENUES = [
    # (uri slug, official name, city, regex)
    ("narendra-modi-stadium", "Narendra Modi Stadium", "Ahmedabad", r"narendra modi"),
    ("wankhede-stadium", "Wankhede Stadium", "Mumbai", r"wankhede"),
    ("eden-gardens", "Eden Gardens", "Kolkata", r"eden gardens"),
    ("ma-chidambaram-stadium", "MA Chidambaram Stadium", "Chennai", r"chidambaram"),
    ("arun-jaitley-stadium", "Arun Jaitley Stadium", "New Delhi", r"jaitley"),
    ("maharaja-yadavindra-singh-stadium", "Maharaja Yadavindra Singh International Cricket Stadium",
     "Mullanpur", r"mullanpur|yadavindra|new pca"),
    ("ekana-cricket-stadium", "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium",
     "Lucknow", r"ekana"),
    ("rajiv-gandhi-international-stadium", "Rajiv Gandhi International Stadium", "Hyderabad",
     r"rajiv gandhi"),
    ("m-chinnaswamy-stadium", "M. Chinnaswamy Stadium", "Bengaluru", r"chinnaswamy"),
    ("barsapara-cricket-stadium", "Barsapara Cricket Stadium", "Guwahati", r"barsapara"),
    ("sawai-mansingh-stadium", "Sawai Mansingh Stadium", "Jaipur", r"sawai mansingh"),
    ("hpca-stadium", "Himachal Pradesh Cricket Association Stadium", "Dharamshala",
     r"hpca|himachal"),
    ("shaheed-veer-narayan-singh-stadium", "Shaheed Veer Narayan Singh International Stadium",
     "Raipur", r"narayan singh|raipur"),
]


def venue_key(raw_name):
    name = raw_name.lower()
    for slug, *_rest, pattern in VENUES:
        if re.search(pattern, name):
            return slug
    raise ValueError(f"Unknown venue: {raw_name!r}")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_date(text):
    text = text.strip().replace("Sept", "Sep")
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unknown date format: {text!r}")


def read_csv(name):
    with open(RAW / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------
# 1. Load and clean
# --------------------------------------------------------------------------
matches_csv = {int(r["match_id"]): r for r in read_csv("matches.csv")}
deliveries = read_csv("deliveries.csv")
venues_csv = read_csv("venues.csv")
official = read_csv("points_table.csv")

# Per match, from the ball-by-ball file: date, venue, batting order, legal balls per innings.
balls = defaultdict(lambda: {"date": None, "venue": None, "innings": {}})
for d in deliveries:
    n = int(d["match_no"])
    inn = int(d["innings"])
    if n > LEAGUE_MATCHES or inn > 2:          # skip playoffs and super-over innings
        continue
    b = balls[n]
    b["date"], b["venue"] = d["date"], d["venue"]
    i = b["innings"].setdefault(inn, {"bat": d["batting_team"], "bowl": d["bowling_team"], "legal": 0})
    if d["wide"] in ("0", "") and d["noballs"] in ("0", ""):
        i["legal"] += 1

cleaning_log = []
rows = []                                       # one cleaned row per league match
for n in range(1, LEAGUE_MATCHES + 1):
    b = balls[n]
    if n <= CUTOFF:
        m = matches_csv[n]
        date = parse_date(m["date"])
        venue = venue_key(m["venue"])
        teams = (m["team1"], m["team2"])
        row = {"match_number": n, "date": date.isoformat(), "venue": venue,
               "team1": teams[0], "team2": teams[1]}
        if m["match_result"] == "abandoned":
            row["status"] = "no_result"
        else:
            row["status"] = "decided"
            row["super_over"] = m["super_over_match"] == "Yes"
            first = b["innings"][1]["bat"]
            second = teams[1] if first == teams[0] else teams[0]
            # Cross-check batting order with the toss
            toss_bats_first = m["toss_winner"] if m["toss_decision"] == "Bat" else \
                (teams[1] if m["toss_winner"] == teams[0] else teams[0])
            if toss_bats_first != first:
                cleaning_log.append(f"match {n}: toss implies {toss_bats_first} batted first, "
                                    f"ball-by-ball says {first}; ball-by-ball used")
            r1, w1 = int(m["first_ings_score"]), int(m["first_ings_wkts"])
            r2, w2 = int(m["second_ings_score"]), int(m["second_ings_wkts"])
            # Winner from the scores; the match_winner column is only trusted for ties (super over).
            winner = first if r1 > r2 else second if r2 > r1 else m["match_winner"]
            if winner != m["match_winner"]:
                cleaning_log.append(f"match {n}: match_winner says {m['match_winner']} but scores "
                                    f"{first} {r1}/{w1} v {second} {r2}/{w2} give {winner}; scores used")
            row["winner"] = winner
            row["loser"] = second if winner == first else first
            quota = OVERS_QUOTA * 6
            # Rain-shortened match: first innings not all out but more than an over short.
            legal1 = b["innings"][1]["legal"]
            if w1 < 10 and legal1 <= quota - 6:
                quota = -(-legal1 // 6) * 6
                row["overs_per_side"] = quota // 6
                cleaning_log.append(f"match {n}: shortened to {quota // 6} overs a side "
                                    f"(first innings {legal1} legal balls, not all out)")
            # Balls faced (legal balls). First innings: full quota unless all out (then ball-by-ball count).
            b1 = quota if w1 < 10 else min(legal1, quota)
            # Second innings: quota minus balls left, when the chase ended early or the side was all out.
            left = int(m["balls_left"]) if m["balls_left"] else 0
            b2 = quota - left if (w2 == 10 or winner == second) else quota
            row.update({"inn1_team": first, "inn1_runs": r1, "inn1_wkts": w1, "inn1_balls": b1,
                        "inn2_team": second, "inn2_runs": r2, "inn2_wkts": w2, "inn2_balls": b2})
    else:
        inn1 = b["innings"][1]
        date = parse_date(b["date"])
        venue = venue_key(b["venue"])
        row = {"match_number": n, "date": date.isoformat(), "venue": venue,
               "team1": inn1["bat"], "team2": inn1["bowl"], "status": "scheduled"}
    rows.append(row)

# --------------------------------------------------------------------------
# 2. Build the A-Box
# --------------------------------------------------------------------------
BASE = "http://example.org/qualifypath/resource/"
QP = Namespace("http://example.org/qualifypath/ontology#")
NS = {k: Namespace(BASE + k + "/") for k in
      ("tournament", "season", "team", "venue", "city", "match", "innings", "rule")}

g = Graph()
g.bind("qp", QP)
for k, ns in NS.items():
    g.bind(k, ns)

tournament = NS["tournament"]["IPL"]
season = NS["season"][SEASON_ID]
g.add((tournament, RDF.type, QP.Tournament))
g.add((tournament, RDFS.label, Literal("Indian Premier League", lang="en")))
g.add((season, RDF.type, QP.Season))
g.add((season, RDFS.label, Literal("IPL 2026", lang="en")))
g.add((season, QP.ofTournament, tournament))
g.add((season, QP.seasonYear, Literal(SEASON_YEAR, datatype=XSD.integer)))
g.add((season, QP.cutoffMatchNumber, Literal(CUTOFF, datatype=XSD.integer)))
g.add((season, QP.oversQuota, Literal(OVERS_QUOTA, datatype=XSD.integer)))

pts = NS["rule"][f"{SEASON_ID}-points"]
g.add((pts, RDF.type, QP.PointsRule))
g.add((pts, RDFS.label, Literal("IPL 2026 points rule", lang="en")))
g.add((pts, QP.pointsForWin, Literal(POINTS_WIN, datatype=XSD.integer)))
g.add((pts, QP.pointsForLoss, Literal(POINTS_LOSS, datatype=XSD.integer)))
g.add((pts, QP.pointsForNoResult, Literal(POINTS_NO_RESULT, datatype=XSD.integer)))
g.add((season, QP.hasPointsRule, pts))

qual = NS["rule"][f"{SEASON_ID}-qualification"]
g.add((qual, RDF.type, QP.QualificationRule))
g.add((qual, RDFS.label, Literal("IPL 2026 qualification rule", lang="en")))
g.add((qual, QP.qualifyingPlaces, Literal(QUALIFYING_PLACES, datatype=XSD.integer)))
g.add((season, QP.hasQualificationRule, qual))

for rank, name in TIE_BREAKS:
    tb = NS["rule"][f"{SEASON_ID}-tiebreak-{rank}"]
    g.add((tb, RDF.type, QP.TieBreakCriterion))
    g.add((tb, QP.criterionName, Literal(name)))
    g.add((tb, QP.tieBreakRank, Literal(rank, datatype=XSD.integer)))
    g.add((season, QP.hasTieBreak, tb))

for short, full in TEAMS.items():
    t = NS["team"][short]
    g.add((t, RDF.type, QP.Team))
    g.add((t, RDFS.label, Literal(full, lang="en")))
    g.add((t, QP.shortName, Literal(short)))

for slug, name, city, _ in VENUES:
    v, c = NS["venue"][slug], NS["city"][slugify(city)]
    g.add((v, RDF.type, QP.Venue))
    g.add((v, RDFS.label, Literal(name, lang="en")))
    g.add((v, QP.locatedIn, c))
    g.add((c, RDF.type, QP.City))
    g.add((c, RDFS.label, Literal(city, lang="en")))

for v in venues_csv:                                  # home grounds (RR and PBKS have two)
    g.add((NS["team"][v["home_team"]], QP.homeVenue, NS["venue"][venue_key(v["venue_stadium"])]))

for row in rows:
    n = row["match_number"]
    mid = f"{SEASON_ID}-M{n:02d}"
    m = NS["match"][mid]
    g.add((m, RDFS.label, Literal(f"IPL 2026 match {n}: {row['team1']} v {row['team2']}", lang="en")))
    g.add((m, QP.matchNumber, Literal(n, datatype=XSD.integer)))
    g.add((m, QP.matchDate, Literal(row["date"], datatype=XSD.date)))
    g.add((m, QP.inSeason, season))
    venue_prop = QP.scheduledAt if row["status"] == "scheduled" else QP.playedAt
    g.add((m, venue_prop, NS["venue"][row["venue"]]))
    if row["status"] == "decided":
        # Only Match + winner/loser are stated. DecidedMatch, CompletedMatch and hasParticipant
        # are left for the reasoner to infer (constructs O1, O3, O4).
        g.add((m, RDF.type, QP.Match))
        g.add((m, QP.hasWinner, NS["team"][row["winner"]]))
        g.add((m, QP.hasLoser, NS["team"][row["loser"]]))
        if "overs_per_side" in row:
            g.add((m, QP.oversPerSide, Literal(row["overs_per_side"], datatype=XSD.integer)))
        for k in (1, 2):
            inn = NS["innings"][f"{mid}-{k}"]
            g.add((m, QP.hasInnings, inn))
            g.add((inn, RDF.type, QP.Innings))
            g.add((inn, QP.inningsNumber, Literal(k, datatype=XSD.integer)))
            g.add((inn, QP.battingTeam, NS["team"][row[f"inn{k}_team"]]))
            other = row["inn2_team"] if k == 1 else row["inn1_team"]
            g.add((inn, QP.bowlingTeam, NS["team"][other]))
            g.add((inn, QP.runs, Literal(row[f"inn{k}_runs"], datatype=XSD.integer)))
            g.add((inn, QP.wicketsLost, Literal(row[f"inn{k}_wkts"], datatype=XSD.integer)))
            g.add((inn, QP.ballsFaced, Literal(row[f"inn{k}_balls"], datatype=XSD.integer)))
            g.add((inn, QP.allOut, Literal(row[f"inn{k}_wkts"] == 10)))
    else:
        cls = QP.NoResultMatch if row["status"] == "no_result" else QP.ScheduledMatch
        g.add((m, RDF.type, cls))
        g.add((m, QP.hasParticipant, NS["team"][row["team1"]]))
        g.add((m, QP.hasParticipant, NS["team"][row["team2"]]))

out = ROOT / "RDF_Knowledge_Graph" / "ipl2026_abox.ttl"
header = ("# QualifyPath-KG A-Box: IPL 2026 league stage, snapshot after match "
          f"{CUTOFF}.\n# Generated by build_kg.py from Dataset/raw (Kaggle krishd123/"
          "ipl-2026-complete-dataset, CC0). Load together with ../Ontology/qualifypath.ttl.\n\n")
out.write_text(header + g.serialize(format="turtle"), encoding="utf-8")

# --------------------------------------------------------------------------
# 3. Cleaned table + validation against the official points table
# --------------------------------------------------------------------------
proc = ROOT / "Dataset" / "processed"
proc.mkdir(exist_ok=True)
cols = ["match_number", "date", "venue", "team1", "team2", "status", "winner", "loser", "super_over",
        "overs_per_side",
        "inn1_team", "inn1_runs", "inn1_wkts", "inn1_balls", "inn2_team", "inn2_runs", "inn2_wkts",
        "inn2_balls"]
with open(proc / "league_matches_clean.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

st = {t: {"P": 0, "W": 0, "L": 0, "NR": 0, "rf": 0, "bf": 0, "ra": 0, "bb": 0} for t in TEAMS}
for row in rows:
    if row["status"] == "scheduled":
        continue
    for t in (row["team1"], row["team2"]):
        st[t]["P"] += 1
    if row["status"] == "no_result":
        st[row["team1"]]["NR"] += 1
        st[row["team2"]]["NR"] += 1
        continue
    st[row["winner"]]["W"] += 1
    st[row["loser"]]["L"] += 1
    for k, o in ((1, 2), (2, 1)):
        bat, bowl = row[f"inn{k}_team"], row[f"inn{o}_team"]
        quota = row.get("overs_per_side", OVERS_QUOTA) * 6
        balls_for_nrr = quota if row[f"inn{k}_wkts"] == 10 else row[f"inn{k}_balls"]
        st[bat]["rf"] += row[f"inn{k}_runs"]
        st[bat]["bf"] += balls_for_nrr
        st[bowl]["ra"] += row[f"inn{k}_runs"]
        st[bowl]["bb"] += balls_for_nrr

inverse = {v: k for k, v in TEAMS.items()}
report = []
for o in official:
    t = inverse[o["team"]]
    s = st[t]
    nrr = s["rf"] / (s["bf"] / 6) - s["ra"] / (s["bb"] / 6)
    points = s["W"] * POINTS_WIN + s["NR"] * POINTS_NO_RESULT
    report.append({
        "team": t, "official_position": o["position"],
        "played": s["P"], "official_played": o["matches"],
        "won": s["W"], "official_won": o["wins"],
        "lost": s["L"], "official_lost": o["defeats"],
        "no_result": s["NR"], "official_no_result": o["abandoned"],
        "points": points, "official_points": o["points"],
        "nrr": f"{nrr:.3f}", "official_nrr": o["nrr"],
        "nrr_diff": f"{nrr - float(o['nrr']):+.3f}",
    })
res = ROOT / "Results"
with open(res / "validation_standings_vs_official.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(report[0]))
    w.writeheader()
    w.writerows(report)

# --------------------------------------------------------------------------
# 4. Summary
# --------------------------------------------------------------------------
print(f"A-Box written: {out.relative_to(ROOT)}  ({len(g)} triples)")
for label, cls in (("Match (decided, type inferred later)", QP.Match), ("NoResultMatch", QP.NoResultMatch),
                   ("ScheduledMatch", QP.ScheduledMatch), ("Innings", QP.Innings), ("Team", QP.Team),
                   ("Venue", QP.Venue), ("City", QP.City)):
    print(f"  {label:38s} {len(set(g.subjects(RDF.type, cls)))}")
ok = all(r["points"] == int(r["official_points"]) and r["won"] == int(r["official_won"])
         and r["lost"] == int(r["official_lost"]) for r in report)
print(f"Standings vs official table after match {CUTOFF}: points/W/L {'all match' if ok else 'MISMATCH'}")
for r in report:
    print(f"  {r['team']:5s} pts {r['points']:>2} (official {r['official_points']:>2})  "
          f"NRR {r['nrr']:>7} (official {r['official_nrr']:>7}, diff {r['nrr_diff']})")
for line in cleaning_log:
    print("  note:", line)
