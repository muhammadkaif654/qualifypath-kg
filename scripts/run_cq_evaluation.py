"""
LLM-only vs KG-grounded evaluation on 10 competency questions (same Groq model, temperature 0,
same token limit in both conditions).

Expected answers come from the KG and were verified against the official IPL points table after match 39
(CQ1-CQ3) or against ground truth recomputed from the cleaned match table (all others; see
scripts/evaluate_multihop.py). `auto_check` is a first-pass keyword check; the final correctness verdict
is reviewed by hand and recorded in Results/iteration2/cq_evaluation_review.csv.

Usage:  python scripts/run_cq_evaluation.py
Output: Results/iteration2/cq_evaluation_raw.json and cq_evaluation_raw.csv
"""
import csv
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from qualifypath import llm, qa  # noqa: E402

OUT = ROOT / "Results" / "iteration2"
OUT.mkdir(parents=True, exist_ok=True)

# (id, type, question, expected answer, required terms: every group must match at least one alternative)
CQS = [
    ("CQ1", "aggregation",
     "How many points do Punjab Kings have after match 39 of IPL 2026, and what is their won / lost / no-result record?",
     "13 points from 7 matches: 6 won, 0 lost, 1 no result.",
     [["13"], ["6 wins", "won 6", "6 won", "six wins"], ["no result", "no-result", "abandon"]]),
    ("CQ2", "aggregation + inference",
     "Which four teams hold the qualifying places in IPL 2026 after match 39, and how are SRH and RR separated?",
     "PBKS 13, RCB 12, SRH 10, RR 10. SRH and RR are level on 10 points and on wins (5 each, tie-break 1), "
     "so net run rate decides (tie-break 2): SRH 0.815 v RR 0.602.",
     [["pbks", "punjab"], ["rcb", "royal challengers"], ["srh", "sunrisers"], ["rr", "rajasthan"],
      ["net run rate", "nrr"]]),
    ("CQ3", "aggregation, LLM-hard",
     "What is Kolkata Knight Riders' net run rate after match 39 of IPL 2026?",
     "-0.751 (the source points table shows +0.751, a dropped minus sign).",
     [["-0.751", "−0.751"]]),
    ("CQ4", "multi-hop",
     "Which fixtures does Rajasthan Royals still have to play after match 39 of IPL 2026?",
     "6 fixtures: PBKS (match 40, Mullanpur), DC (match 43, Jaipur), GT (match 52, Jaipur), DC (match 62, New Delhi), "
     "LSG (match 64, Jaipur), MI (match 69, Mumbai).",
     [["pbks", "punjab"], ["dc", "delhi"], ["gt", "gujarat"], ["lsg", "lucknow"], ["mi", "mumbai"], ["6", "six"]]),
    ("CQ5", "multi-hop + aggregation",
     "What is the highest points total Lucknow Super Giants can still reach in IPL 2026 if they win all their remaining matches?",
     "16 points: 4 now plus 6 remaining matches x 2.",
     [["16"]]),
    ("CQ6", "inference, LLM-hard",
     "Which teams are mathematically eliminated from the IPL 2026 top 4 after match 39?",
     "None. Even last-placed LSG can reach 16 points while the leader has 13, so every team is still in contention.",
     [["no team", "none", "not eliminated", "no teams", "all ten", "all 10", "every team", "in contention"]]),
    ("CQ8", "multi-hop + inference",
     "Which of Rajasthan Royals' remaining opponents are direct rivals still in contention for the top 4 in IPL 2026?",
     "All six remaining opponents are still in contention: GT (8 pts, closest), PBKS (13), DC (6, twice), LSG (4), MI (4).",
     [["gt", "gujarat"], ["pbks", "punjab"], ["dc", "delhi"], ["lsg", "lucknow"], ["mi", "mumbai"]]),
    ("CQ10", "multi-hop scenario, LLM-hard",
     "If Kolkata Knight Riders lose their last league match of IPL 2026, which teams are certain to finish above them on points?",
     "Scenario: KKR's last match is match 70 v DC; KKR could then reach at most 15 points. No team is certain to finish "
     "above; all nine others could still finish level or above.",
     [["no team", "none", "no teams"], ["15"]]),
    ("CQ11", "multi-hop",
     "Which teams has Rajasthan Royals beaten in IPL 2026 so far, and at which venues?",
     "CSK (match 3, Guwahati), GT (match 9, Ahmedabad), MI (match 13, Guwahati), RCB (match 16, Guwahati), "
     "LSG (match 32, Lucknow).",
     [["csk", "chennai"], ["gt", "gujarat"], ["mi", "mumbai"], ["rcb", "royal challengers"], ["lsg", "lucknow"],
      ["guwahati", "barsapara"]]),
    ("CQ13", "multi-hop + inference (property chain)",
     "At which venues has Rajasthan Royals played in IPL 2026 so far?",
     "6 venues: Barsapara Cricket Stadium (Guwahati), Ekana Cricket Stadium (Lucknow), Eden Gardens (Kolkata), "
     "Narendra Modi Stadium (Ahmedabad), Rajiv Gandhi International Stadium (Hyderabad), Sawai Mansingh Stadium (Jaipur).",
     [["barsapara", "guwahati"], ["ekana", "lucknow"], ["eden", "kolkata"], ["narendra modi", "ahmedabad"],
      ["rajiv gandhi", "hyderabad"], ["sawai mansingh", "jaipur"]]),
]


def auto_check(text: str, groups) -> bool:
    t = text.lower()
    return all(any(re.search(rf"(?<![a-z0-9]){re.escape(a.lower())}(?![a-z])", t) for a in alts) for alts in groups)


if __name__ == "__main__":
    rows = []
    for cid, kind, q, expected, groups in CQS:
        g = qa.ask_grounded(q)
        time.sleep(2)
        o = qa.ask_llm_only(q)
        time.sleep(2)
        rows.append({
            "cq": cid, "type": kind, "question": q, "expected": expected,
            "llm_only": o.answer, "kg_grounded": g.answer,
            "auto_llm_only": auto_check(o.answer, groups), "auto_kg_grounded": auto_check(g.answer, groups),
            "evidence_llm_only": False, "evidence_kg_grounded": bool(g.cited),
            "facts_retrieved": len(g.retrieval.facts), "facts_cited": [f.id for f in g.cited],
            "cited_fact_text": [f"[{f.id}] ({f.kind}) {f.text}" for f in g.cited],
            "model": llm.MODEL, "temperature": llm.TEMPERATURE,
        })
        print(f"{cid}: auto LLM-only={rows[-1]['auto_llm_only']}  KG={rows[-1]['auto_kg_grounded']}  "
              f"cited={rows[-1]['facts_cited']}")
    (OUT / "cq_evaluation_raw.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(OUT / "cq_evaluation_raw.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[k for k in rows[0] if k != "cited_fact_text"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"Auto check: LLM-only {sum(r['auto_llm_only'] for r in rows)}/10, "
          f"KG-grounded {sum(r['auto_kg_grounded'] for r in rows)}/10")
