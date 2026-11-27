# Rule R7: league position = 1 + number of teams ranked above.
# IPL tie-break order (IPL rulebook clause 16.10.2): more points; if level, more wins (tie-break 1);
# if still level, higher net run rate (tie-break 2).
# Requires R1_R3 to have run.

PREFIX qp: <http://example.org/qualifypath/ontology#>

INSERT { ?se qp:position ?position }
WHERE {
  {
    SELECT ?se ((COUNT(?o) + 1) AS ?position)
    WHERE {
      ?se qp:standingIn ?s ; qp:points ?p ; qp:won ?w ; qp:netRunRate ?n .
      OPTIONAL {
        ?o qp:standingIn ?s ; qp:points ?op ; qp:won ?ow ; qp:netRunRate ?on .
        FILTER(?o != ?se && (?op > ?p || (?op = ?p && ?ow > ?w) || (?op = ?p && ?ow = ?w && ?on > ?n)))
      }
    }
    GROUP BY ?se
  }
}
