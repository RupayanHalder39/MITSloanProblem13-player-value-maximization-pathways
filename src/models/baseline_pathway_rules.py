"""
Stage 4 -- non-learned baseline rules (B0-B6). No ML model is fit anywhere in this module: every
function is a deterministic, transparent, closed-form rule computed from TRAIN-only aggregates or
from a single event's own leakage-safe fields. All growth predictions are for `future_log_return_12m`.

Milestone recommendations use "newly achieved" indicators: for every eligible Stage-3 milestone
(https://.../docs/Stage3MilestoneTaxonomy.md), we compare each event's own state indicator against
that same player's immediately preceding event (a self-join on player_id, sorted by decision_date).
This keeps every crossing leakage-safe (each side of the comparison uses only information already
known as of its own decision_date) and gives every milestone a uniform "newly_achieved_this_event"
definition, whether it started life as a value threshold, a playing-time threshold, an output
threshold, or an event flag (club change, team-strength tier increase).

Deliberate scope simplification (disclosed, not hidden): of the 17 Stage-3-eligible milestones in
`stage3_milestone_dictionary.csv`, ROLE_STABLE and AGE_EARLY are excluded from the *recommendable*
milestone menu used by B3/B4/B6 -- ROLE_STABLE is a state descriptor, not a "more of this is better"
growth target, and AGE_EARLY has `trainable_transition = False` in the dictionary already. Both
remain valid Stage-3 state/comparability fields; they are simply not offered as a next-milestone
recommendation. 15 milestones remain in the recommendable menu.
"""
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]

EVIDENCE_TIERS = [(100, np.inf, "STRONG"), (30, 100, "MODERATE"), (10, 30, "WEAK"), (0, 10, "INSUFFICIENT")]

# TRAIN-derived clip bound for B1 (99th/1st percentile of finite previous_log_return on TRAIN,
# rounded); see docs/Stage4TemporalSplitProtocol.md for the derivation.
B1_MOMENTUM_CLIP = 1.6

MILESTONE_MENU = [
    # id, category, achieved_now(df)->bool Series, excludes_position
    ("V5", "VALUE", lambda df: df.market_value >= 5_000_000, None),
    ("V10", "VALUE", lambda df: df.market_value >= 10_000_000, None),
    ("V25", "VALUE", lambda df: df.market_value >= 25_000_000, None),
    ("V50", "VALUE", lambda df: df.market_value >= 50_000_000, None),
    ("P500", "PLAYING", lambda df: df.prior_minutes_played >= 500, None),
    ("P1000", "PLAYING", lambda df: df.prior_minutes_played >= 1000, None),
    ("P1500", "PLAYING", lambda df: df.prior_minutes_played >= 1500, None),
    ("P2000", "PLAYING", lambda df: df.prior_minutes_played >= 2000, None),
    ("P2500", "PLAYING", lambda df: df.prior_minutes_played >= 2500, None),
    ("STARTER", "STARTER", lambda df: (df.prior_matches_started / df.prior_matches.replace(0, np.nan)) >= 0.5, None),
    ("O5", "OUTPUT", lambda df: df.prior_goal_contributions >= 5, "Goalkeeper"),
    ("O10", "OUTPUT", lambda df: df.prior_goal_contributions >= 10, "Goalkeeper"),
    ("O15", "OUTPUT", lambda df: df.prior_goal_contributions >= 15, "Goalkeeper"),
    ("TEAM_UP", "TEAM", None, None),  # handled specially (compares tier vs previous event's tier)
    ("CLUB_CHG", "TEAM", lambda df: df.club_changed.fillna(False), None),
]

TEAM_TIER_ORDER = {"LOWER": 0, "MID": 1, "TOP": 2, "ELITE": 3}


def evidence_tier(n):
    for lo, hi, label in EVIDENCE_TIERS:
        if lo <= n < hi:
            return label
    return "INSUFFICIENT"


def age_band(a):
    if pd.isna(a):
        return None
    if a <= 21:
        return "<=21"
    if a <= 24:
        return "22-24"
    if a <= 28:
        return "25-28"
    return "29+"


def add_milestone_indicators(df):
    """Adds `achieved_{id}`, `achieved_prev_{id}`, `newly_{id}` columns for every menu milestone."""
    out = df.sort_values(["player_id", "decision_date"]).copy()
    out["team_tier_ord"] = out.team_strength_tier.map(TEAM_TIER_ORDER)
    out["team_tier_ord_prev"] = out.groupby("player_id")["team_tier_ord"].shift(1)
    out["achieved_TEAM_UP"] = (out.team_tier_ord_prev.notna() & out.team_tier_ord.notna()
                                & (out.team_tier_ord > out.team_tier_ord_prev))
    out["achieved_prev_TEAM_UP"] = False  # TEAM_UP is itself an event flag, not a persistent state
    out["newly_TEAM_UP"] = out["achieved_TEAM_UP"]

    for mid, cat, fn, excl in MILESTONE_MENU:
        if mid == "TEAM_UP":
            continue
        achieved = fn(out).fillna(False)
        out[f"achieved_{mid}"] = achieved
        if mid == "CLUB_CHG":
            out[f"achieved_prev_{mid}"] = False
            out[f"newly_{mid}"] = achieved
        else:
            prev = out.groupby("player_id")[f"achieved_{mid}"].shift(1).fillna(False)
            out[f"achieved_prev_{mid}"] = prev
            out[f"newly_{mid}"] = achieved & (~prev)
    return out


def feasible_milestones_for_row(row):
    """Milestones NOT yet achieved (or, for event-type milestones, always offerable), respecting
    the Goalkeeper output-milestone exclusion."""
    feasible = []
    for mid, cat, fn, excl in MILESTONE_MENU:
        if excl is not None and row.get("position") == excl:
            continue
        if mid == "CLUB_CHG":
            feasible.append(mid)
            continue
        if mid == "TEAM_UP":
            if row.get("team_strength_tier") != "ELITE" and pd.notna(row.get("team_strength_tier")):
                feasible.append(mid)
            continue
        if not row.get(f"achieved_{mid}", False):
            feasible.append(mid)
    return feasible


def stratum_backoff(row, comparable_index_sets):
    """Returns (level_name, matching TRAIN row-index) using the locked 4-level backoff hierarchy."""
    a, p, v = row.get("age_band"), row.get("position"), row.get("value_band")
    for level, key in [
        ("age_x_position_x_value_band", (a, p, v)),
        ("position_x_value_band", (p, v)),
        ("value_band", (v,)),
        ("global", None),
    ]:
        idx = comparable_index_sets.get(level, {}).get(key) if key is not None else comparable_index_sets.get("global")
        if idx is not None and len(idx) >= 10:
            return level, idx
    return "global", comparable_index_sets.get("global", pd.Index([]))


def predict_growth_b0(events):
    return pd.Series(0.0, index=events.index)


def predict_growth_b1(events):
    x = events.previous_log_return.replace([np.inf, -np.inf], np.nan)
    return x.clip(-B1_MOMENTUM_CLIP, B1_MOMENTUM_CLIP).fillna(0.0)
