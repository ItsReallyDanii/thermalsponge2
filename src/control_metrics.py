"""
control_metrics.py — Compute control-effort and SLA compliance metrics.

Metric taxonomy (locked):
    Must:        kWh_ctrl, sla_violations, sla_max_exceedance
    Nice:        chatter_count
    Exploratory: (bio_proxy_trend — computed externally, not in this module)

Definitions:
    kWh_ctrl           = integral(|u(t)|) * dt  — total gate-open energy proxy.
    sla_violations     = count of timesteps where T_max_chip > T_SLA.
    sla_max_exceedance = max(T_max_chip - T_SLA, 0) over all timesteps.
    settling_time      = first timestep after which T_max_chip <= T_SLA permanently.
                         -1 if system never settles.
    chatter_count      = number of 0->1 transitions in the binary gate signal u(t).
                         Explicit definition: at timestep t, chatter increments if
                         u(t) >= 0.5 and u(t-1) < 0.5 (crossing the 0.5 threshold
                         from closed to open). This matches the binary gate contract.

No external dependencies beyond numpy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ControlMetrics:
    """Container for all orchestration metrics."""

    # Must
    kWh_ctrl: float
    sla_violations: int
    sla_max_exceedance: float

    # Nice
    chatter_count: int

    # Derived
    settling_time: int  # -1 if never settles


def compute_control_metrics(
    u_history: np.ndarray,
    T_max_history: np.ndarray,
    T_SLA: float,
    dt: float,
) -> ControlMetrics:
    """Compute control-effort and SLA metrics from simulation histories.

    Parameters
    ----------
    u_history : (n_steps,) control/gate signal in [0, 1].
    T_max_history : (n_steps,) maximum chip temperature per timestep.
    T_SLA : thermal SLA threshold (max allowable T_max_chip).
    dt : timestep size.

    Returns
    -------
    ControlMetrics with all must/nice fields populated.
    """
    n = len(u_history)
    assert len(T_max_history) == n, "u_history and T_max_history must have same length"

    # --- Must: kWh_ctrl ---
    kWh_ctrl = float(np.sum(np.abs(u_history)) * dt)

    # --- Must: SLA compliance ---
    violations_mask = T_max_history > T_SLA
    sla_violations = int(np.sum(violations_mask))

    exceedances = T_max_history - T_SLA
    sla_max_exceedance = float(max(0.0, np.max(exceedances)))

    # --- Derived: settling_time ---
    # First t such that T_max_history[t:] are all <= T_SLA
    settling_time = -1
    if sla_violations == 0:
        settling_time = 0
    else:
        # Scan from end to find last violation, settling = last_violation + 1
        violation_indices = np.where(violations_mask)[0]
        if len(violation_indices) > 0:
            last_violation = int(violation_indices[-1])
            if last_violation < n - 1:
                settling_time = last_violation + 1
            # else: never settles (violation at final step)

    # --- Nice: chatter_count ---
    # Binary gate signal: u >= 0.5 is "open" (1), u < 0.5 is "closed" (0).
    # Chatter = number of 0→1 transitions.
    u_binary = (u_history >= 0.5).astype(np.int32)
    if n > 1:
        transitions = np.diff(u_binary)
        chatter_count = int(np.sum(transitions == 1))  # 0→1 edges only
    else:
        chatter_count = 0

    return ControlMetrics(
        kWh_ctrl=kWh_ctrl,
        sla_violations=sla_violations,
        sla_max_exceedance=sla_max_exceedance,
        chatter_count=chatter_count,
        settling_time=settling_time,
    )
