# Source of Truth: BITO Studio Knowledge Base
**Commit Anchor:** 8e8a35e
**Generated:** 2026-02-08 07:12:13

## Verified Outcomes
- **C4 (Reduced actuator chatter via refractory gating):** status=VERIFIED_SIM_ONLY, reduction~49.8%, p=0.003906
- **C3 (Control effort comparable under gated vs PID-only cooling):** status=NOT_SIGNIFICANT, p=0.8575
- **C5 (Thermal SLA non-inferiority under gated control):** status=VERIFIED_SIM_ONLY, non_inferior=True

## Safety Boundaries
- **Hard Override (T_hard):** NOT_FOUND in src/*.py
- **BITO Gate Anchor:** NOT_FOUND in src/*.py (see FlyTrapGate and PID+Gate)
- **Gate Contract:** - AlwaysOn: u = 1 always. - PID: u = 1 if PID_output > 0.5 else 0 (bang-bang with PID-informed threshold). - PID+Gate: PID output > 0.5 triggers flytrap gate; gate output is 0 or 1. This ensures the gate output contract is binary and consistent everywhere.
- **T_SLA_DEFAULT:** 0.85

## Provenance
- claim_audit/claim_map_v4.json
- src/repro_claims_v4.py
- src/run_thermal_orchestration.py
