"""
QualifyPath-KG — draw high-resolution visualizations of the ontology and the IPL 2026 graph.

Usage (from the project folder):
    pip install rdflib networkx matplotlib
    python Visualization/make_visualizations.py

Outputs (Visualization/):
    ontology_schema.png    classes, subclass links and object properties (T-Box)
    season_graph.png       10 teams; every league match is an edge (completed vs scheduled)
    rr_neighbourhood.png   RR's 14 matches with opponents, results and venues (A-Box)
"""
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from rdflib import Graph, Namespace, RDF, RDFS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "Visualization"
QP = Namespace("http://example.org/qualifypath/ontology#")
R = "http://example.org/qualifypath/resource/"

g = Graph()
g.parse(ROOT / "Ontology" / "qualifypath.ttl")
g.parse(ROOT / "RDF_Knowledge_Graph" / "ipl2026_abox.ttl")

INK, MUTED, GRID = "#1f2937", "#6b7280", "#d1d5db"
BLUE, GREEN, RED, AMBER, PURPLE = "#2563eb", "#16a34a", "#dc2626", "#d97706", "#7c3aed"


def short(uri):
    s = str(uri)
    return s.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


# --------------------------------------------------------------------------
# 1. Ontology schema
# --------------------------------------------------------------------------
pos = {
    "Tournament": (5, 10.2), "Season": (5, 8.2),
    "TournamentRule": (12.6, 10.6), "PointsRule": (9.0, 10.4),
    "QualificationRule": (10.0, 9.2), "TieBreakCriterion": (11.4, 7.9),
    "StandingEntry": (1.0, 8.2), "QualifiedStanding": (-2.2, 9.8),
    "EliminatedStanding": (-2.2, 8.2), "InContentionStanding": (-2.2, 6.6),
    "Team": (1.0, 5.2), "Match": (5, 5.6), "CompletedMatch": (3.8, 3.6),
    "ScheduledMatch": (7.0, 3.6), "DecidedMatch": (2.6, 1.8), "NoResultMatch": (5.2, 1.8),
    "Innings": (-1.2, 2.4), "Venue": (9.8, 5.6), "City": (13.0, 5.6),
}
inferred_classes = {"QualifiedStanding", "EliminatedStanding", "InContentionStanding"}

fig, ax = plt.subplots(figsize=(20, 13), dpi=150)
ax.set_xlim(-3.8, 14.3)
ax.set_ylim(0.6, 11.6)
ax.axis("off")


def box_edge(a, b, pad=(0.95, 0.32)):
    """Shrink a line between box centres so it starts/ends at the box border."""
    (x1, y1), (x2, y2) = pos[a], pos[b]
    dx, dy = x2 - x1, y2 - y1
    tx = pad[0] / abs(dx) if dx else 1e9
    ty = pad[1] / abs(dy) if dy else 1e9
    t = min(tx, ty, 0.45)
    return (x1 + dx * t, y1 + dy * t), (x2 - dx * t, y2 - dy * t)


def arrow(a, b, label="", color=INK, style="-", rad=0.0, head="-|>", lw=1.6, label_pos=0.5, fs=10.5):
    p1, p2 = box_edge(a, b)
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=head, mutation_scale=16, color=color, lw=lw,
                                 linestyle=style, connectionstyle=f"arc3,rad={rad}", zorder=1))
    if label:
        t = label_pos
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        # point on matplotlib's arc3 quadratic Bezier (control = midpoint + rad * (dy, -dx))
        bulge = 2 * t * (1 - t) * rad
        mx, my = p1[0] + dx * t + dy * bulge, p1[1] + dy * t - dx * bulge
        ax.text(mx, my, label, fontsize=fs, color=color, ha="center", va="center", zorder=3,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.92))


# subclass links
for child, parent in [("CompletedMatch", "Match"), ("ScheduledMatch", "Match"),
                      ("DecidedMatch", "CompletedMatch"), ("NoResultMatch", "CompletedMatch"),
                      ("PointsRule", "TournamentRule"), ("QualificationRule", "TournamentRule"),
                      ("TieBreakCriterion", "TournamentRule"), ("QualifiedStanding", "StandingEntry"),
                      ("EliminatedStanding", "StandingEntry"), ("InContentionStanding", "StandingEntry")]:
    arrow(child, parent, color=MUTED, head="-|>", lw=1.3, style=(0, (4, 2)))

# object properties (domain -> range)
arrow("Season", "Tournament", "ofTournament")
arrow("Match", "Season", "inSeason")
arrow("Season", "PointsRule", "hasPointsRule", rad=-0.1)
arrow("Season", "QualificationRule", "hasQualificationRule")
arrow("Season", "TieBreakCriterion", "hasTieBreak", rad=0.1)
arrow("StandingEntry", "Season", "standingIn")
arrow("StandingEntry", "Team", "standingOf")
arrow("Match", "Team", "hasParticipant ⇄\nparticipatesIn (inverse)", color=BLUE, head="<|-|>")
arrow("DecidedMatch", "Team", "hasWinner / hasLoser\n(⊑ hasParticipant)", color=BLUE, label_pos=0.75)
arrow("CompletedMatch", "Innings", "hasInnings", rad=0.15, label_pos=0.55)
arrow("Innings", "Team", "battingTeam /\nbowlingTeam", label_pos=0.4)
arrow("Match", "Venue", "hasVenue")
arrow("CompletedMatch", "Venue", "playedAt (⊑ hasVenue)", rad=0.18, label_pos=0.62)
arrow("ScheduledMatch", "Venue", "scheduledAt (⊑ hasVenue)", label_pos=0.78)
arrow("Venue", "City", "locatedIn")
arrow("Team", "Venue", "homeVenue", rad=-0.22, label_pos=0.3)
arrow("Team", "Venue", "playedAtVenue\n(inferred: participatesIn ∘ playedAt)", color=RED,
      style=(0, (6, 3)), rad=-0.42, label_pos=0.72)

for name, (x, y) in pos.items():
    is_rule_derived = name in inferred_classes
    fc = "#fef3c7" if is_rule_derived else ("#eef2ff" if "Match" in name else "#f9fafb")
    ec = AMBER if is_rule_derived else (BLUE if "Match" in name else INK)
    ax.add_patch(FancyBboxPatch((x - 0.95, y - 0.32), 1.9, 0.64, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=fc, ec=ec, lw=1.6, zorder=2))
    ax.text(x, y, name, ha="center", va="center", fontsize=11.5, color=INK, weight="bold", zorder=4)

ax.text(-3.6, 11.35, "QualifyPath-KG ontology (T-Box)", fontsize=20, weight="bold", color=INK)
ax.text(-3.6, 10.95, "19 classes · 20 object properties · 26 datatype properties  —  namespace qp: "
        "<http://example.org/qualifypath/ontology#>", fontsize=12, color=MUTED)
legend = [Line2D([0], [0], color=INK, lw=1.6, label="object property (domain → range)"),
          Line2D([0], [0], color=MUTED, lw=1.3, ls=(0, (4, 2)), label="rdfs:subClassOf (child → parent)"),
          Line2D([0], [0], color=RED, lw=1.6, ls=(0, (6, 3)), label="inferred by property chain (O5)"),
          Line2D([0], [0], color=AMBER, lw=6, label="class filled by SPARQL rules R4–R6")]
ax.legend(handles=legend, loc="lower right", fontsize=11.5, frameon=False)
fig.savefig(OUT / "ontology_schema.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# --------------------------------------------------------------------------
# 2. Season graph: teams as nodes, each league match as an edge
# --------------------------------------------------------------------------
teams = sorted(short(t) for t in g.subjects(RDF.type, QP.Team))
matches = []
for m in set(g.subjects(QP.matchNumber, None)):
    n = int(g.value(m, QP.matchNumber))
    winner, loser = g.value(m, QP.hasWinner), g.value(m, QP.hasLoser)
    if winner is not None:
        a, b, kind = short(winner), short(loser), "decided"
    else:
        a, b = sorted(short(t) for t in g.objects(m, QP.hasParticipant))
        kind = "no_result" if (m, RDF.type, QP.NoResultMatch) in g else "scheduled"
    matches.append((n, a, b, kind))

fig, ax = plt.subplots(figsize=(13, 13), dpi=150)
ax.axis("off")
G = nx.MultiDiGraph()
G.add_nodes_from(teams)
circle = nx.circular_layout(teams)
pair_count = defaultdict(int)
for n, a, b, kind in sorted(matches):
    key = tuple(sorted((a, b)))
    k = pair_count[key]
    pair_count[key] += 1
    rad = 0.12 + 0.12 * k
    color = {"decided": GREEN, "no_result": AMBER, "scheduled": GRID}[kind]
    style = "-" if kind != "scheduled" else (0, (4, 3))
    head = "-|>" if kind == "decided" else "-"
    ax.add_patch(FancyArrowPatch(circle[a], circle[b], arrowstyle=head, mutation_scale=14,
                                 connectionstyle=f"arc3,rad={rad}", color=color, lw=1.6,
                                 linestyle=style, shrinkA=30, shrinkB=30, zorder=1))
wins = defaultdict(int)
for _, a, _, kind in matches:
    if kind == "decided":
        wins[a] += 1
for t in teams:
    x, y = circle[t]
    ax.add_patch(plt.Circle((x, y), 0.11, fc="#eef2ff", ec=BLUE, lw=2, zorder=2))
    ax.text(x, y + 0.012, t, ha="center", va="center", fontsize=14, weight="bold", color=INK, zorder=3)
    ax.text(x, y - 0.05, f"{wins[t]} W", ha="center", va="center", fontsize=9.5, color=MUTED, zorder=3)
ax.set_xlim(-1.3, 1.3)
ax.set_ylim(-1.35, 1.3)
ax.set_aspect("equal")
done = sum(1 for m in matches if m[3] != "scheduled")
ax.text(-1.28, 1.24, "IPL 2026 league stage as a graph", fontsize=20, weight="bold", color=INK)
ax.text(-1.28, 1.15, f"{len(teams)} teams · {len(matches)} matches · snapshot after match 39 "
        f"({done} completed, {len(matches) - done} scheduled)", fontsize=12, color=MUTED)
legend = [Line2D([0], [0], color=GREEN, lw=2, label="decided match (arrow: winner → loser)"),
          Line2D([0], [0], color=AMBER, lw=2, label="no result (match 12)"),
          Line2D([0], [0], color=GRID, lw=2, ls=(0, (4, 3)), label="scheduled fixture (matches 40–70)")]
ax.legend(handles=legend, loc="lower center", ncol=3, fontsize=11, frameon=False,
          bbox_to_anchor=(0.5, -0.01))
fig.savefig(OUT / "season_graph.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# --------------------------------------------------------------------------
# 3. RR neighbourhood (instances)
# --------------------------------------------------------------------------
RR = "RR"
H = nx.Graph()
edge_style = {}
node_kind = {RR: "focus"}
for n, a, b, kind in matches:
    if RR not in (a, b):
        continue
    m = f"M{n:02d}"
    opp = b if a == RR else a
    result = "scheduled" if kind == "scheduled" else "no_result" if kind == "no_result" else \
        ("won" if a == RR else "lost")
    node_kind[m] = result
    node_kind.setdefault(opp, "team")
    H.add_edge(RR, m)
    edge_style[(RR, m)] = result
    H.add_edge(m, opp)
    edge_style[(m, opp)] = "opp"
    muri = next(s for s in g.subjects(QP.matchNumber, None) if int(g.value(s, QP.matchNumber)) == n)
    v = g.value(muri, QP.playedAt) or g.value(muri, QP.scheduledAt)
    vname = str(g.value(v, QP.locatedIn).split("/")[-1]).replace("-", " ").title()
    vnode = f"@{vname}"
    node_kind[vnode] = "venue"
    H.add_edge(m, vnode)
    edge_style[(m, vnode)] = "venue"

layout = nx.kamada_kawai_layout(H)
fig, ax = plt.subplots(figsize=(17, 13), dpi=150)
ax.axis("off")
colors = {"won": GREEN, "lost": RED, "scheduled": MUTED, "no_result": AMBER}
for (u, v) in H.edges():
    s = edge_style.get((u, v)) or edge_style.get((v, u))
    (x1, y1), (x2, y2) = layout[u], layout[v]
    if s in colors:
        ax.plot([x1, x2], [y1, y2], color=colors[s], lw=2.6, ls="-" if s != "scheduled" else (0, (5, 3)), zorder=1)
    elif s == "opp":
        ax.plot([x1, x2], [y1, y2], color="#93c5fd", lw=1.3, zorder=1)
    else:
        ax.plot([x1, x2], [y1, y2], color="#ddd6fe", lw=1.1, zorder=1)
for node, (x, y) in layout.items():
    k = node_kind[node]
    if k == "focus":
        ax.scatter(x, y, s=4200, c="#1e40af", zorder=2)
        ax.text(x, y, "RR", color="white", ha="center", va="center", fontsize=17, weight="bold", zorder=3)
    elif k == "team":
        ax.scatter(x, y, s=1900, c="#dbeafe", edgecolors=BLUE, linewidths=1.8, zorder=2)
        ax.text(x, y, node, ha="center", va="center", fontsize=12, weight="bold", color=INK, zorder=3)
    elif k == "venue":
        ax.scatter(x, y, s=900, c="#ede9fe", edgecolors=PURPLE, linewidths=1.4, marker="s", zorder=2)
        ax.text(x, y - 0.075, node[1:], ha="center", va="center", fontsize=10.5, color=PURPLE, zorder=3)
    else:
        ax.scatter(x, y, s=1100, c="white", edgecolors=colors[k], linewidths=2.4, zorder=2)
        ax.text(x, y, node, ha="center", va="center", fontsize=10.5, color=INK, weight="bold", zorder=3)
xs, ys = zip(*layout.values())
ax.set_xlim(min(xs) - 0.2, max(xs) + 0.2)
ax.set_ylim(min(ys) - 0.22, max(ys) + 0.28)
ax.text(min(xs) - 0.18, max(ys) + 0.22, "Rajasthan Royals (RR) in the knowledge graph", fontsize=20,
        weight="bold", color=INK)
ax.text(min(xs) - 0.18, max(ys) + 0.14, "RR → its 14 league matches → opponent and venue city  ·  "
        "8 completed (5 won, 3 lost), 6 scheduled", fontsize=12, color=MUTED)
legend = [Line2D([0], [0], color=GREEN, lw=2.6, label="RR won"),
          Line2D([0], [0], color=RED, lw=2.6, label="RR lost"),
          Line2D([0], [0], color=MUTED, lw=2.6, ls=(0, (5, 3)), label="scheduled fixture"),
          Line2D([0], [0], color="#93c5fd", lw=1.5, label="hasParticipant (opponent)"),
          Line2D([0], [0], color="#ddd6fe", lw=1.5, label="playedAt / scheduledAt → city")]
ax.legend(handles=legend, loc="lower center", ncol=5, fontsize=11, frameon=False, bbox_to_anchor=(0.5, -0.03))
fig.savefig(OUT / "rr_neighbourhood.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

print("Written: ontology_schema.png, season_graph.png, rr_neighbourhood.png")
