"""
Stage 8 -- parametrized robustness/sensitivity variant of the Stage 7 pathway engine. This module
NEVER imports Stage-7's `beam_search`/`score_next_milestones` by reference for MUTATION -- it
reimplements the same logic with configurable knobs, so `src/models/pathway_engine.py` (the frozen
Stage-7 reference, hash-verified in `outputs/tables/stage8_stage7_reference_manifest.csv`) is never
touched. Every function here is POST-HOC ROBUSTNESS ANALYSIS -- not a replacement reference engine.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from models.pathway_engine import (
    BAND_ORDER, MILESTONE_MENU, TEAM_TIER_ORDER, VALUE_BANDS, _v, distance_to_100m,
    evidence_tier as tier_from_n, value_band,
)

EVIDENCE_RANK = {"INSUFFICIENT": 0, "WEAK": 1, "MODERATE": 2, "STRONG": 3}


def evidence_ok(tier, min_tier):
    return EVIDENCE_RANK.get(tier, 0) >= EVIDENCE_RANK.get(min_tier, 1)


def feasible_milestones_variant(state, excluded_ids=frozenset()):
    return [m for m in MILESTONE_MENU if m["id"] not in excluded_ids and m["feasible"](state)]


_PREDICT_CACHE = {}


def predict_6m(state, m6_bundle):
    """Memoized: the SAME (state values) always yields the SAME prediction regardless of which
    Stage-8 sensitivity config (lambda/beam width/evidence threshold/etc.) is calling it -- caching
    here turns the O(configs x cohort x steps x candidates) sweep cost into O(cohort x steps x
    candidates), a large, necessary speedup given how many Stage-8 sweeps reuse the same states."""
    from models.stage5_features import ALL_FEATURES
    key = tuple(state.get(f) for f in ALL_FEATURES)
    if key in _PREDICT_CACHE:
        return _PREDICT_CACHE[key]
    row = pd.DataFrame([state])
    X = m6_bundle["preprocessor"].transform(row[ALL_FEATURES])
    pred = float(m6_bundle["model"].predict(X)[0])
    _PREDICT_CACHE[key] = pred
    return pred


def uncertainty_interval(pred, vb, unc_config):
    row = unc_config[unc_config.value_band == vb]
    if len(row) == 0:
        row = unc_config[unc_config.value_band.astype(str).str.contains("GLOBAL", na=False)]
    lo, hi = row.iloc[0].residual_p10, row.iloc[0].residual_p90
    return pred - hi, pred - lo, (hi - lo)


def support_score(support_n, rule):
    """Task 10: support-handling variants. `rule` in {hard, weighted, log_bonus, low_support_penalty}."""
    if rule == "hard":
        return 0.0
    if rule == "weighted":
        return {"STRONG": 0.0, "MODERATE": -0.02, "WEAK": -0.05}.get(tier_from_n(support_n), -0.10)
    if rule == "log_bonus":
        return 0.01 * np.log1p(support_n)
    if rule == "low_support_penalty":
        return -0.05 if support_n < 30 else 0.0
    return 0.0


def score_next_milestones_variant(state, m6_bundle, unc_config, support_df, *,
                                   lam=0.2, evidence_min="WEAK", excluded_ids=frozenset(),
                                   support_rule="hard", plausibility_cap=2.302585092994046):
    results = []
    for m in feasible_milestones_variant(state, excluded_ids):
        support_row = support_df[support_df.milestone_id == m["id"]]
        if len(support_row) == 0:
            continue
        support_row = support_row.iloc[0]
        tier = support_row.evidence_tier if "evidence_tier" in support_row else tier_from_n(support_row.historical_support_n)
        if not evidence_ok(tier, evidence_min):
            continue
        new_state = m["transform"](state)
        pred = predict_6m(new_state, m6_bundle)
        if pred > plausibility_cap:
            continue
        vb = value_band(state["market_value"])
        lo, hi, width = uncertainty_interval(pred, vb, unc_config)
        score = pred - lam * width + support_score(support_row.historical_support_n, support_rule)
        projected_value = state["market_value"] * np.exp(np.clip(pred, -5, 5))
        results.append({
            "milestone_id": m["id"], "category": m["category"], "actionability": m["actionability"],
            "predicted_6m_log_return": round(pred, 4), "score": round(score, 4),
            "interval_low_log_return": round(lo, 4), "interval_high_log_return": round(hi, 4),
            "interval_width": round(width, 4), "projected_value": round(projected_value, 0),
            "projected_value_band": value_band(projected_value),
            "historical_support_n": int(support_row.historical_support_n), "evidence_tier": tier,
            "new_state": new_state,
        })
    return sorted(results, key=lambda r: -r["score"])


def beam_search_variant(state0, m6_bundle, unc_config, support_df, *,
                         lam=0.2, beam_width=5, max_steps=4, evidence_min="WEAK",
                         excluded_ids=frozenset(), support_rule="hard",
                         plausibility_cap=2.302585092994046,
                         band_jump_caps=None, rng_none=True):
    """Deterministic beam search (Stage-7 logic, reimplemented with configurable knobs)."""
    if band_jump_caps is None:
        band_jump_caps = {"<€1M": 4, "€1-5M": 4, "€5-10M": 3, "€10-25M": 2, "€25-50M": 3,
                          "€50-75M": 2, "€75-100M": 1, "€100M+": 0}
    start_band = value_band(state0["market_value"])
    start_idx = BAND_ORDER[start_band]
    max_idx = start_idx + band_jump_caps.get(start_band, 0)
    beams = [{"state": state0, "steps": [], "cum_score": 0.0}]
    for step_no in range(1, max_steps + 1):
        candidates = []
        for beam in beams:
            if beam["state"]["market_value"] >= 100e6:
                candidates.append(beam)
                continue
            scored = score_next_milestones_variant(
                beam["state"], m6_bundle, unc_config, support_df, lam=lam, evidence_min=evidence_min,
                excluded_ids=excluded_ids | {"CLUB_CHG"}, support_rule=support_rule,
                plausibility_cap=plausibility_cap)
            scored = [s for s in scored if BAND_ORDER[s["projected_value_band"]] <= max_idx]
            if not scored:
                candidates.append(beam)
                continue
            for s in scored:
                new_state = dict(s["new_state"])
                new_state["market_value"] = s["projected_value"]
                new_state["age_at_decision"] = beam["state"]["age_at_decision"] + 0.5
                new_state["value_band"] = s["projected_value_band"]
                step_record = {**{k: v for k, v in s.items() if k != "new_state"}, "step_number": step_no}
                candidates.append({"state": new_state, "steps": beam["steps"] + [step_record],
                                   "cum_score": beam["cum_score"] + s["score"]})
        if step_no == 1:
            best_per_milestone = {}
            for c in candidates:
                mid = c["steps"][0]["milestone_id"] if c["steps"] else None
                if mid not in best_per_milestone or c["cum_score"] > best_per_milestone[mid]["cum_score"]:
                    best_per_milestone[mid] = c
            candidates = list(best_per_milestone.values())
        candidates.sort(key=lambda c: -c["cum_score"])
        beams = candidates[:beam_width]
    return beams


def monte_carlo_rollout_variant(path_steps, state0, n_sims=500, seed=42):
    rng = np.random.RandomState(seed)
    if not path_steps:
        v0 = state0["market_value"]
        return {"median_terminal_value": v0, "p10_terminal_value": v0, "p90_terminal_value": v0,
                "prob_reach_25m": 0.0, "prob_reach_50m": 0.0, "prob_reach_75m": 0.0, "prob_reach_100m": 0.0}
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
