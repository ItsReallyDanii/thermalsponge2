# Inverse Design of Functionally Graded Porous Media
### *A Physics-Informed Generative Approach to Biological & Thermal Transport*

![Status](https://img.shields.io/badge/Status-Research_Artifact-blue)
![Domain](https://img.shields.io/badge/Domain-SciML-green)
![Framework](https://img.shields.io/badge/Framework-PyTorch-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## What this repo is (end goal)

A **reproducible research artifact**: generate porous microstructures, evaluate them with simple physics benchmarks, and ship an **evidence-linked claim audit** so anyone can re-run the numbers.

## Key findings (scoped + reproducible)

- **C1 (VERIFIED proxy):** Best synthetic design achieves **2.91×** higher **stiffness_potential (proxy)** vs biological median (**2.76×** vs mean), where  
  `stiffness_potential = (1 − Porosity)^2`.
- **C2 (VERIFIED but scoped):** Designs are Pareto-optimal **vs Straight Fins only** (`Fins_*`) under the current mapping  
  (synthetic `flux := thermal_metrics.Q_total`, `density := thermal_metrics.rho_solid`).

> Scope note (C2): If Grid/Random baselines are included, synthetics are dominated under the current mapping. So the Pareto claim must **name the baseline set**.

---

## ✅ Evidence (Claim Audit)

Primary artifact:
- `claim_audit/claim_map_v3.json`  (authoritative claim audit)

Repro script:
- `src/repro_claims.py`

### Pasteable README evidence block

```md
**VERIFIED C1 (proxy)**: `claim_audit/flow_metrics.csv` filter `Type=='real'` (rows 0–19), cols [`Type`,`Porosity`]; define `stiffness_potential=(1-Porosity)^2` → mean=0.3291847807820886, median=0.31166180002037436.
**VERIFIED C1 (best synthetic)**: `claim_audit/flow_stiffness_candidates.csv` rows 0–9; `argmax(stiffness_potential)` at row 0 → best=0.9078656174242496.
**VERIFIED C1 ratios**: best/mean=2.7579209927849977× and best/median=2.9129832958832282× (from the two CSVs/filters above).
**UNVERIFIED (literal stiffness)**: no measured “hydraulic stiffness” field exists in the provided CSV columns; only the Porosity-derived proxy is supported.
**VERIFIED C2 scope**: baselines are **Straight Fins only**: `claim_audit/baseline_metrics.csv` rows 0–4 where `name.startswith('Fins_')`.
**VERIFIED C2 mapping+Pareto**: synthetic uses `thermal_metrics.csv` (`Q_total`→flux, `rho_solid`→density); Pareto=max flux, min density → front counts vs Fins_*: 21 synthetic + 2 baseline.
**DIAGNOSTIC**: if all baselines included (`baseline_metrics.csv` rows 0–11) → front counts: 0 synthetic + 7 baseline.
```

---

## Reproduce the claim audit (one command)

From repo root:

```bash
python src/repro_claims.py
```

Expected: it prints the C1/C2 summary and regenerates the audit outputs referenced above.

---

## Install

If you have a `requirements.txt`, prefer:

```bash
pip install -r requirements.txt
```

Otherwise, minimum for repro:

```bash
pip install pandas numpy matplotlib torch torchvision pillow
```

---

## Repository structure (high level)

```
src/                 # code (models, solvers, training, analysis)
claim_audit/          # evidence bundle (CSV + claim maps)
results/              # plots / exports
data/                 # datasets (optional)
```

## License

MIT (see `LICENSE`).

## Citation

Daniel Sleiman. (2025). *Inverse Design of Functionally Graded Porous Media via Physics-Informed Generative Models*. GitHub repository.
