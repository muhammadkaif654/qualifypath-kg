# Multi-hop reasoning evaluation

Ground truth is recomputed from `Dataset/processed/league_matches_clean.csv` without the KG.

| Reasoning type | Questions | Correct | Accuracy | Reasoning paths |
| --- | --- | --- | --- | --- |
| CQ4 remaining fixtures | 10 | 10 | 100% | 62 |
| CQ11 teams beaten | 10 | 10 | 100% | 38 |
| CQ13 venues played (chain) | 10 | 10 | 100% | 50 |
| CQ5-7 qualification | 10 | 10 | 100% | 10 |
| CQ8 rivals | 10 | 10 | 100% | 62 |
| CQ10 what-if (scenario) | 10 | 10 | 100% | 10 |
| Win chains (<=3 wins) | 90 | 90 | 100% | 457 |
| **Total** | **150** | **150** | **100.0%** | **689** |

- Hops checked: 3356; hops not found in the graph: 0.
- Average path length: 4.81 hops (max 6).
- Hop provenance: explicit: 2948 (88%), inferred (OWL 2 RL): 244 (7%), rule-derived (SPARQL R1-R7): 164 (5%)
- CQ10 answers are hypothetical scenarios and are labelled as such, never as facts.
