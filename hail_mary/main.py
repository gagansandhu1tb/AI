"""
main.py
-------
Entry point for the Project Hail Mary simulation.
Supports three modes:
  python main.py visual    - Run one live animated simulation
  python main.py batch     - Run 20 simulations, produce analysis charts
  python main.py single    - Run one simulation with text output
"""

import sys
import json
import random
import statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from simulation import Simulation
from visualiser import SimulationVisualiser


# ------------------------------------------------------------------ #
#  Single run with text output                                         #
# ------------------------------------------------------------------ #

def run_single(seed: int = None, verbose: bool = True) -> dict:
    """Run one simulation and return the result dict."""
    sim = Simulation(seed=seed, verbose=verbose)
    result = sim.run()
    print(sim.summary())
    print(f"\nResult: {result.outcome.upper()}")
    return result.to_dict()


# ------------------------------------------------------------------ #
#  Batch run: 20 simulations with analysis                             #
# ------------------------------------------------------------------ #

def run_batch(n_runs: int = 20, base_seed: int = 42) -> list[dict]:
    """
    Run n_runs simulations with different seeds.
    Produce quantitative analysis and save charts to /tmp/.
    """
    results = []
    print(f"\n{'='*60}")
    print(f"PROJECT HAIL MARY — BATCH RUN ({n_runs} simulations)")
    print(f"{'='*60}\n")

    for i in range(n_runs):
        seed = base_seed + i
        print(f"Run {i+1:2d}/{n_runs} (seed={seed})... ", end="", flush=True)
        sim = Simulation(seed=seed, verbose=False)
        result = sim.run()
        d = result.to_dict()
        results.append(d)
        print(
            f"Outcome={d['outcome']:10s} | "
            f"Turns={d['turns']:3d} | "
            f"Knowledge={d['knowledge']:6.1f} | "
            f"Score={d['mission_score']:6.1f}"
        )

    _print_statistics(results)
    _save_analysis_charts(results)
    _save_results_json(results)
    return results


def _print_statistics(results: list[dict]):
    """Print quantitative summary statistics."""
    outcomes = [r["outcome"] for r in results]
    turns = [r["turns"] for r in results]
    knowledge = [r["knowledge"] for r in results]
    scores = [r["mission_score"] for r in results]
    beetles = [r["beetles_deployed"] for r in results]
    experiments = [r["experiments_run"] for r in results]
    taumoeba_rate = sum(1 for r in results if r["taumoeba_viable_earth"]) / len(results)

    print(f"\n{'='*60}")
    print("STATISTICAL ANALYSIS")
    print(f"{'='*60}")
    print(f"Total runs          : {len(results)}")
    print(f"\nOutcome distribution:")
    for outcome in ["success", "partial", "failure", "incomplete"]:
        count = outcomes.count(outcome)
        pct = count / len(results) * 100
        bar = "█" * int(pct / 5)
        print(f"  {outcome:12s} : {count:3d} ({pct:5.1f}%) {bar}")

    print(f"\nSurvival / Progress:")
    print(f"  Avg turns survived  : {statistics.mean(turns):.1f} ± {statistics.stdev(turns):.1f}")
    print(f"  Min/Max turns       : {min(turns)} / {max(turns)}")
    print(f"  Avg knowledge score : {statistics.mean(knowledge):.1f} ± {statistics.stdev(knowledge):.1f}")
    print(f"  Avg mission score   : {statistics.mean(scores):.1f} ± {statistics.stdev(scores):.1f}")
    print(f"  Avg beetles deployed: {statistics.mean(beetles):.2f}")
    print(f"  Avg experiments run : {statistics.mean(experiments):.1f}")
    print(f"  Taumoeba viable rate: {taumoeba_rate:.1%}")
    print(f"{'='*60}\n")


def _save_analysis_charts(results: list[dict]):
    """Generate and save analysis charts."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.patch.set_facecolor("#0a0a1a")
    fig.suptitle(
        "Project Hail Mary — Batch Run Analysis (20 Simulations)",
        color="white", fontsize=13, fontweight="bold"
    )

    def style(ax, title, xlabel, ylabel):
        ax.set_facecolor("#0d0d2b")
        ax.set_title(title, color="#aaaaff", fontsize=9)
        ax.set_xlabel(xlabel, color="gray", fontsize=8)
        ax.set_ylabel(ylabel, color="gray", fontsize=8)
        ax.tick_params(colors="gray", labelsize=7)
        for sp in ax.spines.values():
            sp.set_edgecolor("#333366")

    turns      = [r["turns"] for r in results]
    knowledge  = [r["knowledge"] for r in results]
    scores     = [r["mission_score"] for r in results]
    beetles    = [r["beetles_deployed"] for r in results]
    sun_b      = [r["sun_brightness"] for r in results]
    outcomes   = [r["outcome"] for r in results]

    run_ids = list(range(1, len(results) + 1))

    # 1. Knowledge score per run
    ax = axes[0][0]
    colours = ["#69ff47" if r["taumoeba_viable_earth"] else "#ff6600" for r in results]
    ax.bar(run_ids, knowledge, color=colours, alpha=0.8)
    style(ax, "Knowledge Score per Run", "Run #", "Knowledge")
    ax.axhline(
        sum(knowledge) / len(knowledge),
        color="white", linestyle="--", linewidth=0.8, label="Mean"
    )
    ax.legend(fontsize=7, labelcolor="white", facecolor="#1a1a2e",
              edgecolor="gray")

    # 2. Mission score distribution
    ax = axes[0][1]
    ax.hist(scores, bins=10, color="#00e5ff", alpha=0.8, edgecolor="white",
            linewidth=0.5)
    style(ax, "Mission Score Distribution", "Mission Score", "Frequency")

    # 3. Turns survived
    ax = axes[0][2]
    ax.plot(run_ids, turns, color="#ff6600", marker="o", markersize=4,
            linewidth=1.2)
    ax.fill_between(run_ids, turns, alpha=0.2, color="#ff6600")
    style(ax, "Turns Survived", "Run #", "Turns")

    # 4. Outcome pie chart
    ax = axes[1][0]
    outcome_types = ["success", "partial", "failure", "incomplete"]
    outcome_counts = [outcomes.count(o) for o in outcome_types]
    colours_pie = ["#69ff47", "#ffff00", "#ff4444", "#888888"]
    wedges, texts, autotexts = ax.pie(
        outcome_counts,
        labels=outcome_types,
        colors=colours_pie,
        autopct="%1.0f%%",
        startangle=90,
        textprops={"color": "white", "fontsize": 8}
    )
    for at in autotexts:
        at.set_color("black")
        at.set_fontsize(7)
    ax.set_title("Outcome Distribution", color="#aaaaff", fontsize=9)

    # 5. Beetles deployed vs knowledge
    ax = axes[1][1]
    ax.scatter(knowledge, beetles, c=scores, cmap="plasma", alpha=0.8, s=60)
    style(ax, "Knowledge vs Beetles Deployed", "Knowledge Score", "Beetles")

    # 6. Sun brightness at end
    ax = axes[1][2]
    ax.bar(run_ids, sun_b, color="#ffff00", alpha=0.8)
    ax.axhline(0.7, color="red", linestyle="--", linewidth=0.8,
               label="Critical threshold")
    style(ax, "Sun Brightness at End", "Run #", "Brightness")
    ax.legend(fontsize=7, labelcolor="white", facecolor="#1a1a2e",
              edgecolor="gray")

    plt.tight_layout()
    output_path = "/tmp/hail_mary_analysis.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor="#0a0a1a")
    plt.close()
    print(f"Analysis charts saved to: {output_path}")
    return output_path


def _save_results_json(results: list[dict]):
    path = "/tmp/hail_mary_results.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Raw results saved to: {path}")


# ------------------------------------------------------------------ #
#  Visual mode                                                          #
# ------------------------------------------------------------------ #

def run_visual(seed: int = None):
    """Launch the live animated visualiser."""
    if seed is None:
        seed = random.randint(0, 9999)
    print(f"Starting visual simulation (seed={seed})")
    print("Close the window to stop.\n")
    sim = Simulation(seed=seed, verbose=False)
    vis = SimulationVisualiser(sim, interval_ms=250)
    vis.run()


# ------------------------------------------------------------------ #
#  Entry point                                                          #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "single"
    seed_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None

    if mode == "visual":
        # Visual mode requires display - use Agg backend for headless
        try:
            matplotlib.use("TkAgg")
        except Exception:
            pass
        run_visual(seed=seed_arg)

    elif mode == "batch":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        run_batch(n_runs=n)

    elif mode == "single":
        run_single(seed=seed_arg, verbose=True)

    else:
        print("Usage: python main.py [visual|batch|single] [seed/n_runs]")
        print("  visual  - animated GUI simulation")
        print("  batch   - run 20 simulations, save analysis charts")
        print("  single  - one run with full text output")
