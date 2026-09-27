# Data availability

No raw or row-level player data are included in this release. The private research master used a local La Liga extract containing player identities, valuation snapshots, season performance, teams, careers, positions, and competition metadata. The extract's redistribution licence was not established in the project evidence. Access therefore does not imply permission to republish it.

The released CSV files in `results/tables/` are aggregate or compact audit outputs used to verify the published claims. They do not support end-to-end model retraining.

## Required private schema

An authorized user seeking to reproduce the pipeline needs, at minimum:

- player identifiers and decision-date valuation snapshots in EUR;
- date of birth and position history;
- completed-prior-season minutes, starts, goals, and assists;
- club/competition/season membership and team-strength context;
- enough subsequent valuation history to match the first qualifying snapshot at least six months after each decision date.

The unit of analysis is `(player_id, decision_date)`. The six-month label is `ln(future_value / current_value)`. Future fields must never enter the feature matrix.

Reproducibility is **PARTIAL**: included aggregate evidence can be checked, but the private source data and frozen model binaries are withheld pending a redistribution-rights decision.
