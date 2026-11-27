# Rules R4-R6: classify every standing entry (points only, so the result is conservative).
#   R4 EliminatedStanding   : at least qualifyingPlaces other teams already have MORE points
#                             than this team can still reach.
#   R5 QualifiedStanding    : fewer than qualifyingPlaces other teams can still reach
#                             this team's current points.
#   R6 InContentionStanding : neither of the above.
# Requires R1_R3 to have run.

PREFIX qp: <http://example.org/qualifypath/ontology#>

INSERT { ?se a ?status }
WHERE {
  ?se a qp:StandingEntry ; qp:standingIn ?s .
  ?s qp:hasQualificationRule/qp:qualifyingPlaces ?places .
  # teams already out of this team's reach
  {
    SELECT ?se (COUNT(?o) AS ?outOfReach)
    WHERE {
      ?se qp:standingIn ?s ; qp:maxReachablePoints ?myMax .
      OPTIONAL {
        ?o qp:standingIn ?s ; qp:points ?oPts .
        FILTER(?o != ?se && ?oPts > ?myMax)
      }
    }
    GROUP BY ?se
  }
  # teams that can still catch this team
  {
    SELECT ?se (COUNT(?o2) AS ?canCatch)
    WHERE {
      ?se qp:standingIn ?s ; qp:points ?myPts .
      OPTIONAL {
        ?o2 qp:standingIn ?s ; qp:maxReachablePoints ?oMax .
        FILTER(?o2 != ?se && ?oMax >= ?myPts)
      }
    }
    GROUP BY ?se
  }
  BIND(IF(?outOfReach >= ?places, qp:EliminatedStanding,
       IF(?canCatch < ?places, qp:QualifiedStanding, qp:InContentionStanding)) AS ?status)
}
