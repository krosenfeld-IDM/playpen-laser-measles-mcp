"""
Model 5: Immunity gaps — two-cluster spatial ABM
==================================================
Two geographic clusters of 10 nodes each. Cluster 1 has high vaccination
(MCV1 85-95%), Cluster 2 has low vaccination (20-50%). We run a 2-year
ABM to show how under-immunized pockets sustain outbreaks that spill
into well-vaccinated communities via gravity mixing.

This is the key public health insight: herd immunity breaks down when
spatial heterogeneity in vaccination creates connected pockets of
susceptibility.
"""

import matplotlib
matplotlib.use("Agg")
import numpy as np
import polars as pl
import matplotlib.pyplot as plt
from pathlib import Path

from laser.measles.abm import (
    ABMModel,
    ABMParams,
    ConstantPopProcess,
    InfectionProcess,
    InfectionSeedingProcess,
    StateTracker,
    StateTrackerParams,
)
from laser.measles import create_component
from laser.measles.scenarios import two_cluster_scenario

FIGDIR = Path(__file__).parent / "figures"
FIGDIR.mkdir(exist_ok=True)


def main():
    # --- Scenario: two clusters with contrasting immunity ---
    # We create two scenarios and manually set the mcv1 column
    scenario = two_cluster_scenario(
        n_nodes_per_cluster=10,
        mcv1_coverage_range=(0.2, 0.95),
        seed=42,
    )

    # Override MCV1: cluster_1 = high (85-95%), cluster_2 = low (20-50%)
    rng = np.random.default_rng(99)
    n = len(scenario)
    mcv1_new = np.zeros(n)
    ids = scenario["id"].to_list()
    cluster_labels = []
    for i, node_id in enumerate(ids):
        if node_id.startswith("cluster_1"):
            mcv1_new[i] = rng.uniform(0.85, 0.95)
            cluster_labels.append("High-vax cluster")
        else:
            mcv1_new[i] = rng.uniform(0.20, 0.50)
            cluster_labels.append("Low-vax cluster")

    scenario = scenario.with_columns(pl.Series("mcv1", mcv1_new))
    print("Scenario summary:")
    print(f"  Cluster 1 (high-vax): avg MCV1 = {mcv1_new[:10].mean():.1%}")
    print(f"  Cluster 2 (low-vax):  avg MCV1 = {mcv1_new[10:].mean():.1%}")
    print(f"  Total population: {scenario['pop'].sum():,}")

    # --- Model ---
    params = ABMParams(num_ticks=365 * 2, seed=123, start_time="2000-01")
    model = ABMModel(scenario=scenario, params=params)

    model.add_component(ConstantPopProcess)
    model.add_component(InfectionSeedingProcess)
    model.add_component(InfectionProcess)
    model.add_component(
        create_component(StateTracker, params=StateTrackerParams(aggregation_level=0))
    )
    model.run()

    # --- Extract results ---
    tracker = model.get_instance("StateTracker")[0]
    I = tracker.I  # shape depends on aggregation_level
    S = tracker.S
    if I.ndim == 1:
        I = I[:, None]
        S = S[:, None]
    T, P = I.shape
    print(f"\nTracker shape: ({T}, {P})")

    pop_c1 = scenario.filter(pl.col("id").str.starts_with("cluster_1"))["pop"].sum()
    pop_c2 = scenario.filter(pl.col("id").str.starts_with("cluster_2"))["pop"].sum()

    # aggregation_level=0 with colon-separated IDs gives cluster-level (2 groups)
    if P == 2:
        # Column 0 = cluster_1 (high-vax), column 1 = cluster_2 (low-vax)
        I_c1, I_c2 = I[:, 0], I[:, 1]
        S_c1, S_c2 = S[:, 0], S[:, 1]
    else:
        # Per-node: aggregate manually
        c1_mask = np.array([lab == "High-vax cluster" for lab in cluster_labels])
        I_c1 = I[:, c1_mask].sum(axis=1)
        I_c2 = I[:, ~c1_mask].sum(axis=1)
        S_c1 = S[:, c1_mask].sum(axis=1)
        S_c2 = S[:, ~c1_mask].sum(axis=1)

    total_cases_c1 = int(I_c1.sum())
    total_cases_c2 = int(I_c2.sum())
    print(f"\nCumulative person-days infectious:")
    print(f"  High-vax cluster: {total_cases_c1:,} (pop {pop_c1:,})")
    print(f"  Low-vax cluster:  {total_cases_c2:,} (pop {pop_c2:,})")
    print(f"  Ratio (low/high): {total_cases_c2 / max(total_cases_c1, 1):.1f}x")

    days = np.arange(T)

    # --- Plot 1: Infectious time series by cluster ---
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    ax = axes[0]
    ax.plot(days / 365, I_c1, color="seagreen", lw=2, label=f"High-vax cluster (avg MCV1={mcv1_new[:10].mean():.0%})")
    ax.plot(days / 365, I_c2, color="firebrick", lw=2, label=f"Low-vax cluster (avg MCV1={mcv1_new[10:].mean():.0%})")
    ax.set_ylabel("Infectious (count)")
    ax.set_title("Immunity gaps: how under-vaccinated pockets drive outbreaks")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    ax.plot(days / 365, S_c1 / pop_c1, color="seagreen", lw=2, label="High-vax cluster")
    ax.plot(days / 365, S_c2 / pop_c2, color="firebrick", lw=2, label="Low-vax cluster")
    ax.set_ylabel("Susceptible fraction")
    ax.set_xlabel("Year")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(FIGDIR / "05_immunity_gaps.png", dpi=150)
    print(f"\nSaved {FIGDIR / '05_immunity_gaps.png'}")

    # --- Plot 2: Peak attack rate comparison ---
    peak_c1 = int(I_c1.max())
    peak_c2 = int(I_c2.max())

    fig2, ax2 = plt.subplots(figsize=(7, 5))
    labels = ["High-vax cluster\n(MCV1~91%)", "Low-vax cluster\n(MCV1~34%)"]
    peaks_pct = [peak_c1 / pop_c1 * 100, peak_c2 / pop_c2 * 100]
    bars = ax2.bar(labels, peaks_pct, color=["seagreen", "firebrick"], edgecolor="k", width=0.5)
    for bar, val in zip(bars, peaks_pct):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                 f"{val:.2f}%", ha="center", fontsize=12)
    ax2.set_ylabel("Peak infectious (% of cluster population)")
    ax2.set_title("Peak attack rate: high-vax vs low-vax clusters")
    ax2.grid(True, alpha=0.3, axis="y")
    fig2.tight_layout()
    fig2.savefig(FIGDIR / "05_attack_rates.png", dpi=150)
    print(f"Saved {FIGDIR / '05_attack_rates.png'}")


if __name__ == "__main__":
    main()
