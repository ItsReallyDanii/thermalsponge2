# Claims Registry (Thermal-Sponge)

This file defines what our public claims mean, and where the evidence lives.

## Ground truth location
- Primary evidence (C1/C2): `claim_audit/claim_map_v3.json`
- Primary evidence (C1-C5): `claim_audit/claim_map_v4.json`
- Pre-registered hypotheses: `claim_audit/hypothesis_config.json`

## C1 — "stiffness" claim (proxy)
- Public wording (safe): "Up to ~2.9x stiffness_potential (proxy) vs biological xylem."
- Definition:
  - density = 1 - Porosity
  - stiffness_potential = density^2
- Evidence:
  - `claim_audit/claim_map_v3.json` -> claim `C1` (exact CSV rows/cols + ratios)
  - `claim_audit/claim_map_v4.json` -> claim `C1` (reproduced independently)

## C2 — "Pareto" claim (must define baseline set)
- Public wording (safe): "Pareto-optimal cooling efficiency vs Straight Fins (Fins_*) baselines (under current flux/density mapping)."
- Baseline set definition:
  - "Standard engineering baselines" == `baseline_metrics.csv` rows where `name` starts with `Fins_`
- Metric mapping:
  - Synthetic flux = `thermal_metrics.csv: Q_total`
  - Synthetic density = `thermal_metrics.csv: rho_solid`
  - Baseline flux/density = `baseline_metrics.csv: flux, density`
  - Pareto rule: maximize flux, minimize density
- Evidence:
  - `claim_audit/claim_map_v3.json` -> claim `C2` (Pareto-front counts + baseline definition note)
  - `claim_audit/claim_map_v4.json` -> claim `C2` (reproduced independently)

## C3 — Control effort (kWh_ctrl)
- Status: **NOT_SIGNIFICANT**
- Public wording (safe): "Control effort (kWh_ctrl) is comparable between PID+Gate and PID-only under tested settings; no material increase observed."
- No superiority claim is made. The paired test (Wilcoxon signed-rank, one-sided) returned p=0.81.
- Test route: n=8 < 20 -> Wilcoxon signed-rank mandatory (one-sided, H1: gate < PID).
- Effect size: r_rb=0.958 (rank-biserial). gate_mean=11.06, pid_mean=11.03 (diff=+0.04, 0.3% increase, not material).
- Reduction vs AlwaysOn: 97.2% (400.0 -> 11.06).
- n_total=8, n_eff=8. Seeds: [1,4,6,7,8,10,11,13]. Analysis: trigger-qualified.
- Metric tier: Must.
- Evidence: `claim_audit/claim_map_v4.json` -> claim `C3`

## C4 — Actuator chatter reduction
- Status: **VERIFIED_SIM_ONLY**
- Public wording (safe): "PID+Gate reduces actuator chatter by ~50% vs PID-only (p=0.004, Wilcoxon signed-rank, one-sided, sim-only)."
- Chatter definition: count of 0->1 transitions in binary gate signal u(t), threshold=0.5.
- Test route: Wilcoxon signed-rank (count metric, always Wilcoxon). One-sided, H1: gate < PID.
- p=0.0039, significant at alpha=0.05. Effect size: r_rb=1.000 (rank-biserial).
- gate_mean=50.2, pid_mean=100.1 (reduction=49.8%).
- n_total=8, n_eff=8. Seeds: [1,4,6,7,8,10,11,13]. Analysis: trigger-qualified.
- Metric tier: Nice.
- Evidence: `claim_audit/claim_map_v4.json` -> claim `C4`

## C5 — Thermal SLA non-inferiority
- Status: **VERIFIED_SIM_ONLY**
- Public wording (safe): "PID+Gate is non-inferior to PID-only for thermal SLA compliance within pre-registered margins (sim-only)."
- Non-inferiority criteria (from `hypothesis_config.json`):
  1. SLA violations: gate_total <= pid_total * (1 + Delta), Delta=0.10. Result: 12589 <= 14561. **PASS**.
  2. Max exceedance: gate_max <= pid_max + Delta, Delta=0.02. Result: 0.0616 <= 0.0715. **PASS**.
- Both criteria pass -> non-inferior.
- T_SLA=0.85. AlwaysOn: 0 violations (upper bound reference).
- n_total=8, n_eff=8. Seeds: [1,4,6,7,8,10,11,13]. Analysis: trigger-qualified.
- Morphology band: porosity [0.405, 0.546], mean=0.469.
- Metric tier: Must.
- Evidence: `claim_audit/claim_map_v4.json` -> claim `C5`

## Statistical test selection rule

For all paired comparisons (C3, C4, C5):
1. Compute paired differences d_i = treatment_i - control_i (same seed, same morphology).
2. If n < 20: Wilcoxon signed-rank mandatory (t-test unreliable at small n).
3. Count metrics (chatter_count) always use Wilcoxon signed-rank.
4. Continuous metrics with n >= 20: Shapiro-Wilk on d_i — if p >= 0.05 -> `ttest_rel`; else -> `wilcoxon`.
5. alpha = 0.05, one-sided: H1: treatment < control (lower is better for effort/chatter).
6. Wilcoxon tests report rank-biserial effect size: r_rb = 1 - 2W/(n(n+1)).
7. SLA compliance uses non-inferiority test with pre-registered margins from `hypothesis_config.json`.

Pairing: same seed, same morphology (Xylem), different controller.

## Reproduction

```bash
# C1/C2 only (legacy):
python src/repro_claims.py

# C1-C5 (full):
python src/repro_claims_v4.py
```

## Rule
If a claim can't be supported by `claim_audit/claim_map_v4.json`, it's UNVERIFIED and should not be stated publicly.
