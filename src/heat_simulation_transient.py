"""
heat_simulation_transient.py — 2D transient heat solver for bio-thermal orchestration.

Extends the steady-state solver concept from heat_simulation.py with explicit Euler
time-stepping, a volumetric heat source in the chip region, and a gate_signal callback
that modulates void-phase conductivity.

Physics:
    dT/dt = div(k(x,y,t) * grad(T)) + S(x,y)

    S(x,y) = q_chip  for x < hot_strip_width  (chip heat generation)
    S(x,y) = 0       otherwise

    k is rebuilt each timestep from the microstructure image and the gate signal:
      - solid pixels: K_SOLID (always)
      - void pixels:  K_VOID_PASSIVE + u(t) * (K_VOID_ACTIVE - K_VOID_PASSIVE)
        u=1 -> forced convection (K_VOID_ACTIVE=2.0), u=0 -> stagnant (K_VOID_PASSIVE=0.005)

BCs:
    Left:   Neumann dT/dx = 0  (insulated; chip heat enters via source term)
    Right:  T = t_cold         (Dirichlet — cold sink, always connected)
    Top/Bottom: Neumann dT/dn = 0 (insulated)

Initial condition: T = 0 everywhere (ambient).

Why source term + Neumann left (not Dirichlet T_HOT):
    The steady-state solver uses Dirichlet T_HOT on the left, which fixes the chip
    temperature and makes the control problem trivial (T_max = T_HOT always).
    For a meaningful control problem, chip temperature must be FREE to respond to
    the balance between heat generation and cooling. The source term provides this.

Stability: explicit Euler with CFL dt <= dx^2 / (4 * k_max) = 1/(4*2.0) = 0.125
           Default dt = 0.1 is CFL-safe for k_max=K_VOID_ACTIVE=2.0.

This file does NOT modify heat_simulation.py. The existing steady-state pipeline
is fully preserved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from src.constants import (
    VOID_THRESHOLD,
    K_SOLID,
    K_VOID_ACTIVE,
    K_VOID_PASSIVE,
    DT_DEFAULT,
    N_STEPS_DEFAULT,
)

# Default chip heat generation rate.
# Chosen so that: with full cooling (u=1) T_max_chip stabilizes ~0.4-0.6,
# and with cooling off (u=0) T_max_chip rises above T_SLA=0.85 within ~200-500 steps.
Q_CHIP_DEFAULT = 0.005


@dataclass
class TransientResult:
    """Container for transient simulation outputs."""

    T_final: np.ndarray        # (H, W) final temperature field
    T_max_history: np.ndarray  # (n_steps,) max chip temperature per step
    Q_out_history: np.ndarray  # (n_steps,) heat flux at cold boundary per step
    u_history: np.ndarray      # (n_steps,) recorded gate signal


def build_k_grid(img_arr: np.ndarray, u: float) -> np.ndarray:
    """Map microstructure image + gate signal to conductivity field.

    Parameters
    ----------
    img_arr : (H, W) float array in [0, 1].
              Bright (> VOID_THRESHOLD) = void, dark = solid.
    u : float in [0, 1]. Gate signal.
        u=1 -> forced convection (void gets K_VOID_ACTIVE=2.0).
        u=0 -> cooling off (void gets K_VOID_PASSIVE=0.005).

    Returns
    -------
    k_grid : (H, W) float32 conductivity field.
    """
    void_mask = img_arr > VOID_THRESHOLD
    k_void_eff = K_VOID_PASSIVE + u * (K_VOID_ACTIVE - K_VOID_PASSIVE)
    k_grid = np.where(void_mask, k_void_eff, K_SOLID).astype(np.float32)
    return k_grid


def solve_transient_heat(
    img_arr: np.ndarray,
    gate_signal: Callable[[int, float], float],
    dt: float = DT_DEFAULT,
    n_steps: int = N_STEPS_DEFAULT,
    q_chip: float = Q_CHIP_DEFAULT,
    t_cold: float = 0.0,
    hot_strip_width: int = 5,
) -> TransientResult:
    """Explicit Euler 2D transient heat solver with source term and time-varying gate.

    Parameters
    ----------
    img_arr : (H, W) normalized image in [0, 1].
    gate_signal : callable(timestep: int, T_max_chip: float) -> float in [0, 1].
                  Called each step; return value modulates void conductivity.
    dt : timestep size. Must satisfy dt <= 0.125 for CFL stability (k_max=2.0, dx=1).
    n_steps : number of time steps to simulate.
    q_chip : volumetric heat generation rate in chip region (source term).
    t_cold : right (sink) boundary temperature.
    hot_strip_width : columns from left edge defining "chip region" for source + T_max.

    Returns
    -------
    TransientResult with T_final, T_max_history, Q_out_history, u_history.
    """
    cfl_limit = 1.0 / (4.0 * K_VOID_ACTIVE)  # 0.125 for K_VOID_ACTIVE=2.0
    if dt > cfl_limit:
        raise ValueError(f"dt={dt} exceeds CFL limit {cfl_limit} for k_max={K_VOID_ACTIVE}, dx=1")

    H, W = img_arr.shape

    # Precompute solid mask (time-invariant)
    solid_mask = img_arr <= VOID_THRESHOLD

    # Build source field (time-invariant)
    source = np.zeros((H, W), dtype=np.float32)
    chip_cols = min(hot_strip_width, W)
    source[:, :chip_cols] = q_chip

    # Initialize T = 0 (ambient)
    T = np.zeros((H, W), dtype=np.float32)

    T_max_history = np.zeros(n_steps, dtype=np.float32)
    Q_out_history = np.zeros(n_steps, dtype=np.float32)
    u_history = np.zeros(n_steps, dtype=np.float32)

    eps = 1e-8

    for step in range(n_steps):
        # Read current chip temperature
        T_max_chip = float(T[:, :chip_cols].max())

        # Query controller for gate signal
        u = float(gate_signal(step, T_max_chip))
        u = max(0.0, min(1.0, u))  # clamp
        u_history[step] = u

        # Build conductivity field for this timestep
        k_void_eff = K_VOID_PASSIVE + u * (K_VOID_ACTIVE - K_VOID_PASSIVE)
        k_grid = np.where(solid_mask, K_SOLID, k_void_eff).astype(np.float32)

        # --- Neumann BCs on top/bottom/left ---
        T[0, :] = T[1, :]      # top insulated
        T[-1, :] = T[-2, :]    # bottom insulated
        T[:, 0] = T[:, 1]      # left insulated (chip heat via source term)

        # --- Dirichlet BC on right (cold sink) ---
        T[:, -1] = t_cold

        # --- Explicit Euler update on interior ---
        T_up = T[0:-2, 1:-1]
        T_down = T[2:, 1:-1]
        T_left = T[1:-1, 0:-2]
        T_right = T[1:-1, 2:]
        T_center = T[1:-1, 1:-1]

        k_c = k_grid[1:-1, 1:-1]

        # Harmonic mean interface conductivities (matching heat_simulation.py)
        k_n = 2.0 * k_c * k_grid[0:-2, 1:-1] / (k_c + k_grid[0:-2, 1:-1] + eps)
        k_s = 2.0 * k_c * k_grid[2:, 1:-1] / (k_c + k_grid[2:, 1:-1] + eps)
        k_w = 2.0 * k_c * k_grid[1:-1, 0:-2] / (k_c + k_grid[1:-1, 0:-2] + eps)
        k_e = 2.0 * k_c * k_grid[1:-1, 2:] / (k_c + k_grid[1:-1, 2:] + eps)

        # Laplacian term: sum of k_face * (T_neighbor - T_center) for each face
        laplacian = (
            k_n * (T_up - T_center)
            + k_s * (T_down - T_center)
            + k_w * (T_left - T_center)
            + k_e * (T_right - T_center)
        )

        # Update: dT/dt = laplacian + source
        T[1:-1, 1:-1] = T_center + dt * (laplacian + source[1:-1, 1:-1])

        # Re-apply Dirichlet BC (right side, may have been overwritten)
        T[:, -1] = t_cold

        # --- Record metrics ---
        T_max_history[step] = float(T[:, :chip_cols].max())

        # Heat flux at cold boundary: q = -k * dT/dx, flux leaving domain is positive
        dTdx = T[:, -1] - T[:, -2]
        q_boundary = -k_grid[:, -1] * dTdx
        Q_out_history[step] = float(q_boundary.sum())

    return TransientResult(
        T_final=T.copy(),
        T_max_history=T_max_history,
        Q_out_history=Q_out_history,
        u_history=u_history,
    )
