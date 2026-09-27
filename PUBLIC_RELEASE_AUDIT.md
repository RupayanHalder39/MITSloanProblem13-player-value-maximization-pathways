# Public Release Audit

## Project identity

Problem 13 local release for *Player Development Scenario Pathways: Forecasting Six-Month Market-Value Evolution in La Liga*. Private master: `player-value-maximization-pathways` (read-only). Public candidate: this repository. Audit date: 2026-09-27.

## Research understanding

The football problem is near-term trajectory assessment for recruitment, retention, and academy planning. At a valuation date the system knows current value and momentum, age, position, completed-prior-season performance, milestone state, and available team context. It forecasts six-month log market-value return and uses the frozen forecast to score hypothetical milestone states. MAE evaluates log-return error; Spearman evaluates growth ranking. Clubs may compare conditional scenarios and their uncertainty, but must not read them as intervention effects, guaranteed futures, transfer fees, or instructions.

## Authoritative scientific results

- Cohort: 1,132 players, 8,433 events, 2022-07-01–2025-06-30.
- Selected six-month model: HistGradientBoostingRegressor.
- TEST: n=1,345, MAE 0.3094, Spearman 0.5916.
- VALIDATION: n=1,188, MAE 0.3390, Spearman 0.5688 (rounded to 0.569 in prose).
- Twelve-month TEST: n=10 finite labels; inconclusive.
- Pathway verdict: partially robust and associational only.
- Replay: mean lift approximately −0.143, n=150; matched result negative/worse for 9/11 milestones; selection diagnostic AUC 0.86–1.00 for 9/11.
- Safety case: 425.00× uncapped to 55.25× capped; 0/6 exceeded individual ceilings; 0/20 met the material-distortion rule, while 2/20 first steps changed.

## Claim-to-source mapping

| Claim | Authoritative source |
|---|---|
| population and dates | `stage2_laliga_source_summary.csv` |
| temporal split | `stage4_temporal_split_summary.csv` |
| candidates and selection | `stage5_regression_model_comparison.csv`, Stage 5 report |
| six-month validation/test | `stage5_6m_model_metrics.csv`, `stage6_6m_test_metrics.csv` |
| twelve-month test n | `stage6_primary_test_metrics.csv` |
| parameter stability | `stage8_lambda_sensitivity.csv`, `stage8_beam_width_sensitivity.csv` |
| five-variant stability | `stage8_recommendation_stability.csv` |
| matched replay | `stage8_matched_replay_results.csv` |
| selection bias | `stage8_milestone_selection_bias_audit.csv` |
| cap and distortion | `stage9_low_value_cap_validation.csv`, `stage9_cap_distortion_audit.csv` |

## Robustness discrepancy audit

**Resolved: different experiments and denominators.** The 100% statement combines two separate one-parameter sweeps on 32 events: all λ values at or above 0.20 agreed with the reference first step, and all beam widths at or above five agreed. The 75% statement comes from a five-variant audit on 16 events: 12 were classed STABLE (agreement ≥80%), four PARTIALLY STABLE, none UNSTABLE. The figures must not be averaged. The first establishes local stability in two parameters; the second tests broader joint design changes on a smaller cohort.

## Current MIT Sloan requirements

Official source: MIT Sloan Sports Analytics Conference, Research Paper Competition page, accessed 2026-09-27: https://www.sloansportsconference.com/research-paper-competition

| Rule | Implication |
|---|---|
| fewer than 500 words including title and body | existing draft must be recounted under the exact portal convention |
| up to two figures/tables combined | two selected figures fit the limit |
| Introduction, Methods, Results, Conclusion | draft uses the required structure |
| abstract due 2026-10-01 11:59 p.m. Eastern | submission deadline recorded |
| invited full paper due 2026-12-04 11:59 p.m. Eastern | later-stage deadline recorded |
| open-source repository link required, including data used; proprietary data should be anonymized with judgement | current local-only repository does not yet satisfy the live-link requirement; data licence remains unresolved |

The official page does not specify upload file format, page count, detailed supplementary-material rules, anonymization/blind review, or whether a repository may expose author identity. **MANUAL CONFIRMATION REQUIRED** for those items and for the apparent tension between the open-data wording and unconfirmed redistribution rights.

## Data licensing

The master identifies a local La Liga extract but does not establish provider ownership, licence terms, redistribution rights, or anonymization obligations. Raw/row-level data, parquet files, SQL extracts, and model binaries are excluded. Publication status: aggregate tables only in this candidate. **DATA LICENCE: NEEDS CONFIRMATION.**

## Files included

README, audit, handoff, MIT licence for original code/docs, citation metadata, requirements, ignore rules, data schema note, methodology, claim verifier, five pathway/model source modules and five JSON configurations, two figures, fifteen aggregate tables, and the existing abstract draft.

## Files excluded

Raw/interim/processed player data; SQL; parquet; joblib models; virtual environment; caches; master `.git`; logs; private planning/history; PDFs and HTML; detailed row-level engine outputs; unrelated research; reviewer correspondence; local absolute-path workflows.

## Reproducibility

**PARTIAL.** `scripts/verify_release.py` checks frozen claims and fails on mismatch. Full data reconstruction, training, and scoring require restricted source rows and frozen binaries not included here.

## Writing and Originality Audit

Documents reviewed: master README/handoff; Stage 0–10 summaries and core reports; abstract drafts; guideline/style/reference audits; public README, methodology, data note, audit, and handoff. Obvious copied/unattributed passages found: **NO** in newly written release prose. Existing abstract language was retained as a research artifact and requires final author review. Prose was rewritten around direct football definitions, evidentiary boundaries, and explicit negative findings. Official rules are summarized and linked. No scientific number or meaning was altered. Passages requiring human review: author list, collaboration/logo permissions, and the final submission draft.

## Secret scan

Automated keyword and high-risk credential-pattern scans completed on 2026-09-27. No credentials, keys, tokens, database URLs, SSH material, or private endpoints were found. The public contact email is intentional.

## Portability scan

No executable workflow or public documentation depends on a local home-directory path, `file://`, Windows drive paths, external symlinks, or private database locations.

## Large-file audit

No databases, archives, parquet files, model binaries, or symlinks are included. The largest files are the two research figures and logo; all were inspected as valid images.

## Privacy / metadata audit

The public portrait is a re-encoded copy of the confirmed source; the source was not modified. No GPS/device EXIF was retained. The intentional public identity fields are name, affiliations supplied in the brief, profile links, and email. Logo ownership/use permission remains a human responsibility.

## README visual QA

Heading order, relative links, figure dimensions, portrait aspect ratio, logo aspect ratio, captions, and narrow-width image behavior were checked. Both figures are high-resolution PNGs and all image references resolve. GitHub's exact rendering was not published or externally previewed; local Markdown structural QA passed.

### Presentation consistency pass — 2026-09-27

The complete Problem 6 public README was used as the presentation reference. Problem 13 now uses
the same research-first hierarchy, warning treatment, paragraph density, reproduction structure,
150-pixel researcher portrait, inline Connect links, 180-pixel SoccerSolver logo, citation warning,
and licence boundary. Its scientific sections remain specific to the market-value forecast and
development-scenario engine.

The private document `Player_Development_Pathways_Story_Style1_Spaced_A4 (1).docx` was inspected
and rendered read-only. Its forecast-to-pathway narrative was retained where useful. It was not
treated as authoritative where it diverged from the audited outputs: the public text identifies
n=1,345 as valuation events, distinguishes the 32-event parameter sweeps from the 16-event broader
variant audit, and reports 0/20 materially distorted normal-value paths while acknowledging that
two first steps changed. The private DOCX was not modified.

The public Markdown submission copy was updated with those distinctions, the correct TEST unit,
and the minimal statement, “This paper was developed in collaboration with SoccerSolver.” Its
title-plus-four-section body count is 490 words under the documented project counting convention.
The author and repository placeholders remain blockers.

Both READMEs were rendered to local previews and compared. Problem 13 now matches the Problem 6
repository family's heading rhythm, image sizing, research/profile separation, and compact closing
sections. Figure 1 visibly reads “n = 1,345 valuation events.” No scientific constant, aggregate
table, model output, or private-master artifact was changed. The writing/originality review found
no new unattributed external passage; the wording is direct and evidence-led rather than adapted
from Problem 6 scientific prose.

## Authorship

Rupayan Halder is confirmed. No evidence confirms that he is the sole author or establishes the complete list. **AUTHORSHIP STATUS: PENDING HUMAN CONFIRMATION.** `CITATION.cff` names only the confirmed author and flags the pending list.

## Blind-review identity

The official rules page reviewed does not state whether abstract review is blind or whether the required repository may expose identity. The README, portrait, contact links, citation, and collaboration section are identifying. **MANUAL CONFIRMATION REQUIRED before publication/submission.**

## Remaining publication blockers

1. Confirm the complete author list.
2. Confirm source-data ownership, licence, and what the conference expects when redistribution is not permitted.
3. Confirm blind-review and repository-identity rules with SSAC.
4. Obtain/confirm permission for public use of the portrait and SoccerSolver logo/acknowledgement.
5. Reconcile the existing abstract's own 491-word statement with the official “fewer than 500” rule using the portal's count, and replace placeholders.
6. Create and verify a real public repository URL only after review; no repository currently exists.

## Publication authorization update — 2026-09-27

The public repository now exists at
`https://github.com/RupayanHalder39/MITSloanProblem13-player-value-maximization-pathways`, and the
user authorized publication of this audited local release. The earlier statement above is retained
as a historical audit record. Current citation metadata and `Handoff.md` use the verified URL. The
submission artifact keeps its anonymized repository placeholder because blind-review identity
treatment still requires confirmation.

## Final-paper documentation alignment — 2026-09-27

The two-page paper `Player_Development_Pathways_Story_Style1_Spaced_A4.docx (1).pdf` was read and
rendered from the private master without modification. Public documentation now follows its central
forecast-to-pathway narrative and exact title. The README, methodology, and public Markdown
submission copy explicitly describe 18 eligible milestones, residual-quantile uncertainty,
evidence tiers, actionability labels, seven warning flags, and uncertainty widening across composed
steps.

The paper was used as a narrative reference, not as a replacement for authoritative result tables.
Two audited corrections remain in the public documentation: n=1,345 is identified as valuation
events, and the normal-value cap audit is reported as 0/20 materially distorted with two first-step
changes—not as 20/20 wholly unaltered. The public release also retains the resolved distinction
between the isolated 32-event parameter sweeps and the broader 16-event variant audit.
