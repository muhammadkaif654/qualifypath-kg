# Inference examples — facts the graph knows but never stores

Each example shows **Explicit facts → Rule / schema knowledge → Inferred fact**, the query that
proves it, and its result with inference off and on (`inference_examples.csv`, produced by
`SPARQL_Queries/run_queries.py` with an OWL 2 RL reasoner, the same profile as GraphDB's OWL2-RL ruleset).

## Example 1 — the winner of a match took part in it

| | |
| --- | --- |
| **Explicit facts** | `match:IPL-2026-M01 qp:hasWinner team:RCB .`<br>`match:IPL-2026-M01 qp:hasLoser team:SRH .` |
| **Rule (O1)** | `qp:hasWinner rdfs:subPropertyOf qp:hasParticipant .`<br>`qp:hasLoser rdfs:subPropertyOf qp:hasParticipant .` |
| **Inferred fact** | `match:IPL-2026-M01 qp:hasParticipant team:RCB , team:SRH .` |
| **Query** | `SPARQL_Queries/inference/I1_winner_is_participant.rq` |
| **Result** | inference off: 0 rows · inference on: RCB, SRH |

No decided match stores its participants. Of the season's 140 participation links, 76 (every
decided match) are inferred by this rule; the other 64 are stated for the no-result and scheduled matches.

## Example 2 — a match with a winner is a completed match

| | |
| --- | --- |
| **Explicit facts** | `match:IPL-2026-M01 a qp:Match ; qp:hasWinner team:RCB .` |
| **Rules (O3, O4)** | `qp:hasWinner rdfs:domain qp:DecidedMatch .`<br>`qp:DecidedMatch rdfs:subClassOf qp:CompletedMatch .` |
| **Inferred facts** | `match:IPL-2026-M01 a qp:DecidedMatch , qp:CompletedMatch .` |
| **Query** | `SPARQL_Queries/inference/I2_match_classified_completed.rq` |
| **Result** | inference off: `qp:Match` only · inference on: `qp:Match`, `qp:DecidedMatch`, `qp:CompletedMatch` |

Season-wide, **0** matches are stored as completed; the reasoner classifies **39** (38 decided +
the no-result match 12, via `qp:NoResultMatch rdfs:subClassOf qp:CompletedMatch`). The points table
(Q02) depends on this: with inference off it finds only match 12.

## Example 3 — the venues a team has played at

| | |
| --- | --- |
| **Explicit facts** | `match:IPL-2026-M03 qp:hasWinner team:RR .`<br>`match:IPL-2026-M03 qp:playedAt venue:barsapara-cricket-stadium .` |
| **Rules (O1, O2, O5)** | `qp:hasWinner rdfs:subPropertyOf qp:hasParticipant .`<br>`qp:participatesIn owl:inverseOf qp:hasParticipant .`<br>`qp:playedAtVenue owl:propertyChainAxiom ( qp:participatesIn qp:playedAt ) .` |
| **Inferred facts** | `team:RR qp:participatesIn match:IPL-2026-M03 .`<br>`team:RR qp:playedAtVenue venue:barsapara-cricket-stadium .` |
| **Query** | `SPARQL_Queries/inference/I3_team_played_at_venue.rq` |
| **Result** | inference off: 0 rows · inference on: 6 venues (Ahmedabad, Guwahati, Hyderabad, Jaipur, Kolkata, Lucknow) |

This is a three-step chain: subproperty, then inverse, then property chain. Season-wide the graph
stores **0** team–venue links and infers **50**. Because only completed matches use `qp:playedAt`
(fixtures use `qp:scheduledAt`), the chain never counts venues where a team has not yet played.

## Bonus — rule-based inference (SPARQL rules)

Standings, net run rate, position and qualification status are not stored either. The rules in
`SPARQL_Queries/rules/` derive them, e.g. for RR:

- **Explicit facts:** 8 completed matches involving RR (5 `hasWinner team:RR`, 3 `hasLoser team:RR`),
  their innings, and the points rule (2 per win).
- **Rules:** R1 (points), R2 (net run rate), R7 (position).
- **Inferred facts:** `standing:IPL-2026-RR qp:points 10 ; qp:netRunRate 0.602 ; qp:position 4 .`,
  which matches the official IPL table after match 39.
