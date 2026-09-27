"""
Stage 9 -- user-facing pathway engine: the Stage 7/8 beam search logic, now with a genuine
CUMULATIVE MULTIPLICATIVE cap (docs/Stage9MultiplicativeCapDesign.md) applied at every step,
keyed to the path's own STARTING value band and ELAPSED time, closing the Stage-8 BLOCKING
low-value compounding finding. Does not modify `pathway_engine.py` or `stage8_variant_engine.py` --
both remain frozen references; this module composes them.

Every output remains a MODEL-GENERATED DEVELOPMENT SCENARIO, never a causal recommendation.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from models.pathway_engine import BAND_ORDER, VALUE_BANDS, distance_to_100m, value_band
from models.stage8_variant_engine import score_next_milestones_variant

BASE = Path(__file__).resolve().parents[2]
TABLES = BASE / "outputs" / "tables"

TRUE_6M_BAND_JUMP_CAP = {"<€1M": 4, "€1-5M": 3, "€5-10M": 2, "€10-25M": 2, "€25-50M": 2,
                        "€50-75M": 1, "€75-100M": 1, "€100M+": 0}


def load_cap_table():
    df = pd.read_csv(TABLES / "stage9_locked_multiplicative_cap_table.csv", index_col=0)
    df.columns = [int(c) for c in df.columns]
    return df


def capped_beam_search(state0, m6_bundle, unc_config, support_df, cap_table, *,
                        lam=0.2, beam_width=5, max_steps=4, evidence_min="WEAK",
                        excluded_ids=frozenset(), plausibility_cap=2.302585092994046,
                        band_jump_caps=TRUE_6M_BAND_JUMP_CAP):
    start_band = value_band(state0["market_value"])
    start_value = state0["market_value"]
    start_idx = BAND_ORDER[start_band]
    max_band_idx = start_idx + band_jump_caps.get(start_band, 0)
    row_cap = cap_table.loc[start_band] if start_band in cap_table.index else None

    beams = [{"state": state0, "steps": [], "cum_score": 0.0, "elapsed_months": 0}]
    for step_no in range(1, max_steps + 1):
        elapsed = step_no * 6
        mult_cap = float(row_cap[elapsed]) if row_cap is not None and elapsed in row_cap.index else None
        candidates = []
        for beam in beams:
            if beam["state"]["market_value"] >= 100e6:
                candidates.append(beam)
                continue
            scored = score_next_milestones_variant(
                beam["state"], m6_bundle, unc_config, support_df, lam=lam, evidence_min=evidence_min,
                excluded_ids=excluded_ids | {"CLUB_CHG"}, support_rule="hard",
                plausibility_cap=plausibility_cap)
            scored = [s for s in scored if BAND_ORDER[s["projected_value_band"]] <= max_band_idx]
            if not scored:
                candidates.append(beam)
                continue
            for s in scored:
                uncapped_value = s["projected_value"]
                cap_ceiling = start_value * mult_cap if mult_cap is not None else np.inf
                capped_value = min(uncapped_value, cap_ceiling)
                cap_applied = capped_value < uncapped_value - 1.0  # tolerance for float rounding
                new_state = dict(s["new_state"])
                new_state["market_value"] = capped_value
                new_state["age_at_decision"] = beam["state"]["age_at_decision"] + 0.5
                new_state["value_band"] = value_band(capped_value)
                step_record = {**{k: v for k, v in s.items() if k != "new_state"},
                              "step_number": step_no, "elapsed_months": elapsed,
                              "uncapped_projected_value": round(uncapped_value, 0),
                              "capped_projected_value": round(capped_value, 0),
                              "multiplicative_cap_applied": cap_applied,
                              "cap_ceiling": round(cap_ceiling, 0) if np.isfinite(cap_ceiling) else None,
                              "projected_value": round(capped_value, 0),
                              "projected_value_band": value_band(capped_value)}
                candidates.append({"state": new_state, "steps": beam["steps"] + [step_record],
                                   "cum_score": beam["cum_score"] + s["score"], "elapsed_months": elapsed})
        if step_no == 1:
            best_per_milestone = {}
            for c in candidates:
                mid = c["steps"][0]["milestone_id"] if c["steps"] else None
                if mid not in best_per_milestone or c["cum_score"] > best_per_milestone[mid]["cum_score"]:
                    best_per_milestone[mid] = c
            candidates = list(best_per_milestone.values())
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
    return beams


def select_diverse_paths(beams):
    if not beams:
        return {}
    complete = [b for b in beams if b["steps"]] or beams
    path_a = max(complete, key=lambda b: b["cum_score"])

    def first_milestone(b):
        return b["steps"][0]["milestone_id"] if b["steps"] else None

    def pick_diverse(key_fn, exclude_first):
        candidates = sorted(complete, key=key_fn)
        for c in candidates:
            if first_milestone(c) != exclude_first:
                return c
        return candidates[0] if candidates else path_a

    path_b = pick_diverse(lambda b: np.mean([s["interval_width"] for s in b["steps"]]) if b["steps"] else 999,
                          first_milestone(path_a))
    used = {first_milestone(path_a), first_milestone(path_b)}
    candidates_c = sorted(complete, key=lambda b: -np.mean([s["historical_support_n"] for s in b["steps"]]) if b["steps"] else 0)
    path_c = next((c for c in candidates_c if first_milestone(c) not in used), candidates_c[0])
    return {"GROWTH_FOCUSED_SCENARIO": path_a, "LOWER_RISK_SCENARIO": path_b, "HIGHEST_EVIDENCE_SCENARIO": path_c}
