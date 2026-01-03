# Inverse Design of Functionally Graded Porous Media
### *A Physics-Informed Generative Approach to Biological & Thermal Transport*

![Status](https://img.shields.io/badge/Status-Research_Artifact-blue)
![Domain](https://img.shields.io/badge/Domain-SciML-green)
![Framework](https://img.shields.io/badge/Framework-PyTorch-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## What this repo is (end goal)

A **reproducible research artifact**: a porous-microstructure generator + simple physics benchmarks, packaged with an **evidence-linked claim audit** so others can rerun the same numbers and judge the claims without trusting vibes.

## Key finding (scoped + reproducible)

- **C1 (proxy, VERIFIED):** Best synthetic design achieves **~2.91×** higher **stiffness_potential (proxy)** vs biological median (**~2.76×** vs mean), where  
  `stiffness_potential = (1 − Porosity)^2`.
- **C2 (Pareto, VERIFIED but scoped):** Designs are Pareto-optimal **vs Straight Fins only** (**Fins_*** subset) under the **current flux/density mapping**  
  (synthetic `flux := thermal_metrics.Q_total`, `density := thermal_metrics.rho_solid`).

> Scope note (C2): If **Grid_*** / **Random_*** baselines are included, synthetics are dominated under the current mapping. The Pareto claim must therefore **name the baseline set**.

---

## ✅ Evidence (Claim Audit)

Evidence bundle:
- `claim_audit/claim_map_v2.json`
- CSVs: `claim_audit/*.csv`
- Repro: `src/repro_claims.py`

Pasteable evidence block:

```md
**VERIFIED (C1 proxy)**: `claim_audit/flow_metrics.csv` filter `Type=='real'` (rows 0–19), cols [`Type`,`Porosity`]; compute `stiffness_potential=(1-Porosity)^2` → mean=0.3291847807820886, median=0.31166180002037436.
**VERIFIED (C1 best synthetic)**: `claim_audit/flow_stiffness_candidates.csv` rows 0–9, cols [`Type`,`stiffness_potential`]; `argmax(stiffness_potential)` at row 0 → best=0.9078656174242496.
**VERIFIED (C1 ratios)**: best/mean=2.7579209927849977× and best/median=2.9129832958832282× (`claim_audit/flow_metrics.csv` rows 0–19 + `claim_audit/flow_stiffness_candidates.csv` rows 0–9).
**VERIFIED (C2 baseline scope)**: `claim_audit/baseline_metrics.csv` filter `name.startswith('Fins_')` (rows 0–4, n=5), cols [`name`,`flux`,`density`] = Straight Fins baselines.
**VERIFIED (C2 mapping)**: synthetic flux=`claim_audit/thermal_metrics.csv:Q_total`, synthetic density=`claim_audit/thermal_metrics.csv:rho_solid` (rows 0–127, cols [`filename`,`Q_total`,`rho_solid`]); baseline flux/density from `claim_audit/baseline_metrics.csv` cols [`flux`,`density`].
**VERIFIED (C2 Pareto vs Fins_*)**: Pareto=max flux, min density → front counts: 21 synthetic + 2 baseline (baselines `Fins_5` row 0 and `Fins_10` row 1 in `claim_audit/baseline_metrics.csv`).
**VERIFIED diagnostic (ALL baselines)**: if `claim_audit/baseline_metrics.csv` rows 0–11 included → front counts: 0 synthetic + 7 baseline (`Grid_4` row 5, `Grid_8` row 6, `Grid_16` row 7, `Grid_32` row 8, `Random_0.2` row 9, `Random_0.4` row 10, `Random_0.6` row 11).
**UNVERIFIED (literal stiffness)**: no measured “hydraulic stiffness” field exists in `claim_audit/flow_metrics.csv` or `claim_audit/flow_stiffness_candidates.csv`; only the Porosity-derived proxy is supported by provided columns.
```

---

## Abstract

Transport microstructures—whether in biological xylem or engineered cooling plates—often face a trade-off between **transport performance** (flow/heat) and **material cost** (density and/or pressure drop). This repository explores a physics-informed generative pipeline: learn a structure manifold from biological patterns, then optimize in latent space against physics targets using differentiable / surrogate-assisted evaluations.

**Data source & scale (as used here):**
- Trained on macroscopic cross-sections of *Pinus taeda* (UruDendro) to learn mesoscale density gradients (earlywood → latewood).
- Focuses on printable-scale heterogeneity rather than micron-scale cellular detail.

---

## Reproduce the claim audit (one command)

From repo root:

```bash
python src/repro_claims.py
```

Outputs:
- Prints C1 + C2 numbers to stdout
- Writes: `claim_audit/claim_map_v2.json` (if script is configured to emit it)

---

## Install

```bash
pip install -r requirements.txt
pip install pandas numpy matplotlib pillow torch torchvision
```

(If you’re using conda, activate your env first.)

---

## Repository structure (high level)

```
src/                 # code (models, solvers, training, optimization, analysis)
claim_audit/          # evidence bundle (CSV + claim_map)
results/              # figures / exports (optional)
data/                 # training datasets (optional / referenced by scripts)
```

---

## What makes this “an artifact” (and where you stand)

An artifact is “done enough” when:
1) a stranger can run the repro script and get the same numbers,
2) claims are scoped and tied to exact files/columns/filters,
3) repo text matches what the evidence supports.

You are **at that stage now** (this work is packaging + accuracy, not endless tuning).

---

## License

MIT (see `LICENSE`).

## Citation

Daniel Sleiman. (2025). *Inverse Design of Functionally Graded Porous Media via Physics-Informed Generative Models*. GitHub repository.
