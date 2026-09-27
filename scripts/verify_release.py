#!/usr/bin/env python3
"""Verify frozen public-release claims against included aggregate tables."""
from pathlib import Path
import csv
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"

def rows(name):
    with (TABLES / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

def close(actual, expected, tol=1e-4):
    if not math.isclose(float(actual), expected, abs_tol=tol):
        raise AssertionError(f"expected {expected}, found {actual}")

test = rows("stage6_6m_test_metrics.csv")[0]
assert int(test["n"]) == 1345
close(test["MAE"], 0.3094)
close(test["Spearman"], 0.5916)
close(test["validation_MAE"], 0.339)
close(test["validation_Spearman"], 0.5688)

twelve = rows("stage6_primary_test_metrics.csv")[0]
assert int(twelve["n"]) == 10

source = rows("stage2_laliga_source_summary.csv")[0]
assert int(source["players_with_valuation"]) == 1132
assert int(source["valuation_observations"]) == 8433
assert source["valuation_date_min"] == "2022-07-01"
assert source["valuation_date_max"] == "2025-06-30"

low = rows("stage9_low_value_cap_validation.csv")
case = next(r for r in low if r["player_id"] == "795809")
close(case["multiplier_uncapped"], 425.0)
close(case["multiplier_capped"], 55.25)
assert all(r["exceeds_own_locked_ceiling"] == "False" for r in low)

distortion = rows("stage9_cap_distortion_audit.csv")
assert len(distortion) == 20
assert all(r["distortion_class"] == "NONE" for r in distortion)
assert sum(r["first_step_unchanged"] == "False" for r in distortion) == 2

stability = rows("stage8_recommendation_stability.csv")
assert len(stability) == 16
assert sum(r["stability_class"] == "STABLE" for r in stability) == 12
assert sum(r["stability_class"] == "PARTIALLY STABLE" for r in stability) == 4

lam = rows("stage8_lambda_sensitivity.csv")
assert all(float(r["first_step_agreement_with_reference"]) == 1.0 for r in lam if float(r["lambda"]) >= 0.2)
beam = rows("stage8_beam_width_sensitivity.csv")
assert all(float(r["first_step_agreement_with_reference"]) == 1.0 for r in beam if int(r["beam_width"]) >= 5)

print("PASS: frozen headline claims match the included aggregate tables")
sys.exit(0)
