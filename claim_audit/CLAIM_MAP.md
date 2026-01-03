  # Claim Map (v3)

  This file is a human-readable companion to `claim_audit/claim_map_v3.json`.

  ## C1 — ~2.8–2.9× stiffness_potential (proxy) vs biological xylem

  **Status:** VERIFIED (proxy only)

  **What is being measured**
  - Proxy: `stiffness_potential = (1 - Porosity)^2` (heuristic, not literal/measured “hydraulic stiffness”).

  **Evidence**
  - `claim_audit/flow_metrics.csv` where `Type=='real'` (rows 0–19), cols [`Type`,`Porosity`]
    - mean = 0.3291847807820886
    - median = 0.31166180002037436
  - `claim_audit/flow_stiffness_candidates.csv` (rows 0–9), cols [`Type`,`stiffness_potential`,`Porosity`,`density`]
    - best synthetic = 0.9078656174242496 (row 0)

  **Computed ratios**
  - best/mean = 2.7579209927849977×
  - best/median = 2.9129832958832282×

  **Do not overclaim**
  - The CSVs do not include a measured field called “hydraulic stiffness”. This claim is a Porosity-derived proxy only.

  ---

  ## C2 — Pareto-optimal vs Straight Fins baselines (Fins_* only)

  **Status:** VERIFIED (scoped)

  **Mapping**
  - Synthetic: `flux := thermal_metrics.Q_total`, `density := thermal_metrics.rho_solid`
  - Baseline: `flux := baseline_metrics.flux`, `density := baseline_metrics.density`
  - Pareto: maximize flux, minimize density

  **Baseline scope (must be stated)**
  - Straight fins only: `baseline_metrics.csv` rows 0–4 where `name.startswith('Fins_')`

  **Result**
  - Pareto-front counts vs scoped baselines: 21 synthetic + 2 baseline

  **Diagnostic**
  - If you include all baselines (rows 0–11), Pareto-front becomes: 0 synthetic + 7 baseline
