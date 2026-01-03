
---

### 2) `Thermal-Sponge/CLAIMS.md` (new file; create it with exactly this)
```md
# Claims Registry (Thermal-Sponge)

This file defines what our public claims mean, and where the evidence lives.

## Ground truth location
- Primary evidence: `claim_audit/claim_map.json`

## C1 — “stiffness” claim (proxy)
- Public wording (safe): “Up to ~2.9× stiffness_potential (proxy) vs biological xylem.”
- Definition:
  - density = 1 - Porosity
  - stiffness_potential = density^2
- Evidence:
  - `claim_audit/claim_map.json` → claim `C1` (exact CSV rows/cols + ratios)

## C2 — “Pareto” claim (must define baseline set)
- Public wording (safe): “Pareto-optimal cooling efficiency vs Straight Fins (Fins_*) baselines (under current flux/density mapping).”
- Baseline set definition:
  - “Standard engineering baselines” == `baseline_metrics.csv` rows where `name` starts with `Fins_`
- Metric mapping:
  - Synthetic flux = `thermal_metrics.csv: Q_total`
  - Synthetic density = `thermal_metrics.csv: rho_solid`
  - Baseline flux/density = `baseline_metrics.csv: flux, density`
  - Pareto rule: maximize flux, minimize density
- Evidence:
  - `claim_audit/claim_map.json` → claim `C2` (Pareto-front counts + baseline definition note)

## Rule
If a claim can’t be supported by `claim_audit/claim_map.json`, it’s UNVERIFIED and should not be stated publicly.
