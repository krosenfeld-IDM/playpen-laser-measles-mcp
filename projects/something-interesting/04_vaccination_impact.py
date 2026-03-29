"""
Model 4: Vaccination impact — routine MCV1 over 10 years (Compartmental)
=========================================================================
Compares no-vaccination vs 80% routine MCV1 over a 10-year run.
Shows how routine immunization of newborns slowly reduces susceptibility
and dampens outbreaks. Uses InitializeEquilibriumStates at R0=8 for
realistic starting conditions.
"""

import matplotlib
matplotlib.use("Agg")
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import laser.measles as lm
from laser.measles import create_component
from laser.measles.scenarios import single_patch_scenario
from laser.measles.compartmental import (
    CompartmentalModel,
    CompartmentalParams,
    InitializeEquilibriumStatesProcess,
    InitializeEquilibriumStatesParams,
    ImportationPressureProcess,
    InfectionProcess,
    VitalDynamicsProcess,
    StateTracker,
)

FIGDIR = Path(__file__).parent / "figures"
FIGDIR.mkdir(exist_ok=True)


def run_scenario(label, mcv1, num_ticks, seed=42):
    scenario = single_patch_scenario(population=500_000, mcv1_coverage=mcv1)
    params = CompartmentalParams(num_ticks=num_ticks, seed=seed, start_time="2000-01")
    model = CompartmentalModel(scenario, params)

    model.add_component(
        create_component(
            InitializeEquilibriumStatesProcess,
            params=InitializeEquilibriumStatesParams(R0=8.0),
        )
    )
    model.add_component(ImportationPressureProcess)
    model.add_component(InfectionProcess)
    model.add_component(VitalDynamicsProcess)
    model.add_component(StateTracker)
    model.run()

    tracker = model.get_instance("StateTracker")[0]
    return {"S": tracker.S.copy(), "I": tracker.I.copy()}


def main():
    years = 10
    num_ticks = years * 365

    scenarios = {
        "No vaccination (MCV1=0%)": 0.0,
        "Routine MCV1 = 80%": 0.80,
        "Routine MCV1 = 95%": 0.95,
    }

    results = {}
    for label, mcv1 in scenarios.items():
        print(f"Running: {label}")
        results[label] = run_scenario(label, mcv1, num_ticks)

    days = np.arange(num_ticks)
    colors = ["firebrick", "steelblue", "seagreen"]

    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    # Susceptible fraction
    ax = axes[0]
    for (label, res), c in zip(results.items(), colors):
        ax.plot(days / 365, res["S"] / 500_000, label=label, color=c, lw=2)
    ax.set_ylabel("Susceptible fraction")
    ax.set_title("10-year vaccination impact: routine MCV1 (compartmental, 500k)")
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Infectious
    ax = axes[1]
    for (label, res), c in zip(results.items(), colors):
        ax.plot(days / 365, res["I"], label=label, color=c, lw=2)
    ax.set_ylabel("Infectious (count)")
    ax.set_xlabel("Year")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(FIGDIR / "04_vaccination_impact.png", dpi=150)
    print(f"Saved {FIGDIR / '04_vaccination_impact.png'}")


if __name__ == "__main__":
    main()
