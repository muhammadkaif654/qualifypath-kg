# RDF Knowledge Graph — IPL 2026 (A-Box)

`ipl2026_abox.ttl` holds the instance data for the IPL 2026 league stage, snapshot after match 39.
Load it together with the schema `../Ontology/qualifypath.ttl`.

## Contents

| Resource | Count | Notes |
| --- | --- | --- |
| Tournament / Season | 1 / 1 | IPL, IPL 2026 (cut-off match 39, 20-over quota) |
| Rules | 3 | points (2 / 0 / 1), qualification (top 4), tie-break 1 = net run rate |
| Teams | 10 | full name + short name; home venues |
| Venues / Cities | 13 / 13 | |
| Decided matches | 38 | stated only as `qp:Match` + winner/loser (see below) |
| No-result matches | 1 | match 12 |
| Scheduled matches | 31 | matches 40–70, with teams, date and `qp:scheduledAt` venue |
| Innings | 76 | runs, wickets, legal balls, all-out flag |
| **Triples** | **1,374** | plus 334 in the ontology = 1,708 explicit triples |

**Left for the reasoner on purpose.** Decided matches are stated only as `qp:Match` with
`qp:hasWinner` / `qp:hasLoser`. The reasoner infers that they are `DecidedMatch` and
`CompletedMatch`, that both teams are participants, `participatesIn` in the other direction, and
`playedAtVenue`. An OWL 2 RL run over the full graph gives 38 decided and 39 completed matches,
140 participation links, 50 team–venue links and no inconsistencies.

## URI design

Ontology terms and data use separate namespaces, so the schema can be reused for another season or
tournament without clashing with instances.

| What | Pattern | Example |
| --- | --- | --- |
| Ontology terms | `http://example.org/qualifypath/ontology#<Term>` | `qp:DecidedMatch`, `qp:hasWinner` |
| Tournament | `…/resource/tournament/<code>` | `tournament:IPL` |
| Season | `…/resource/season/<tournament>-<year>` | `season:IPL-2026` |
| Team | `…/resource/team/<official abbreviation>` | `team:RCB` |
| Venue | `…/resource/venue/<slug of official name>` | `venue:m-chinnaswamy-stadium` |
| City | `…/resource/city/<slug>` | `city:bengaluru` |
| Match | `…/resource/match/<season>-M<2-digit number>` | `match:IPL-2026-M32` |
| Innings | `…/resource/innings/<match id>-<innings number>` | `innings:IPL-2026-M32-1` |
| Rule | `…/resource/rule/<season>-<rule>` | `rule:IPL-2026-points`, `rule:IPL-2026-tiebreak-1` |
| Standing entry | `…/resource/standing/<season>-<team>` (created by the SPARQL rules, not loaded) | `standing:IPL-2026-RR` |

Design choices:
- **Readable and stable.** IDs come from official codes and match numbers, not row numbers or random
  IDs, so `match:IPL-2026-M32` always means the same match and can be read in query results.
- **Season-scoped.** Matches, innings and rules include the season, so a second season can be added
  without collisions. Teams and venues are not season-scoped, because they persist across seasons.
- **Names are labels, not IDs.** Human-readable names go in `rdfs:label`; spelling variants in the
  source files therefore never create duplicate resources.
- `example.org` is a placeholder base for coursework; a real deployment would use an owned domain.

## Rebuild

```bash
python RDF_Knowledge_Graph/build_kg.py
```

Run from the project folder (needs Python 3 and `rdflib`). The script reads `../Dataset/raw/`, writes
this file, `../Dataset/processed/league_matches_clean.csv` and
`../Results/validation_standings_vs_official.csv`, and prints the validation against the official table.
To change the snapshot or the rules, edit the configuration block at the top of the script.

## Load into GraphDB

1. Create a repository with ruleset **OWL2-RL**.
2. Import `../Ontology/qualifypath.ttl`, then `ipl2026_abox.ttl`.
3. Check: `SELECT (COUNT(*) AS ?n) WHERE { ?m a qp:CompletedMatch }` should return 39 with inference on.
