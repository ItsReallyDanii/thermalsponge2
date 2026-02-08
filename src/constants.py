"""
Shared physics constants for the Thermal Sponge project.
"""

VOID_THRESHOLD = 0.60
K_SOLID = 1.0
K_VOID = 0.05

# --- Bio-Thermal Orchestration (BITO) constants ---
# Transient solver
T_SLA_DEFAULT = 0.85         # max allowable T_max_chip (normalized)
DT_DEFAULT = 0.1             # explicit Euler timestep (CFL-safe: dt <= 0.125 for k_max=K_VOID_ACTIVE=2.0, dx=1)
N_STEPS_DEFAULT = 5000       # simulation length (total_time = dt * n_steps = 1000)
K_VOID_PASSIVE = 0.005       # void conductivity when cooling gated off (stagnant)
K_VOID_ACTIVE = 2.0          # void conductivity when cooling gated on (forced convection >> K_SOLID)

# Flytrap gate defaults
GATE_N_TRIGGER = 3           # trigger events required before opening
GATE_T_WINDOW = 50           # event counting window (timesteps)
GATE_T_REFRACTORY = 20       # refractory period after close (timesteps)
