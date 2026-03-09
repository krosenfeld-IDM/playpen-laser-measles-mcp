"""
Satellite-Hub Measles Transmission Demo
========================================

Demonstrates measles transmission dynamics in a satellite-hub network
using the laser-measles compartmental model. Infection is seeded in a
central hub and propagates to surrounding satellite towns via
gravity-based spatial mixing.
"""

# %% Imports

import numpy as np
import polars as pl
import matplotlib.pyplot as plt
from pathlib import Path

from laser.measles.compartmental import CompartmentalModel, CompartmentalParams
from laser.measles.compartmental.components import (
    InfectionParams,
    InfectionProcess,
    InfectionSeedingParams,
    InfectionSeedingProcess,
    StateTracker,
    StateTrackerParams,
    ConstantPopProcess,
)
from laser.measles.components import create_component
from laser.measles.mixing.gravity import GravityMixing, GravityParams

# %% Create satellite-hub scenario


def create_satellite_hub_scenario() -> pl.DataFrame:
    """Build a 7-patch scenario: 1 hub + 6 satellites at varying distances."""
    satellite_distances_km = [50, 75, 100, 100, 125, 150]
    satellite_populations = [80_000, 60_000, 50_000, 40_000, 30_000, 20_000]
    angles_deg = [i * 60 for i in range(6)]

    ids = ["hub"]
    pops = [500_000]
    lats = [0.0]
    lons = [0.0]

    for i, (dist_km, pop, angle) in enumerate(
        zip(satellite_distances_km, satellite_populations, angles_deg, strict=True)
    ):
        angle_rad = np.radians(angle)
        lat = dist_km / 111.0 * np.cos(angle_rad)
        lon = dist_km / 111.0 * np.sin(angle_rad)
        ids.append(f"sat_{i + 1}")
        pops.append(pop)
        lats.append(float(lat))
        lons.append(float(lon))

    return pl.DataFrame(
        {
            "id": ids,
            "pop": pops,
            "lat": lats,
            "lon": lons,
            "mcv1": [0.0] * len(ids),
        }
    )


# %% Configure and build the model


def configure_model(scenario: pl.DataFrame) -> CompartmentalModel:
    """Configure a compartmental SEIR model with gravity mixing."""
    params = CompartmentalParams(num_ticks=365, seed=42, start_time="2024-01")

    model = CompartmentalModel(scenario, params, name="satellite_hub")

    mixer = GravityMixing(params=GravityParams(a=1.0, b=1.0, c=2.0, k=0.01))

    infection_params = InfectionParams(
        beta=0.5,
        exp_mu=8.0,
        inf_mu=5.0,
        seasonality=0.15,
        mixer=mixer,
    )

    seeding_params = InfectionSeedingParams(
        target_patches=["hub"],
        num_infections=10,
    )

    state_tracker_params = StateTrackerParams(aggregation_level=0)

    model.components = [
        create_component(StateTracker, params=state_tracker_params),
        create_component(InfectionSeedingProcess, params=seeding_params),
        create_component(InfectionProcess, params=infection_params),
        create_component(ConstantPopProcess),
    ]

    return model


# %% Plotting functions


def _get_distances_km(scenario: pl.DataFrame) -> np.ndarray:
    """Compute distance from hub (first row) for each patch in km."""
    lats = scenario["lat"].to_numpy()
    lons = scenario["lon"].to_numpy()
    dlat = lats - lats[0]
    dlon = lons - lons[0]
    return np.sqrt(dlat**2 + dlon**2) * 111.0


def plot_network(scenario: pl.DataFrame, figures_dir: Path) -> None:
    """Plot the spatial network: hub + satellites with connecting lines."""
    ids = scenario["id"].to_list()
    pops = scenario["pop"].to_numpy()
    lats = scenario["lat"].to_numpy()
    lons = scenario["lon"].to_numpy()
    distances = _get_distances_km(scenario)

    fig, ax = plt.subplots(figsize=(8, 8))

    # Lines from hub to each satellite, thickness proportional to 1/distance^2
    for i in range(1, len(ids)):
        coupling = 1.0 / max(distances[i], 1.0) ** 2
        ax.plot(
            [lons[0], lons[i]],
            [lats[0], lats[i]],
            color="gray",
            linewidth=coupling * 5000,
            alpha=0.5,
        )

    # Nodes sized by population
    scale = 80_000
    colors = ["red"] + ["steelblue"] * (len(ids) - 1)
    ax.scatter(lons, lats, s=pops / scale * 100, c=colors, zorder=5, edgecolors="k")

    for i, patch_id in enumerate(ids):
        ax.annotate(
            f"{patch_id}\n({pops[i]:,})",
            (lons[i], lats[i]),
            textcoords="offset points",
            xytext=(10, 10),
            fontsize=8,
        )

    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")
    ax.set_title("Satellite-Hub Network")
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(figures_dir / "network_map.png", dpi=150)
    plt.close(fig)


def plot_epidemic_curves(
    model: CompartmentalModel, scenario: pl.DataFrame, figures_dir: Path
) -> None:
    """Plot infection time series for each patch."""
    tracker = model.get_instance(StateTracker)[0]
    I = tracker.I  # shape (num_ticks, num_groups)
    group_ids = tracker.group_ids

    fig, ax = plt.subplots(figsize=(10, 5))

    for j, gid in enumerate(group_ids):
        lw = 2.5 if gid == "hub" else 1.0
        ax.plot(I[:, j], label=gid, linewidth=lw)

    ax.set_xlabel("Day")
    ax.set_ylabel("Infected (I)")
    ax.set_title("Epidemic Curves by Patch")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(figures_dir / "epidemic_curves.png", dpi=150)
    plt.close(fig)


def plot_spatial_spread(
    model: CompartmentalModel, scenario: pl.DataFrame, figures_dir: Path
) -> None:
    """Plot arrival time vs distance from hub."""
    tracker = model.get_instance(StateTracker)[0]
    I = tracker.I
    group_ids = tracker.group_ids
    distances = _get_distances_km(scenario)

    # Map group_ids back to scenario order to get correct distances
    scenario_ids = scenario["id"].to_list()
    arrival_days = []
    dist_list = []

    for j, gid in enumerate(group_ids):
        if gid == "hub":
            continue
        first_tick = np.argmax(I[:, j] >= 1)
        if I[first_tick, j] >= 1:
            arrival_days.append(first_tick)
            idx = scenario_ids.index(gid)
            dist_list.append(distances[idx])

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(dist_list, arrival_days, s=80, zorder=5, edgecolors="k")

    for d, a in zip(dist_list, arrival_days):
        ax.annotate(f"day {a}", (d, a), textcoords="offset points", xytext=(8, 4), fontsize=8)

    ax.set_xlabel("Distance from Hub (km)")
    ax.set_ylabel("Arrival Day (first I >= 1)")
    ax.set_title("Spatial Spread: Arrival Time vs Distance")
    fig.tight_layout()
    fig.savefig(figures_dir / "spatial_spread.png", dpi=150)
    plt.close(fig)


def plot_attack_rates(
    model: CompartmentalModel, scenario: pl.DataFrame, figures_dir: Path
) -> None:
    """Plot final attack rates (R_final / initial_pop) per patch."""
    tracker = model.get_instance(StateTracker)[0]
    R = tracker.R
    group_ids = tracker.group_ids

    scenario_ids = scenario["id"].to_list()
    pops = scenario["pop"].to_numpy()
    distances = _get_distances_km(scenario)

    # Build attack rate per group, sorted by distance
    records = []
    for j, gid in enumerate(group_ids):
        idx = scenario_ids.index(gid)
        attack_rate = R[-1, j] / pops[idx]
        records.append((gid, distances[idx], attack_rate))

    records.sort(key=lambda r: r[1])
    labels = [r[0] for r in records]
    rates = [r[2] for r in records]

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["red" if lbl == "hub" else "steelblue" for lbl in labels]
    ax.bar(labels, rates, color=colors, edgecolor="k")
    ax.set_ylabel("Attack Rate (R_final / Pop)")
    ax.set_title("Final Attack Rates (sorted by distance from hub)")
    ax.set_ylim(0, 1.05)
    fig.tight_layout()
    fig.savefig(figures_dir / "attack_rates.png", dpi=150)
    plt.close(fig)


# %% Main


def main():
    figures_dir = Path(__file__).parent / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    scenario = create_satellite_hub_scenario()
    model = configure_model(scenario)
    model.run()

    plot_network(scenario, figures_dir)
    plot_epidemic_curves(model, scenario, figures_dir)
    plot_spatial_spread(model, scenario, figures_dir)
    plot_attack_rates(model, scenario, figures_dir)

    model.cleanup()
    print("Figures saved to", figures_dir)


if __name__ == "__main__":
    main()
