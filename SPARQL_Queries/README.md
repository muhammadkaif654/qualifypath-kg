# SPARQL queries and rules — QualifyPath-KG

11 SELECT queries (Q01–Q11), 3 rule files (R1–R7) that compute standings, and 3 inference
demonstrations (I1–I3). Every query answers a competency question; outputs are in `../Results/`.

## Queries

| Query | CQ | Question | Features | Rows |
| --- | --- | --- | --- | --- |
| Q01 | CQ15 | Season rules and tie-break order | basic graph pattern, property path | 1 |
| Q02 | CQ1 | Played / won / lost / no result / points per team | aggregation, **inference-dependent** | 10 |
| Q03 | CQ3 | Net run rate per team from innings | aggregation, OPTIONAL, VALUES | 10 |
| Q04 | CQ2 | Who holds the top-4 places after the tie-break | property path, rule results | 10 |
| Q05 | CQ4 | RR's remaining fixtures, opponents, dates, venues | **multi-hop**, FILTER, property path | 6 |
| Q06 | CQ5–7 | Highest reachable points; qualified / eliminated / in contention | rule-inferred classes, FILTER | 10 |
| Q07 | CQ11 | Teams RR has beaten, and where | **multi-hop**, inverse property path `^qp:hasWinner` | 5 |
| Q08 | CQ13 | Venues RR has played at | **inference-dependent** (property chain) | 6 |
| Q09 | CQ12 | KKR's results and points earned | **UNION**, OPTIONAL, FILTER | 8 |
| Q10 | CQ14 | Teams winning ≥ 50% at home | aggregation with HAVING, FILTER NOT EXISTS | 6 |
| Q11 | CQ8–9 | RR's remaining opponents still in contention, by points gap | **multi-hop**, rule-inferred class, FILTER | 6 |

Required features, all covered: basic graph patterns (Q01), FILTER (Q05, Q09, Q11), OPTIONAL or UNION
(Q03, Q09), aggregation (Q02, Q03, Q10), multi-hop traversal (Q05, Q07, Q11), property paths
(Q01, Q04, Q05, Q07), inference-dependent (Q02, Q08). Team X = RR and Team Z = KKR.

## Rules (`rules/`, SPARQL Update)

Standings need arithmetic, which OWL cannot do, so they are computed by SPARQL rules that write
`qp:StandingEntry` resources into the graph (URI `…/resource/standing/IPL-2026-<team>`).

| File | Rules | Adds |
| --- | --- | --- |
| `R1_R3_standing_entries.ru` | R1 points, R2 net run rate, R3 highest reachable points | 10 entries, 100 triples |
| `R4_R6_qualification_status.ru` | R4 eliminated, R5 qualified, R6 in contention | 10 status types |
| `R7_position.ru` | R7 league position (points, then net run rate) | 10 positions |

Run them in this order, after OWL 2 RL inference and before the queries.

## Inference demonstrations (`inference/`)

I1–I3 are run with inference off and on; see `../Results/inference_examples.md`.

## Key results (snapshot after match 39)

- **Q04 matches the official table:** positions 1–10 are identical to `Dataset/raw/points_table.csv`
  (PBKS, RCB, SRH, RR, GT, CSK, DC, KKR, MI, LSG). SRH and RR are level on 10 points and are separated
  by net run rate (0.815 vs 0.602).
- **Q06:** with 31 fixtures left, no team is qualified or eliminated yet. The highest any team can
  reach is 27 (PBKS) and the lowest is 16 (LSG), while the top score is 13, so the rules correctly leave
  all 10 in contention. This is a case where an LLM guessing from the table might wrongly call a team out.
- **Q07 / Q09** reflect the cleaned data: RR's 5 wins include match 32 (wrongly credited to LSG in the
  source), and KKR's record is 2 won, 5 lost, 1 no result.

## How to run

**Python** (from the project folder):

```bash
pip install rdflib owlrl
```

```bash
python SPARQL_Queries/run_queries.py
```

The script loads the ontology and A-Box, applies OWL 2 RL reasoning, runs the rules, runs every
query and writes the CSVs in `Results/`. Takes about 5 seconds.

**GraphDB:**

1. Create a repository with ruleset **OWL2-RL**; import `Ontology/qualifypath.ttl` and
   `RDF_Knowledge_Graph/ipl2026_abox.ttl`.
2. In the SPARQL tab, run the three files in `rules/` as updates, in order.
3. Paste and run any `Q*.rq`. For I1–I3, toggle **Include inferred data** off and on to show the difference.
