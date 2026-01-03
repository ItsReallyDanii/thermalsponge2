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

from datetime import datetime, timezone
from pathlib import Path
import json

import pandas as pd


def pareto_front(points: list[dict], maximize_cols: list[str], minimize_cols: list[str]) -> list[dict]:
    """Return Pareto-efficient points under:
    - maximize for maximize_cols
    - minimize for minimize_cols
    """
    front: list[dict] = []
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


def utc_now_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    audit_dir = repo_root / "claim_audit"

    # Load CSVs (repo-relative)
    flow_metrics = pd.read_csv(audit_dir / "flow_metrics.csv")
    candidates = pd.read_csv(audit_dir / "flow_stiffness_candidates.csv")
    thermal = pd.read_csv(audit_dir / "thermal_metrics.csv")
    baselines = pd.read_csv(audit_dir / "baseline_metrics.csv")

    # --- C1 (proxy): stiffness_potential = (1 - Porosity)^2
    real = flow_metrics[flow_metrics["Type"] == "real"].copy()
    real["density"] = 1.0 - real["Porosity"]
    real["stiffness_potential"] = real["density"] ** 2

    real_mean = float(real["stiffness_potential"].mean())
    real_median = float(real["stiffness_potential"].median())

    best_idx = int(candidates["stiffness_potential"].idxmax())
    best_val = float(candidates.loc[best_idx, "stiffness_potential"])

    ratio_mean = best_val / real_mean
    ratio_median = best_val / real_median

    print("C1 (proxy stiffness_potential = (1-Porosity)^2)")
    print(f"  real_mean_stiffness_potential:   {real_mean:.16f}")
    print(f"  real_median_stiffness_potential: {real_median:.16f}")
    print(f"  best_synthetic_stiffness_potential (row {best_idx}): {best_val:.16f}")
    print(f"  ratio(best/mean):   {ratio_mean:.16f}x")
    print(f"  ratio(best/median): {ratio_median:.16f}x")

    # --- C2 (Pareto): maximize flux, minimize density
    # Synthetic mapping: flux := Q_total, density := rho_solid
    synthetic_points: list[dict] = []
    for i, r in thermal.iterrows():
        synthetic_points.append(
            {
                "kind": "synthetic",
                "label": str(r["filename"]),
                "row_index": int(i),
                "flux": float(r["Q_total"]),
                "density": float(r["rho_solid"]),
            }
        )

    baseline_points: list[dict] = []
    for i, r in baselines.iterrows():
        baseline_points.append(
            {
                "kind": "baseline",
                "label": str(r["name"]),
                "row_index": int(i),
                "flux": float(r["flux"]),
                "density": float(r["density"]),
            }
        )

    # Scope baselines to Straight Fins only: name startswith 'Fins_'
    fins_baselines = [p for p in baseline_points if p["label"].startswith("Fins_")]

    combined_scoped = synthetic_points + fins_baselines
    front_scoped = pareto_front(combined_scoped, maximize_cols=["flux"], minimize_cols=["density"])
    counts_scoped = {
        "synthetic": sum(1 for p in front_scoped if p["kind"] == "synthetic"),
        "baseline": sum(1 for p in front_scoped if p["kind"] == "baseline"),
    }

    scoped_baselines_on_front = sorted(
        [p for p in front_scoped if p["kind"] == "baseline"],
        key=lambda x: x["flux"],
    )

    print("")
    print("C2 (Pareto: maximize flux, minimize density)")
    print(f"  Baseline scope: Fins_* only (n={len(fins_baselines)})")
    print(f"  Pareto-front counts (synthetic vs Fins_* baselines): {counts_scoped}")
    if scoped_baselines_on_front:
        print("  Pareto-front baseline points (scoped):")
        for p in scoped_baselines_on_front:
            print(f"    {p['label']}: flux={p['flux']:.6f}, density={p['density']:.6f}")

    # Diagnostic: include ALL baselines
    combined_all = synthetic_points + baseline_points
    front_all = pareto_front(combined_all, maximize_cols=["flux"], minimize_cols=["density"])
    counts_all = {
        "synthetic": sum(1 for p in front_all if p["kind"] == "synthetic"),
        "baseline": sum(1 for p in front_all if p["kind"] == "baseline"),
    }

    all_baselines_on_front = sorted(
        [p for p in front_all if p["kind"] == "baseline"],
        key=lambda x: x["flux"],
    )

    print("")
    print("C2 diagnostic (if ALL baselines included)")
    print(f"  Pareto-front counts (synthetic vs all baselines): {counts_all}")
    if all_baselines_on_front:
        print("  Pareto-front baseline points (all):")
        for p in all_baselines_on_front:
            print(f"    {p['label']}: flux={p['flux']:.6f}, density={p['density']:.6f}")

    # Write v3 claim map snapshot (repo-relative)
    out = {
        "generated_at_utc": utc_now_z(),
        "inputs_used": {
            "flow_metrics_csv": "claim_audit/flow_metrics.csv",
            "flow_stiffness_candidates_csv": "claim_audit/flow_stiffness_candidates.csv",
            "thermal_metrics_csv": "claim_audit/thermal_metrics.csv",
            "baseline_metrics_csv": "claim_audit/baseline_metrics.csv",
            "repro_script": "src/repro_claims.py",
        },
        "claims": [
            {
                "id": "C1",
                "label": "~2.8–2.9× stiffness_potential (proxy)",
                "original_public_claim": "3× hydraulic stiffness compared to biological xylem",
                "status": "VERIFIED_PROXY",
                "what_is_supported": (
                    "Best synthetic stiffness_potential (proxy) = 0.9078656174242496; "
                    "ratios = 2.7579209927849977× vs bio mean and 2.9129832958832282× vs bio median, "
                    "where stiffness_potential=(1-Porosity)^2 computed on biological rows Type=='real'."
                ),
                "definition": {
                    "proxy_name": "stiffness_potential",
                    "proxy_formula": "stiffness_potential = (1 - Porosity)^2 ; density = 1 - Porosity",
                    "notes": "Porosity-derived stiffness proxy (heuristic E ∝ ρ^2). Not a measured hydraulic stiffness.",
                },
                "evidence": [
                    {
                        "file": "claim_audit/flow_metrics.csv",
                        "rows": {
                            "where": "Type == 'real' (biological)",
                            "row_indices": [],  # filled below
                        },
                        "columns": ["Type", "Porosity"],
                        "transform": "density=1-Porosity; stiffness_potential=density^2",
                        "summary_stats": {
                            "real_mean_stiffness_potential": real_mean,
                            "real_median_stiffness_potential": real_median,
                        },
                    },
                    {
                        "file": "claim_audit/flow_stiffness_candidates.csv",
                        "rows": {
                            "where": "Type == 'synthetic' (all rows in this file)",
                            "row_indices": "0-9",
                        },
                        "columns": ["Type", "stiffness_potential", "Porosity", "density"],
                        "selection": "argmax(stiffness_potential)",
                        "selected_row_index": best_idx,
                        "selected_value": best_val,
                    },
                ],
                "computed_claim_check": {
                    "best_synthetic_stiffness_potential": best_val,
                    "real_mean_stiffness_potential": real_mean,
                    "real_median_stiffness_potential": real_median,
                    "ratio_best_over_real_mean": ratio_mean,
                    "ratio_best_over_real_median": ratio_median,
                    "headline": "Proxy stiffness_potential improves ~2.76× over biological mean (and ~2.91× over median).",
                },
                "plot_paths": ["results/claim_audit_plots/flow_vs_stiffness_claimmap.png"],
                "notes": "Do not describe this as literal/measured 'hydraulic stiffness'; only the Porosity-derived proxy is supported by the CSV columns.",
            },
            {
                "id": "C2",
                "label": "Pareto-optimal vs Straight Fins (Fins_* only, scoped)",
                "original_public_claim": "Pareto-optimal cooling efficiency compared to standard engineering baselines",
                "status": "VERIFIED_SCOPED",
                "metric_mapping_used": {
                    "flux": "synthetic: thermal_metrics.csv: Q_total ; baseline: baseline_metrics.csv: flux",
                    "density": "synthetic: thermal_metrics.csv: rho_solid ; baseline: baseline_metrics.csv: density",
                    "pareto_definition": "maximize flux, minimize density",
                },
                "baseline_scope": {
                    "file": "claim_audit/baseline_metrics.csv",
                    "rows": {
                        "where": "name startswith 'Fins_' (Straight Fins only)",
                        "row_indices": [],  # filled below
                    },
                    "n_baseline_points": int(len(fins_baselines)),
                },
                "evidence": [
                    {
                        "file": "claim_audit/thermal_metrics.csv",
                        "columns": ["filename", "Q_total", "rho_solid"],
                        "row_indices": "all (0-127)",
                    },
                    {
                        "file": "claim_audit/baseline_metrics.csv",
                        "columns": ["name", "flux", "density"],
                        "row_indices": "all (0-11); scope applied via baseline_scope",
                    },
                ],
                "computed_claim_check": {
                    "pareto_front_counts_vs_fins_scope": counts_scoped,
                    "pareto_front_baseline_points_in_scope": [
                        {
                            "id": p["label"],
                            "row_index": p["row_index"],
                            "flux": p["flux"],
                            "density": p["density"],
                        }
                        for p in scoped_baselines_on_front
                    ],
                    "diagnostic_if_all_baselines_included": {
                        "pareto_front_counts": counts_all,
                        "pareto_front_baseline_points": [
                            {
                                "id": p["label"],
                                "row_index": p["row_index"],
                                "flux": p["flux"],
                                "density": p["density"],
                            }
                            for p in all_baselines_on_front
                        ],
                    },
                    "headline": (
                        "With baselines scoped to Fins_* only, 21 synthetics are Pareto-optimal; "
                        "including Grid_/Random_ baselines removes synthetics from the Pareto front under current mapping."
                    ),
                },
                "plot_paths": ["results/claim_audit_plots/thermal_flux_density_claimmap.png"],
                "notes": "If baseline scope is broadened beyond Fins_* (e.g., Grid_*/Random_*), the Pareto claim fails under the current flux/density mapping.",
            },
        ],
    }

    # Fill row_indices
    out["claims"][0]["evidence"][0]["rows"]["row_indices"] = list(map(int, real.index.tolist()))
    out["claims"][1]["baseline_scope"]["rows"]["row_indices"] = [
        int(i) for i in baselines.index[baselines["name"].astype(str).str.startswith("Fins_")].tolist()
    ]

    out_path = audit_dir / "claim_map_v3.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("")
    print(f"Wrote {out_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
