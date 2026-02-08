# Bio-Inspired Thermal Orchestration — Feasibility Audit

**Date:** 2026-02-08
**Auditor:** Principal Research Engineer (automated)
**Repo:** Thermal-Sponge (Generative Porous Microstructure Design + Physics Validation)
**Scope:** Evaluate feasibility of extending into bio-inspired thermal orchestration claims

---

## A) Feasibility Assessment

### Verdict: MEDIUM-HIGH

The repo has ~70% of the scaffolding needed. The steady-state thermal solver, autoencoder-driven morphology loop, surrogate-based inverse design, and claim audit infrastructure are all in place. The gap is entirely in the temporal dimension (transient solver, gating logic, control-effort accounting).

### Top 5 Risks

| # | Risk | Severity |
|---|---|---|
| R1 | Transient solver stability (CFL constraint on 256x256 grid if explicit scheme) | High |
| R2 | Flytrap gating is novel + untested — audit-defensible framing critical | High |
| R3 | Control-effort metric ambiguity (no physical actuator model exists) | Medium |
| R4 | Baseline fairness (C2 already fails with broader baselines; PID tuning matters) | Medium |
| R5 | Scope creep into 3D / real hardware from bio-inspired framing | Medium |

### Top 5 Mitigations

| # | Mitigation | Addresses |
|---|---|---|
| M1 | Implicit (backward Euler) time-stepping — unconditionally stable | R1 |
| M2 | Formal state machine with named params; claim "bio-inspired policy" only | R2 |
| M3 | Define kWh_ctrl = integral |u(t)| dt; chatter = 0->1 transition count | R3 |
| M4 | PID with Ziegler-Nichols auto-tuning + always-on degenerate baseline | R4 |
| M5 | Explicit "Simulation-Only Scope" in CLAIMS.md; all new claims VERIFIED_SIM_ONLY | R5 |

### 90-Day Viability

| Phase | Weeks | Deliverable |
|---|---|---|
| P1: Transient solver + PID baseline | 1-3 | heat_simulation_transient.py, pid_controller.py |
| P2: Xylem morphology optimizer | 3-5 | xylem_flow_optimizer.py |
| P3: Flytrap gating + control metrics | 5-7 | flytrap_gate.py, control_metrics.py |
| P4: Claim audit + repro | 7-9 | claim_map_v4.json, repro_claims_v4.py |
| P5: README / paper-safe wording | 9-10 | Updated docs |
| Buffer | 10-13 | Iteration |

### Proven vs Exploratory Boundaries

| Layer | Status |
|---|---|
| 2D transient heat conduction (FDM) | Proven |
| PID thermal control | Proven |
| Autoencoder -> morphology -> physics loop | Proven in this repo |
| Flytrap-style temporal gating | Exploratory |
| Xylem-informed flow-path optimization | Exploratory |
| Control-effort reduction claim | Exploratory |

---

## B) Architecture Delta

### New Files

| File | Purpose |
|---|---|
| `src/heat_simulation_transient.py` | Implicit Euler time-stepping thermal solver |
| `src/pid_controller.py` | Discrete PID with ZN auto-tune |
| `src/flytrap_gate.py` | State-machine gating policy (IDLE/PRIMED/OPEN/REFRACTORY) |
| `src/control_metrics.py` | kWh_ctrl, chatter, SLA violation metrics |
| `src/xylem_flow_optimizer.py` | Extends cambium loop with flow-path reward |
| `src/run_thermal_orchestration.py` | Experiment runner |
| `src/repro_claims_v4.py` | Extended repro script for C1-C5 |

### Touched Files

| File | Change | Backward Compat |
|---|---|---|
| `src/constants.py` | Add T_SLA_DEFAULT, DT_DEFAULT, gate params | Additive only |
| `CLAIMS.md` | Add C3, C4, C5 entries | Additive |
| `README.md` | Add experimental section | Additive |
| `requirements.txt` | Add scipy, pandas | No removals |

### Interface Contracts

```
# heat_simulation_transient.py
solve_transient_heat(k_grid, gate_signal, dt, n_steps, ...) -> TransientResult

# pid_controller.py
PIDController(Kp, Ki, Kd, dt, u_min, u_max)
  .step(error) -> float
  .auto_tune_zn(plant_response, dt) -> PIDController

# flytrap_gate.py
FlyTrapGate(N_trigger, T_window, T_refractory)
  .update(trigger, t_now) -> bool
  .state -> str
  .transition_count -> int

# control_metrics.py
compute_control_metrics(u_history, T_max_history, T_SLA, dt) -> ControlMetrics
```

---

## C) Metrics & Validation Plan

### Must Metrics
- kWh_ctrl: total gate-open time (integral |u(t)| dt)
- chatter_count: 0->1 transitions in u(t)
- SLA_violation_count: timesteps where T_max > T_SLA
- SLA_max_exceedance: max(T_max - T_SLA, 0)

### Nice Metrics
- settling_time, eta_thermal (Q_out / kWh_ctrl), morphology conductivity

### Experiment Matrix
- E1 (morphology effect): 3 morphologies x PID x 5 seeds = 15 runs
- E2 (gating effect): xylem x 3 controllers x 5 seeds = 15 runs
- E3 (full cross): 3 x 3 x 5 = 45 runs

### Pass/Fail
- C3: kWh_ctrl(PID+Gate) < kWh_ctrl(PID-only), p < 0.05, paired Welch's t
- C4: chatter(PID+Gate) < chatter(PID-only), p < 0.05, Wilcoxon
- C5: SLA_violation_count(PID+Gate) == 0 across all runs

---

## D) Claim Audit Integration

### New Claims

| ID | Label | Status |
|---|---|---|
| C3 | Reduced cooling control effort via flytrap gating | VERIFIED_SIM_ONLY |
| C4 | Reduced actuator chatter via refractory gating | VERIFIED_SIM_ONLY |
| C5 | Thermal SLA preserved under gated control | VERIFIED_SIM_ONLY |

### Red-Line Phrases

- NEVER: "replicates biological xylem" -> SAY: "xylem-inspired morphology"
- NEVER: "mimics venus flytrap" -> SAY: "flytrap-inspired gating policy"
- NEVER: "reduces energy consumption" -> SAY: "reduces simulated control effort"
- NEVER: "guarantees thermal SLA" -> SAY: "preserves SLA bounds in simulation"
- NEVER: "outperforms PID" -> SAY: "PID + gating reduces effort vs PID-only"
- NEVER: unqualified "optimal" -> SAY: "Pareto-efficient under [metrics] with [baselines]"

### Safe Claim Templates

**1-line:** Bio-inspired temporal gating reduces simulated cooling control effort while preserving thermal SLA bounds in porous microstructure designs.

**README:**
> C3 -- Reduced control effort via flytrap gating (sim-only)
> Status: VERIFIED_SIM_ONLY
> Result: PID + FlyTrapGate reduces kWh_ctrl by [X]% vs PID-only (p < 0.05, paired Welch's t, n=[N]).
> Caveat: kWh_ctrl = integral |u(t)| dt is a simulation proxy. No physical energy measurement.

---

## E) Minimal Change Set

### Do Now (items 1-12)
1. Create src/heat_simulation_transient.py
2. Create src/pid_controller.py
3. Create src/flytrap_gate.py
4. Create src/control_metrics.py
5. Add constants to src/constants.py
6. Add scipy to requirements.txt
7. Create src/run_thermal_orchestration.py
8. Run E1 + E2 experiments
9. Create src/repro_claims_v4.py
10. Update CLAIMS.md (add C3, C4, C5)
11. Update README.md (add experimental section)
12. Fix CLAIMS.md version drift (claim_map.json -> v3/v4)

### Defer
13. src/xylem_flow_optimizer.py (Phase 2)
14. E3 full cross experiment
15. Pareto analysis for eta_thermal vs kWh_ctrl
16. Remove stale claim_audit/repro_claims.py duplicate

### Token Strategy (future sessions)
- Always read: constants.py, heat_simulation.py, repro_claims.py, CLAIMS.md, claim_map_v3.json (~800 lines)
- Summarize once: model.py, train_thermal_surrogate.py, benchmark_baselines.py, synthetic_cambium.py
- Safe to omit: analyze_*.py, morpho*.py, train_*.py (5 variants), beam_*.py, 3D export/preview, titanium scripts

---

**Ready for Patch Plan v1**
