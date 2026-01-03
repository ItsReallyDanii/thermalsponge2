# Thermal-Sponge — Claim-Audited Snapshot

This repository includes a self-contained claim audit bundle under `claim_audit/` and a one-command reproduction script under `src/`.

## Reproduce

From repo root:

```bash
python src/repro_claims.py
```

This reproduces the C1/C2 numeric checks directly from `claim_audit/*.csv` and regenerates the audit artifact (`claim_audit/claim_map_v3.json`) and plots (`results/claim_audit_plots/`).

## Claims

### VERIFIED (scoped / proxy-qualified)

- **C1 — ~2.8–2.9× stiffness_potential (proxy)**: Best synthetic `stiffness_potential` is **0.9078656174242496**, and the ratios are **2.7579209927849977×** vs real mean and **2.9129832958832282×** vs real median, where `stiffness_potential = (1 - Porosity)^2`.  
  (Evidence: `claim_audit/flow_metrics.csv` rows 0–19 where `Type=='real'`; `claim_audit/flow_stiffness_candidates.csv` row 0 = `argmax(stiffness_potential)` over rows 0–9)

- **C2 — Pareto-optimal vs Straight Fins baselines only (Fins_*)**: With baselines scoped to `name` starting with `Fins_` (**n=5**), Pareto front (maximize flux, minimize density) contains **21 synthetic + 2 baseline** points under `flux := Q_total` and `density := rho_solid` for synthetics.  
  (Evidence: `claim_audit/thermal_metrics.csv` rows 0–127; `claim_audit/baseline_metrics.csv` rows 0–4 where `name.startswith('Fins_')`)

- **C2 diagnostic (baseline scope matters)**: If **all** baselines are included (baseline rows 0–11), the Pareto front becomes **0 synthetic + 7 baseline** under the same mapping and Pareto rule.  
  (Evidence: `claim_audit/baseline_metrics.csv` rows 0–11)

### UNVERIFIED / PROXY (do not overclaim)

- **C1 is a Porosity-derived proxy, not measured “hydraulic stiffness.”** No column in the provided CSVs is labeled/defined as literal measured hydraulic stiffness; only the Porosity-derived proxy is supported.

- **C2 “standard engineering baselines” is overbroad unless scoped.** The verified Pareto claim is only supported when the baseline set is explicitly scoped to `Fins_*`; expanding the baseline set (e.g., Grid_/Random_) removes synthetics from the Pareto front under the current flux/density mapping.

## Evidence block (paste into README / paper)

```md
**VERIFIED C1 (proxy)**: `claim_audit/flow_metrics.csv` filter `Type=='real'` (rows 0–19), cols [`Type`,`Porosity`]; define `stiffness_potential=(1-Porosity)^2` → mean=0.3291847807820886, median=0.31166180002037436.
**VERIFIED C1 (best synthetic)**: `claim_audit/flow_stiffness_candidates.csv` rows 0–9; `argmax(stiffness_potential)` at row 0 → best=0.9078656174242496.
**VERIFIED C1 ratios**: best/mean=2.7579209927849977× and best/median=2.9129832958832282×.
**UNVERIFIED (literal stiffness)**: no measured “hydraulic stiffness” field exists in the provided CSV columns; only the Porosity-derived proxy is supported.
**VERIFIED C2 scope**: baselines are Straight Fins only: `claim_audit/baseline_metrics.csv` rows 0–4 where `name.startswith('Fins_')`.
**VERIFIED C2 mapping+Pareto**: synthetic uses `claim_audit/thermal_metrics.csv` rows 0–127 cols [`Q_total`→flux, `rho_solid`→density]; Pareto=max flux, min density → front counts vs Fins_*: 21 synthetic + 2 baseline.
**DIAGNOSTIC**: if all baselines included (`baseline_metrics.csv` rows 0–11) → front counts: 0 synthetic + 7 baseline under same mapping/rule.
```
