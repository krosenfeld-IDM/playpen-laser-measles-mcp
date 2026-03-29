"""
Model 1: Single-patch measles outbreak (ABM)
=============================================
Simplest possible model: 100k fully susceptible population,
no vaccination, 365 days. A pure epidemic burn-through.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

from laser.measles.abm import (
    ABMModel,
    ABMParams,
    VitalDynamicsProcess,
    InfectionSeedingProcess,
    InfectionProcess,
    StateTracker,
)
from laser.measles.scenarios import single_patch_scenario

FIGDIR = Path(__file__).parent / "figures"
FIGDIR.mkdir(exist_ok=True)


def main():
    scenario = single_patch_scenario(population=100_000, mcv1_coverage=0.0)
    params = ABMParams(num_ticks=365, seed=42, start_time="2000-01")

    model = ABMModel(scenario=scenario, params=params)
    model.add_component(VitalDynamicsProcess)
    model.add_component(InfectionSeedingProcess)
    model.add_component(InfectionProcess)
    model.add_component(StateTracker)
    model.run()

    tracker = model.get_instance("StateTracker")[0]
    I_ts = tracker.I

    peak_I = int(I_ts.max())
    peak_day = int(I_ts.argmax())
    print(f"Peak infectious: {peak_I:,} on day {peak_day}")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(I_ts, color="crimson", lw=2)
    ax.set_xlabel("Day")
    ax.set_ylabel("Infectious (I)")
    ax.set_title("Single-patch ABM: epidemic curve (100k, no vaccination)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGDIR / "01_single_patch_outbreak.png", dpi=150)
    print(f"Saved {FIGDIR / '01_single_patch_outbreak.png'}")


if __name__ == "__main__":
    main()
