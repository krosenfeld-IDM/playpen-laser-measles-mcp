# Plan: Satellite-Hub Measles Transmission Script

## Context

The `projects/getting-started/` directory is empty. We need to create an educational script that demonstrates measles transmission dynamics in a satellite-hub network using the `laser-measles` compartmental model. This showcases spatial epidemic spread — seeding infection in a central hub and watching it propagate to surrounding satellite towns via gravity-based mixing.

## Files to Create

- `projects/getting-started/satellite_hub_measles.py` — single self-contained script

The script creates a `figures/` subdirectory at runtime for output.

## Script Structure

Use cell-style formatting (per CLAUDE.md: "Build tutorials using cell formatting and `*.py` files").

### Cell 1: Imports

```python
import numpy as np
import polars as pl
import matplotlib.pyplot as plt
from pathlib import Path

from laser.measles.compartmental import CompartmentalModel, CompartmentalParams
from laser.measles.compartmental import components
from laser.measles.components import create_component
from laser.measles.mixing.gravity import GravityMixing, GravityParams
```

### Cell 2: `create_satellite_hub_scenario()` → `pl.DataFrame`

Build a 7-patch scenario (1 hub + 6 satellites):

| id    | pop     | lat/lon                        | mcv1 |
|-------|---------|--------------------------------|------|
| hub   | 500,000 | (0.0, 0.0)                     | 0.0  |
| sat_1 | 80,000  | ring at varying distances      | 0.0  |
| sat_2 | 60,000  | 50-150 km from hub             | 0.0  |
| ...   | ...     | angles at 60° intervals        | 0.0  |
| sat_6 | 20,000  |                                | 0.0  |

- Convert km to degrees: `km / 111.0` (pattern from `scenarios/synthetic.py:189-190`)
- `mcv1=0.0` — fully susceptible population for clear epidemic dynamics
- Vary satellite distances: `[50, 75, 100, 100, 125, 150]` km
- Vary satellite populations: `[80000, 60000, 50000, 40000, 30000, 20000]`

### Cell 3: `configure_model(scenario)` → `CompartmentalModel`

Parameters:
- `CompartmentalParams(num_ticks=365, seed=42, start_time="2024-01")`

Components (in order):
1. `StateTracker` with `aggregation_level=0` — per-patch tracking (flat IDs, so level 0 = per-patch)
2. `InfectionSeedingProcess` — seed 10 infections in hub (S→E)
3. `InfectionProcess` — SEIR transmission with gravity mixing
4. `ConstantPopProcess` — demographic turnover

Key parameter choices:
- `beta=0.5, exp_mu=8.0, inf_mu=5.0` → R0 = beta/gamma = beta*inf_mu = 2.5 (clear epidemic without instant burnout)
- `seasonality=0.15` — mild seasonal modulation
- `GravityParams(a=1.0, b=1.0, c=2.0, k=0.01)` — distance-squared decay, modest mixing rate

Reuse: `create_component()` from `laser.measles.components` (see `components/utils.py`)

### Cell 4: Plotting Functions (4 figures)

**Figure 1: `plot_network(scenario, figures_dir)`** — Network map
- Scatter plot: nodes sized by population, hub in red, satellites in blue
- Lines from hub to each satellite, thickness ∝ coupling strength (1/distance²)
- Labels with patch ID and population

**Figure 2: `plot_epidemic_curves(model, scenario, figures_dir)`** — Infections over time
- Access `tracker.I` → shape `(365, 7)` via `model.get_instance(components.StateTracker)`
- One line per patch, hub highlighted (thicker line)
- `tracker.group_ids` gives sorted patch IDs for legend mapping

**Figure 3: `plot_spatial_spread(model, scenario, figures_dir)`** — Arrival time vs distance
- "Arrival time" = first tick where `I[:, patch] >= 1`
- Scatter plot: x = distance from hub (km), y = arrival day
- Shows the spatial wave propagation

**Figure 4: `plot_attack_rates(model, scenario, figures_dir)`** — Final attack rates
- Attack rate = `R[-1, patch] / initial_pop[patch]`
- Bar chart sorted by distance from hub

### Cell 5: `main()` and `if __name__ == "__main__"`

```python
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
```

## Key Framework References

- `src/laser-measles/src/laser/measles/scenarios/synthetic.py` — `satellites_scenario()` pattern for lat/lon conversion
- `src/laser-measles/src/laser/measles/compartmental/components/process_infection.py` — InfectionParams fields, transmission formula
- `src/laser-measles/src/laser/measles/compartmental/components/process_infection_seeding.py` — seeds S→E (not S→I)
- `src/laser-measles/src/laser/measles/components/base_tracker_state.py` — StateTracker: `.I` returns `(num_ticks, num_groups)` when `aggregation_level>=0`, `.group_ids` for patch names
- `src/laser-measles/src/laser/measles/mixing/gravity.py` — GravityMixing/GravityParams API
- `src/laser-measles/src/laser/measles/components/utils.py` — `create_component()` factory

## Verification

1. Run `python projects/getting-started/satellite_hub_measles.py`
2. Check that `projects/getting-started/figures/` contains 4 PNG files
3. Visually confirm: epidemic starts in hub, spreads to satellites with delay proportional to distance
4. Verify attack rates are high (near 100% since mcv1=0.0 and R0=2.5)
