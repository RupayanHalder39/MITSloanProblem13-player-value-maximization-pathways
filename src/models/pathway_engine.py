"""
Stage 7 -- pathway optimization engine. Builds multi-step, historically-grounded SCENARIO paths
toward higher value bands (framed toward the EUR100M product destination), using the FROZEN
6-month model as the primary single-step predictor (Stage 6 confirmed this generalizes well,
n=1,345 TEST) and the frozen 12-month model only as secondary/contextual context (Stage 6: TEST
result INCONCLUSIVE at n=10).

Nothing here is causal. Every generated state is a SCENARIO STATE (a hypothetical "what if this
player's state looked like X"), never an OBSERVED STATE for that player. No model is retrained;
this module only composes the already-frozen Stage-5 models.
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
MODELS = BASE / "models"

VALUE_BANDS = ["<€1M", "€1-5M", "€5-10M", "€10-25M", "€25-50M", "€50-75M", "€75-100M", "€100M+"]
BAND_EDGES = [0, 1e6, 5e6, 10e6, 25e6, 50e6, 75e6, 100e6, np.inf]
BAND_ORDER = {b: i for i, b in enumerate(VALUE_BANDS)}
TEAM_TIER_ORDER = ["LOWER", "MID", "TOP", "ELITE"]

EVIDENCE_TIERS = [(100, np.inf, "STRONG"), (30, 100, "MODERATE"), (10, 30, "WEAK"), (0, 10, "INSUFFICIENT")]

# Locked scoring hyperparameters (Task 9-11, documented in docs/Stage7SingleStepScoringRule.md).
UNCERTAINTY_LAMBDA = 0.2
BEAM_WIDTH = 5
MAX_STEPS = 4  # 4 x ~6 months = ~24 months, per Task 13's locked default
MC_SIMULATIONS = 500
MC_SEED = 42


def value_band(v):
    for i in range(len(BAND_EDGES) - 1):
        if BAND_EDGES[i] <= v < BAND_EDGES[i + 1]:
            return VALUE_BANDS[i]
    return VALUE_BANDS[-1]


def evidence_tier(n):
    for lo, hi, label in EVIDENCE_TIERS:
        if lo <= n < hi:
            return label
    return "INSUFFICIENT"


def age_band(a):
    if a <= 21:
        return "<=21"
    if a <= 24:
        return "22-24"
    if a <= 28:
        return "25-28"
    return "29+"


# --- Task 3: current-state builder ---
def build_current_state(row):
    """Builds S_t from a canonical-dataset row (or an equivalent dict). Only leakage-safe,
    decision_date-known fields are included -- identical set to Stage 5's frozen feature list."""
    return {
        "player_id": row["player_id"], "decision_date": row["decision_date"],
        "market_value": row["market_value"], "age_at_decision": row["age_at_decision"],
        "position": row["position"], "value_band": row.get("value_band", value_band(row["market_value"])),
        "team_strength_tier": row.get("team_strength_tier"),
        "prior_minutes_played": row.get("prior_minutes_played"),
        "prior_matches": row.get("prior_matches"), "prior_matches_started": row.get("prior_matches_started"),
        "prior_goals": row.get("prior_goals"), "prior_assists": row.get("prior_assists"),
        "prior_goal_contributions": row.get("prior_goal_contributions"),
        "minutes_change": row.get("minutes_change", 0.0), "goal_contributions_change": row.get("goal_contributions_change", 0.0),
        "previous_log_return_clipped": row.get("previous_log_return_clipped", 0.0),
        "days_since_previous_value": row.get("days_since_previous_value", 182.0),
        "valuation_sequence_number": row.get("valuation_sequence_number", 1),
        "season_dominant_position": row.get("season_dominant_position", row["position"]),
        "season_position_changed": str(row.get("season_position_changed", False)),
        "club_changed": "False",  # a scenario step always STARTS from "no new club change yet"
        "has_prior_completed_season": str(row.get("has_prior_completed_season", False)),
        "log_market_value": np.log1p(row["market_value"]),
    }


# --- Task 4-6: candidate milestone menu with actionability + scenario transforms ---
def _v(state, key, default=0.0):
    """Feasibility-check helper: treats missing/NaN performance fields as 0 (no completed prior
    season observed = effectively 0 measured minutes/goals/etc for feasibility purposes), distinct
    from the model input itself, which keeps the true NaN for the frozen preprocessor's own median
    imputation. FIXED THIS RUN (real bug): the original `state.get(key) or 0` pattern returns NaN
    unchanged when the value IS NaN (Python's `or` treats NaN as truthy), which silently made every
    threshold-based feasibility check return False for any player with missing performance data --
    the majority of "no feasible milestone" results in the first pipeline run were actually just
    players with missing performance state, not players who had genuinely exhausted every
    milestone."""
    v = state.get(key)
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return default
    return v


def _transform_minutes(state, threshold):
    s = dict(state)
    before = _v(state, "prior_minutes_played")
    s["prior_minutes_played"] = max(before, threshold)
    s["minutes_change"] = s["prior_minutes_played"] - before
    s["has_prior_completed_season"] = "True"
    return s


def _transform_starter(state):
    s = dict(state)
    matches = max(_v(state, "prior_matches"), 10)
    s["prior_matches"] = matches
    s["prior_matches_started"] = max(_v(state, "prior_matches_started"), int(np.ceil(matches * 0.5)))
    s["has_prior_completed_season"] = "True"
    return s


def _transform_output(state, threshold):
    s = dict(state)
    before = _v(state, "prior_goal_contributions")
    s["prior_goal_contributions"] = max(before, threshold)
    s["goal_contributions_change"] = s["prior_goal_contributions"] - before
    s["has_prior_completed_season"] = "True"
    return s


def _transform_team_up(state):
    s = dict(state)
    cur = state.get("team_strength_tier")
    if cur in TEAM_TIER_ORDER and cur != "ELITE":
        s["team_strength_tier"] = TEAM_TIER_ORDER[TEAM_TIER_ORDER.index(cur) + 1]
    return s


def _transform_club_chg(state):
    s = dict(state)
    s["club_changed"] = "True"
    return s


MILESTONE_MENU = [
    dict(id="P500", category="PLAYING", name="Reach >=500 prior-season minutes", actionability="SEMI-ACTIONABLE",
         target=500, transform=lambda s: _transform_minutes(s, 500),
         feasible=lambda s: _v(s, "prior_minutes_played") < 500),
    dict(id="P1000", category="PLAYING", name="Reach >=1000 prior-season minutes", actionability="SEMI-ACTIONABLE",
         target=1000, transform=lambda s: _transform_minutes(s, 1000),
         feasible=lambda s: _v(s, "prior_minutes_played") < 1000),
    dict(id="P1500", category="PLAYING", name="Reach >=1500 prior-season minutes", actionability="SEMI-ACTIONABLE",
         target=1500, transform=lambda s: _transform_minutes(s, 1500),
         feasible=lambda s: _v(s, "prior_minutes_played") < 1500),
    dict(id="P2000", category="PLAYING", name="Reach >=2000 prior-season minutes", actionability="SEMI-ACTIONABLE",
         target=2000, transform=lambda s: _transform_minutes(s, 2000),
         feasible=lambda s: _v(s, "prior_minutes_played") < 2000),
    dict(id="P2500", category="PLAYING", name="Reach >=2500 prior-season minutes", actionability="SEMI-ACTIONABLE",
         target=2500, transform=lambda s: _transform_minutes(s, 2500),
         feasible=lambda s: _v(s, "prior_minutes_played") < 2500),
    dict(id="STARTER", category="STARTER", name="Become a regular starter (>=50% matches started)", actionability="SEMI-ACTIONABLE",
         target="starter", transform=_transform_starter,
         feasible=lambda s: (_v(s, "prior_matches_started") / max(_v(s, "prior_matches"), 1)) < 0.5),
    dict(id="O5", category="OUTPUT", name="Reach >=5 goal contributions, prior season", actionability="ACTIONABLE",
         target=5, transform=lambda s: _transform_output(s, 5),
         feasible=lambda s: s.get("position") != "Goalkeeper" and _v(s, "prior_goal_contributions") < 5),
    dict(id="O10", category="OUTPUT", name="Reach >=10 goal contributions, prior season", actionability="ACTIONABLE",
         target=10, transform=lambda s: _transform_output(s, 10),
         feasible=lambda s: s.get("position") != "Goalkeeper" and _v(s, "prior_goal_contributions") < 10),
    dict(id="O15", category="OUTPUT", name="Reach >=15 goal contributions, prior season", actionability="ACTIONABLE",
         target=15, transform=lambda s: _transform_output(s, 15),
         feasible=lambda s: s.get("position") != "Goalkeeper" and _v(s, "prior_goal_contributions") < 15),
    dict(id="TEAM_UP", category="TEAM", name="Move into a stronger team-strength tier", actionability="SEMI-ACTIONABLE",
         target="tier_up", transform=_transform_team_up,
         feasible=lambda s: s.get("team_strength_tier") in TEAM_TIER_ORDER and s.get("team_strength_tier") != "ELITE"),
    dict(id="CLUB_CHG", category="TEAM", name="Change club within La Liga (INFERRED, historical context only)",
         actionability="SEMI-ACTIONABLE (HARD-BLOCKED FROM RECOMMENDATION)", target="club_change", transform=_transform_club_chg,
         feasible=lambda s: True),
]
HARD_BLOCKED_IDS = {"CLUB_CHG"}  # Task 21: never ranked as an actionable recommended step


def feasible_milestones(state):
    return [m for m in MILESTONE_MENU if m["feasible"](state)]


# --- Frozen model loading (read-only, never re-fit) ---
def load_frozen_models():
    m6 = joblib.load(MODELS / "stage5_secondary_6m_model.joblib")
    m12 = joblib.load(MODELS / "stage5_primary_12m_model.joblib")
    return m6, m12


def predict_6m(state, m6_bundle):
    from models.stage5_features import ALL_FEATURES
    row = pd.DataFrame([state])
    X = m6_bundle["preprocessor"].transform(row[ALL_FEATURES])
    return float(m6_bundle["model"].predict(X)[0])


def uncertainty_interval(pred, vb, unc_config):
    row = unc_config[unc_config.value_band == vb]
    if len(row) == 0:
        row = unc_config[unc_config.value_band.astype(str).str.contains("GLOBAL", na=False)]
    lo, hi = row.iloc[0].residual_p10, row.iloc[0].residual_p90
    return pred - hi, pred - lo, (hi - lo)


# --- Task 16: distance to EUR100M ---
def distance_to_100m(value):
    if value >= 100e6:
        return 0.0
    return float(np.log(100e6 / value))


# --- Task 8/9: single-step milestone scoring ---
def score_next_milestones(state, m6_bundle, unc_config, support_df):
    results = []
    for m in feasible_milestones(state):
        support_row = support_df[support_df.milestone_id == m["id"]].iloc[0]
        if support_row.evidence_tier == "INSUFFICIENT":
            continue  # Task 2/20: never surface INSUFFICIENT as a recommendation
        new_state = m["transform"](state)
        pred = predict_6m(new_state, m6_bundle)
        vb = value_band(state["market_value"])
        lo, hi, width = uncertainty_interval(pred, vb, unc_config)
        score = pred - UNCERTAINTY_LAMBDA * width
        projected_value = state["market_value"] * np.exp(np.clip(pred, -5, 5))
        results.append({
            "milestone_id": m["id"], "category": m["category"], "milestone_name": m["name"],
            "actionability": m["actionability"], "hard_blocked": m["id"] in HARD_BLOCKED_IDS,
            "predicted_6m_log_return": round(pred, 4), "score": round(score, 4),
            "interval_low_log_return": round(lo, 4), "interval_high_log_return": round(hi, 4),
            "interval_width": round(width, 4), "projected_value": round(projected_value, 0),
            "projected_value_band": value_band(projected_value),
            "historical_support_n": int(support_row.historical_support_n),
            "evidence_tier": support_row.evidence_tier, "new_state": new_state,
        })
    return sorted(results, key=lambda r: -r["score"])


# --- Task 14: deterministic beam search ---
# Task 12: max forward value-band jump ever observed (12m transition table, reused as a
# conservative ceiling applied CUMULATIVELY across the whole path, not reset each step -- a path
# that reaches its cap after step 1 must not be allowed to jump the same distance again at step 2;
# see docs/Stage7PathObjective_LOCKED.md for the reasoning).
MAX_BAND_JUMP_FROM_START = {
    "<€1M": 4, "€1-5M": 4, "€5-10M": 3, "€10-25M": 2, "€25-50M": 3,
    "€50-75M": 2, "€75-100M": 1, "€100M+": 0,
}


def beam_search(state0, m6_bundle, unc_config, support_df, plausibility_cap, max_steps=MAX_STEPS, beam_width=BEAM_WIDTH):
    """Returns the top `beam_width` complete paths (list of step dicts each), ranked by cumulative
    score. Deterministic: no randomness anywhere in this function."""
    start_band = value_band(state0["market_value"])
    start_idx = BAND_ORDER[start_band]
    max_idx = start_idx + MAX_BAND_JUMP_FROM_START[start_band]
    beams = [{"state": state0, "steps": [], "cum_score": 0.0}]
    for step_no in range(1, max_steps + 1):
        candidates = []
        for beam in beams:
            cur_value = beam["state"]["market_value"]
            if cur_value >= 100e6:
                candidates.append(beam)  # Task 28: terminate -- already at/above target, don't extend further
                continue
            scored = score_next_milestones(beam["state"], m6_bundle, unc_config, support_df)
            scored = [s for s in scored if not s["hard_blocked"]]  # Task 21: never RANK CLUB_CHG as a step
            scored = [s for s in scored if s["predicted_6m_log_return"] <= plausibility_cap]  # Task 26
            # FOUND THIS RUN (real bug): a plausibility check on each step's OWN log-return alone
            # is not enough -- 4 consecutive near-P99 single-step jumps compound into an absurd
            # result (one example: a 16-year-old EUR500K midfielder projected to EUR337M in 24
            # months). Fixed by also capping the CUMULATIVE band jump from the path's own starting
            # band against the empirical transition-support table (Task 12/28), not just each
            # step's own log-return against the P99 cap.
            scored = [s for s in scored if BAND_ORDER[s["projected_value_band"]] <= max_idx]
            if not scored:
                candidates.append(beam)  # no feasible milestones remain -- terminate this beam
                continue
            for s in scored:
                new_state = dict(s["new_state"])
                new_state["market_value"] = s["projected_value"]
                new_state["age_at_decision"] = beam["state"]["age_at_decision"] + 0.5  # ~6 months
                new_state["value_band"] = s["projected_value_band"]
                step_record = {**{k: v for k, v in s.items() if k != "new_state"}, "step_number": step_no}
                candidates.append({"state": new_state, "steps": beam["steps"] + [step_record],
                                   "cum_score": beam["cum_score"] + s["score"]})
        if step_no == 1:
            # Diversity-aware seeding (Task 27): keep only the best-scoring candidate PER DISTINCT
            # first-step milestone, so the beam doesn't collapse to beam_width near-duplicate
            # variants of a single dominant milestone before Path A/B/C selection even runs.
            best_per_milestone = {}
            for c in candidates:
                mid = c["steps"][0]["milestone_id"] if c["steps"] else None
                if mid not in best_per_milestone or c["cum_score"] > best_per_milestone[mid]["cum_score"]:
                    best_per_milestone[mid] = c
            candidates = list(best_per_milestone.values())
        # keep top beam_width unique-path candidates by cumulative score, but ALSO always keep the
        # single best candidate per distinct FIRST-step milestone so diversity survives truncation
        # at later steps even when one milestone dominates on raw score (Task 27) -- may push the
        # kept set slightly above beam_width, acceptable given the small candidate pool here.
        candidates.sort(key=lambda c: -c["cum_score"])
        top_by_score = candidates[:beam_width]
        best_per_first = {}
        for c in candidates:
            first = c["steps"][0]["milestone_id"] if c["steps"] else None
            if first not in best_per_first or c["cum_score"] > best_per_first[first]["cum_score"]:
                best_per_first[first] = c
        merged = {id(c): c for c in top_by_score}
        for c in best_per_first.values():
            merged[id(c)] = c
        beams = sorted(merged.values(), key=lambda c: -c["cum_score"])
        if all(len(b["steps"]) < step_no for b in beams):
            break  # every beam terminated early
    return beams


# --- Task 15: Monte Carlo rollout ---
def monte_carlo_rollout(path_steps, state0, unc_config, n_sims=MC_SIMULATIONS, seed=MC_SEED):
    """Simulates terminal value by resampling each step's growth from a uniform distribution over
    its own [interval_low, interval_high] (the same empirical residual-quantile interval already
    attached to that step) -- NOT a trained probability model. Labeled MODEL-BASED PATHWAY
    SCENARIO PROBABILITY everywhere this is surfaced."""
    rng = np.random.RandomState(seed)
    if not path_steps:
        return {"median_terminal_value": state0["market_value"], "p10_terminal_value": state0["market_value"],
                "p90_terminal_value": state0["market_value"], "prob_reach_25m": 0.0, "prob_reach_50m": 0.0,
                "prob_reach_75m": 0.0, "prob_reach_100m": 0.0}
    terminals = np.empty(n_sims)
    for i in range(n_sims):
        v = state0["market_value"]
        for step in path_steps:
            g = rng.uniform(step["interval_low_log_return"], step["interval_high_log_return"])
            v = v * np.exp(np.clip(g, -5, 5))
        terminals[i] = v
    return {
        "median_terminal_value": float(np.median(terminals)), "p10_terminal_value": float(np.percentile(terminals, 10)),
        "p90_terminal_value": float(np.percentile(terminals, 90)),
        "prob_reach_25m": float((terminals >= 25e6).mean()), "prob_reach_50m": float((terminals >= 50e6).mean()),
        "prob_reach_75m": float((terminals >= 75e6).mean()), "prob_reach_100m": float((terminals >= 100e6).mean()),
    }


# --- Task 19: qualitative path confidence ---
def path_confidence(path_steps):
    if not path_steps:
        return "LOW"
    tiers = [s["evidence_tier"] for s in path_steps]
    avg_width = np.mean([s["interval_width"] for s in path_steps])
    n_steps = len(path_steps)
    if all(t in ("STRONG", "MODERATE") for t in tiers) and n_steps <= 2 and avg_width < 1.0:
        return "HIGH"
    if any(t == "WEAK" for t in tiers) and (n_steps >= 4 or avg_width > 1.3):
        return "LOW"
    return "MEDIUM"
