# Rules R1-R3: create one qp:StandingEntry per team per season.
#   R1 points            = won x pointsForWin + lost x pointsForLoss + noResult x pointsForNoResult
#   R2 netRunRate        = runs scored / overs faced - runs conceded / overs bowled
#                          (an all-out innings counts as the full quota; shortened matches use oversPerSide)
#   R3 maxReachablePoints = points + remaining fixtures x pointsForWin
# Needs OWL 2 RL inference on (uses inferred qp:CompletedMatch and qp:participatesIn).
# Run order: R1_R3 -> R4_R6 -> R7, before the SELECT queries.

PREFIX qp:  <http://example.org/qualifypath/ontology#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

INSERT {
  ?se a qp:StandingEntry ;
      qp:standingOf ?t ;
      qp:standingIn ?s ;
      qp:played ?played ;
      qp:won ?won ;
      qp:lost ?lost ;
      qp:noResult ?noResult ;
      qp:points ?points ;
      qp:netRunRate ?nrr ;
      qp:maxReachablePoints ?maxPts .
}
WHERE {
  # R1: results of completed matches
  {
    SELECT ?s ?t (COUNT(?m) AS ?played) (SUM(?w) AS ?won) (SUM(?l) AS ?lost) (SUM(?nr) AS ?noResult)
           (SUM(?w * ?pw + ?l * ?pl + ?nr * ?pnr) AS ?points)
    WHERE {
      ?s qp:hasPointsRule ?rule .
      ?rule qp:pointsForWin ?pw ; qp:pointsForLoss ?pl ; qp:pointsForNoResult ?pnr .
      ?t a qp:Team ; qp:participatesIn ?m .
      ?m a qp:CompletedMatch ; qp:inSeason ?s .
      BIND(IF(EXISTS { ?m qp:hasWinner ?t }, 1, 0) AS ?w)
      BIND(IF(EXISTS { ?m qp:hasLoser ?t }, 1, 0) AS ?l)
      BIND(IF(EXISTS { ?m a qp:NoResultMatch }, 1, 0) AS ?nr)
    }
    GROUP BY ?s ?t
  }
  # R2: net run rate from innings
  {
    SELECT ?s ?t (ROUND((SUM(?rf) / (SUM(?bf) / 6) - SUM(?ra) / (SUM(?bb) / 6)) * 1000) / 1000 AS ?nrr)
    WHERE {
      VALUES ?role { "bat" "bowl" }
      ?s qp:oversQuota ?quota .
      ?m qp:inSeason ?s ; a qp:CompletedMatch ; qp:hasInnings ?inn .
      OPTIONAL { ?m qp:oversPerSide ?short }
      ?inn qp:battingTeam ?bat ; qp:bowlingTeam ?bowl ; qp:runs ?runs ;
           qp:ballsFaced ?balls ; qp:allOut ?allOut .
      BIND(IF(?allOut, COALESCE(?short, ?quota) * 6, ?balls) AS ?nrrBalls)
      BIND(IF(?role = "bat", ?bat, ?bowl) AS ?t)
      BIND(IF(?role = "bat", ?runs, 0) AS ?rf)
      BIND(IF(?role = "bat", ?nrrBalls, 0) AS ?bf)
      BIND(IF(?role = "bowl", ?runs, 0) AS ?ra)
      BIND(IF(?role = "bowl", ?nrrBalls, 0) AS ?bb)
    }
    GROUP BY ?s ?t
  }
  # R3: fixtures still to play
  {
    SELECT ?s ?t (COUNT(?f) AS ?remaining)
    WHERE {
      ?s a qp:Season .
      ?t a qp:Team .
      OPTIONAL { ?f a qp:ScheduledMatch ; qp:inSeason ?s ; qp:hasParticipant ?t . }
    }
    GROUP BY ?s ?t
  }
  ?s qp:hasPointsRule/qp:pointsForWin ?winPts .
  ?t qp:shortName ?short .
  BIND(?points + ?remaining * ?winPts AS ?maxPts)
  BIND(IRI(CONCAT("http://example.org/qualifypath/resource/standing/",
                  STRAFTER(STR(?s), "/season/"), "-", ?short)) AS ?se)
}
