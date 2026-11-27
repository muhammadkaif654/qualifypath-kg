# Visualization and GraphDB

## Files

| File | What it shows |
| --- | --- |
| `ontology_schema.png` | The T-Box: 19 classes, subclass links, object properties (domain → range), the inferred `playedAtVenue` chain, and the rule-filled status classes |
| `season_graph.png` | The whole league stage: 10 teams as nodes, each of the 70 matches as an edge (decided = winner → loser, no result, scheduled) |
| `rr_neighbourhood.png` | Instance level: RR → its 14 matches → opponent and venue city, coloured by result |
| `graphdb_graphs_overview.png` | GraphDB repository `qualifypath-ipl2026` loaded (default graph) |
| `graphdb_class_hierarchy.png` | GraphDB class hierarchy: the 19 classes sized by instance count |
| `graphdb_visual_graph_match03.png` | GraphDB Visual graph of match 3 — note the **inferred** types `Completed match` and `Decided match` |
| `graphdb_visual_graph_RR.png` | GraphDB Visual graph of RR: its 14 matches, 6 venues played at (inferred) and its standing entry (settings: schema statements and predicate labels off, type `qp:Innings` ignored) |
| `graphdb_sparql_Q05.png` | Multi-hop query Q05 in GraphDB: RR's 6 remaining fixtures |
| `graphdb_sparql_Q04.png` | Q04 in GraphDB: positions 1–10 identical to the official table |
| `graphdb_inference_I3_off.png` / `_on.png` | I3 with *Include inferred data* off (no results) and on (6 venues) |
| `graphdb_inference_I2_off.png` / `_on.png` | I2 off (`qp:Match` only) and on (+ `CompletedMatch`, `DecidedMatch`) |

The three diagrams are drawn from the RDF files by `make_visualizations.py`. The `graphdb_*.png`
screenshots were taken full-screen in GraphDB Workbench (browser bar cropped).

```bash
python Visualization/make_visualizations.py
```

## GraphDB repository

The repository **`qualifypath-ipl2026`** (ruleset OWL2-RL optimized) has been created in your GraphDB
Desktop 11.5.1 and loaded with the ontology, the A-Box and the rule results.

| | Explicit | With inference |
| --- | --- | --- |
| After loading ontology + A-Box | 1,708 | 3,957 |
| After SPARQL rules R1–R7 | 1,828 | 4,097 |

All 11 queries return the same rows in GraphDB as in `Results/`, and I1–I3 return 0 → 2, 1 → 3 and
0 → 6 rows when *Include inferred data* is switched off → on.

To rebuild it from scratch (GraphDB Desktop must be running):

```bash
python RDF_Knowledge_Graph/graphdb/load_graphdb.py --reset
```

Or by hand: Setup → Repositories → Create new repository → *Import repository config file* →
`RDF_Knowledge_Graph/graphdb/repo-config.ttl`; then Import → upload `Ontology/qualifypath.ttl` and
`RDF_Knowledge_Graph/ipl2026_abox.ttl`; then run the three files in `SPARQL_Queries/rules/` in the SPARQL tab.

## Review demo script (about 5 minutes)

1. **Graph loaded.** Workbench → select `qualifypath-ipl2026` → Explore → *Graphs overview*: 1,828 explicit statements.
   *Class hierarchy*: 19 classes; click `qp:Match` to show CompletedMatch / ScheduledMatch nesting.
2. **Visual graph.** Explore → Visual graph → search `IPL-2026-M03`. Point out that the match is stored only
   as `Match` + winner/loser, yet shows types *Completed match* and *Decided match* — inferred.
   Then search `RR` and expand a match node.
3. **Multi-hop query.** SPARQL tab → paste `Q05_remaining_fixtures.rq` (RR → fixture → opponent / venue → city).
4. **Inference, live.** Paste `inference/I3_team_played_at_venue.rq`. Run with the *Include inferred data*
   toggle (the `>>` icon) **off** → 0 rows, then **on** → 6 venues. Repeat with I1 and I2.
5. **Standings.** Paste `Q04_qualifying_places.rq`: positions 1–10 match the official IPL table after match 39.

## Retaking the screenshots

In GraphDB Workbench, maximise the window, open each view above, and use Windows **Win + Shift + S**.
Save over the three `graphdb_*.jpg` files (PNG is fine too). Also worth capturing: a SPARQL result for Q05,
and I3 with inference off and on side by side.
