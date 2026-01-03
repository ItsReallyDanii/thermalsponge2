# Claim Map (v3)

This document is a human-readable companion to `claim_audit/claim_map_v3.json` and must not contradict it.

## VERIFIED (scoped / proxy-qualified)

### C1 — ~2.8–2.9× stiffness_potential (proxy)

**Status:** VERIFIED (proxy)

**Proxy definition**
- `density = 1 - Porosity`
- `stiffness_potential = density^2 = (1 - Porosity)^2`

**Reproduction (exact selectors)**
- Biological reference (“real”): `claim_audit/flow_metrics.csv` filter `Type == 'real'` (row indices 0–19), columns `Type`, `Porosity`.
- Best synthetic: `claim_audit/flow_stiffness_candidates.csv` select `argmax(stiffness_potential)` over rows 0–9, columns `Type`, `stiffness_potential`, `Porosity`, `density` → selected row index 0.

**Numeric results**
- `real_mean_stiffness_potential = 0.3291847807820886`
- `real_median_stiffness_potential = 0.31166180002037436`
- `best_synthetic_stiffness_potential = 0.9078656174242496` (candidate row 0)
- `ratio(best/mean) = 2.7579209927849977×`
- `ratio(best/median) = 2.9129832958832282×`

**UNVERIFIED interpretation warning (do not overclaim)**
- “Hydraulic stiffness” is not directly measured in the provided artifacts; only the Porosity-derived proxy above is supported.

---

### C2 — Pareto-optimal vs Straight Fins (Fins_* only, scoped)

**Status:** VERIFIED (scoped)

**Metric mapping (as used in the audit)**
- Synthetic: `flux := claim_audit/thermal_metrics.csv:Q_total`, `density := claim_audit/thermal_metrics.csv:rho_solid`.
- Baseline: `flux := claim_audit/baseline_metrics.csv:flux`, `density := claim_audit/baseline_metrics.csv:density`.
- Pareto definition: maximize flux, minimize density.

**Baseline scope (must be stated)**
- Straight Fins only: `claim_audit/baseline_metrics.csv` filter `name.startswith('Fins_')` (row indices 0–4; n=5), columns `name`, `flux`, `density`.

**Pareto front results (scoped baselines)**
- Pareto-front counts vs Fins_* scope: synthetic=21, baseline=2.
- Baseline points on the scoped Pareto front:
  - `Fins_5` (row 0): flux=0.0543938033777702, density=0.078125
  - `Fins_10` (row 1): flux=0.0573652370699687, density=0.15625

**Diagnostic (if ALL baselines are included)**
- If `claim_audit/baseline_metrics.csv` uses all rows 0–11 (no scoping), Pareto-front counts become synthetic=0, baseline=7.
- Baselines on that (all-baselines) Pareto front:
  `Grid_4`, `Grid_8`, `Grid_16`, `Grid_32`, `Random_0.2`, `Random_0.4`, `Random_0.6`.

**UNVERIFIED scope warning (do not overclaim)**
- The phrase “standard engineering baselines” is not supported unless the baseline set is explicitly specified; under the current mapping, including Grid_/Random_ baselines removes synthetics from the Pareto front.
