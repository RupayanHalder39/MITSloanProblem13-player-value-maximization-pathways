# From Forecast to Pathway: Market-Value Scenario Analysis for La Liga Player Development

> **Publication status: blocked pending data-licence, authorship, and blind-review confirmation.**
> The code and aggregate results are prepared locally, but raw and row-level data cannot be
> released without confirmed redistribution rights. Do not publish or submit this repository yet.
> See `PUBLIC_RELEASE_AUDIT.md`.

## Research question

Can the information available to a football club on a player's valuation date predict how his
market value will change over the next six months? If so, can that forecast support transparent
development scenarios without implying that any milestone causes value growth?

A club knows what a player is worth today, but transfer, retention, and academy decisions also
depend on where that value may be heading. Two players with similar current values can have very
different recent trajectories, playing histories, and development contexts.

## Dataset

The analysis covers **1,132 La Liga players and 8,433 valuation events** from July 2022 to June
2025. Each observation represents one player at one valuation date. The model can use only
information known by that date: current market value and recent valuation movement, age, position,
completed-prior-season minutes, starts, goals and assists, milestone state, and available team
context. Future information is reserved for constructing the outcome.

Raw and row-level records are excluded because no redistribution licence was established. The
release therefore contains code, documentation, figures, and aggregate evidence only. See
`data/README.md`.

## Market-value target and forecast

The prediction target is the six-month log market-value return:

`ln(first qualifying observed market value at least six months later / current market value)`

In football terms, the model starts with the player's value at the decision date, finds the first
eligible valuation snapshot at least six months later, and predicts the proportional change
between the two. It forecasts an observed market-value estimate, not a transfer fee and not value
caused by a club intervention.

## Prediction task and comparisons

The split is chronological. TRAIN covers July 2022–December 2023, VALIDATION covers January–June
2024, and the untouched TEST period covers July 2024–June 2025. Candidate models included Ridge,
Extra Trees, Gradient Boosting, and HistGradientBoosting. They were assessed alongside persistence,
value-momentum, and comparable-player baselines. The selected six-month model is a frozen
`HistGradientBoostingRegressor`.

Mean absolute error (MAE) measures the typical absolute miss on the log-return scale; lower is
better. Spearman correlation measures whether the model ranks higher-growth and lower-growth
events in roughly the right order; higher is better.

## Development-scenario pathways

The pathway engine extends the frozen forecast into a set of milestone-based what-if scenarios.
It changes one feasible state at a time—such as playing-time, starter, output, or team-context
state—scores that hypothetical state with the six-month model, and retains several four-step paths.
Each step carries uncertainty and an evidence tier. Club change is excluded from the scenario menu,
and a historically derived cumulative multiplier cap limits implausible compounding from very low
starting values.

These paths are not instructions. A milestone may be associated with later value growth without
causing it; a model-generated pathway is not a guaranteed future. Clubs can use the output to
compare conditional possibilities and identify where evidence is weak, but not to conclude that
making a player reach a milestone will produce the forecasted value.

## Main findings

The strongest independent result is the six-month model on held-out TEST: **n = 1,345 valuation
events, MAE = 0.3094, Spearman rho = 0.5916**. It matched or improved on VALIDATION (**n = 1,188,
MAE = 0.3390, Spearman rho = 0.5688**). The 12-month TEST evaluation has only **10 finite labels**
and is inconclusive; it is not evidence of successful long-horizon forecasting.

![Held-out predictive evidence](results/figures/Figure1_HeldOutPredictiveEvidence.png)

Separate one-parameter sweeps on 32 events found 100% first-step agreement for uncertainty penalty
lambda ≥ 0.20 and beam width ≥ 5. A broader five-variant audit asked a harder question on 16
events: 12 (75%) were stable and four were partially stable. These are different experiments, not
competing estimates.

The overall pathway verdict remains **partially robust**. Historical replay produced mean lift of
about −0.143 across 150 cases; matched replay remained negative or worsened for 9 of 11 milestones;
and milestone attainment was strongly predictable from prior player state, with AUC 0.86–1.00 for
9 of 11 milestones. Those diagnostics prevent causal interpretation.

The low-value stress case compounded from €25,000 to about €10.6 million (425×). The safety cap
reduced the scenario to €1.381 million (55.25×), and none of six known stress cases exceeded its
own ceiling. No path in a 20-case normal-value audit met the study's material-distortion rule,
although two first steps changed.

![Safety-capped development scenario](results/figures/Figure2_ScenarioPathwayWithSafetyCap.png)

## Reproduction

Python 3.12 was used for release testing.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/verify_release.py
```

The last command checks the published cohort, held-out metrics, robustness distinction, and safety
cap values against the included aggregate tables. Full model retraining is not possible from this
repository because the source rows and frozen model binaries are withheld pending a data-rights
decision. Reproducibility is therefore **partial**, not full. See `data/README.md` and
`docs/methodology.md`.

Expected headline output is TEST n=1,345 valuation events, MAE 0.3094, and Spearman rho 0.5916. A
failed check is not permission to change the frozen scientific constants.

## Limitations

The study covers one league over a short 2022–2025 period, so performance in other competitions is
unknown. Market values are observational estimates rather than realized transfer fees. The
12-month TEST sample is too small for a conclusion. Team context has incomplete coverage, while
performance features summarize the last completed season rather than current match-level form.
Historical replay is negative, matching retains material imbalance, and longer paths are less
stable than first steps. The €100 million marker is an illustrative scenario destination, not a
calibrated probability that a player will reach that value.

---

## Researcher

<p align="left">
  <img src="assets/RupayanHalder.jpeg"
       width="150"
       alt="Rupayan Halder">
</p>

### Rupayan Halder

**PhD Student**<br>
Jadavpur University, Kolkata

**Football AI Researcher**

**Assistant Professor**<br>
University of Engineering & Management (UEM), Kolkata

**Research Collaborator**<br>
SoccerSolver

**Former Software Engineer — Platform Engineering**<br>
Session AI

Rupayan's research interests focus on applying artificial intelligence, machine learning, data
analytics, and computational methods to real-world problems in football, including player
performance analysis, recruitment, transfer-market decision-making, and sporting strategy.

### Connect

[GitHub](https://github.com/RupayanHalder39) ·
[LinkedIn](https://www.linkedin.com/in/rupayan-halder-962922209/) ·
[Email](mailto:rupayanhalder313239@gmail.com)

---

## Research Collaboration

<p align="left">
  <img src="assets/SoccerSolverLogo.png"
       width="180"
       alt="SoccerSolver">
</p>

**This research was developed in collaboration with SoccerSolver.**

---

## Citation

Rupayan Halder is a confirmed researcher/author of this project. The complete author list is still
being finalized; no claim of sole authorship is made. Use the metadata in `CITATION.cff`, and
resolve the remaining authorship placeholder before publication.

## Licence

The repository software is provided under the MIT License. This does not grant rights to the
underlying private or third-party data, names, marks, photographs, or other provider content. Data
access and redistribution remain subject to separate authorization; see `PUBLIC_RELEASE_AUDIT.md`.
