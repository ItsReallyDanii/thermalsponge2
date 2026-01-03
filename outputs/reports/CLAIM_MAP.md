# Claim Map (auto-generated)

Generated: 2026-01-03T19:47:24.590312Z

## C1 — "3× stiffness" (proxy)
- Supported as **stiffness_potential proxy** (E ∝ ρ²), not literal "hydraulic stiffness".
- Best candidate stiffness_potential: 0.907866
- Real (bio) mean stiffness_potential: 0.329185
- Ratio (best / mean): 2.758×
- Evidence:
  - flow_metrics.csv rows where Type=='real' (indices: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19])
  - flow_stiffness_candidates.csv top row after sort (index 0)

Plot: results/claim_map/flow_vs_stiffness_claimmap.png

## C2 — Pareto cooling efficiency
- Using mapping **Flux = Q_total** and **Density = rho_solid**, Pareto front of (maximize flux, minimize density) contains baselines only.
- Needs either (a) correct thermal metric mapping, or (b) missing CSV(s) for optimized designs / pressure-drop tradeoff.

Plot: results/claim_map/thermal_flux_density_claimmap.png
