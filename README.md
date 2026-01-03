# Inverse Design of Functionally Graded Porous Media
### *A Physics-Informed Generative Approach to Biological & Thermal Transport*

![Status](https://img.shields.io/badge/Status-Research_Artifact-blue)
![Domain](https://img.shields.io/badge/Domain-SciML-green)
![Framework](https://img.shields.io/badge/Framework-PyTorch-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

**Key Finding:** Validated a generative design engine that creates microstructures with **up to ~2.9× stiffness_potential (proxy)** compared to biological xylem and **Pareto-optimal cooling efficiency vs Straight Fins (Fins_*) baselines** (under the current flux/density mapping).

---

## ✅ Evidence (Claim Audit)
- Evidence bundle lives in: `claim_audit/claim_map.json`
- C1 (proxy repro): `flow_metrics.csv` rows 0–19 where `Type=='real'`, `Porosity` → `density=1-Porosity` → `stiffness_potential=density^2`
- C1 (best synthetic): `flow_stiffness_candidates.csv` max `stiffness_potential` at row 0 → ratios ~2.76× (vs mean real) / ~2.91× (vs median real)
- C2 (Pareto): defined baseline set is **Fins_*** only (from `baseline_metrics.csv`), mapping uses `thermal_metrics.Q_total` as flux and `thermal_metrics.rho_solid` as density
- If you include Grid_/Random_ baselines, synthetics are dominated under the current mapping (so the “Pareto vs baselines” claim must name the baseline set)

---

## 📄 Abstract

Transport microstructures—whether in biological xylem or electronic cooling plates—are often limited by a trade-off between **efficiency** (flow rate/heat flux) and **material cost** (density/pressure drop). Traditional topology optimization is computationally expensive, while standard biomimicry often copies evolutionary constraints (like growth and self-repair) that are irrelevant to engineering.

This project introduces a **"Bio-Audited" Generative Design Framework**. By training a surrogate-assisted autoencoder on biological data and fine-tuning it via differentiable physics solvers, we created a **"Material Compiler"** capable of inverse-designing microstructures for specific multi-physics targets.

**Data Source & Scale:**
The model was trained on macroscopic cross-sections of *Pinus taeda* (UruDendro dataset) to learn the **mesoscale density gradients** of biological wood (e.g., the transition from porous earlywood to dense latewood).
* **Why this matters:** Unlike microscopic cellular models which are often too small to manufacture, this model captures **printable structural heterogeneity**—allowing us to generate Functionally Graded Materials (FGMs) that can be produced via standard SLA/FDM 3D printing.

---

## 📊 Key Results

### 1. The Biological Efficiency Gap
We mapped the trade-off between **Flow Rate** (Simulated via Darcy solver) and **Stiffness Potential** (Heuristic $E \propto \rho^2$).
* **Finding:** The AI identified a Pareto front of designs that are significantly stiffer than biological xylem for the equivalent hydraulic conductivity.
* **Implication:** Much of the void space in real xylem is hydraulically redundant in steady-state conditions, optimized instead for cavitation resistance and repair—constraints we can remove for synthetic engineering.

![Trade-off Plot](results/flow_stiffness_tradeoff.png)
*(Figure 1: AI-optimized microstructures [circled] vs. biological baselines.)*

### 2. Thermal Generalization (The "Cooling Coral")
We retrained the physics engine to solve the **Steady-State Heat Diffusion Equation** ($\nabla \cdot (k \nabla T) = 0$) to design heat sinks for high-performance electronics.
* **Benchmark (baseline set for the Pareto claim):** Straight Fins (**Fins_***).
* **Additional comparators (not used to define the Pareto claim):** Grids and Random Noise (Foam).
* **The Win:** Under the current flux/density mapping, AI designs are Pareto-optimal vs the Straight-Fin baseline set.

### 3. Manufacturability & Control
Unlike generative models that produce "pixel dust," this framework enforces structural connectivity.
* **Functionally Graded Materials (FGM):** We successfully generated continuous beams transitioning from **Dense ($E_{high}$)** to **Porous ($E_{low}$)**, validated for SLA 3D printing.
* **Design Manifold:** We demonstrated control by sweeping the latent space to generate a smooth transition of morphologies.

![Gradient Beam](results/gradient_beam/gradient_beam_render.png)
*(Figure 2: 3D-printable functionally graded beam generated via latent interpolation.)*

---

## 🧠 System Architecture

The framework consists of three coupled modules forming a closed-loop design engine:

```mermaid
graph TD
    A[Geometry Generator] -->|Latent Code z| B(Decoder)
    B -->|Microstructure| C{Physics Surrogate}
    C -->|Predict Flow/Heat| D[Optimizer]
    D -->|Gradient Update| A
    B -->|Validation| E[FEM/FDM Solver]
The Eye (Autoencoder): A Convolutional Autoencoder learns the manifold of valid porous structures from biological datasets.
```
The Brain (Surrogate): A Differentiable CNN predicts physics properties (R
2

0.95) instantly, replacing slow simulations during the design loop.

The Hand (Optimizer): Performs gradient descent in the latent space to maximize performance targets (e.g., "Maximize Heat Flux while keeping Density < 0.3").

🚀 Installation & Usage
Prerequisites
Bash

pip install torch numpy matplotlib scipy pandas

Train the Models
To train the Autoencoder on the dataset and the Physics Surrogate:

Bash

python src/train_model.py
python src/train_thermal_surrogate.py
2. Run Inverse Design
To generate a structure for a specific target (e.g., Flux=0.12, Density=0.4):

Bash

python src/optimize_latent_thermal.py --target_flux 0.12 --target_rho 0.4
3. Benchmark
To compare the AI designs against engineering baselines (Fins, Grids):

Bash

python src/benchmark_multiphysics.py
📂 Repository Structure
├── src/
│ ├── model.py # Autoencoder Architecture
│ ├── train_thermal_surrogate.py # Physics Surrogate Training
│ ├── optimize_latent_thermal.py # Inverse Design Loop
│ ├── heat_simulation.py # FDM Heat Solver
│ ├── flow_simulation.py # Darcy Flow Solver
│ ├── analyze_connectivity.py # Manufacturability Audit
│ └── benchmark_baselines.py # Standard Geometry Generator
├── results/
│ ├── thermal_design/ # Generated Heat Sinks
│ ├── baselines/ # Comparison Plots
│ └── gradient_beam/ # 3D STL Files
└── data/ # Training Datasets
🔮 Future Directions
This work establishes a "Computational Testbed" for inverse material design. Immediate expansions include:

Acoustics: Retraining the surrogate on the Helmholtz equation to design noise-damping tiles.

Closed-Loop Robotics: Connecting the generator to a 3D printer and flow-test rig.

High-Fidelity Mechanics: Integrating differentiable FEM to replace the stiffness heuristic.

📚 Citation
Daniel Sleiman. (2025). Inverse Design of Functionally Graded Porous Media via Physics-Informed Generative Models. GitHub Repository.
