"""
Model 3: Spatial spread — hub-and-satellite ABM
=================================================
A core city (500k) surrounded by 20 satellite towns (50k each).
MCV1 = 50%. Gravity-based spatial mixing transmits measles
from the core outward. Visualized as a heatmap of infectious
counts by patch (ordered by distance from core).
"""

import matplotlib
matplotlib.use("Agg")
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import laser.measles as lm
from laser.measles.abm import (
    ABMModel,
    ABMParams,
    ConstantPopProcess,
    InfectionProcess,
    StateTracker,
    StateTrackerParams,
)
from laser.measles.abm import InfectionSeedingProcess
from laser.measles import create_component
from laser.measles.scenarios import satellites_scenario

FIGDIR = Path(__file__).parent / "figures"
FIGDIR.mkdir(exist_ok=True)


def main():
    # 1) Build scenario
    scenario = satellites_scenario(
        core_population=500_000,
        satellite_population=50_000,
        n_towns=21,
        max_distance=200.0,
        mcv1=0.50,
        seed=52,
    )
    print(f"Scenario: {len(scenario)} patches, total pop = {scenario['pop'].sum():,}")

    # 2) Model: 2-year ABM
    params = ABMParams(num_ticks=365 * 2, seed=123, start_time="2000-01")
    model = ABMModel(scenario=scenario, params=params)
    model.add_component(ConstantPopProcess)
    model.add_component(InfectionSeedingProcess)
    model.add_component(InfectionProcess)
    model.add_component(
        create_component(StateTracker, params=StateTrackerParams(aggregation_level=0))
    )
    model.run()

    # 3) Extract per-patch infectious
    tracker = model.get_instance("StateTracker")[0]
    I = tracker.I  # shape (T, P) for aggregation_level=0
    if I.ndim == 1:
        I = I[:, None]
    T, P = I.shape
    print(f"I shape: {I.shape}")

    # 4) Order patches by distance from core (largest-pop patch)
    scen_pd = scenario.to_pandas()
    core_idx = int(scen_pd["pop"].values.argmax())
    core_lat, core_lon = scen_pd.loc[core_idx, "lat"], scen_pd.loc[core_idx, "lon"]

    lats, lons = scen_pd["lat"].values, scen_pd["lon"].values
    R = 6371.0
    dlat = np.radians(lats - core_lat)
    dlon = np.radians(lons - core_lon)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(core_lat)) * np.cos(np.radians(lats)) * np.sin(dlon / 2) ** 2
    dist_km = 2 * R * np.arcsin(np.sqrt(a))

    order = np.argsort(dist_km)
    I_ordered = I[:, order]
    dist_ordered = dist_km[order]

    # 5) First-infection day by patch
    first_day = np.full(P, np.nan)
    for j in range(P):
        nz = np.nonzero(I_ordered[:, j] > 0)[0]
        if nz.size > 0:
            first_day[j] = nz[0]

    print("\nFirst infection day by distance from core:")
    for j in range(min(P, 10)):
        d = dist_ordered[j]
        fd = first_day[j]
        print(f"  patch {j}: {d:.0f} km → day {fd:.0f}" if not np.isnan(fd) else f"  patch {j}: {d:.0f} km → never")

    # 6) Heatmap
    fig, ax = plt.subplots(figsize=(12, 6))
    # Smooth with weekly aggregation for readability
    week_bins = T // 7
    I_weekly = I_ordered[:week_bins * 7].reshape(week_bins, 7, P).sum(axis=1)
    im = ax.imshow(
        I_weekly.T,
        aspect="auto",
        cmap="magma",
        interpolation="nearest",
        origin="lower",
    )
    ax.set_xlabel("Week")
    ax.set_ylabel("Patch (sorted by distance from core)")
    ax.set_title("Measles spatial spread: weekly infectious counts by patch")
    cbar = fig.colorbar(im, ax=ax, label="Infectious (weekly total)")

    # Label y-axis with distances
    ytick_pos = list(range(0, P, max(1, P // 10)))
    ax.set_yticks(ytick_pos)
    ax.set_yticklabels([f"{dist_ordered[j]:.0f} km" for j in ytick_pos])
    fig.tight_layout()
    fig.savefig(FIGDIR / "03_spatial_spread.png", dpi=150)
    print(f"\nSaved {FIGDIR / '03_spatial_spread.png'}")

    # 7) Scatter: first-infection-day vs distance
    fig2, ax2 = plt.subplots(figsize=(7, 5))
    valid = ~np.isnan(first_day)
    ax2.scatter(dist_ordered[valid], first_day[valid], c="crimson", edgecolors="k", s=60)
    ax2.set_xlabel("Distance from core (km)")
    ax2.set_ylabel("First day with any infectious")
    ax2.set_title("Spatial wave: infection arrival time vs distance")
    ax2.grid(True, alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(FIGDIR / "03_arrival_vs_distance.png", dpi=150)
    print(f"Saved {FIGDIR / '03_arrival_vs_distance.png'}")


if __name__ == "__main__":
    main()
