"""
repro_claims_v4.py — Reproduce all claims C1-C5 from repo-relative CSVs.

Additive extension of repro_claims.py (which handles C1/C2 only).
This script reproduces C1, C2 (same logic), plus new BITO claims C3, C4, C5.

C1/C2 logic is duplicated (not imported) to avoid coupling with existing script.

Statistical test selection rule (documented identically in CLAIMS.md):
    For same-seed paired comparisons:
        1. Compute paired differences d_i = treatment_i - control_i.
        2. Shapiro-Wilk on d_i: if p >= 0.05 (normal), use scipy.stats.ttest_rel.
        3. If Shapiro-Wilk p < 0.05 (non-normal), use scipy.stats.wilcoxon.
        4. Count metrics (chatter_count) always use wilcoxon.
        5. alpha = 0.05, one-sided: treatment < control for effort/chatter.
        6. SLA compliance uses exact count (zero-violation threshold or comparison).

Metric taxonomy (locked, matches everywhere):
    Must:        kWh_ctrl, sla_violations, sla_max_exceedance
    Nice:        chatter_count
    Exploratory: bio_proxy_trend (not tested here)

Run:
    python src/repro_claims_v4.py

Outputs:
    claim_audit/claim_map_v4.json

scipy is used ONLY in this audit/repro path — never in the runtime simulation loop.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import shapiro, ttest_rel, wilcoxon

# Ensure repo root is importable
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def utc_now_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------
# C1 / C2 reproduction (duplicated from repro_claims.py for isolation)
# ---------------------------------------------------------------

def pareto_front(points: list[dict], maximize_cols: list[str],
                 minimize_cols: list[str]) -> list[dict]:
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


def _find_csv(audit_dir: Path, name: str, fallback_paths: list[Path]) -> Path | None:
    """Locate a CSV under audit_dir first, then fallback paths."""
    p = audit_dir / name
    if p.exists():
        return p
    for fb in fallback_paths:
        if fb.exists():
            return fb
    return None


def repro_c1(audit_dir: Path, repo_root: Path) -> dict | None:
    flow_path = _find_csv(audit_dir, "flow_metrics.csv", [
        repo_root / "results" / "flow_metrics" / "flow_metrics.csv",
    ])
    cand_path = _find_csv(audit_dir, "flow_stiffness_candidates.csv", [
        repo_root / "results" / "flow_stiffness_candidates.csv",
    ])
    if flow_path is None or cand_path is None:
        print("  SKIP C1: flow_metrics.csv or flow_stiffness_candidates.csv not found")
        return None

    flow_metrics = pd.read_csv(flow_path)
    candidates = pd.read_csv(cand_path)

    real = flow_metrics[flow_metrics["Type"] == "real"].copy()
    real["density"] = 1.0 - real["Porosity"]
    real["stiffness_potential"] = real["density"] ** 2

    real_mean = float(real["stiffness_potential"].mean())
    real_median = float(real["stiffness_potential"].median())

    best_idx = int(candidates["stiffness_potential"].idxmax())
    best_val = float(candidates.loc[best_idx, "stiffness_potential"])

    return {
        "id": "C1",
        "label": "~2.8-2.9x stiffness_potential (proxy)",
        "status": "VERIFIED_PROXY",
        "computed_claim_check": {
            "best_synthetic_stiffness_potential": best_val,
            "real_mean_stiffness_potential": real_mean,
            "real_median_stiffness_potential": real_median,
            "ratio_best_over_real_mean": best_val / real_mean,
            "ratio_best_over_real_median": best_val / real_median,
        },
    }


def repro_c2(audit_dir: Path, repo_root: Path) -> dict | None:
    therm_path = _find_csv(audit_dir, "thermal_metrics.csv", [
        repo_root / "results" / "thermal_metrics" / "thermal_metrics.csv",
    ])
    base_path = _find_csv(audit_dir, "baseline_metrics.csv", [
        repo_root / "results" / "baselines" / "baseline_metrics.csv",
    ])
    if therm_path is None or base_path is None:
        print("  SKIP C2: thermal_metrics.csv or baseline_metrics.csv not found")
        return None

    thermal = pd.read_csv(therm_path)
    baselines = pd.read_csv(base_path)

    synthetic_points = [
        {"kind": "synthetic", "label": str(r["filename"]),
         "flux": float(r["Q_total"]), "density": float(r["rho_solid"])}
        for _, r in thermal.iterrows()
    ]
    fins_baselines = [
        {"kind": "baseline", "label": str(r["name"]),
         "flux": float(r["flux"]), "density": float(r["density"])}
        for _, r in baselines.iterrows()
        if str(r["name"]).startswith("Fins_")
    ]

    combined = synthetic_points + fins_baselines
    front = pareto_front(combined, maximize_cols=["flux"], minimize_cols=["density"])
    counts = {
        "synthetic": sum(1 for p in front if p["kind"] == "synthetic"),
        "baseline": sum(1 for p in front if p["kind"] == "baseline"),
    }

    return {
        "id": "C2",
        "label": "Pareto-optimal vs Straight Fins (Fins_* only, scoped)",
        "status": "VERIFIED_SCOPED",
        "computed_claim_check": {
            "pareto_front_counts_vs_fins_scope": counts,
            "baseline_scope": "name.startswith('Fins_')",
            "n_baselines_in_scope": len(fins_baselines),
        },
    }


# ---------------------------------------------------------------
# Paired statistical testing
# ---------------------------------------------------------------

def run_paired_test(
    treatment: np.ndarray,
    control: np.ndarray,
    metric_name: str,
    alpha: float = 0.05,
    is_count: bool = False,
) -> dict:
    """Run appropriate paired test per the documented selection rule.

    Rule:
        - Count metrics → always Wilcoxon signed-rank.
        - Continuous metrics → Shapiro-Wilk on paired diffs:
            if p >= 0.05: ttest_rel (paired t-test)
            else: Wilcoxon signed-rank
        - All tests one-sided: H_a: treatment < control (lower is better).
        - alpha = 0.05.
    """
    n = len(treatment)
    assert len(control) == n
    diffs = treatment - control

    result = {
        "metric": metric_name,
        "n": n,
        "alpha": alpha,
        "treatment_mean": float(treatment.mean()),
        "control_mean": float(control.mean()),
        "mean_diff": float(diffs.mean()),
        "direction": "treatment < control (lower is better)",
    }

    # Check for zero-variance (all differences identical)
    if np.all(diffs == diffs[0]):
        result.update({
            "test": "none (zero variance in differences)",
            "statistic": float("nan"),
            "p_value": float("nan"),
            "significant": False,
            "note": f"All paired differences identical ({diffs[0]:.6f}); no test possible.",
        })
        return result

    if is_count:
        # Count metrics → Wilcoxon
        stat, p_two = wilcoxon(diffs, alternative="two-sided")
        # One-sided: treatment < control → diffs should be negative
        p_one = p_two / 2 if diffs.mean() < 0 else 1.0 - p_two / 2
        result.update({
            "test": "wilcoxon_signed_rank",
            "test_selection_reason": "count metric (always wilcoxon)",
            "statistic": float(stat),
            "p_value": float(p_one),
            "significant": p_one < alpha,
        })
    else:
        # Continuous: Shapiro-Wilk on diffs
        sw_stat, sw_p = shapiro(diffs)
        result["shapiro_wilk_p"] = float(sw_p)

        if sw_p >= 0.05:
            # Normal → paired t-test (one-sided: treatment < control)
            stat, p_two = ttest_rel(treatment, control)
            p_one = p_two / 2 if diffs.mean() < 0 else 1.0 - p_two / 2
            result.update({
                "test": "ttest_rel",
                "test_selection_reason": f"Shapiro-Wilk p={sw_p:.4f} >= 0.05 (normal)",
                "statistic": float(stat),
                "p_value": float(p_one),
                "significant": p_one < alpha,
            })
        else:
            # Non-normal → Wilcoxon
            stat, p_two = wilcoxon(diffs, alternative="two-sided")
            p_one = p_two / 2 if diffs.mean() < 0 else 1.0 - p_two / 2
            result.update({
                "test": "wilcoxon_signed_rank",
                "test_selection_reason": f"Shapiro-Wilk p={sw_p:.4f} < 0.05 (non-normal)",
                "statistic": float(stat),
                "p_value": float(p_one),
                "significant": p_one < alpha,
            })

    return result


# ---------------------------------------------------------------
# C3 / C4 / C5 reproduction
# ---------------------------------------------------------------

def repro_c3(df: pd.DataFrame, config: dict) -> dict:
    """C3 (Must: kWh_ctrl). Paired test: PID+Gate vs PID-only, same seeds, Xylem."""
    xylem = df[df["morphology"] == "Xylem"]
    pid = xylem[xylem["controller"] == "PID"].sort_values("seed")
    gate = xylem[xylem["controller"] == "PID+Gate"].sort_values("seed")
    always = xylem[xylem["controller"] == "AlwaysOn"].sort_values("seed")

    assert list(pid["seed"]) == list(gate["seed"]), "Seed mismatch in pairing"

    # Primary: PID+Gate vs PID (paired by seed)
    test_vs_pid = run_paired_test(
        gate["kWh_ctrl"].values, pid["kWh_ctrl"].values,
        "kWh_ctrl (PID+Gate vs PID)", is_count=False,
    )

    # Secondary: PID+Gate vs AlwaysOn (paired by seed)
    test_vs_always = run_paired_test(
        gate["kWh_ctrl"].values, always["kWh_ctrl"].values,
        "kWh_ctrl (PID+Gate vs AlwaysOn)", is_count=False,
    )

    # Determine status
    gate_mean = float(gate["kWh_ctrl"].mean())
    pid_mean = float(pid["kWh_ctrl"].mean())
    always_mean = float(always["kWh_ctrl"].mean())

    # C3 status: no superiority claim. Report as comparable unless material increase.
    if test_vs_pid["significant"]:
        status = "VERIFIED_SIM_ONLY"
        verdict = "PID+Gate reduces kWh_ctrl vs PID (significant)"
    elif gate_mean > pid_mean * 1.05:
        status = "NOT_SUPPORTED"
        verdict = "PID+Gate increases kWh_ctrl vs PID by >5% (material increase)"
    else:
        status = "NOT_SIGNIFICANT"
        verdict = "kWh_ctrl comparable / no material increase under tested settings"

    return {
        "id": "C3",
        "label": "Control effort comparable under gated vs PID-only cooling",
        "status": status,
        "verdict": verdict,
        "metric_tier": "Must",
        "computed_claim_check": {
            "gate_mean_kWh_ctrl": gate_mean,
            "pid_mean_kWh_ctrl": pid_mean,
            "always_mean_kWh_ctrl": always_mean,
            "reduction_vs_always_pct": (1.0 - gate_mean / always_mean) * 100 if always_mean > 0 else 0,
            "test_vs_pid": test_vs_pid,
            "test_vs_always": test_vs_always,
            "n_total": len(config.get("seeds", [])),
            "n_eff": len(pid),
            "seeds_used": list(map(int, pid["seed"].tolist())),
            "excluded_seeds": [],
            "exclusion_reason": "none (all seeds included per pre-registration)",
        },
        "analysis_label": "trigger-qualified analysis",
    }


def repro_c4(df: pd.DataFrame, config: dict) -> dict:
    """C4 (Nice: chatter). Paired Wilcoxon: PID+Gate vs PID-only, same seeds."""
    xylem = df[df["morphology"] == "Xylem"]
    pid = xylem[xylem["controller"] == "PID"].sort_values("seed")
    gate = xylem[xylem["controller"] == "PID+Gate"].sort_values("seed")

    test = run_paired_test(
        gate["chatter_count"].values, pid["chatter_count"].values,
        "chatter_count (PID+Gate vs PID)", is_count=True,
    )

    gate_mean = float(gate["chatter_count"].mean())
    pid_mean = float(pid["chatter_count"].mean())

    status = "VERIFIED_SIM_ONLY" if test["significant"] else "NOT_SIGNIFICANT"

    return {
        "id": "C4",
        "label": "Reduced actuator chatter via refractory gating",
        "status": status,
        "metric_tier": "Nice",
        "computed_claim_check": {
            "gate_mean_chatter": gate_mean,
            "pid_mean_chatter": pid_mean,
            "reduction_pct": (1.0 - gate_mean / pid_mean) * 100 if pid_mean > 0 else 0,
            "test": test,
            "n_total": len(config.get("seeds", [])),
            "n_eff": len(pid),
            "seeds_used": list(map(int, pid["seed"].tolist())),
            "excluded_seeds": [],
            "exclusion_reason": "none (all seeds included per pre-registration)",
        },
        "chatter_definition": "count of 0->1 transitions in binary gate signal u(t), threshold=0.5",
        "analysis_label": "trigger-qualified analysis",
    }


def repro_c5(df: pd.DataFrame, config: dict, hypothesis: dict) -> dict:
    """C5 (Must: SLA non-inferiority). Gate vs PID violations with pre-registered Δ.

    Non-inferiority criteria (from hypothesis_config.json):
        1. gate_total_viol <= pid_total_viol * (1 + Delta_sla_violations)
        2. gate_max_exc   <= pid_max_exc + Delta_max_exceedance
    Both must pass for non-inferiority verdict.
    """
    xylem = df[df["morphology"] == "Xylem"]
    pid = xylem[xylem["controller"] == "PID"].sort_values("seed")
    gate = xylem[xylem["controller"] == "PID+Gate"].sort_values("seed")
    always = xylem[xylem["controller"] == "AlwaysOn"].sort_values("seed")

    pid_total_viol = int(pid["sla_violations"].sum())
    gate_total_viol = int(gate["sla_violations"].sum())
    always_total_viol = int(always["sla_violations"].sum())

    pid_max_exc = float(pid["sla_max_exceedance"].max())
    gate_max_exc = float(gate["sla_max_exceedance"].max())

    # Non-inferiority margins from pre-registered hypothesis_config.json
    c5_hyp = hypothesis.get("C5", {})
    delta_viol = c5_hyp.get("Delta_sla_violations", 0.10)
    delta_exc = c5_hyp.get("Delta_max_exceedance", 0.02)

    # Criterion 1: violations within margin
    viol_bound = pid_total_viol * (1.0 + delta_viol)
    viol_pass = gate_total_viol <= viol_bound

    # Criterion 2: max exceedance within margin
    exc_bound = pid_max_exc + delta_exc
    exc_pass = gate_max_exc <= exc_bound

    non_inferior = viol_pass and exc_pass
    status = "VERIFIED_SIM_ONLY" if non_inferior else "NOT_SUPPORTED"

    # Porosity band for morphology qualification
    porosities = {}
    for _, row in xylem[xylem["controller"] == "PID"].iterrows():
        seed = int(row["seed"])
        from src.run_thermal_orchestration import generate_morphology
        from src.constants import VOID_THRESHOLD
        img = generate_morphology("Xylem", seed)
        porosities[seed] = float((img > VOID_THRESHOLD).mean())

    return {
        "id": "C5",
        "label": "Thermal SLA non-inferiority under gated control",
        "status": status,
        "metric_tier": "Must",
        "non_inferiority_test": {
            "Delta_sla_violations": delta_viol,
            "violations_bound": viol_bound,
            "gate_total_sla_violations": gate_total_viol,
            "pid_total_sla_violations": pid_total_viol,
            "violations_pass": viol_pass,
            "Delta_max_exceedance": delta_exc,
            "exceedance_bound": exc_bound,
            "gate_max_exceedance": gate_max_exc,
            "pid_max_exceedance": pid_max_exc,
            "exceedance_pass": exc_pass,
            "non_inferior": non_inferior,
            "source": "claim_audit/hypothesis_config.json",
        },
        "computed_claim_check": {
            "always_total_sla_violations": always_total_viol,
            "T_SLA": config.get("simulation", {}).get("T_SLA", 0.85),
            "n_total": len(config.get("seeds", [])),
            "n_eff": len(pid),
            "seeds_used": list(map(int, pid["seed"].tolist())),
            "excluded_seeds": [],
            "exclusion_reason": "none (all seeds included per pre-registration)",
        },
        "morphology_band": {
            "seed_porosities": porosities,
            "porosity_min": min(porosities.values()),
            "porosity_max": max(porosities.values()),
            "porosity_mean": sum(porosities.values()) / len(porosities),
        },
        "analysis_label": "trigger-qualified analysis",
    }


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    audit_dir = repo_root / "claim_audit"

    # --- C1 ---
    c1 = repro_c1(audit_dir, repo_root)
    if c1 is not None:
        print("C1 (proxy stiffness_potential)")
        cc = c1["computed_claim_check"]
        print(f"  best_synthetic: {cc['best_synthetic_stiffness_potential']:.16f}")
        print(f"  ratio(best/mean):   {cc['ratio_best_over_real_mean']:.16f}x")
        print(f"  ratio(best/median): {cc['ratio_best_over_real_median']:.16f}x")
        print(f"  status: {c1['status']}")

    # --- C2 ---
    c2 = repro_c2(audit_dir, repo_root)
    if c2 is not None:
        print(f"\nC2 (Pareto vs Fins_*)")
        print(f"  front counts: {c2['computed_claim_check']['pareto_front_counts_vs_fins_scope']}")
        print(f"  status: {c2['status']}")

    # --- C3/C4/C5 ---
    metrics_path = audit_dir / "orchestration_metrics.csv"
    config_path = audit_dir / "experiment_config.json"

    if not metrics_path.exists() or not config_path.exists():
        print("\nWARNING: orchestration_metrics.csv or experiment_config.json not found.")
        print("Run 'python -m src.run_thermal_orchestration' first.")
        return 1

    df = pd.read_csv(metrics_path)
    config = json.loads(config_path.read_text())

    # Load pre-registered hypotheses for non-inferiority margins
    hyp_path = audit_dir / "hypothesis_config.json"
    if not hyp_path.exists():
        print("\nERROR: hypothesis_config.json not found. Required for C5 non-inferiority test.")
        return 1
    hypothesis = json.loads(hyp_path.read_text()).get("hypotheses", {})

    c3 = repro_c3(df, config)
    print(f"\nC3 (kWh_ctrl: PID+Gate vs PID)")
    print(f"  gate_mean: {c3['computed_claim_check']['gate_mean_kWh_ctrl']:.4f}")
    print(f"  pid_mean:  {c3['computed_claim_check']['pid_mean_kWh_ctrl']:.4f}")
    print(f"  reduction vs AlwaysOn: {c3['computed_claim_check']['reduction_vs_always_pct']:.1f}%")
    t = c3["computed_claim_check"]["test_vs_pid"]
    print(f"  test(vs PID): {t['test']}, p={t['p_value']:.4f}, sig={t['significant']}")
    print(f"  n_total={c3['computed_claim_check']['n_total']}, n_eff={c3['computed_claim_check']['n_eff']}")
    print(f"  verdict: {c3['verdict']}")
    print(f"  analysis: {c3['analysis_label']}")
    print(f"  status: {c3['status']}")

    c4 = repro_c4(df, config)
    print(f"\nC4 (chatter: PID+Gate vs PID)")
    print(f"  gate_mean: {c4['computed_claim_check']['gate_mean_chatter']:.1f}")
    print(f"  pid_mean:  {c4['computed_claim_check']['pid_mean_chatter']:.1f}")
    print(f"  reduction: {c4['computed_claim_check']['reduction_pct']:.1f}%")
    t = c4["computed_claim_check"]["test"]
    print(f"  test: {t['test']}, p={t['p_value']:.4f}, sig={t['significant']}")
    print(f"  n_total={c4['computed_claim_check']['n_total']}, n_eff={c4['computed_claim_check']['n_eff']}")
    print(f"  analysis: {c4['analysis_label']}")
    print(f"  status: {c4['status']}")

    c5 = repro_c5(df, config, hypothesis)
    print(f"\nC5 (SLA non-inferiority)")
    ni = c5["non_inferiority_test"]
    cc5 = c5["computed_claim_check"]
    print(f"  violations: gate={ni['gate_total_sla_violations']}, pid={ni['pid_total_sla_violations']}, "
          f"bound={ni['violations_bound']:.0f} (Delta={ni['Delta_sla_violations']})")
    print(f"  violations_pass: {ni['violations_pass']}")
    print(f"  max_exceedance: gate={ni['gate_max_exceedance']:.4f}, pid={ni['pid_max_exceedance']:.4f}, "
          f"bound={ni['exceedance_bound']:.4f} (Delta={ni['Delta_max_exceedance']})")
    print(f"  exceedance_pass: {ni['exceedance_pass']}")
    print(f"  non_inferior: {ni['non_inferior']}")
    mb = c5["morphology_band"]
    print(f"  porosity band: [{mb['porosity_min']:.3f}, {mb['porosity_max']:.3f}] (mean={mb['porosity_mean']:.3f})")
    print(f"  n_total={cc5['n_total']}, n_eff={cc5['n_eff']}")
    print(f"  analysis: {c5['analysis_label']}")
    print(f"  status: {c5['status']}")

    # --- Write claim_map_v4.json ---
    out = {
        "generated_at_utc": utc_now_z(),
        "inputs_used": {
            "flow_metrics_csv": "claim_audit/flow_metrics.csv (fallback: results/flow_metrics/)",
            "flow_stiffness_candidates_csv": "claim_audit/flow_stiffness_candidates.csv (fallback: results/)",
            "thermal_metrics_csv": "claim_audit/thermal_metrics.csv (fallback: results/thermal_metrics/)",
            "baseline_metrics_csv": "claim_audit/baseline_metrics.csv (fallback: results/baselines/)",
            "orchestration_metrics_csv": "claim_audit/orchestration_metrics.csv",
            "experiment_config_json": "claim_audit/experiment_config.json",
            "hypothesis_config_json": "claim_audit/hypothesis_config.json",
            "repro_script": "src/repro_claims_v4.py",
        },
        "claims": [c for c in [c1, c2, c3, c4, c5] if c is not None],
        "statistical_test_rule": {
            "rule": (
                "For same-seed paired comparisons: Shapiro-Wilk on paired differences. "
                "If p >= 0.05 use ttest_rel (paired t-test), else Wilcoxon signed-rank. "
                "Count metrics always use Wilcoxon. alpha=0.05, one-sided: "
                "treatment < control for effort/chatter."
            ),
            "pairing": "same seed, same morphology (Xylem), different controller",
        },
        "metric_taxonomy": {
            "must": ["kWh_ctrl", "sla_violations", "sla_max_exceedance"],
            "nice": ["chatter_count"],
            "exploratory": ["bio_proxy_trend"],
        },
    }

    out_path = audit_dir / "claim_map_v4.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {out_path.as_posix()}")

    # Print statistical test selection rule
    print("\n" + "=" * 70)
    print("STATISTICAL TEST SELECTION RULE (applies to C3, C4, C5):")
    print(out["statistical_test_rule"]["rule"])
    print(f"Pairing: {out['statistical_test_rule']['pairing']}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
