"""
QualifyPath-KG — run every SPARQL rule and query and save the results.

Usage (from the project folder):
    pip install rdflib owlrl
    python SPARQL_Queries/run_queries.py

Steps:
  1. Load Ontology/qualifypath.ttl + RDF_Knowledge_Graph/ipl2026_abox.ttl (explicit triples only).
  2. Copy the graph and apply OWL 2 RL reasoning (owlrl) - the same profile as GraphDB's OWL2-RL ruleset.
  3. Apply the SPARQL rules in SPARQL_Queries/rules/ (R1-R3, R4-R6, R7) to the inferred graph.
  4. Run Q01-Q11 on the inferred graph  -> Results/Qxx_<name>.csv
  5. Run I1-I3 on BOTH graphs           -> Results/inference_examples.csv (explicit vs inferred)

In GraphDB the same files work as-is: use an OWL2-RL repository, run the three rule files
in the Update tab (in order), then run the queries.
"""
import csv
from pathlib import Path

import owlrl
from rdflib import Graph, Literal, URIRef

ROOT = Path(__file__).resolve().parent.parent
Q_DIR = ROOT / "SPARQL_Queries"
RESULTS = ROOT / "Results"

PREFIXES = [
    ("http://example.org/qualifypath/ontology#", "qp:"),
    ("http://example.org/qualifypath/resource/", ""),
]


def short(value):
    """Readable cell value: compact IRIs, plain literals."""
    if value is None:
        return ""
    if isinstance(value, URIRef):
        s = str(value)
        for base, prefix in PREFIXES:
            if s.startswith(base):
                return prefix + s[len(base):]
        return s
    if isinstance(value, Literal):
        v = value.toPython()
        if isinstance(v, float) or type(v).__name__ == "Decimal":
            return f"{float(v):.3f}".rstrip("0").rstrip(".") if float(v) != int(float(v)) else str(int(float(v)))
        return str(v)
    return str(value)


def run(graph, path):
    result = graph.query(path.read_text(encoding="utf-8"))
    header = [str(v) for v in result.vars]
    rows = [[short(row[v]) for v in result.vars] for row in result]
    return header, rows


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# 1. explicit graph
explicit = Graph()
explicit.parse(ROOT / "Ontology" / "qualifypath.ttl")
explicit.parse(ROOT / "RDF_Knowledge_Graph" / "ipl2026_abox.ttl")
print(f"Explicit triples: {len(explicit)}")

# 2. OWL 2 RL reasoning
inferred = Graph()
inferred += explicit
owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(inferred)
print(f"After OWL 2 RL reasoning: {len(inferred)}")

# 3. SPARQL rules
for rule in sorted((Q_DIR / "rules").glob("*.ru")):
    before = len(inferred)
    inferred.update(rule.read_text(encoding="utf-8"))
    print(f"Rule {rule.stem}: +{len(inferred) - before} triples")

# 4. queries
print()
for q in sorted(Q_DIR.glob("Q*.rq")):
    header, rows = run(inferred, q)
    write_csv(RESULTS / f"{q.stem}.csv", header, rows)
    print(f"{q.stem}: {len(rows)} rows")

# 5. inference examples: explicit vs inferred
print()
summary = []
for q in sorted((Q_DIR / "inference").glob("I*.rq")):
    _, rows_off = run(explicit, q)
    _, rows_on = run(inferred, q)
    summary.append([q.stem, len(rows_off), "; ".join(r[0] for r in rows_off),
                    len(rows_on), "; ".join(r[0] for r in rows_on)])
    print(f"{q.stem}: inference off {len(rows_off)} rows, on {len(rows_on)} rows")

# Season-wide counts that show how much the reasoner adds
counts = """
PREFIX qp: <http://example.org/qualifypath/ontology#>
SELECT (COUNT(DISTINCT ?c) AS ?completed) (COUNT(DISTINCT ?d) AS ?decided)
       (COUNT(DISTINCT ?pv) AS ?teamVenuePairs)
WHERE {
  { ?c a qp:CompletedMatch } UNION { ?d a qp:DecidedMatch }
  UNION { ?t qp:playedAtVenue ?v . BIND(CONCAT(STR(?t), STR(?v)) AS ?pv) }
}"""
for label, g in (("explicit", explicit), ("inferred", inferred)):
    row = list(g.query(counts))[0]
    summary.append([f"season-wide ({label})", "", "", "",
                    f"CompletedMatch={row[0]}, DecidedMatch={row[1]}, team-venue pairs={row[2]}"])

write_csv(RESULTS / "inference_examples.csv",
          ["query", "rows_inference_off", "values_inference_off", "rows_inference_on",
           "values_inference_on"], summary)
print("\nResults written to Results/")
