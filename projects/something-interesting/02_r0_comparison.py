"""
Model 2: R0 comparison (Compartmental)
=======================================
Same single patch, but vary R0 (4, 8, 16) to show how
transmissibility shapes endemic equilibrium dynamics.
Uses the compartmental (deterministic SEIR) model for speed.
"""

import matplotlib
matplotlib.use("Agg")
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import laser.measles as lm
from laser.measles.scenarios import single_patch_scenario
from laser.measles.compartmental import (
    CompartmentalModel,
    CompartmentalParams,
    InitializeEquilibriumStatesProcess,
    ImportationPressureProcess,
    InfectionProcess,
    InfectionParams,
    VitalDynamicsProcess,
    StateTracker,
    StateTrackerParams,
)

try:
    from laser.measles.compartmental import InitializeEquilibriumStatesParams
except ImportError:
    from laser.measles.compartmental.components import InitializeEquilibriumStatesParams

FIGDIR = Path(__file__).parent / "figures"
FIGDIR.mkdir(exist_ok=True)

R0_DEFAULT = 8.0
BETA_DEFAULT = 0.5714285714285714


def main():
    scenario = single_patch_scenario(population=100_000, mcv1_coverage=0.0)
    params = CompartmentalParams(num_ticks=730, seed=42, start_time="2000-01")

    results = {}
    for target_r0 in [4.0, 8.0, 16.0]:
        model = CompartmentalModel(scenario, params)

        model.add_component(
            lm.create_component(
                InitializeEquilibriumStatesProcess,
                params=InitializeEquilibriumStatesParams(R0=target_r0),
            )
        )
        model.add_component(ImportationPressureProcess)

        scaled_beta = target_r0 * (BETA_DEFAULT / R0_DEFAULT)
        model.add_component(
            lm.create_component(
                InfectionProcess,
                params=InfectionParams(beta=scaled_beta),
            )
        )
        model.add_component(VitalDynamicsProcess)
        model.add_component(
            lm.create_component(
                StateTracker, params=StateTrackerParams(aggregation_level=0)
            )
        )
        model.run()

        tracker = model.get_instance("StateTracker")[0]
        I = tracker.I
        if I.ndim == 2:
            I = I[:, 0]
        results[target_r0] = I

    days = np.arange(params.num_ticks)
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = {4.0: "steelblue", 8.0: "darkorange", 16.0: "firebrick"}
    for r0, I in results.items():
        ax.plot(days, I, label=f"R0 = {r0:.0f}", color=colors[r0], lw=2)
        peak = int(I.max())
        peak_day = int(I.argmax())
        print(f"R0={r0:.0f}: peak={peak:,} on day {peak_day}")

    ax.set_xlabel("Day")
    ax.set_ylabel("Infectious individuals")
    ax.set_title("Compartmental model: endemic dynamics at different R0 values")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGDIR / "02_r0_comparison.png", dpi=150)
    print(f"Saved {FIGDIR / '02_r0_comparison.png'}")


if __name__ == "__main__":
    main()
