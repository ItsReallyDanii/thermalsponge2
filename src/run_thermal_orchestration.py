"""
run_thermal_orchestration.py — Experiment runner for bio-thermal orchestration.

Runs the E1 + E2 experiment matrix:
    E1 (morphology effect): {Fins_20, Random_0.4, Xylem} x PID x 5 seeds = 15 runs
    E2 (gating effect):     Xylem x {PID, PID+Gate, AlwaysOn} x 5 seeds  = 15 runs
    Total: 30 runs.

For each run:
    1. Generate or load a morphology image (256x256).
    2. Build a gate_signal function from the controller config.
    3. Run the transient thermal solver.
    4. Compute control metrics.
    5. Collect results.

Outputs (under claim_audit/):
    - orchestration_metrics.csv   : all 30 rows of experiment results
    - sla_check.csv               : per-run SLA pass/fail
    - experiment_config.json      : locked experiment parameters

All controllers output binary gate signals u in {0, 1}:
    - AlwaysOn: u = 1 always.
    - PID: u = 1 if PID_output > 0.5 else 0 (bang-bang with PID-informed threshold).
    - PID+Gate: PID output > 0.5 triggers flytrap gate; gate output is 0 or 1.
This ensures the gate output contract is binary and consistent everywhere.

Chatter definition (must match control_metrics.py and all docs):
    chatter_count = number of 0->1 transitions in u(t), where u(t) is binarized
    at threshold 0.5.

No network dependencies. Local-only runtime.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

# Ensure repo root is importable
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.constants import (
    DT_DEFAULT,
    GATE_N_TRIGGER,
    GATE_T_REFRACTORY,
    GATE_T_WINDOW,
    K_VOID,
    N_STEPS_DEFAULT,
    T_SLA_DEFAULT,
    VOID_THRESHOLD,
)
from src.control_metrics import ControlMetrics, compute_control_metrics
from src.flytrap_gate import FlyTrapGate
from src.heat_simulation_transient import Q_CHIP_DEFAULT, solve_transient_heat
from src.pid_controller import PIDController

# ---------------------------------------------------------------
# Experiment config
# ---------------------------------------------------------------

SEEDS = [1, 4, 6, 7, 8, 10, 11, 13]

# PID gains (moderate, same across all experiments for fairness)
PID_KP = 8.0
PID_KI = 0.3
PID_KD = 2.0

# Reduced simulation for tractability (full 5000 can be slow x25 runs).
# 4000 steps at dt=0.1 = 400 time units — sufficient for multiple gate cycles.
N_STEPS_EXPERIMENT = 4000

CLAIM_AUDIT_DIR = REPO_ROOT / "claim_audit"


@dataclass
class ExperimentConfig:
    morphology: str
    controller: str
    seed: int
    dt: float
    n_steps: int
    T_SLA: float
    q_chip: float
    pid_Kp: float
    pid_Ki: float
    pid_Kd: float
    gate_N: int
    gate_T_window: int
    gate_T_refractory: int


# ---------------------------------------------------------------
# Morphology generators
# ---------------------------------------------------------------


def _generate_vertical_fins(shape: tuple[int, int] = (256, 256),
                            num_fins: int = 20, thickness: int = 4) -> np.ndarray:
    """Straight vertical fins. Matches benchmark_baselines.py generator."""
    img = np.ones(shape, dtype=np.float32)  # void (white)
    spacing = shape[1] // num_fins
    for i in range(num_fins):
        x = i * spacing + (spacing // 2)
        x_end = min(x + thickness, shape[1])
        img[:, x:x_end] = 0.0  # solid (black)
    return img


def _generate_random_noise(shape: tuple[int, int] = (256, 256),
                           density: float = 0.4, seed: int = 42) -> np.ndarray:
    """Random porous media. Matches benchmark_baselines.py generator."""
    rng = np.random.RandomState(seed)
    return rng.choice([0.0, 1.0], size=shape, p=[density, 1 - density]).astype(np.float32)


def _generate_xylem(shape: tuple[int, int] = (256, 256), seed: int = 42) -> np.ndarray:
    """Procedural xylem-like vascular network.

    Generates a high-porosity structure (~55-65% void) with multiple vertical
    trunks connected by horizontal vessel elements, mimicking xylem cross-section
    anatomy. Fully deterministic from seed. No model weights required.
    """
    rng = np.random.RandomState(seed)
    img = np.zeros(shape, dtype=np.float32)  # start all solid

    H, W = shape
    tw = W // 18  # trunk half-width (~14 pixels)

    # 3-4 vertical trunks (main vessels), evenly spaced with jitter
    n_trunks = 3 + rng.randint(0, 2)
    spacing = W // (n_trunks + 1)
    for i in range(n_trunks):
        cx = spacing * (i + 1) + rng.randint(-spacing // 8, spacing // 8 + 1)
        cx = max(tw, min(W - tw, cx))
        w = tw + rng.randint(-tw // 4, tw // 4 + 1)
        img[:, max(0, cx - w):min(W, cx + w)] = 1.0

    # 10-16 horizontal connections (vessel elements) between trunks
    n_horiz = 10 + rng.randint(0, 7)
    for _ in range(n_horiz):
        y = rng.randint(0, H)
        x1 = rng.randint(0, W)
        x2 = rng.randint(0, W)
        x_lo, x_hi = min(x1, x2), max(x1, x2)
        hw = rng.randint(max(1, tw // 4), tw // 2 + 1)
        y_lo = max(0, y - hw)
        y_hi = min(H, y + hw)
        img[y_lo:y_hi, x_lo:x_hi] = 1.0

    # 6-10 smaller lateral channels (ray parenchyma analog)
    n_rays = 6 + rng.randint(0, 5)
    for _ in range(n_rays):
        cy = rng.randint(0, H)
        cx = rng.randint(0, W)
        rw = rng.randint(max(1, tw // 5), tw // 3 + 1)
        rh = rng.randint(tw, tw * 2)
        y_lo = max(0, cy - rh)
        y_hi = min(H, cy + rh)
        x_lo = max(0, cx - rw)
        x_hi = min(W, cx + rw)
        img[y_lo:y_hi, x_lo:x_hi] = 1.0

    return img


def generate_morphology(name: str, seed: int,
                        shape: tuple[int, int] = (256, 256)) -> np.ndarray:
    """Generate a structure image by name.

    Parameters
    ----------
    name : one of "Fins_20", "Random_0.4", "Xylem".
    seed : random seed for reproducibility.
    shape : image dimensions.

    Returns
    -------
    img : (H, W) float32 array in [0, 1]. Bright=void, dark=solid.
    """
    if name == "Fins_20":
        return _generate_vertical_fins(shape=shape, num_fins=20, thickness=4)
    elif name == "Random_0.4":
        return _generate_random_noise(shape=shape, density=0.4, seed=seed)
    elif name == "Xylem":
        return _generate_xylem(shape=shape, seed=seed)
    else:
        raise ValueError(f"Unknown morphology: {name}")


# ---------------------------------------------------------------
# Controller builders
# ---------------------------------------------------------------


def make_controller(config: ExperimentConfig) -> Callable[[int, float], float]:
    """Build a gate_signal(timestep, T_max) -> u function from config.

    All controllers produce binary output u in {0, 1}.

    - 'AlwaysOn':  u = 1 always.
    - 'PID':       u = 1 if PID_step() > 0.5 else 0 (bang-bang with PID threshold).
    - 'PID+Gate':  PID output > 0.5 triggers flytrap gate; gate output is binary.
    """
    if config.controller == "AlwaysOn":
        def always_on(_step: int, _T_max: float) -> float:
            return 1.0
        return always_on

    elif config.controller == "PID":
        # Reverse-acting PID for cooling: feed (T_SLA - T_max) as measured,
        # setpoint = 0. When T > T_SLA: error = T_max - T_SLA > 0 -> u > 0.
        pid = PIDController(
            Kp=config.pid_Kp, Ki=config.pid_Ki, Kd=config.pid_Kd,
            dt=config.dt, setpoint=0.0,
        )

        def pid_controller(_step: int, T_max: float) -> float:
            measured = config.T_SLA - T_max  # negative when too hot
            u_raw = pid.step(measured)
            return 1.0 if u_raw > 0.5 else 0.0  # binary gate contract
        return pid_controller

    elif config.controller == "PID+Gate":
        pid = PIDController(
            Kp=config.pid_Kp, Ki=config.pid_Ki, Kd=config.pid_Kd,
            dt=config.dt, setpoint=0.0,
        )
        gate = FlyTrapGate(
            N_trigger=config.gate_N,
            T_window=config.gate_T_window,
            T_refractory=config.gate_T_refractory,
        )

        def pid_gate_controller(step: int, T_max: float) -> float:
            measured = config.T_SLA - T_max
            u_raw = pid.step(measured)
            trigger = u_raw > 0.5
            gate_open = gate.update(trigger, step)
            return 1.0 if gate_open else 0.0  # binary gate contract
        return pid_gate_controller

    else:
        raise ValueError(f"Unknown controller: {config.controller}")


# ---------------------------------------------------------------
# Single run
# ---------------------------------------------------------------


def run_single(config: ExperimentConfig) -> dict:
    """Run one experiment and return a flat dict of config + metrics."""
    img = generate_morphology(config.morphology, config.seed)
    controller = make_controller(config)

    result = solve_transient_heat(
        img_arr=img,
        gate_signal=controller,
        dt=config.dt,
        n_steps=config.n_steps,
        q_chip=config.q_chip,
    )

    metrics = compute_control_metrics(
        u_history=result.u_history,
        T_max_history=result.T_max_history,
        T_SLA=config.T_SLA,
        dt=config.dt,
    )

    row = asdict(config)
    row.update(asdict(metrics))
    return row


# ---------------------------------------------------------------
# Experiment matrix
# ---------------------------------------------------------------


def build_experiment_matrix() -> list[ExperimentConfig]:
    """Build E1 + E2 experiment configs.

    E1 (morphology effect): {Fins_20, Random_0.4, Xylem} x PID x 5 seeds = 15
    E2 (gating effect):     Xylem x {PID, PID+Gate, AlwaysOn} x 5 seeds  = 15
    Note: Xylem x PID appears in both E1 and E2 — deduplicated (5 runs shared).
    Total unique: 25 runs.
    """
    configs: list[ExperimentConfig] = []
    base = dict(
        dt=DT_DEFAULT,
        n_steps=N_STEPS_EXPERIMENT,
        T_SLA=T_SLA_DEFAULT,
        q_chip=Q_CHIP_DEFAULT,
        pid_Kp=PID_KP,
        pid_Ki=PID_KI,
        pid_Kd=PID_KD,
        gate_N=GATE_N_TRIGGER,
        gate_T_window=GATE_T_WINDOW,
        gate_T_refractory=GATE_T_REFRACTORY,
    )

    # E1: morphology sweep under PID
    for morph in ["Fins_20", "Random_0.4", "Xylem"]:
        for seed in SEEDS:
            configs.append(ExperimentConfig(
                morphology=morph, controller="PID", seed=seed, **base,
            ))

    # E2: controller sweep under Xylem (PID already in E1, add Gate + AlwaysOn)
    for ctrl in ["PID+Gate", "AlwaysOn"]:
        for seed in SEEDS:
            configs.append(ExperimentConfig(
                morphology="Xylem", controller=ctrl, seed=seed, **base,
            ))

    return configs


def run_experiment_matrix() -> pd.DataFrame:
    """Run full matrix and return DataFrame of all results."""
    configs = build_experiment_matrix()
    rows: list[dict] = []

    total = len(configs)
    for i, cfg in enumerate(configs, 1):
        print(f"[{i:2d}/{total}] {cfg.morphology:12s} | {cfg.controller:10s} | seed={cfg.seed}")
        row = run_single(cfg)
        rows.append(row)
        print(f"         kWh_ctrl={row['kWh_ctrl']:.2f}  chatter={row['chatter_count']}  "
              f"sla_viol={row['sla_violations']}  T_max_exc={row['sla_max_exceedance']:.4f}")

    return pd.DataFrame(rows)


# ---------------------------------------------------------------
# Main: run + save artifacts
# ---------------------------------------------------------------


def main() -> None:
    print("=" * 70)
    print("Bio-Thermal Orchestration — Experiment Runner")
    print("=" * 70)

    os.makedirs(CLAIM_AUDIT_DIR, exist_ok=True)

    # Run experiments
    df = run_experiment_matrix()

    # Save orchestration_metrics.csv
    metrics_path = CLAIM_AUDIT_DIR / "orchestration_metrics.csv"
    df.to_csv(metrics_path, index=False)
    print(f"\nSaved: {metrics_path}")

    # Save sla_check.csv (per-run SLA pass/fail)
    sla_df = df[["morphology", "controller", "seed",
                  "sla_violations", "sla_max_exceedance"]].copy()
    sla_df["sla_pass"] = sla_df["sla_violations"] == 0
    sla_path = CLAIM_AUDIT_DIR / "sla_check.csv"
    sla_df.to_csv(sla_path, index=False)
    print(f"Saved: {sla_path}")

    # Save experiment_config.json (locked parameters)
    config_snapshot = {
        "seeds": SEEDS,
        "pid": {"Kp": PID_KP, "Ki": PID_KI, "Kd": PID_KD},
        "gate": {
            "N_trigger": GATE_N_TRIGGER,
            "T_window": GATE_T_WINDOW,
            "T_refractory": GATE_T_REFRACTORY,
        },
        "simulation": {
            "dt": DT_DEFAULT,
            "n_steps": N_STEPS_EXPERIMENT,
            "q_chip": Q_CHIP_DEFAULT,
            "T_SLA": T_SLA_DEFAULT,
        },
        "morphologies": ["Fins_20", "Random_0.4", "Xylem"],
        "controllers": ["PID", "PID+Gate", "AlwaysOn"],
        "total_runs": len(df),
        "metric_taxonomy": {
            "must": ["kWh_ctrl", "sla_violations", "sla_max_exceedance"],
            "nice": ["chatter_count"],
            "exploratory": ["bio_proxy_trend"],
        },
        "gate_output_contract": "binary 0/1; chatter = count of 0->1 transitions at threshold 0.5",
        "statistical_tests": {
            "rule": "Shapiro-Wilk on paired differences: if p >= 0.05 use ttest_rel, else wilcoxon. Count metrics always wilcoxon. alpha=0.05, one-sided.",
            "pairing": "same seed, same morphology, different controller",
        },
    }
    config_path = CLAIM_AUDIT_DIR / "experiment_config.json"
    config_path.write_text(json.dumps(config_snapshot, indent=2), encoding="utf-8")
    print(f"Saved: {config_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("Summary by controller (Xylem morphology only):")
    xylem = df[df["morphology"] == "Xylem"]
    summary = xylem.groupby("controller").agg({
        "kWh_ctrl": ["mean", "std"],
        "chatter_count": ["mean", "std"],
        "sla_violations": ["mean", "sum"],
        "sla_max_exceedance": "max",
    })
    print(summary.to_string())
    print("=" * 70)


if __name__ == "__main__":
    main()
