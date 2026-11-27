"""
Load the QualifyPath knowledge graph in three layers and keep track of where every fact comes from.

  explicit  : ontology (T-Box) + IPL 2026 instance data (A-Box), exactly as stored in the .ttl files
  owl       : explicit + everything an OWL 2 RL reasoner derives (owlrl, same profile as GraphDB OWL2-RL)
  full      : owl + the SPARQL Update rules R1-R7 (standings, NRR, qualification status, position)

`KG.provenance(s, p, o)` tells whether a triple is explicit, OWL-inferred or rule-derived, so every
answer can separate stored facts from inferred ones.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path

import owlrl
from rdflib import RDF, RDFS, Graph, Literal, Namespace, URIRef

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY = ROOT / "Ontology" / "qualifypath.ttl"
ABOX = ROOT / "RDF_Knowledge_Graph" / "ipl2026_abox.ttl"
RULES_DIR = ROOT / "SPARQL_Queries" / "rules"

QP = Namespace("http://example.org/qualifypath/ontology#")
RES = "http://example.org/qualifypath/resource/"
TEAM = Namespace(RES + "team/")
MATCH = Namespace(RES + "match/")
SEASON = Namespace(RES + "season/")
SEASON_ID = SEASON["IPL-2026"]

EXPLICIT, INFERRED, RULE = "explicit", "inferred (OWL 2 RL)", "rule-derived (SPARQL R1-R7)"

# rdflib's SPARQL parser (pyparsing) is not thread-safe; Streamlit runs each session in its own
# thread, so every parse/query/update goes through this lock.
SPARQL_LOCK = threading.RLock()


@dataclass
class KG:
    explicit: Graph
    owl: Graph
    full: Graph
    _labels: dict = field(default_factory=dict)

    # ---------------------------------------------------------------- provenance
    def provenance(self, s, p, o) -> str:
        if (s, p, o) in self.explicit:
            return EXPLICIT
        if (s, p, o) in self.owl:
            return INFERRED
        return RULE

    # ---------------------------------------------------------------- labels
    def label(self, node) -> str:
        if isinstance(node, Literal):
            return str(node)
        if node in self._labels:
            return self._labels[node]
        short = self.full.value(node, QP.shortName)
        lab = self.full.value(node, RDFS.label)
        text = str(short or lab or str(node).rsplit("/", 1)[-1].rsplit("#", 1)[-1])
        self._labels[node] = text
        return text

    def full_name(self, node) -> str:
        lab = self.full.value(node, RDFS.label)
        return str(lab) if lab else self.label(node)

    def value(self, s, p):
        return self.full.value(s, p)

    def query(self, sparql: str) -> list:
        with SPARQL_LOCK:
            return list(self.full.query(sparql, initNs={"qp": QP, "rdfs": RDFS, "rdf": RDF}))

    # ---------------------------------------------------------------- domain helpers
    def teams(self) -> list[URIRef]:
        return sorted(set(self.full.subjects(RDF.type, QP.Team)), key=self.label)

    def standing(self, team: URIRef) -> URIRef | None:
        return self.full.value(None, QP.standingOf, team)

    def status_of(self, standing: URIRef) -> str:
        for cls, name in ((QP.QualifiedStanding, "qualified"), (QP.EliminatedStanding, "eliminated"),
                          (QP.InContentionStanding, "in contention")):
            if (standing, RDF.type, cls) in self.full:
                return name
        return "unknown"

    def match_number(self, m: URIRef) -> int:
        return int(self.full.value(m, QP.matchNumber))

    def season_rule(self, prop) -> int:
        q = f"SELECT ?v WHERE {{ <{SEASON_ID}> ?r ?rule . ?rule <{prop}> ?v . }}"
        return int(self.query(q)[0][0])


def _apply_rules(g: Graph) -> None:
    for rule in sorted(RULES_DIR.glob("*.ru")):
        g.update(rule.read_text(encoding="utf-8"))


_KG: KG | None = None


def load_kg() -> KG:
    global _KG
    with SPARQL_LOCK:
        if _KG is None:
            _KG = _build()
        return _KG


def _build() -> KG:
    explicit = Graph()
    explicit.parse(ONTOLOGY)
    explicit.parse(ABOX)
    owl = Graph()
    owl += explicit
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(owl)
    full = Graph()
    full += owl
    _apply_rules(full)
    for g in (explicit, owl, full):
        g.bind("qp", QP)
    return KG(explicit=explicit, owl=owl, full=full)


if __name__ == "__main__":
    kg = load_kg()
    print(f"explicit {len(kg.explicit)}  +OWL {len(kg.owl)}  +rules {len(kg.full)} triples")
