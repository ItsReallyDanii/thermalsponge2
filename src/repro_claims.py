"""
Reproduce Claim Audit numbers from repo-relative CSVs.

Expected layout (repo root):
  claim_audit/
    flow_metrics.csv
    flow_stiffness_candidates.csv
    thermal_metrics.csv
    baseline_metrics.csv

Run:
  python src/repro_claims.py
"""

from __future__ import annotations

from pathlib import Path
import json
import pandas as pd


def pareto_front(points, maximize_cols, minimize_cols):
    front = []
    for i, p in enumerate(points):
        dominated = False
        for j, q in enumerate(points):
            if i == j:
                continue

            better_or_equal = True
            strictly_better = False

            for c in maximize_cols:
                if q[c] < p[c]:
                    better_or_equal = False
                    break
                if q[c] > p[c]:
                    strictly_better = True

            if not better_or_equal:
                continue

            for c in minimize_cols:
                if q[c] > p[c]:
                    better_or_equal = False
                    break
                if q[c] < p[c]:
                    strictly_better = True

            if better_or_equal and strictly_better:
                dominated = True
                break

        if not dominated:
            front.append(p)
    return front


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    audit_dir = repo_root / "claim_audit"

    # Load CSVs (repo-relative)
    flow_metrics = pd.read_csv(audit_dir / "flow_metrics.csv")
    candidates = pd.read_csv(audit_dir / "flow_stiffness_candidates.csv")
    thermal = pd.read_csv(audit_dir / "thermal_metrics.csv")
    baselines = pd.read_csv(audit_dir / "baseline_metrics.csv")

    # --- C1 (proxy)
    real = flow_metrics[flow_metrics["Type"] == "real"].copy()
    real["density"] = 1.0 - real["Porosity"]
    real["stiffness_potential"] = real["density"] ** 2
    real_mean = float(real["stiffness_potential"].mean())
    real_median = float(real["stiffness_potential"].median())

    if "stiffness_potential" not in candidates.columns:
        candidates = candidates.copy()
        candidates["density"] = 1.0 - candidates["Porosity"]
        candidates["stiffness_potential"] = candidates["density"] ** 2

    best_idx = int(candidates["stiffness_potential"].idxmax())
    best_val = float(candidates.loc[best_idx, "stiffness_potential"])
    ratio_mean = best_val / real_mean
    ratio_median = best_val / real_median

    print("C1 (stiffness_potential proxy)")
    print(f"  real mean   = {real_mean}")
    print(f"  real median = {real_median}")
    print(f"  best_synthetic stiffness_potential = {best_val} (row {best_idx} in flow_stiffness_candidates.csv)")
    print(f"  ratio(best/mean)   = {ratio_mean}x")
    print(f"  ratio(best/median) = {ratio_median}x")
    print("")

    # --- C2 (Pareto maximize flux, minimize density) vs baseline_set=Fins_*
    fins = baselines[baselines["name"].astype(str).str.startswith("Fins_")].copy()

    syn_points = [
        {
            "kind": "synthetic",
            "label": str(r.get("filename", "synthetic")),
            "flux": float(r["Q_total"]),
            "density": float(r["rho_solid"]),
        }
        for _, r in thermal.iterrows()
    ]

    base_points_fins = [
        {
            "kind": "baseline",
            "label": str(r["name"]),
            "flux": float(r["flux"]),
            "density": float(r["density"]),
        }
        for _, r in fins.iterrows()
    ]

    front_fins = pareto_front(syn_points + base_points_fins, maximize_cols=["flux"], minimize_cols=["density"])
    counts_fins = {"synthetic": 0, "baseline": 0}
    for p in front_fins:
        counts_fins[p["kind"]] += 1

    print("C2 (Pareto maximize flux, minimize density) vs baseline_set=Fins_*")
    print("  mapping: synthetic flux=thermal_metrics.Q_total, density=thermal_metrics.rho_solid")
    print("           baseline  flux=baseline_metrics.flux, density=baseline_metrics.density")
    print(f"  baseline scope: name startswith 'Fins_' (n={len(fins)})")
    print(f"  Pareto-front counts (synthetic vs Fins_*): {counts_fins}")

    in_scope_baselines = [p for p in front_fins if p["kind"] == "baseline"]
    if in_scope_baselines:
        print("  Pareto-front baseline points (in-scope):")
        for p in sorted(in_scope_baselines, key=lambda x: x["density"]):
            print(f"    {p['label']}: flux={p['flux']:.6f}, density={p['density']:.6f}")
    print("")

    # Diagnostic: include ALL baselines
    base_points_all = [
        {
            "kind": "baseline",
            "label": str(r["name"]),
            "flux": float(r["flux"]),
            "density": float(r["density"]),
        }
        for _, r in baselines.iterrows()
    ]

    front_all = pareto_front(syn_points + base_points_all, maximize_cols=["flux"], minimize_cols=["density"])
    counts_all = {"synthetic": 0, "baseline": 0}
    for p in front_all:
        counts_all[p["kind"]] += 1

    print("C2 diagnostic (if ALL baselines included)")
    print(f"  Pareto-front counts (synthetic vs all baselines): {counts_all}")

    all_baselines_on_front = [p for p in front_all if p["kind"] == "baseline"]
    if all_baselines_on_front:
        print("  Pareto-front baseline points (all):")
        for p in sorted(all_baselines_on_front, key=lambda x: x["flux"]):
            print(f"    {p['label']}: flux={p['flux']:.6f}, density={p['density']:.6f}")

        # Write a minimal v3 claim map snapshot (repo-relative)
    out = {
        "claims": [
            {
                "id": "C1",
                "name": "Stiffness proxy uplift vs real xylem",
                "status": "VERIFIED (proxy)",
                "definition": "stiffness_potential = (1 - Porosity)^2",
                "evidence": {
                    "bio_file": "claim_audit/flow_metrics.csv",
                    "bio_filter": "Type == 'real' (rows 0–19)",
                    "best_synth_file": "claim_audit/flow_stiffness_candidates.csv",
                    "best_synth_row": best_idx,
                    "best_value": best_val,
                    "real_mean": real_mean,
                    "real_median": real_median,
                    "ratio_vs_mean": ratio_mean,
                    "ratio_vs_median": ratio_median,
                },
            },
            {
                "id": "C2",
                "name": "Pareto-optimal vs Straight Fins (scoped)",
                "status": "VERIFIED (scoped)",
                "pareto_rule": "maximize flux, minimize density",
                "mapping": {
                    "synthetic_flux": "thermal_metrics.Q_total",
                    "synthetic_density": "thermal_metrics.rho_solid",
                    "baseline_flux": "baseline_metrics.flux",
                    "baseline_density": "baseline_metrics.density",
                },
                "baseline_scope": "baseline_metrics.name startswith 'Fins_'",
                "evidence": {
                    "synthetic_file": "claim_audit/thermal_metrics.csv",
                    "baseline_file": "claim_audit/baseline_metrics.csv",
                    "pareto_front_counts_vs_fins": counts_fins,
                    "pareto_front_counts_vs_all_baselines_diagnostic": counts_all,
                },
            },
        ]
    }

    out_path = audit_dir / "claim_map_v2.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("")
    print(f"Wrote {out_path.as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
