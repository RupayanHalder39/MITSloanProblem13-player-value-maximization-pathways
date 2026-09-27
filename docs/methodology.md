# Methodology

The cohort contains 1,132 players with 8,433 La Liga valuation events from 1 July 2022 through 30 June 2025. One observation is a player at a valuation date. At that decision point, features describe current value and momentum, age, position, completed-prior-season performance, milestone state, and available team context.

The primary target is the log change in observed market value at the first qualifying valuation snapshot at least six months later:

`future_log_return_6m = ln(future_value_6m / current_value)`

This is a market-value forecast, not a transfer-fee forecast. MAE is the average absolute error on this log-return scale; lower is better. Spearman correlation measures whether predicted growth ranks players similarly to observed growth; higher is better.

The chronological split is TRAIN (2022-07-01–2023-12-29), VALIDATION (2024-01-08–2024-06-30), and TEST (2024-07-18–2025-06-30). TEST was opened once. Ridge, Extra Trees, Gradient Boosting, persistence, momentum, and comparable-player baselines were considered. A HistGradientBoostingRegressor was frozen for the six-month task.

The scenario engine searches across 18 eligible milestones. It applies one feasible milestone state change, scores the changed state with the frozen six-month model, penalizes residual-quantile uncertainty, and searches four six-month steps with beam width five. Each step includes an evidence tier and actionability label, while seven computed warning flags expose support, stability, replay, and compounding concerns. A historically derived cumulative multiplier cap limits compounding from very low starting values.

The engine is best read as a forecast-to-pathway layer: it turns one leakage-safe forecast into several uncertainty-labelled scenarios. These paths are model-generated what-if scenarios, not promises or development instructions. The data do not identify the causal effect of achieving a milestone, and historical replay gives strong reasons not to treat the paths as interventions.
