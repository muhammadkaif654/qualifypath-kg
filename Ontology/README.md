# Ontology — QualifyPath-KG (T-Box)

`qualifypath.ttl` is the schema of the knowledge graph, written in Turtle (RDF/RDFS/OWL 2).
It contains only the T-Box. The A-Box (actual teams, matches, innings, rules) is generated from the
match data and stored in `../RDF_Knowledge_Graph/`.

- Namespace: `qp: <http://example.org/qualifypath/ontology#>`
- Size: 334 triples, 19 classes, 20 object properties, 26 datatype properties
- Guideline minimum: 10 classes, 8 properties, 3 reasoning-enabling constructs

## Class hierarchy

```
Tournament
Season
Team
Venue
City
Match                      (exactly 2 participants)
├── CompletedMatch         (disjoint with ScheduledMatch)
│   ├── DecidedMatch       (exactly 1 winner; disjoint with NoResultMatch)
│   └── NoResultMatch
└── ScheduledMatch
Innings
TournamentRule
├── PointsRule
├── QualificationRule
└── TieBreakCriterion
StandingEntry              (one team in one season)
├── QualifiedStanding      (set by SPARQL rule R5)
├── EliminatedStanding     (set by SPARQL rule R4)
└── InContentionStanding   (set by SPARQL rule R6)
```

## Reasoning-enabling constructs

| Code | Construct | What the reasoner infers | Used by |
| --- | --- | --- | --- |
| O1 | `hasWinner`, `hasLoser` rdfs:subPropertyOf `hasParticipant` | Winner and loser are participants | CQ11 |
| O2 | `participatesIn` owl:inverseOf `hasParticipant` | Team → participatesIn → Match | CQ1, CQ4, CQ11 |
| O3 | `hasWinner` rdfs:domain `DecidedMatch` | A match with a winner is a DecidedMatch | CQ1, CQ11 |
| O4 | `DecidedMatch`, `NoResultMatch` rdfs:subClassOf `CompletedMatch` | Decided and no-result matches count as completed | CQ1, CQ12 |
| O5 | `playedAtVenue` owl:propertyChainAxiom (`participatesIn` `playedAt`) | Team → playedAtVenue → Venue | CQ13 |

Venues: `playedAt` (domain CompletedMatch) and `scheduledAt` (domain ScheduledMatch) are both
sub-properties of `hasVenue`. Keeping them apart means the O5 chain only counts venues a team has
actually played at, never future fixtures. A query on `hasVenue` covers both.

Constraints (consistency checks, not new facts): CompletedMatch ⊓ ScheduledMatch is empty;
a Match has exactly 2 participants; a DecidedMatch has exactly 1 winner; StandingEntry statuses are
mutually disjoint. Standings, NRR, qualification and elimination need arithmetic, so they are computed
by SPARQL rules R1–R7 (see the CQ document), not by OWL.

## Verified

The ontology was loaded with a small test A-Box (two teams, one decided match, one no-result match,
one scheduled match) and expanded with an OWL 2 RL reasoner (Python `owlrl`), the same rule profile as
GraphDB's OWL2-RL ruleset. Every check passed:

- O1–O5 each produced their inferred triple.
- The scheduled match was **not** inferred to be completed.
- A scheduled match given a winner was reported as inconsistent (CompletedMatch and ScheduledMatch are disjoint).

With the full IPL 2026 A-Box loaded (1,708 explicit triples), the reasoner infers 38 DecidedMatch,
39 CompletedMatch, 140 participation links and 50 team–venue links, and reports no inconsistency.

## Open in Protégé

1. File → Open → `qualifypath.ttl`.
2. Entities tab: browse Classes, Object properties, Data properties.
3. Reasoner → HermiT → Start reasoner. With only the T-Box loaded there are no individuals,
   so inferred facts appear once the A-Box from `../RDF_Knowledge_Graph/` is imported
   (File → Import ontology, or merge both files).
4. Select an individual (e.g. a match) to see inferred types and property values highlighted in yellow.

## Load in GraphDB

Create a repository with the **OWL2-RL** ruleset (it supports property chains and inverse properties),
then import `qualifypath.ttl` followed by the instance data.
