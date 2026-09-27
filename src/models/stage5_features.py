"""
Stage 5 -- frozen feature eligibility list and preprocessing pipeline builder. Every included
feature is knowable strictly as of `decision_date` (the same leakage-safe discipline audited in
Stage 2's leakage audit and Stage 3's player-state definition). Nothing here trains a model; this
module only defines WHAT goes in and HOW it is preprocessed.
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

# (feature, group, source_column_or_expr, categorical_numeric)
NUMERIC_FEATURES = [
    ("age_at_decision", "IDENTITY", "age_at_decision"),
    ("log_market_value", "VALUE_STATE", "log1p(market_value)"),
    ("previous_log_return_clipped", "VALUE_STATE", "clip(previous_log_return, -1.6, 1.6)"),
    ("days_since_previous_value", "VALUE_STATE", "days_since_previous_value"),
    ("valuation_sequence_number", "SEQUENCE_STATE", "valuation_sequence_number"),
    ("prior_minutes_played", "PERFORMANCE_STATE", "prior_minutes_played"),
    ("prior_matches", "PERFORMANCE_STATE", "prior_matches"),
    ("prior_matches_started", "PERFORMANCE_STATE", "prior_matches_started"),
    ("prior_goals", "PERFORMANCE_STATE", "prior_goals"),
    ("prior_assists", "PERFORMANCE_STATE", "prior_assists"),
    ("prior_goal_contributions", "PERFORMANCE_STATE", "prior_goal_contributions"),
    ("minutes_change", "PERFORMANCE_STATE", "minutes_change"),
    ("goal_contributions_change", "PERFORMANCE_STATE", "goal_contributions_change"),
]
CATEGORICAL_FEATURES = [
    ("position", "IDENTITY", "position"),
    ("value_band", "VALUE_STATE", "value_band"),
    ("team_strength_tier", "TEAM_STATE", "team_strength_tier (NaN -> 'MISSING')"),
    ("season_dominant_position", "ROLE_STATE", "season_dominant_position"),
    ("season_position_changed", "ROLE_STATE", "season_position_changed"),
    ("club_changed", "TEAM_STATE", "club_changed"),
    ("has_prior_completed_season", "PERFORMANCE_STATE", "has_prior_completed_season"),
]
ALL_FEATURES = [f[0] for f in NUMERIC_FEATURES] + [f[0] for f in CATEGORICAL_FEATURES]

EXCLUDED_LEAKAGE_PATTERNS = ["future_", "censored_", "label_available_", "number_of_bands_gained",
                             "value_band_change_", "newly_", "achieved_"]


def engineer_features(df):
    out = df.copy()
    out["log_market_value"] = np.log1p(out.market_value)
    out["previous_log_return_clipped"] = out.previous_log_return.replace(
        [np.inf, -np.inf], np.nan).clip(-1.6, 1.6)
    out["team_strength_tier"] = out.team_strength_tier.fillna("MISSING")
    out["season_position_changed"] = out.season_position_changed.astype(str)
    out["club_changed"] = out.club_changed.astype(str)
    out["has_prior_completed_season"] = out.has_prior_completed_season.astype(str)
    return out


def build_preprocessor():
    """ColumnTransformer fit on TRAIN only by the caller (sklearn Pipeline discipline: .fit() is
    always called with TRAIN data; VALIDATION only ever sees .transform())."""
    num_cols = [f[0] for f in NUMERIC_FEATURES]
    cat_cols = [f[0] for f in CATEGORICAL_FEATURES]
    numeric_pipe = Pipeline([("impute", SimpleImputer(strategy="median"))])
    categorical_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="constant", fill_value="MISSING")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer([
        ("num", numeric_pipe, num_cols),
        ("cat", categorical_pipe, cat_cols),
    ])
