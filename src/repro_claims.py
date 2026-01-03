#!/usr/bin/env python3
"""
Repro script for repo claims C1 and C2.

Ground truth CSVs (repo-relative):
- flow_metrics.csv
- flow_stiffness_candidates.csv
- thermal_metrics.csv
- baseline_metrics.csv

Outputs:
- C1: real mean/median stiffness_potential and best-synthetic ratios
- C2: Pareto-front counts vs Fins_* only, plus (optional) counts if all baselines included
"""

from __future__ import annotations

import os
import sys
from typing import Dict

import numpy as np
import pandas as pd


def pareto_front_maximize_flux_minimize_density(df: pd.DataFrame, flux_col: str, dens_col: str) -> np.ndarray:
    """
    Boolean mask for Pareto-optimal points where:
      - higher flux is better (maximize)
      - lower density is better (minimize)

    A point j dominates i if:
      flux_j >= flux_i AND dens_j <= dens_i AND (flux_j > flux_i OR dens_j < dens_i)
    """
    flux = df[flux_col].to_numpy()
    dens = df[dens_col].to_numpy()
    n = len(df)
    is_pareto = np.ones(n, dtype=bool)

    for i in range(n):
        if not is_pareto[i]:
            continue
        dominates = (flux >= flux[i]) & (dens <= dens[i]) & ((flux > flux[i]) | (dens < dens[i]))
        dominates[i] = False  # exclude self
        if dominates.any():
            is_pareto[i] = False
    return is_pareto


def main() -> int:
    repo_dir = os.path.dirname(os.path.abspath(__file__))

    # --- C1: stiffness_potential proxy from Porosity ---
    flow_metrics = pd.read_csv(os.path.join(repo_dir, "flow_metrics.csv"))
    real = flow_metrics[flow_metrics["Type"] == "real"].copy()

    # proxy: density = 1 - Porosity ; stiffness_potential = density^2
    real["density"] = 1.0 - real["Porosity"]
    real["stiffness_potential"] = real["density"] ** 2

    real_mean = float(real["stiffness_potential"].mean())
    real_median = float(real["stiffness_potential"].median())

    flow_cand = pd.read_csv(os.path.join(repo_dir, "flow_stiffness_candidates.csv"))
    best_idx = int(flow_cand["stiffness_potential"].idxmax())
    best = flow_cand.loc[best_idx]
    best_stiff = float(best["stiffness_potential"])

    ratio_mean = best_stiff / real_mean
    ratio_median = best_stiff / real_median

    print("C1 (stiffness_potential proxy from Porosity)")
    print(f"  real rows: Type=='real' (n={len(real)})")
    print(f"  proxy: stiffness_potential = (1-Porosity)^2")
    print(f"  real_mean_stiffness_potential   = {real_mean:.16f}")
    print(f"  real_median_stiffness_potential = {real_median:.16f}")
    print(f"  best_synthetic stiffness_potential = {best_stiff:.16f} (row {best_idx} in flow_stiffness_candidates.csv)")
    print(f"  ratio(best/mean)   = {ratio_mean:.16f}x")
    print(f"  ratio(best/median) = {ratio_median:.16f}x")
    print()

    # --- C2: Pareto (maximize flux, minimize density) vs Fins_* only ---
    thermal = pd.read_csv(os.path.join(repo_dir, "thermal_metrics.csv"))[["filename", "Q_total", "rho_solid"]].copy()
    baseline = pd.read_csv(os.path.join(repo_dir, "baseline_metrics.csv"))[["name", "flux", "density"]].copy()

    baseline_fins = baseline[baseline["name"].astype(str).str.startswith("Fins_")].copy()

    # Normalize columns for combined Pareto computation
    thermal_points = thermal.rename(columns={"filename": "id", "Q_total": "flux", "rho_solid": "density"}).assign(source="synthetic")
    fins_points = baseline_fins.rename(columns={"name": "id"}).assign(source="baseline")

    combined_fins = pd.concat([thermal_points, fins_points], ignore_index=True)
    pareto_mask_fins = pareto_front_maximize_flux_minimize_density(combined_fins, "flux", "density")
    pareto_fins = combined_fins[pareto_mask_fins]
    counts_fins: Dict[str, int] = pareto_fins["source"].value_counts().to_dict()

    print("C2 (Pareto maximize flux, minimize density) vs baseline_set=Fins_*")
    print("  mapping: synthetic flux=thermal_metrics.Q_total, density=thermal_metrics.rho_solid")
    print("           baseline  flux=baseline_metrics.flux, density=baseline_metrics.density")
    print(f"  baseline scope: name startswith 'Fins_' (n={len(baseline_fins)})")
    print(f"  Pareto-front counts (synthetic vs Fins_*): {counts_fins}")
    print("  Pareto-front baseline points (in-scope):")
    for _, r in pareto_fins[pareto_fins["source"] == "baseline"].sort_values(["density", "flux"]).iterrows():
        print(f"    {r['id']}: flux={r['flux']:.6f}, density={r['density']:.6f}")
    print()

    # Optional diagnostic: what happens if you include ALL baselines (Grid_/Random_/etc.)
    all_points = baseline.rename(columns={"name": "id"}).assign(source="baseline")
    combined_all = pd.concat([thermal_points, all_points], ignore_index=True)
    pareto_mask_all = pareto_front_maximize_flux_minimize_density(combined_all, "flux", "density")
    pareto_all = combined_all[pareto_mask_all]
    counts_all: Dict[str, int] = pareto_all["source"].value_counts().to_dict()

    print("C2 diagnostic (if ALL baselines included)")
    print(f"  Pareto-front counts (synthetic vs all baselines): {counts_all}")
    print("  Pareto-front baseline points (all):")
    for _, r in pareto_all[pareto_all["source"] == "baseline"].sort_values(["density", "flux"]).iterrows():
        print(f"    {r['id']}: flux={r['flux']:.6f}, density={r['density']:.6f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
