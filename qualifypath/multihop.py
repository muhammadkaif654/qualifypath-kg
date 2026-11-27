"""
Option C - Multi-hop KG reasoning.

Every answer is produced by walking connected relationships in the knowledge graph, and every walk is
kept as a *reasoning path*: a list of hops (subject, predicate, object) with the provenance of each
hop (explicit / OWL-inferred / rule-derived). Two kinds of reasoning are provided:

1. Generic path search (`find_paths`): breadth-first search over entity-to-entity relations that returns
   the shortest connecting paths between two entities, e.g. how RR is connected to Wankhede Stadium.
2. Question-specific multi-hop chains (CQ4, CQ5-CQ7, CQ8, CQ10, CQ11, CQ13 and transitive win chains),
   each following a fixed relation pattern and reporting every intermediate entity.

Hypothetical "what-if" outcomes (CQ10) are labelled as scenarios, never as facts.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from rdflib import RDF, URIRef

from .kg import KG, QP, SEASON_ID, load_kg

# Relations the generic path search may traverse (inverse duplicates and season hubs left out
# so that paths stay meaningful: everything is trivially connected through the season node).
PATH_RELATIONS = [QP.participatesIn, QP.hasWinner, QP.hasLoser, QP.playedAt, QP.scheduledAt,
                  QP.locatedIn, QP.homeVenue]


@dataclass
class Hop:
    s: URIRef
    p: URIRef
    o: object
    provenance: str
    forward: bool = True  # False when the path walks the relation backwards

    def text(self, kg: KG) -> str:
        p = str(self.p).rsplit("#", 1)[-1]
        if self.forward:
            return f"{kg.label(self.s)} --{p}--> {kg.label(self.o)}"
        return f"{kg.label(self.o)} <--{p}-- {kg.label(self.s)}"


@dataclass
class Result:
    question: str
    answer: str
    items: list = field(default_factory=list)        # structured answer (for evaluation)
    paths: list[list[Hop]] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)   # reasoning steps in words
    scenario: bool = False                           # True for hypothetical what-if answers

    def render(self, kg: KG, max_paths: int = 20) -> str:
        out = [f"Q: {self.question}", f"A: {self.answer}"]
        if self.scenario:
            out.append("   (hypothetical scenario - not a fact stored in or inferred from the graph)")
        if self.steps:
            out.append("Reasoning steps:")
            out += [f"  {i}. {s}" for i, s in enumerate(self.steps, 1)]
        if self.paths:
            out.append(f"Reasoning paths ({len(self.paths)}):")
            for path in self.paths[:max_paths]:
                out.append("  " + "  =>  ".join(f"{h.text(kg)} [{h.provenance}]" for h in path))
        return "\n".join(out)


class MultiHopReasoner:
    def __init__(self, kg: KG | None = None):
        self.kg = kg or load_kg()
        self.places = self.kg.season_rule(QP.qualifyingPlaces)
        self.win_pts = self.kg.season_rule(QP.pointsForWin)

    # ------------------------------------------------------------------ helpers
    def hop(self, s, p, o, forward=True) -> Hop:
        return Hop(s, p, o, self.kg.provenance(s, p, o), forward)

    def _team_matches(self, team, cls):
        g = self.kg.full
        ms = [m for m in g.objects(team, QP.participatesIn) if (m, RDF.type, cls) in g]
        return sorted(ms, key=self.kg.match_number)

    def _opponent(self, m, team):
        return next(t for t in self.kg.full.objects(m, QP.hasParticipant) if t != team)

    def _standing_facts(self, team):
        g, se = self.kg.full, self.kg.standing(team)
        return se, int(g.value(se, QP.points)), int(g.value(se, QP.maxReachablePoints))

    # ------------------------------------------------------------------ 1. generic path search
    def find_paths(self, start: URIRef, end: URIRef, max_hops: int = 4, limit: int = 5) -> Result:
        g = self.kg.full
        q = f"How is {self.kg.label(start)} connected to {self.kg.label(end)}?"
        found: list[list[Hop]] = []
        queue = deque([(start, [])])
        best = None
        while queue:
            node, path = queue.popleft()
            if best is not None and len(path) > best:
                break
            if node == end and path:
                best = len(path)
                found.append(path)
                if len(found) >= limit:
                    break
                continue
            if len(path) >= max_hops:
                continue
            visited = {start} | {h.o if h.forward else h.s for h in path}
            for p in PATH_RELATIONS:
                for o in g.objects(node, p):
                    if isinstance(o, URIRef) and o not in visited:
                        queue.append((o, path + [self.hop(node, p, o, True)]))
                for s in g.subjects(p, node):
                    if s not in visited:
                        queue.append((s, path + [Hop(s, p, node, self.kg.provenance(s, p, node), False)]))
        if not found:
            return Result(q, f"No path of up to {max_hops} hops found.")
        return Result(q, f"{len(found)} shortest path(s) of {best} hops.", paths=found,
                      items=[[(h.text(self.kg)) for h in p] for p in found])

    # ------------------------------------------------------------------ 2. CQ4 remaining fixtures
    def remaining_fixtures(self, team: URIRef) -> Result:
        kg, t = self.kg, self.kg.label(team)
        paths, items = [], []
        for m in self._team_matches(team, QP.ScheduledMatch):
            opp, venue = self._opponent(m, team), kg.value(m, QP.scheduledAt)
            city = kg.value(venue, QP.locatedIn)
            paths.append([self.hop(team, QP.participatesIn, m), self.hop(m, RDF.type, QP.ScheduledMatch),
                          self.hop(m, QP.hasParticipant, opp), self.hop(m, QP.scheduledAt, venue),
                          self.hop(venue, QP.locatedIn, city)])
            items.append((kg.match_number(m), kg.label(opp), str(kg.value(m, QP.matchDate)), kg.label(city)))
        ans = f"{t} has {len(items)} fixtures left: " + "; ".join(
            f"match {n} v {o} on {d} in {c}" for n, o, d, c in items)
        return Result(f"Which fixtures does {t} still have to play?", ans, items=items, paths=paths)

    # ------------------------------------------------------------------ 3. CQ5-CQ7 qualification
    def qualification(self, team: URIRef) -> Result:
        kg, t = self.kg, self.kg.label(team)
        se, pts, mx = self._standing_facts(team)
        remaining = (mx - pts) // self.win_pts
        others = []
        for o in kg.teams():
            if o != team:
                _, op, om = self._standing_facts(o)
                others.append((kg.label(o), op, om))
        out_of_reach = [o for o, op, _ in others if op > mx]
        can_catch = [o for o, _, om in others if om >= pts]
        status = kg.status_of(se)
        # wins needed: to stay alive (fewer than `places` teams already above the reachable total)
        # and to guarantee a place on points alone (fewer than `places` teams able to reach it)
        alive = next((w for w in range(remaining + 1)
                      if sum(op > pts + w * self.win_pts for _, op, _ in others) < self.places), None)
        safe = next((w for w in range(remaining + 1)
                     if sum(om >= pts + w * self.win_pts for _, _, om in others) < self.places), None)
        steps = [
            f"{t} <-standingOf- {kg.label(se)}: points = {pts} (rule R1), maxReachablePoints = {mx} "
            f"(rule R3: {pts} + {remaining} remaining x {self.win_pts}).",
            f"IPL 2026 -hasQualificationRule-> qualifyingPlaces = {self.places}.",
            f"Teams already above {t}'s reachable maximum ({mx}): {out_of_reach or 'none'} "
            f"-> {len(out_of_reach)} < {self.places}, so not eliminated." if len(out_of_reach) < self.places else
            f"Teams already above {t}'s reachable maximum ({mx}): {out_of_reach} -> eliminated (rule R4).",
            f"Teams that can still reach {t}'s current {pts} points: {len(can_catch)} "
            f"({'>=' if len(can_catch) >= self.places else '<'} {self.places}), so "
            f"{'not yet qualified' if len(can_catch) >= self.places else 'qualified (rule R5)'}.",
            f"Status from rules R4-R6: {status}.",
        ]
        if alive is not None:
            steps.append(f"Wins needed to stay mathematically alive: {alive} of {remaining}.")
        steps.append(f"Wins that guarantee a top-{self.places} finish on points alone, whatever other "
                     f"results: {safe if safe is not None else 'none - also depends on other results or NRR'}.")
        paths = [[self.hop(se, QP.standingOf, team, True), self.hop(se, QP.points, kg.value(se, QP.points)),
                  self.hop(se, QP.maxReachablePoints, kg.value(se, QP.maxReachablePoints)),
                  self.hop(se, RDF.type, {"qualified": QP.QualifiedStanding, "eliminated": QP.EliminatedStanding,
                                          "in contention": QP.InContentionStanding}[status])]]
        ans = (f"{t} has {pts} points with {remaining} matches left (maximum {mx}). Status: {status}. "
               + (f"It needs {safe} more win(s) to guarantee a top-{self.places} place on points alone."
                  if safe is not None else "No number of wins guarantees qualification on points alone."))
        return Result(f"Can {t} still qualify, and what does it need?", ans,
                      items={"points": pts, "max": mx, "status": status, "remaining": remaining,
                             "out_of_reach": sorted(out_of_reach), "safe_wins": safe, "alive_wins": alive},
                      steps=steps, paths=paths)

    # ------------------------------------------------------------------ 4. CQ8 direct rivals
    def rivals(self, team: URIRef) -> Result:
        kg, t = self.kg, self.kg.label(team)
        _, pts, _ = self._standing_facts(team)
        paths, items = [], []
        for m in self._team_matches(team, QP.ScheduledMatch):
            opp = self._opponent(m, team)
            ose, op, _ = self._standing_facts(opp)
            if kg.status_of(ose) == "in contention":
                paths.append([self.hop(team, QP.participatesIn, m), self.hop(m, QP.hasParticipant, opp),
                              self.hop(ose, QP.standingOf, opp), self.hop(ose, RDF.type, QP.InContentionStanding)])
                items.append((kg.match_number(m), kg.label(opp), op, abs(op - pts)))
        items.sort(key=lambda x: (x[3], x[0]))
        ans = f"{t}'s remaining opponents still in contention, closest on points first: " + "; ".join(
            f"{o} ({p} pts, gap {gap}) in match {n}" for n, o, p, gap in items)
        return Result(f"Which of {t}'s remaining opponents are direct rivals?", ans, items=items, paths=paths)

    # ------------------------------------------------------------------ 5. CQ10 what-if
    def what_if_lose_last(self, team: URIRef) -> Result:
        kg, t = self.kg, self.kg.label(team)
        _, pts, mx = self._standing_facts(team)
        fixtures = self._team_matches(team, QP.ScheduledMatch)
        last = max(fixtures, key=lambda m: (str(kg.value(m, QP.matchDate)), kg.match_number(m)))
        opp = self._opponent(last, team)
        cap = mx - self.win_pts
        above, level_or_above = [], []
        for o in kg.teams():
            if o in (team,):
                continue
            _, op, om = self._standing_facts(o)  # om already counts the opponent's win over `team`
            if op > cap:
                above.append(kg.label(o))
            elif om >= cap:
                level_or_above.append(kg.label(o))
        steps = [f"{t} -participatesIn-> last ScheduledMatch {kg.label(last)} "
                 f"(latest matchDate {kg.value(last, QP.matchDate)}) -hasParticipant-> {kg.label(opp)}.",
                 f"Scenario: {t} loses that match, so {kg.label(opp)} gets the win.",
                 f"{t}'s best possible total becomes {mx} - {self.win_pts} = {cap}.",
                 f"Already above {cap} whatever happens: {above or 'none'}.",
                 f"Could still finish level with or above {t} (maximum >= {cap}): {level_or_above or 'none'}; "
                 f"level teams are separated by the tie-breaks (most wins, then net run rate)."]
        paths = [[self.hop(team, QP.participatesIn, last), self.hop(last, QP.hasParticipant, opp),
                  self.hop(last, QP.matchDate, kg.value(last, QP.matchDate))]]
        ans = (f"Scenario: if {t} loses its last match (match {kg.match_number(last)} v {kg.label(opp)}), "
               f"it can reach at most {cap} points. Teams certain to finish above: {above or 'none'}. "
               f"Teams that could finish level or above: {', '.join(level_or_above) or 'none'}.")
        return Result(f"If {t} loses its last match, which teams finish above it?", ans,
                      items={"cap": cap, "above": sorted(above), "level_or_above": sorted(level_or_above),
                             "last_match": kg.match_number(last), "opponent": kg.label(opp)},
                      steps=steps, paths=paths, scenario=True)

    # ------------------------------------------------------------------ 6. CQ11 teams beaten
    def teams_beaten(self, team: URIRef) -> Result:
        kg, t = self.kg, self.kg.label(team)
        g = kg.full
        paths, items = [], []
        for m in sorted(g.subjects(QP.hasWinner, team), key=kg.match_number):
            loser, venue = g.value(m, QP.hasLoser), g.value(m, QP.playedAt)
            city = g.value(venue, QP.locatedIn)
            paths.append([self.hop(m, QP.hasWinner, team), self.hop(m, QP.hasLoser, loser),
                          self.hop(m, QP.playedAt, venue), self.hop(venue, QP.locatedIn, city)])
            items.append((kg.match_number(m), kg.label(loser), kg.label(city)))
        ans = f"{t} has beaten {len(items)} team(s): " + "; ".join(
            f"{o} in match {n} ({c})" for n, o, c in items)
        return Result(f"Which teams has {t} beaten, and where?", ans, items=items, paths=paths)

    # ------------------------------------------------------------------ 7. CQ13 venues (inferred chain)
    def venues_played(self, team: URIRef) -> Result:
        kg, t = self.kg, self.kg.label(team)
        g = kg.full
        paths, items = [], []
        for v in sorted(g.objects(team, QP.playedAtVenue), key=kg.label):
            m = next(m for m in self._team_matches(team, QP.CompletedMatch) if (m, QP.playedAt, v) in g)
            city = g.value(v, QP.locatedIn)
            paths.append([self.hop(team, QP.playedAtVenue, v),
                          self.hop(team, QP.participatesIn, m), self.hop(m, QP.playedAt, v),
                          self.hop(v, QP.locatedIn, city)])
            items.append((str(v).rsplit("/", 1)[-1], kg.full_name(v), kg.label(city)))
        ans = f"{t} has played at {len(items)} venue(s): " + "; ".join(f"{v} ({c})" for _, v, c in items)
        return Result(f"At which venues has {t} played?", ans, items=items, paths=paths,
                      steps=["playedAtVenue is not stored: it is inferred by the property chain "
                             "participatesIn o playedAt (O5); each path shows the match that supports it."])

    # ------------------------------------------------------------------ 8. transitive win chains
    def win_chains(self, a: URIRef, b: URIRef, max_len: int = 3) -> Result:
        kg = self.kg
        g = kg.full
        beat = {}
        for m in g.subjects(QP.hasWinner, None):
            beat.setdefault(g.value(m, QP.hasWinner), []).append((g.value(m, QP.hasLoser), m))
        chains, queue = [], deque([(a, [])])
        while queue:
            node, path = queue.popleft()
            if node == b and path:
                chains.append(path)
                continue
            if len(path) >= max_len:
                continue
            seen = {a} | {x for x, _ in path}
            for loser, m in beat.get(node, []):
                if loser not in seen or loser == b:
                    queue.append((loser, path + [(loser, m)]))
        paths, items = [], []
        for chain in chains:
            hops, prev, names = [], a, [kg.label(a)]
            for loser, m in chain:
                hops += [self.hop(m, QP.hasWinner, prev), self.hop(m, QP.hasLoser, loser)]
                names.append(kg.label(loser))
                prev = loser
            paths.append(hops)
            items.append(" > ".join(names))
        q = f"Is there a chain of wins from {kg.label(a)} to {kg.label(b)}?"
        if not chains:
            return Result(q, f"No chain of up to {max_len} wins from {kg.label(a)} to {kg.label(b)}.")
        unique = sorted(set(items))  # the same team chain can be supported by different matches
        return Result(q, f"{len(unique)} chain(s), supported by {len(paths)} match path(s): "
                      + "; ".join(unique[:10]), items=unique, paths=paths)


if __name__ == "__main__":
    r = MultiHopReasoner()
    from .kg import TEAM
    for res in (r.remaining_fixtures(TEAM.RR), r.qualification(TEAM.LSG), r.what_if_lose_last(TEAM.KKR),
                r.teams_beaten(TEAM.RR), r.venues_played(TEAM.RR), r.rivals(TEAM.RR),
                r.win_chains(TEAM.RR, TEAM.PBKS), r.find_paths(TEAM.RR, TEAM.MI)):
        print(res.render(r.kg, max_paths=3), "\n")
