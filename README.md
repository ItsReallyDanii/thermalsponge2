# Inverse Design of Functionally Graded Porous Media
### *A Physics-Informed Generative Approach to Biological & Thermal Transport*

![Status](https://img.shields.io/badge/Status-Research_Artifact-blue)
![Domain](https://img.shields.io/badge/Domain-SciML-green)
![Framework](https://img.shields.io/badge/Framework-PyTorch-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## Key finding (scoped + reproducible)

Validated a generative design engine that produces porous microstructures with:

- **C1 (proxy):** **up to ~2.91×** higher **stiffness_potential** than biological xylem **median** (and **~2.76×** vs mean), where  
  `stiffness_potential = (1 − Porosity)^2`.
- **C2 (Pareto, scoped):** Pareto-optimal designs **vs Straight Fins only** (**Fins_*** baseline subset) under the **current flux/density mapping**  
  (synthetic `flux := thermal_metrics.Q_total`, `density := thermal_metrics.rho_solid`).

> **Scope note (C2):** If **Grid_*** / **Random_*** baselines are included, synthetics are dominated under the current mapping. The Pareto claim must therefore **name the baseline set**.

---

## ✅ Evidence (Claim Audit)

- Evidence bundle: `claim_audit/claim_map.json`  
- Reproduction script: `src/repro_claims.py`

Minimal reproducible definitions:

- **C1 (bio reference):** `flow_metrics.csv` rows 0–19 where `Type == 'real'` using `Porosity`
- **C1 (best synthetic):** `flow_stiffness_candidates.csv` max `stiffness_potential` (row 0)
- **C2 (baseline scope):** `baseline_metrics.csv` rows where `name` starts with `Fins_`
- **C2 (mapping):** synthetic uses `thermal_metrics.csv` columns `Q_total` (flux) + `rho_solid` (density)

---

## Abstract

Transport microstructures—whether in biological xylem or engineered cooling plates—often face a trade-off between **transport performance** (flow/heat) and **material cost** (density and/or pressure drop). Classic topology optimization can be expensive; direct biomimicry can inherit biological constraints that are irrelevant to engineering.

This repository explores a **physics-informed generative pipeline**: learn a structure manifold from biological patterns, then **optimize in latent space** against physics targets (flow and/or heat) using differentiable / surrogate-assisted evaluations.

**Data source & scale (as used here):**
- Trained on **macroscopic cross-sections** of *Pinus taeda* (UruDendro) to learn **mesoscale density gradients** (earlywood → latewood).
- This focuses the design space on **manufacturable, printable-scale heterogeneity** rather than micron-scale cellular lumens.

---

## Key results (supported by the current artifacts)

### 1) Biological trade-off: flow vs stiffness_potential (proxy)

Proxy stiffness definition:

- `density = 1 − Porosity`
- `stiffness_potential = density^2`

Repro summary:
- Best synthetic `stiffness_potential` = **0.9078656174**
- Ratio(best / real mean) = **2.7579209928×**
- Ratio(best / real median) = **2.9129832959×**

> This is a **proxy**. No literal/measured “hydraulic stiffness” field is present in the provided CSVs.

### 2) Thermal generalization: Pareto vs baselines (scoped)

Pareto rule: maximize flux, minimize density  
Baseline set for the claim: `Fins_*` only

Repro summary (vs Fins_* only):
- Pareto-front counts: **21 synthetic + 2 baseline**

Diagnostic (if *all* baselines included):
- Pareto-front counts: **0 synthetic + 7 baseline** (Grid_/Random_ dominate)

---

## Reproduce the claim audit locally

### Install
```bash
pip install -r requirements.txt
pip install pandas
```

### Run
From repo root:
```bash
python src/repro_claims.py
```

---

## Repository structure (high level)

```
src/                 # code (models, solvers, training, optimization, analysis)
data/                # datasets (if included / referenced by scripts)
results/             # figures / renders / exports (if included)
claim_audit/         # claim evidence bundle (CSV + claim_map)
```

---

## License

MIT (see `LICENSE`).

## Citation

Daniel Sleiman. (2025). *Inverse Design of Functionally Graded Porous Media via Physics-Informed Generative Models*. GitHub repository.
