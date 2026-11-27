"""
KG retrieval for the question-answering application (SPARQL-generated context + multi-hop paths).

  question --> entity linking (teams, venues, match numbers)
           --> intent detection (keyword patterns mapped to competency questions)
           --> retrieval: Iteration 1 SPARQL queries + multi-hop reasoner (Option C)
           --> numbered evidence facts, each tagged with its provenance

Provenance tags: explicit (stored triple), inferred (OWL 2 RL), rule-derived (SPARQL rules R1-R7),
reasoning path (multi-hop chain over the above), scenario (hypothetical what-if, not a fact).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from rdflib import RDF, RDFS, URIRef

from .kg import EXPLICIT, INFERRED, KG, QP, RES, ROOT, SEASON_ID, TEAM, load_kg
from .multihop import MultiHopReasoner, Result

QUERIES = ROOT / "SPARQL_Queries"

TEAM_ALIASES = {
    "CSK": ["csk", "chennai super kings", "chennai"],
    "DC": ["dc", "delhi capitals", "delhi"],
    "GT": ["gt", "gujarat titans", "gujarat", "titans"],
    "KKR": ["kkr", "kolkata knight riders", "knight riders", "kolkata"],
    "LSG": ["lsg", "lucknow super giants", "lucknow", "super giants"],
    "MI": ["mi", "mumbai indians", "mumbai"],
    "PBKS": ["pbks", "punjab kings", "punjab"],
    "RCB": ["rcb", "royal challengers bengaluru", "royal challengers", "bangalore", "bengaluru"],
    "RR": ["rr", "rajasthan royals", "rajasthan"],
    "SRH": ["srh", "sunrisers hyderabad", "sunrisers", "hyderabad"],
}

INTENTS = {
    "standings": r"\btable\b|standing|position|\brank|top (four|4)|top-4|qualifying place|leader|first place|who (is|are) top",
    "nrr": r"net run rate|\bnrr\b|run rate",
    "fixtures": r"remaining|still (have|has|got) to play|fixture|upcoming|next match|left to play|still to play|schedule",
    "qualification": r"qualif|eliminat|knocked out|chance|still (reach|make)|playoff|make the top|need(s)? to",
    "rivals": r"rival|direct competitor|in contention",
    "what_if": r"what if|\bif\b.*\blos(e|es|t)\b|\blos(e|es) (its|their) last",
    "beaten": r"\bbeat(en)?\b|defeat|won against|wins against|victor",
    "venues": r"venue|stadium|ground|where .*play|played at|which cit(y|ies)|\bcit(y|ies)\b",
    "home": r"\bhome\b",
    "no_result": r"no result|abandon|washed out|\brain",
    "rules": r"\brules?\b|tie-?break|points? (for|per) (a )?win|how many points (is|are|do)|format|how many teams qualify",
    "chains": r"chain|transitiv|beat .* who beat|indirect",
    "connection": r"connected|relationship between|link between|connection",
    "results": r"result|record|\bwon\b|\blost\b|\bwins\b|\blosses\b|points|how (is|are) .* doing|form",
    "match": r"\bmatch(es)?\s*(no\.?|number|#)?\s*\d+",
    "head_to_head": r"\bvs\.?\b|\bversus\b|\bagainst\b|head.to.head|\bbetween\b",
}


@dataclass
class Fact:
    id: str
    text: str
    kind: str          # explicit | inferred | rule-derived | reasoning path | scenario
    source: str = ""   # which query / reasoning step produced it


@dataclass
class Retrieval:
    question: str
    teams: list[URIRef] = field(default_factory=list)
    venues: list[URIRef] = field(default_factory=list)
    matches: list[int] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    results: list[Result] = field(default_factory=list)   # multi-hop reasoning results (paths)

    def context(self) -> str:
        return "\n".join(f"[{f.id}] ({f.kind}) {f.text}" for f in self.facts)


class Retriever:
    def __init__(self, kg: KG | None = None):
        self.kg = kg or load_kg()
        self.mh = MultiHopReasoner(self.kg)
        self._venues = {}
        for v in self.kg.full.subjects(RDF.type, QP.Venue):
            names = {str(self.kg.full.value(v, RDFS.label)).lower()}
            city = self.kg.full.value(v, QP.locatedIn)
            names.add(str(self.kg.full.value(city, RDFS.label)).lower())
            for n in list(names):
                names.update(w for w in re.findall(r"[a-z]{5,}", n) if w not in {"stadium", "cricket", "international"})
            self._venues[v] = names

    # ------------------------------------------------------------------ linking
    def link(self, q: str) -> tuple[list, list, list, list]:
        # "after match 39" names the snapshot, not a match the user is asking about
        ql = re.sub(r"\b(after|as of|since|until|up to)\s+match\s*\d+", " ", q.lower())
        teams = []
        for short, aliases in TEAM_ALIASES.items():
            hits = [re.search(rf"\b{re.escape(a)}\b", ql) for a in aliases]
            pos = min((h.start() for h in hits if h), default=None)
            if pos is not None:
                teams.append((pos, TEAM[short]))
        teams = [t for _, t in sorted(teams)]
        venues = []
        for v, names in self._venues.items():
            if any(re.search(rf"\b{re.escape(n)}\b", ql) for n in names) and \
                    re.search(INTENTS["venues"] + r"|stadium|gardens", ql):
                venues.append(v)
        matches = [int(n) for n in re.findall(r"\bmatch(?:es)?\s*(?:no\.?|number|#)?\s*(\d{1,2})\b", ql)]
        intents = [k for k, pat in INTENTS.items() if re.search(pat, ql)]
        return teams, venues, matches, intents

    # ------------------------------------------------------------------ main entry
    def retrieve(self, q: str) -> Retrieval:
        teams, venues, matches, intents = self.link(q)
        r = Retrieval(q, teams, venues, matches, intents)
        self._add = lambda text, kind, source="": r.facts.append(Fact(f"F{len(r.facts) + 1}", text, kind, source))
        if not (teams or venues or matches or set(intents) & {"standings", "rules", "no_result", "nrr"}):
            return r  # nothing in the question maps to the graph -> insufficient evidence
        if "rules" in intents or "qualification" in intents or "standings" in intents or "what_if" in intents:
            self.rules()
        if "standings" in intents or ("qualification" in intents and not teams) or ("nrr" in intents and not teams):
            self.standings()
        if "qualification" in intents and not teams:
            self.qualification_overview()
        for t in teams[:2]:
            self.team_standing(t)
            if "nrr" in intents:
                self.nrr(t)
            if "fixtures" in intents or "rivals" in intents:
                self.multihop(r, self.mh.remaining_fixtures(t))
            if "qualification" in intents:
                self.multihop(r, self.mh.qualification(t))
            if "rivals" in intents:
                self.multihop(r, self.mh.rivals(t))
            if "what_if" in intents:
                self.multihop(r, self.mh.what_if_lose_last(t), scenario=True)
            if "beaten" in intents and len(teams) == 1:
                self.multihop(r, self.mh.teams_beaten(t))
            if "venues" in intents:
                self.multihop(r, self.mh.venues_played(t))
            if "home" in intents:
                self.home(t)
            if "results" in intents or "beaten" in intents or not intents or intents == ["head_to_head"]:
                self.results(t)
        if len(teams) >= 2:
            a, b = teams[0], teams[1]
            self.head_to_head(a, b)
            if "chains" in intents or "beaten" in intents:
                self.multihop(r, self.mh.win_chains(a, b))
            if "connection" in intents:
                self.multihop(r, self.mh.find_paths(a, b))
        for v in venues[:2]:
            self.venue(v)
            for t in teams[:1]:
                if "connection" in intents:
                    self.multihop(r, self.mh.find_paths(t, v))
        for n in matches[:3]:
            self.match(n)
        if "no_result" in intents:
            self.no_results()
        return r

    # ------------------------------------------------------------------ retrieval functions
    def _sparql(self, name: str):
        return self.kg.query((QUERIES / name).read_text(encoding="utf-8"))

    def rules(self):
        rows = self._sparql("Q01_season_rules.rq")
        row = rows[0]
        ties = ", then ".join(f"({r.tieBreakRank}) {str(r.tieBreak).lower()}" for r in rows)
        self._add(f"IPL 2026 rules: {row.pointsForWin} points for a win, {row.pointsForLoss} for a loss, "
                  f"{row.pointsForNoResult} for a no result; {row.qualifyingPlaces} teams qualify from the "
                  f"league stage; teams level on points are separated by {ties}; {row.oversQuota} overs per side. "
                  "The knowledge graph is a snapshot after match 39 (27 April 2026); matches 40-70 are "
                  "scheduled fixtures without results.", EXPLICIT, "Q01")

    def _standing_text(self, row) -> str:
        return (f"{row.team}: position {row.position}, {row.points} points, played {row.played}, won {row.won}, "
                f"lost {row.lost}, no result {row.noResult}, net run rate {row.nrr}, "
                f"maximum reachable {row.maxPts} points, status {row.status}")

    def _standings(self, team=None):
        flt = f"FILTER(?t = <{team}>)" if team else ""
        q = f"""SELECT ?team ?position ?points ?played ?won ?lost ?noResult ?nrr ?maxPts ?status WHERE {{
          ?se qp:standingIn <{SEASON_ID}> ; qp:standingOf ?t ; qp:position ?position ; qp:points ?points ;
              qp:played ?played ; qp:won ?won ; qp:lost ?lost ; qp:noResult ?noResult ;
              qp:netRunRate ?nrr ; qp:maxReachablePoints ?maxPts ; a ?cls .
          ?cls rdfs:subClassOf qp:StandingEntry ; rdfs:label ?status . FILTER(?cls != qp:StandingEntry)
          ?t qp:shortName ?team . {flt} }} ORDER BY ?position"""
        return self.kg.query(q)

    def standings(self):
        rows = self._standings()
        self._add("League table after match 39 (computed by rules R1-R7 from the stored match results): "
                  + " | ".join(self._standing_text(r) for r in rows), "rule-derived", "R1-R7 standings")

    def qualification_overview(self):
        rows = self._standings()
        by = {}
        for r in rows:
            by.setdefault(str(r.status), []).append(f"{r.team} ({r.points} pts, max {r.maxPts})")
        top = max(int(r.points) for r in rows)
        low = min(rows, key=lambda r: int(r.maxPts))
        self._add("Qualification status of every team from rules R4-R6 (points only): "
                  + "; ".join(f"{k}: {', '.join(v)}" for k, v in by.items())
                  + f". Eliminated teams: {', '.join(by.get('Eliminated standing', [])) or 'none'}. "
                  f"Qualified teams: {', '.join(by.get('Qualified standing', [])) or 'none'}. "
                  f"The lowest reachable maximum is {low.team}'s {low.maxPts} points, above the current top "
                  f"score of {top}, so no team can be out yet.", "rule-derived", "R4-R6 status")

    def team_standing(self, team):
        for row in self._standings(team):
            self._add(self._standing_text(row), "rule-derived", "R1-R7 standing entry")

    def nrr(self, team):
        short = self.kg.label(team)
        for row in self._sparql("Q03_net_run_rate.rq"):
            if str(row.team) == short:
                self._add(f"{short} net run rate inputs: {row.runsFor} runs scored in {row.ballsFaced} balls, "
                          f"{row.runsAgainst} runs conceded in {row.ballsBowled} balls; NRR = {row.netRunRate} "
                          "(all-out innings counted as the full quota of overs).", "rule-derived", "Q03 / R2")

    def results(self, team):
        g, kg = self.kg.full, self.kg
        for m in sorted(g.objects(team, QP.participatesIn), key=kg.match_number):
            if (m, RDF.type, QP.CompletedMatch) not in g:
                continue
            self._add(self._match_text(m), EXPLICIT, f"match {kg.match_number(m)}")

    def _match_text(self, m) -> str:
        g, kg = self.kg.full, self.kg
        n, date = kg.match_number(m), g.value(m, QP.matchDate)
        venue = g.value(m, QP.playedAt) or g.value(m, QP.scheduledAt)
        where = f"{kg.full_name(venue)}, {kg.label(g.value(venue, QP.locatedIn))}"
        if (m, RDF.type, QP.ScheduledMatch) in g:
            a, b = sorted(kg.label(t) for t in g.objects(m, QP.hasParticipant))
            return f"Match {n} ({date}, {where}): {a} v {b} is a scheduled fixture, not yet played."
        if (m, RDF.type, QP.NoResultMatch) in g:
            a, b = sorted(kg.label(t) for t in g.objects(m, QP.hasParticipant))
            return f"Match {n} ({date}, {where}): {a} v {b} was abandoned with no result (1 point each)."
        w, l = kg.label(g.value(m, QP.hasWinner)), kg.label(g.value(m, QP.hasLoser))
        inns = []
        for i in sorted(g.objects(m, QP.hasInnings), key=lambda i: int(g.value(i, QP.inningsNumber))):
            inns.append(f"{kg.label(g.value(i, QP.battingTeam))} {g.value(i, QP.runs)}/{g.value(i, QP.wicketsLost)}")
        short = g.value(m, QP.oversPerSide)
        extra = f" (shortened to {short} overs a side)" if short else ""
        return f"Match {n} ({date}, {where}): {w} beat {l}; {' , '.join(inns)}{extra}."

    def match(self, n: int):
        m = URIRef(f"{RES}match/IPL-2026-M{n:02d}")
        if (m, QP.matchNumber, None) in self.kg.full:
            self._add(self._match_text(m), EXPLICIT, f"match {n}")

    def head_to_head(self, a, b):
        g = self.kg.full
        both = set(g.objects(a, QP.participatesIn)) & set(g.objects(b, QP.participatesIn))
        for m in sorted(both, key=self.kg.match_number):
            self._add(self._match_text(m), EXPLICIT, "head to head")

    def no_results(self):
        for m in self.kg.full.subjects(RDF.type, QP.NoResultMatch):
            self._add(self._match_text(m), EXPLICIT, "no-result matches")

    def venue(self, v):
        g, kg = self.kg.full, self.kg
        homes = [kg.label(t) for t in g.subjects(QP.homeVenue, v)]
        played = sorted(g.subjects(QP.playedAt, v), key=kg.match_number)
        self._add(f"{kg.full_name(v)} is in {kg.label(g.value(v, QP.locatedIn))}; home venue of "
                  f"{', '.join(homes) or 'no team'}; {len(played)} completed matches played there.", EXPLICIT, "venue")
        for m in played:
            self._add(self._match_text(m), EXPLICIT, "venue matches")

    def home(self, team):
        g, kg = self.kg.full, self.kg
        for v in g.objects(team, QP.homeVenue):
            ms = [m for m in g.subjects(QP.playedAt, v) if (team, QP.participatesIn, m) in g
                  and (m, RDF.type, QP.DecidedMatch) in g]
            wins = sum((m, QP.hasWinner, team) in g for m in ms)
            self._add(f"{kg.label(team)} home venue {kg.full_name(v)}: {len(ms)} decided matches there, "
                      f"{wins} won.", INFERRED, "homeVenue + playedAt")

    def multihop(self, r: Retrieval, res: Result, scenario: bool = False):
        r.results.append(res)
        kind = "scenario" if scenario or res.scenario else "reasoning path"
        self._add(f"{res.question} -> {res.answer}", kind, "multi-hop reasoner")
        for s in res.steps:
            self._add(s, kind, "multi-hop step")
        for path in res.paths[:8]:
            self._add("Path: " + " => ".join(f"{h.text(self.kg)} [{h.provenance}]" for h in path),
                      "reasoning path", "multi-hop path")


if __name__ == "__main__":
    import sys
    rt = Retriever()
    for q in sys.argv[1:] or ["Can Lucknow still qualify for the playoffs?"]:
        r = rt.retrieve(q)
        print(q, "| teams", [rt.kg.label(t) for t in r.teams], "| intents", r.intents)
        print(r.context()[:3000], "\n")
