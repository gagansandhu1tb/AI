"""
visualiser.py
-------------
Real-time visualisation of the Project Hail Mary simulation.
Uses matplotlib to display the grid, agent positions,
knowledge progress, and mission metrics.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.animation import FuncAnimation
from grid import CellType


# Colour map for each cell type
CELL_COLOURS = {
    CellType.EMPTY:      0,
    CellType.ADRIAN:     1,
    CellType.ASTROPHAGE: 2,
    CellType.PETROVA:    3,
    CellType.HAIL_MARY:  4,
    CellType.BLIP_A:     5,
    CellType.TUNNEL:     6,
    CellType.RADIATION:  7,
    CellType.DEBRIS:     8,
}

COLOUR_LIST = [
    "#0a0a1a",   # 0 EMPTY      - deep space black
    "#2e7d32",   # 1 ADRIAN     - green planet
    "#ff6600",   # 2 ASTROPHAGE - orange threat
    "#cc0000",   # 3 PETROVA    - deep red danger
    "#1565c0",   # 4 HAIL_MARY  - blue spacecraft
    "#7b1fa2",   # 5 BLIP_A     - purple alien ship
    "#00bcd4",   # 6 TUNNEL     - cyan connector
    "#f9a825",   # 7 RADIATION  - yellow hazard
    "#795548",   # 8 DEBRIS     - brown debris
]


class SimulationVisualiser:
    """
    Visualises the simulation in real time using matplotlib.
    Shows: grid, agent positions, knowledge graph, mission metrics.
    """

    def __init__(self, simulation, interval_ms: int = 300):
        self.sim = simulation
        self.interval = interval_ms
        self.running = False

        self._setup_figure()
        self._anim = None

    def _setup_figure(self):
        """Build the figure layout."""
        self.fig = plt.figure(
            figsize=(16, 9),
            facecolor="#0a0a1a"
        )
        self.fig.suptitle(
            "PROJECT HAIL MARY — Multi-Agent Simulation",
            color="white", fontsize=14, fontweight="bold"
        )

        # Grid layout: 2 rows x 3 cols
        gs = self.fig.add_gridspec(
            2, 3,
            left=0.05, right=0.97,
            top=0.92, bottom=0.06,
            hspace=0.35, wspace=0.3
        )

        # Main grid view (large, left)
        self.ax_grid = self.fig.add_subplot(gs[:, 0])
        self._style_ax(self.ax_grid, "Space Grid — Tau Ceti Region")

        # Knowledge score over time
        self.ax_knowledge = self.fig.add_subplot(gs[0, 1])
        self._style_ax(self.ax_knowledge, "Knowledge Score Progress")

        # Mission score over time
        self.ax_mission = self.fig.add_subplot(gs[0, 2])
        self._style_ax(self.ax_mission, "Mission Score")

        # Astrophage coverage
        self.ax_astrophage = self.fig.add_subplot(gs[1, 1])
        self._style_ax(self.ax_astrophage, "Astrophage Coverage")

        # Status text panel
        self.ax_status = self.fig.add_subplot(gs[1, 2])
        self._style_ax(self.ax_status, "Mission Status")
        self.ax_status.set_xticks([])
        self.ax_status.set_yticks([])

        # Build colour map
        cmap = mcolors.ListedColormap(COLOUR_LIST)
        bounds = list(range(len(COLOUR_LIST) + 1))
        norm = mcolors.BoundaryNorm(bounds, cmap.N)
        self.cmap = cmap
        self.norm = norm

        # Legend patches
        patches = [
            mpatches.Patch(color=COLOUR_LIST[v], label=k.name)
            for k, v in CELL_COLOURS.items()
        ]
        self.ax_grid.legend(
            handles=patches,
            loc="upper right", fontsize=5,
            facecolor="#1a1a2e", edgecolor="white",
            labelcolor="white"
        )

    def _style_ax(self, ax, title: str):
        ax.set_facecolor("#0d0d2b")
        ax.set_title(title, color="#aaaaff", fontsize=8, pad=4)
        ax.tick_params(colors="gray", labelsize=6)
        for spine in ax.spines.values():
            spine.set_edgecolor("#333366")

    def _grid_to_array(self) -> np.ndarray:
        """Convert grid cell types to numeric array for imshow."""
        grid = self.sim.grid
        arr = np.zeros((grid.height, grid.width), dtype=int)
        for y in range(grid.height):
            for x in range(grid.width):
                cell = grid.cells[y][x]
                arr[y][x] = CELL_COLOURS.get(cell.cell_type, 0)
        return arr

    def _update(self, frame):
        """Animation update callback - advance simulation one step."""
        done = self.sim.step_once()

        # ---- Grid ----
        self.ax_grid.cla()
        self._style_ax(self.ax_grid, f"Space Grid — Turn {self.sim.turn}")
        arr = self._grid_to_array()
        self.ax_grid.imshow(
            arr, cmap=self.cmap, norm=self.norm,
            origin="upper", interpolation="nearest"
        )

        # Plot agent positions
        grace = self.sim.grace
        rocky = self.sim.rocky
        if grace.alive:
            self.ax_grid.plot(
                grace.x, grace.y, "w*", markersize=10,
                label="Grace", zorder=5
            )
        if rocky.alive:
            self.ax_grid.plot(
                rocky.x, rocky.y, "y^", markersize=8,
                label="Rocky", zorder=5
            )
        for b in self.sim.beetle_probes:
            if b.alive and not b.transmitted:
                self.ax_grid.plot(
                    b.x, b.y, "g>", markersize=5, zorder=4
                )
        self.ax_grid.legend(
            loc="lower right", fontsize=6,
            facecolor="#1a1a2e", edgecolor="white",
            labelcolor="white"
        )

        # ---- Knowledge chart ----
        self.ax_knowledge.cla()
        self._style_ax(self.ax_knowledge, "Knowledge Score")
        if self.sim.knowledge_history:
            self.ax_knowledge.plot(
                self.sim.knowledge_history, color="#00e5ff", linewidth=1.2
            )
            self.ax_knowledge.set_xlabel("Turn", color="gray", fontsize=6)
            self.ax_knowledge.set_ylabel("Score", color="gray", fontsize=6)

        # ---- Mission score chart ----
        self.ax_mission.cla()
        self._style_ax(self.ax_mission, "Mission Score")
        if self.sim.mission_score_history:
            self.ax_mission.plot(
                self.sim.mission_score_history, color="#69ff47", linewidth=1.2
            )
            self.ax_mission.set_xlabel("Turn", color="gray", fontsize=6)
            self.ax_mission.set_ylabel("Score", color="gray", fontsize=6)

        # ---- Astrophage coverage ----
        self.ax_astrophage.cla()
        self._style_ax(self.ax_astrophage, "Astrophage Coverage")
        if self.sim.astrophage_mgr.coverage_history:
            cov = self.sim.astrophage_mgr.coverage_history
            bright = self.sim.astrophage_mgr.brightness_history
            self.ax_astrophage.plot(cov, color="#ff6600", linewidth=1.2,
                                    label="Coverage")
            self.ax_astrophage.plot(bright, color="#ffff00", linewidth=1.2,
                                    label="Sun brightness", linestyle="--")
            self.ax_astrophage.legend(
                fontsize=5, facecolor="#1a1a2e",
                edgecolor="gray", labelcolor="white"
            )
            self.ax_astrophage.set_xlabel("Turn", color="gray", fontsize=6)

        # ---- Status panel ----
        self.ax_status.cla()
        self._style_ax(self.ax_status, "Mission Status")
        self.ax_status.set_xticks([])
        self.ax_status.set_yticks([])

        taumoeba_ok = self.sim.taumoeba_lab.has_viable_earth_strain()
        transmitted = sum(1 for b in self.sim.beetle_probes if b.transmitted)

        status_lines = [
            f"Turn        : {self.sim.turn}",
            f"Grace HP    : {grace.health:.0f}",
            f"Grace Energy: {grace.energy:.0f}",
            f"Knowledge   : {grace.knowledge_score:.0f}",
            f"",
            f"Translation : {rocky.translation_level}/10",
            f"Cooperation : {rocky.cooperation_score:.2f}",
            f"Rocky energy: {rocky.energy:.0f}",
            f"",
            f"Taumoeba OK : {'YES ✓' if taumoeba_ok else 'no'}",
            f"Beetles dep.: {len(grace.beetles_deployed)}/4",
            f"Transmitted : {transmitted}",
            f"",
            f"Sun bright  : {self.sim.astrophage_mgr.sun_brightness:.3f}",
            f"Mission score: {self.sim.mission_score:.0f}",
            f"",
            f"Flashbacks  : {len(grace.flashbacks_triggered)}/5",
        ]

        for i, line in enumerate(status_lines):
            colour = "#00e5ff" if "YES" in line else (
                "#ff6600" if "no" in line.lower() else "#ccccff"
            )
            self.ax_status.text(
                0.05, 0.95 - i * 0.055, line,
                transform=self.ax_status.transAxes,
                color=colour, fontsize=7,
                fontfamily="monospace", va="top"
            )

        if done:
            self.ax_grid.set_title(
                f"SIMULATION COMPLETE — {self.sim.event_log[-1]}",
                color="#ff4444", fontsize=8
            )
            if self._anim:
                self._anim.event_source.stop()

        return []

    def run(self):
        """Start the animated simulation display."""
        self._anim = FuncAnimation(
            self.fig,
            self._update,
            interval=self.interval,
            cache_frame_data=False,
            blit=False,
        )
        plt.show()

    def run_static_snapshot(self):
        """Render a single static frame (useful for testing without display)."""
        self._update(0)
        plt.tight_layout()
        return self.fig
