# Dataset — IPL 2026

## Source

- **Dataset:** [IPL 2026 – Complete Dataset](https://www.kaggle.com/datasets/krishd123/ipl-2026-complete-dataset) by Data Knight (Kaggle user `krishd123`), the dataset named in our approved proposal.
- **Licence:** CC0 Public Domain.
- **Original compilation:** manually from ESPNcricinfo, the IPL official website and Google (per the dataset card).
- **Downloaded:** 8 November 2026 through the Kaggle public download API. The untouched archive is kept as `ipl-2026-complete-dataset.zip`, extracted to `raw/`.

## Files

| File | Rows | Used for |
| --- | --- | --- |
| `raw/matches.csv` | 39 matches (1–39, 28 Mar – 27 Apr 2026) | Results, scores, wickets, balls left, toss — **completed matches** |
| `raw/deliveries.csv` | 17,477 balls, all 74 matches | Batting order, legal-ball counts, and teams/date/venue of matches 40–70 — **remaining fixtures** |
| `raw/venues.csv` | 12 venues | City and home team of each ground |
| `raw/points_table.csv` | 10 teams, after match 39 | **Validation only**: the official table we check our standings against |
| `raw/squads.csv`, `batting_stats.csv`, `bowling_stats.csv`, `fielding_stats.csv` | — | Not used: players are outside the qualification model |

The dataset card says `matches.csv` has 74 rows, but the file stops at match 39, the same point as
`points_table.csv`. We use that as the **season snapshot**: matches 1–39 are completed, matches 40–70
are scheduled fixtures, and matches 71–74 (playoffs) are outside the league-stage model.

## Cleaning and transformation

All cleaning is done by `../RDF_Knowledge_Graph/build_kg.py`. The cleaned table is
`processed/league_matches_clean.csv` (one row per league match).

1. **Scores from the summary, not the ball-by-ball file.** In 23 innings the runs summed from
   `deliveries.csv` differ from `matches.csv` by 1–3 runs (one innings even has 121 legal balls).
   Runs and wickets are therefore taken from `matches.csv`. The ball-by-ball file is used only for
   batting order, legal-ball counts and the remaining fixtures.
2. **Winner from the scores.** The winner is the side with more runs; `match_winner` is trusted only
   for ties (super over, match 38). This corrected **match 32**: `match_winner` says LSG, but RR made
   159/6 and LSG were all out for 119, so RR won by 40 runs. The official table agrees (RR 5 wins).
3. **Balls faced** (stored as legal balls; overs like 19.4 cannot be used in arithmetic):
   - first innings not all out → the full quota (120 balls);
   - second innings won by the chasing side, or all out → quota − `balls_left`;
   - first innings all out → legal balls counted from `deliveries.csv`.
4. **Rain-shortened matches.** If a first innings was not all out but is more than an over short of 20
   overs, the match is treated as shortened. **Match 13** (RR v MI) was 11 overs a side; it gets
   `qp:oversPerSide 11` and both innings are counted as 66 balls for NRR.
5. **Venue names unified.** The same ground appears under up to three spellings
   (e.g. "M. Chinnaswamy Stadium, Bangalore", "M.Chinnaswamy Stadium, Bengaluru", "M. Chinnaswamy Stadium").
   Each venue is matched by a keyword and mapped to one official name and city. Two grounds used in
   the season are missing from `venues.csv` and were added: Shaheed Veer Narayan Singh International
   Stadium (Raipur) and, under its current name, the HPCA Stadium (Dharamshala). 13 venues in total.
6. **Team names unified.** `matches.csv` uses abbreviations (RCB) and `points_table.csv` uses full names;
   both are mapped to one team resource with `qp:shortName` and `rdfs:label`.
7. **Dates** in two formats ("March 28, 2026" and "Mar 28, 2026") are converted to `xsd:date`.
8. **Abandoned match 12** (KKR v PBKS) is loaded as a `qp:NoResultMatch` with no innings (its 22
   recorded balls do not count for NRR).
9. **Super-over balls** (innings 3 and 4 of match 38) are ignored, as NRR excludes super overs.

## Validation

After cleaning, our standings after match 39 match the official `points_table.csv` for **all 10
teams** on played, won, lost, no-result and points, and on NRR to three decimals for 9 teams
(`../Results/validation_standings_vs_official.csv`).

The exception is **KKR**: we compute −0.751 and the file says +0.751. With 2 wins and 5 losses a
positive NRR is implausible, and the magnitude matches exactly, so we treat it as a dropped minus sign
in the source file.
