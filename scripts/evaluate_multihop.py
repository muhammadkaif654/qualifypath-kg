"""
Evaluate the multi-hop reasoner (Option C) against ground truth computed independently of the KG.

Ground truth comes straight from Dataset/processed/league_matches_clean.csv with plain Python (no RDF,
no SPARQL, no reasoner), so the KG pipeline and the check do not share code. For every team (and every
ordered pair of teams for win chains) the reasoner's answer is compared with the ground truth, and every
hop of every reasoning path is checked to exist in the graph.

Usage (from the project folder):  python scripts/evaluate_multihop.py
Outputs: Results/iteration2/multihop_evaluation.csv, multihop_summary.md, multihop_examples.txt
"""
import csv
import sys
from collections import Counter, defaultdict, deque
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from qualifypath.kg import TEAM, load_kg  # noqa: E402
from qualifypath.multihop import MultiHopReasoner  # noqa: E402

OUT = ROOT / "Results" / "iteration2"
OUT.mkdir(parents=True, exist_ok=True)
WIN, NR, PLACES = 2, 1, 4

# ------------------------------------------------------------------ ground truth from the CSV
rows = list(csv.DictReader(open(ROOT / "Dataset" / "processed" / "league_matches_clean.csv", encoding="utf-8")))
teams = sorted({r["team1"] for r in rows} | {r["team2"] for r in rows})
done = [r for r in rows if r["status"] != "scheduled"]
todo = [r for r in rows if r["status"] == "scheduled"]
pts = {t: 0 for t in teams}
for r in done:
    if r["status"] == "decided":
        pts[r["winner"]] += WIN
    else:
        pts[r["team1"]] += NR
        pts[r["team2"]] += NR
remaining = Counter([r["team1"] for r in todo] + [r["team2"] for r in todo])
mx = {t: pts[t] + WIN * remaining[t] for t in teams}


def status(t):
    if sum(pts[o] > mx[t] for o in teams if o != t) >= PLACES:
        return "eliminated"
    if sum(mx[o] >= pts[t] for o in teams if o != t) < PLACES:
        return "qualified"
    return "in contention"


def other(r, t):
    return r["team2"] if r["team1"] == t else r["team1"]


def gt_fixtures(t):
    return sorted((int(r["match_number"]), other(r, t)) for r in todo if t in (r["team1"], r["team2"]))


def gt_beaten(t):
    return sorted((int(r["match_number"]), r["loser"]) for r in done if r.get("winner") == t)


def gt_venues(t):
    return sorted({r["venue"] for r in done if t in (r["team1"], r["team2"])})


def gt_qualification(t):
    others = [o for o in teams if o != t]
    alive = next((w for w in range(remaining[t] + 1)
                  if sum(pts[o] > pts[t] + WIN * w for o in others) < PLACES), None)
    safe = next((w for w in range(remaining[t] + 1)
                 if sum(mx[o] >= pts[t] + WIN * w for o in others) < PLACES), None)
    return (pts[t], mx[t], status(t), alive, safe)


def gt_rivals(t):
    return sorted((int(r["match_number"]), other(r, t)) for r in todo
                  if t in (r["team1"], r["team2"]) and status(other(r, t)) == "in contention")


def gt_what_if(t):
    mine = [r for r in todo if t in (r["team1"], r["team2"])]
    last = max(mine, key=lambda r: (r["date"], int(r["match_number"])))
    cap = mx[t] - WIN
    above = sorted(o for o in teams if o != t and pts[o] > cap)
    level = sorted(o for o in teams if o != t and pts[o] <= cap <= mx[o])
    return (int(last["match_number"]), other(last, t), cap, above, level)


beats = defaultdict(set)
for r in done:
    if r["status"] == "decided":
        beats[r["winner"]].add(r["loser"])


def gt_chains(a, b, max_len=3):
    out, q = set(), deque([(a, [a])])
    while q:
        node, path = q.popleft()
        if node == b and len(path) > 1:
            out.add(" > ".join(path))
            continue
        if len(path) - 1 >= max_len:
            continue
        for x in beats[node]:
            if x not in path or x == b:
                q.append((x, path + [x]))
    return sorted(out)


# ------------------------------------------------------------------ run the reasoner
kg = load_kg()
R = MultiHopReasoner(kg)
records, hop_prov, path_lens, invalid = [], Counter(), [], 0
examples = []


def check_paths(res):
    global invalid
    for path in res.paths:
        path_lens.append(len(path))
        for h in path:
            hop_prov[h.provenance] += 1
            if (h.s, h.p, h.o) not in kg.full:
                invalid += 1


def record(kind, q, predicted, expected, res):
    check_paths(res)
    records.append({"reasoning_type": kind, "question": q, "correct": predicted == expected,
                    "predicted": predicted, "expected": expected, "paths": len(res.paths)})


for t in teams:
    T = TEAM[t]
    res = R.remaining_fixtures(T)
    record("CQ4 remaining fixtures", res.question, sorted((n, o) for n, o, _, _ in res.items), gt_fixtures(t), res)
    res = R.teams_beaten(T)
    record("CQ11 teams beaten", res.question, sorted((n, o) for n, o, _ in res.items), gt_beaten(t), res)
    res = R.venues_played(T)
    record("CQ13 venues played (chain)", res.question, sorted(s for s, _, _ in res.items), gt_venues(t), res)
    res = R.qualification(T)
    i = res.items
    record("CQ5-7 qualification", res.question, (i["points"], i["max"], i["status"], i["alive_wins"], i["safe_wins"]),
           gt_qualification(t), res)
    res = R.rivals(T)
    record("CQ8 rivals", res.question, sorted((n, o) for n, o, _, _ in res.items), gt_rivals(t), res)
    res = R.what_if_lose_last(T)
    i = res.items
    record("CQ10 what-if (scenario)", res.question,
           (i["last_match"], i["opponent"], i["cap"], i["above"], i["level_or_above"]), gt_what_if(t), res)
for a, b in permutations(teams, 2):
    res = R.win_chains(TEAM[a], TEAM[b])
    record("Win chains (<=3 wins)", res.question, res.items, gt_chains(a, b), res)
for a, b in [("RR", "MI"), ("RR", "wankhede-stadium"), ("KKR", "PBKS"), ("LSG", "eden-gardens")]:
    from qualifypath.kg import RES
    end = TEAM[b] if b.isupper() else __import__("rdflib").URIRef(RES + "venue/" + b)
    res = R.find_paths(TEAM[a], end)
    check_paths(res)
    examples.append(res)

for t, fn in [("RR", R.remaining_fixtures), ("LSG", R.qualification), ("KKR", R.what_if_lose_last),
              ("RR", R.venues_played), ("RR", R.rivals)]:
    examples.append(fn(TEAM[t]))
examples.append(R.win_chains(TEAM.RR, TEAM.KKR))

# ------------------------------------------------------------------ write outputs
with open(OUT / "multihop_evaluation.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(records[0]))
    w.writeheader()
    w.writerows(records)

by = defaultdict(lambda: [0, 0, 0])
for r in records:
    by[r["reasoning_type"]][0] += 1
    by[r["reasoning_type"]][1] += r["correct"]
    by[r["reasoning_type"]][2] += r["paths"]
total_hops = sum(hop_prov.values())
lines = ["# Multi-hop reasoning evaluation", "",
         "Ground truth is recomputed from `Dataset/processed/league_matches_clean.csv` without the KG.", "",
         "| Reasoning type | Questions | Correct | Accuracy | Reasoning paths |", "| --- | --- | --- | --- | --- |"]
for k, (n, c, p) in by.items():
    lines.append(f"| {k} | {n} | {c} | {c / n:.0%} | {p} |")
n_all, c_all = len(records), sum(r["correct"] for r in records)
lines += [f"| **Total** | **{n_all}** | **{c_all}** | **{c_all / n_all:.1%}** | **{sum(v[2] for v in by.values())}** |", "",
          f"- Hops checked: {total_hops}; hops not found in the graph: {invalid}.",
          f"- Average path length: {sum(path_lens) / len(path_lens):.2f} hops (max {max(path_lens)}).",
          "- Hop provenance: " + ", ".join(f"{k}: {v} ({v / total_hops:.0%})" for k, v in hop_prov.most_common()),
          "- CQ10 answers are hypothetical scenarios and are labelled as such, never as facts."]
(OUT / "multihop_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
(OUT / "multihop_examples.txt").write_text("\n\n".join(e.render(kg, max_paths=6) for e in examples) + "\n",
                                          encoding="utf-8")
print("\n".join(lines))
wrong = [r for r in records if not r["correct"]]
for r in wrong[:10]:
    print("MISMATCH", r["question"], "\n  predicted", r["predicted"], "\n  expected ", r["expected"])
