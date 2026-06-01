"""
run_gui.py
----------
Project Hail Mary — Interactive GUI Runner

- Ek ek simulation chalata hai (200 turns each)
- Har simulation ke baad window band ho jati hai
- User se poochha jata hai: next simulation chalana hai ya nahi
- 20 simulations ke baad graphs show hote hain
- User choose kar sakta hai kya dekhna hai

Run: python run_gui.py
"""

import tkinter as tk
from tkinter import messagebox, ttk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import sys
import os
import json
import statistics
import random
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulation import Simulation
from grid import CellType

# ─────────────────────────────────────────────
#  COLOUR MAP
# ─────────────────────────────────────────────
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
    "#050510", "#1b5e20", "#e65100",
    "#b71c1c", "#0d47a1", "#6a1b9a",
    "#006064", "#f57f17", "#4e342e",
]
CMAP  = mcolors.ListedColormap(COLOUR_LIST)
BNORM = mcolors.BoundaryNorm(range(len(COLOUR_LIST) + 1), CMAP.N)

MAX_RUNS  = 20
MAX_TURNS = 300


# ══════════════════════════════════════════════════════════════════
#  SIMULATION WINDOW
# ══════════════════════════════════════════════════════════════════
class SimWindow:
    """One simulation run displayed in a tkinter window."""

    def __init__(self, run_number: int, seed: int, on_close_callback):
        self.run_number = run_number
        self.seed       = seed
        self.on_close   = on_close_callback
        self.result     = None
        # verbose=True so event_log entries are printed to the launching terminal
        self.sim        = Simulation(seed=seed, verbose=True)
        self.sim.MAX_TURNS = MAX_TURNS
        self._done      = False

        # ── root window ──────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title(f"🚀  Project Hail Mary  —  Simulation {run_number}/{MAX_RUNS}")
        self.root.configure(bg="#050510")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        self._build_ui()
        self._schedule_step()
        self.root.mainloop()

    # ─────────────────────────────────────────
    #  UI BUILD
    # ─────────────────────────────────────────
    def _build_ui(self):
        # ── title bar ───────────────────────────────────────────
        title_frame = tk.Frame(self.root, bg="#050510")
        title_frame.pack(fill="x", padx=10, pady=(8, 0))

        tk.Label(
            title_frame,
            text=f"PROJECT HAIL MARY  ·  Run {self.run_number}/{MAX_RUNS}  ·  Seed {self.seed}",
            font=("Courier New", 11, "bold"),
            fg="#00e5ff", bg="#050510"
        ).pack(side="left")

        self.turn_label = tk.Label(
            title_frame, text="Turn: 0",
            font=("Courier New", 10),
            fg="#aaaaff", bg="#050510"
        )
        self.turn_label.pack(side="right")

        # ── main layout ─────────────────────────────────────────
        main = tk.Frame(self.root, bg="#050510")
        main.pack(fill="both", expand=True, padx=10, pady=6)

        # left: matplotlib grid
        left = tk.Frame(main, bg="#050510")
        left.pack(side="left", fill="both", expand=True)

        self.fig_grid, self.ax_grid = plt.subplots(
            figsize=(5.5, 5.5), facecolor="#050510"
        )
        self.ax_grid.set_facecolor("#050510")
        self.canvas_grid = FigureCanvasTkAgg(self.fig_grid, master=left)
        self.canvas_grid.get_tk_widget().pack(fill="both", expand=True)

        # right: stats + log
        right = tk.Frame(main, bg="#050510", width=310)
        right.pack(side="right", fill="y", padx=(8, 0))
        right.pack_propagate(False)

        # ── stats panel ─────────────────────────────────────────
        stats_frame = tk.LabelFrame(
            right, text=" Mission Stats ",
            font=("Courier New", 9, "bold"),
            fg="#aaaaff", bg="#0d0d2b",
            relief="flat", bd=1
        )
        stats_frame.pack(fill="x", pady=(0, 6))

        self.stat_vars = {}
        stat_items = [
            ("grace_hp",    "Grace HP",      "#69ff47"),
            ("grace_en",    "Grace Energy",  "#00e5ff"),
            ("knowledge",   "Knowledge",     "#ffe57f"),
            ("",            "",              ""),
            ("translation", "Translation",   "#ce93d8"),
            ("cooperation", "Rocky Coop.",   "#f48fb1"),
            ("",            "",              ""),
            ("taumoeba",    "Taumoeba OK",   "#69ff47"),
            ("beetles",     "Beetles",       "#80deea"),
            ("transmitted", "Transmitted",   "#a5d6a7"),
            ("",            "",              ""),
            ("sun",         "Sun Brightness","#fff176"),
            ("astrophage",  "Astrophage %",  "#ff8a65"),
            ("score",       "Mission Score", "#ef9a9a"),
        ]
        for key, label, colour in stat_items:
            if key == "":
                tk.Frame(stats_frame, bg="#0d0d2b", height=4).pack()
                continue
            row = tk.Frame(stats_frame, bg="#0d0d2b")
            row.pack(fill="x", padx=6, pady=1)
            tk.Label(
                row, text=f"{label:<16}", width=16,
                font=("Courier New", 8), fg="#7777aa", bg="#0d0d2b",
                anchor="w"
            ).pack(side="left")
            var = tk.StringVar(value="—")
            lbl = tk.Label(
                row, textvariable=var,
                font=("Courier New", 8, "bold"),
                fg=colour, bg="#0d0d2b", anchor="w"
            )
            lbl.pack(side="left")
            self.stat_vars[key] = var

        # ── progress bar ─────────────────────────────────────────
        pb_frame = tk.Frame(right, bg="#050510")
        pb_frame.pack(fill="x", pady=(0, 6))
        tk.Label(
            pb_frame, text="Progress", font=("Courier New", 8),
            fg="#555588", bg="#050510"
        ).pack(anchor="w")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "hm.Horizontal.TProgressbar",
            troughcolor="#0d0d2b", background="#00e5ff",
            darkcolor="#00e5ff", lightcolor="#00e5ff", bordercolor="#0d0d2b"
        )
        self.progress = ttk.Progressbar(
            pb_frame, style="hm.Horizontal.TProgressbar",
            maximum=MAX_TURNS, value=0, length=290
        )
        self.progress.pack(fill="x")

        # ── legend (explain cell types) ─────────────────────────────
        legend_frame = tk.LabelFrame(
            right, text=" Legend ",
            font=("Courier New", 9, "bold"),
            fg="#aaaaff", bg="#0d0d2b",
            relief="flat", bd=1
        )
        legend_frame.pack(fill="both", expand=True)

        legend_items = [
            ("Petrova (P)", COLOUR_LIST[3], "Dense astrophage — very hazardous"),
            ("Astrophage (*)", COLOUR_LIST[2], "Astrophage clouds — spread and drain energy"),
            ("Adrian (A)", COLOUR_LIST[1], "Planet Adrian — taumoeba source"),
            ("Hail Mary (H) — Grace", COLOUR_LIST[4], "Grace's ship — your agent"),
            ("Blip-A (B) — Rocky", COLOUR_LIST[5], "Rocky's ship — alien ally"),
            ("Tunnel (T)", COLOUR_LIST[6], "Xenonite tunnel — improves comms"),
            ("Radiation (R)", COLOUR_LIST[7], "Radiation hazard"),
            ("Debris (D)", COLOUR_LIST[8], "Debris fields — minor hazard"),
        ]

        for name, colour, desc in legend_items:
            row = tk.Frame(legend_frame, bg="#0d0d2b")
            row.pack(fill="x", padx=6, pady=2)
            sw = tk.Label(row, bg=colour, width=3, height=1, relief="ridge", bd=1)
            sw.pack(side="left", padx=(4, 8))
            tk.Label(
                row, text=f"{name} — {desc}",
                font=("Courier New", 8), fg="#ccc", bg="#0d0d2b", anchor="w",
            ).pack(side="left")

        # ── status bar ───────────────────────────────────────────
        self.status_bar = tk.Label(
            self.root,
            text="Simulation initialising...",
            font=("Courier New", 8),
            fg="#555588", bg="#020208", anchor="w"
        )
        self.status_bar.pack(fill="x", padx=10, pady=(0, 4))

        # colour legend patches
        patches = [
            mpatches.Patch(color=COLOUR_LIST[v], label=k.name)
            for k, v in CELL_COLOURS.items()
        ]
        self.ax_grid.legend(
            handles=patches, loc="upper right",
            fontsize=5, facecolor="#0d0d2b",
            edgecolor="#333366", labelcolor="white"
        )

    # ─────────────────────────────────────────
    #  STEP LOOP
    # ─────────────────────────────────────────
    def _schedule_step(self):
        """Schedule next turn with 120 ms delay."""
        self.root.after(120, self._step)

    def _step(self):
        if self._done:
            return

        done = self.sim.step_once()
        self._refresh_display()

        if done or self.sim.turn >= MAX_TURNS:
            self._finish()
        else:
            self._schedule_step()

    def _refresh_display(self):
        sim   = self.sim
        grace = sim.grace
        rocky = sim.rocky

        # ── turn label ───────────────────────────────────────────
        self.turn_label.config(text=f"Turn: {sim.turn}/{MAX_TURNS}")
        self.progress["value"] = sim.turn

        # ── stats ────────────────────────────────────────────────
        transmitted = sum(1 for b in sim.beetle_probes if b.transmitted)
        taumoeba_ok = sim.taumoeba_lab.has_viable_earth_strain()

        self.stat_vars["grace_hp"].set(f"{grace.health:.0f}/{grace.max_health:.0f}")
        self.stat_vars["grace_en"].set(f"{grace.energy:.1f}")
        self.stat_vars["knowledge"].set(f"{grace.knowledge_score:.0f}")
        self.stat_vars["translation"].set(f"{rocky.translation_level}/10")
        self.stat_vars["cooperation"].set(f"{rocky.cooperation_score:.2f}")
        self.stat_vars["taumoeba"].set("YES ✓" if taumoeba_ok else "not yet")
        self.stat_vars["beetles"].set(
            f"{len(grace.beetles_deployed)}/4 deployed"
        )
        self.stat_vars["transmitted"].set(f"{transmitted}/4 probes")
        self.stat_vars["sun"].set(f"{sim.astrophage_mgr.sun_brightness:.3f}")
        self.stat_vars["astrophage"].set(
            f"{sim.grid.astrophage_coverage():.1%}"
        )
        self.stat_vars["score"].set(f"{sim.mission_score:.0f}")

        # ── grid ─────────────────────────────────────────────────
        self.ax_grid.cla()
        self.ax_grid.set_facecolor("#050510")
        self.ax_grid.set_title(
            f"Tau Ceti Region  —  Turn {sim.turn}",
            color="#aaaaff", fontsize=8, pad=3
        )
        self.ax_grid.tick_params(
            left=False, bottom=False,
            labelleft=False, labelbottom=False
        )

        arr = np.array([
            [CELL_COLOURS.get(sim.grid.cells[y][x].cell_type, 0)
             for x in range(sim.grid.width)]
            for y in range(sim.grid.height)
        ], dtype=int)

        self.ax_grid.imshow(
            arr, cmap=CMAP, norm=BNORM,
            origin="upper", interpolation="nearest"
        )

        # agents
        if grace.alive:
            self.ax_grid.plot(
                grace.x, grace.y, "w*",
                markersize=12, zorder=6, label="Grace"
            )
        if rocky.alive:
            self.ax_grid.plot(
                rocky.x, rocky.y, "y^",
                markersize=9, zorder=5, label="Rocky"
            )
        for b in sim.beetle_probes:
            if b.alive and not b.transmitted:
                self.ax_grid.plot(
                    b.x, b.y, "g>", markersize=6, zorder=4
                )

        self.ax_grid.legend(
            loc="lower right", fontsize=6,
            facecolor="#0d0d2b", edgecolor="#333366",
            labelcolor="white"
        )
        self.canvas_grid.draw()

        # ── event log (printed to terminal only) ──────────────────
        if sim.event_log:
            last = sim.event_log[-1]
            # Print latest event to the terminal that launched the GUI.
            print(last)

        # ── status bar ───────────────────────────────────────────
        self.status_bar.config(
            text=f"  Turn {sim.turn}/{MAX_TURNS}  |  "
                 f"Knowledge: {grace.knowledge_score:.0f}  |  "
                 f"{sim.astrophage_mgr.earth_status()}"
        )

    # ─────────────────────────────────────────
    #  FINISH
    # ─────────────────────────────────────────
    def _finish(self):
        self._done  = True
        result      = self.sim._compile_result()
        self.result = result.to_dict()

        # Flash result on status bar
        outcome_colour = {
            "success":    "#69ff47",
            "partial":    "#ffe57f",
            "failure":    "#ff4444",
            "incomplete": "#aaaaaa",
        }.get(result.outcome, "#ffffff")

        self.status_bar.config(
            text=f"  ✓  Simulation {self.run_number} complete  |  "
                 f"Outcome: {result.outcome.upper()}  |  "
                 f"Score: {result.mission_score:.0f}",
            fg=outcome_colour
        )

        # Show "Next / Done" dialog inside tkinter (not blocking messagebox)
        self._show_end_dialog(result)

    def _show_end_dialog(self, result):
        """Show a non-blocking end-of-run dialog at the bottom."""
        dialog = tk.Frame(self.root, bg="#0d0d2b", relief="ridge", bd=2)
        dialog.place(relx=0.5, rely=0.5, anchor="center")

        outcome_text = result.outcome.upper()
        colour = {
            "SUCCESS":    "#69ff47",
            "PARTIAL":    "#ffe57f",
            "FAILURE":    "#ff4444",
            "INCOMPLETE": "#aaaaaa",
        }.get(outcome_text, "#ffffff")

        tk.Label(
            dialog,
            text=f"  SIMULATION {self.run_number} COMPLETE  ",
            font=("Courier New", 13, "bold"),
            fg="#00e5ff", bg="#0d0d2b"
        ).pack(pady=(12, 4))

        tk.Label(
            dialog,
            text=f"Outcome: {outcome_text}",
            font=("Courier New", 11, "bold"),
            fg=colour, bg="#0d0d2b"
        ).pack()

        tk.Label(
            dialog,
            text=(
                f"Score: {result.mission_score:.0f}   |   "
                f"Knowledge: {result.final_knowledge:.0f}   |   "
                f"Turns: {result.turns_survived}"
            ),
            font=("Courier New", 9),
            fg="#aaaaff", bg="#0d0d2b"
        ).pack(pady=4)

        btn_frame = tk.Frame(dialog, bg="#0d0d2b")
        btn_frame.pack(pady=(8, 14))

        if self.run_number < MAX_RUNS:
            next_text = f"▶  Next Simulation ({self.run_number + 1}/{MAX_RUNS})"
        else:
            next_text = "📊  Show Final Graphs"

        tk.Button(
            btn_frame,
            text=next_text,
            font=("Courier New", 10, "bold"),
            fg="#050510", bg="#00e5ff",
            activebackground="#80deea",
            relief="flat", bd=0, padx=16, pady=6,
            cursor="hand2",
            command=self._proceed
        ).pack(side="left", padx=6)

        tk.Button(
            btn_frame,
            text="▶  Run Remaining",
            font=("Courier New", 10, "bold"),
            fg="#050510", bg="#69ff47",
            activebackground="#a5d6a7",
            relief="flat", bd=0, padx=12, pady=6,
            cursor="hand2",
            command=self._run_remaining
        ).pack(side="left", padx=6)

    def _proceed(self):
        self.root.destroy()
        self.on_close(self.result, proceed=True)

    def _run_remaining(self):
        # signal orchestrator to run remaining simulations headless
        self.root.destroy()
        self.on_close(self.result, proceed="batch")

    def _stop(self):
        self.root.destroy()
        self.on_close(self.result, proceed=False)

    def _on_window_close(self):
        self.root.destroy()
        self.on_close(self.result, proceed=False)


# ══════════════════════════════════════════════════════════════════
#  GRAPH WINDOW
# ══════════════════════════════════════════════════════════════════
class GraphWindow:
    """Shows final analysis graphs after all 20 simulations."""

    def __init__(self, results: list[dict]):
        self.results = results
        self.root = tk.Tk()
        self.root.title("📊  Project Hail Mary — Final Analysis (20 Simulations)")
        self.root.configure(bg="#050510")

        self._build()
        self.root.mainloop()

    def _build(self):
        results = self.results

        # ── header ──────────────────────────────────────────────
        tk.Label(
            self.root,
            text="PROJECT HAIL MARY  ·  BATCH ANALYSIS  ·  20 SIMULATIONS",
            font=("Courier New", 12, "bold"),
            fg="#00e5ff", bg="#050510"
        ).pack(pady=(10, 0))

        # ── summary stats bar ───────────────────────────────────
        outcomes    = [r["outcome"] for r in results]
        success_pct = outcomes.count("success")  / len(results) * 100
        partial_pct = outcomes.count("partial")  / len(results) * 100
        failure_pct = outcomes.count("failure")  / len(results) * 100
        avg_score   = statistics.mean([r["mission_score"] for r in results])
        avg_turns   = statistics.mean([r["turns"] for r in results])
        taumoeba_pct = sum(1 for r in results if r["taumoeba_viable_earth"]) / len(results) * 100

        stats_line = (
            f"  Success: {success_pct:.0f}%   Partial: {partial_pct:.0f}%   "
            f"Failure: {failure_pct:.0f}%   |   "
            f"Avg Score: {avg_score:.0f}   Avg Turns: {avg_turns:.0f}   "
            f"Taumoeba viable: {taumoeba_pct:.0f}%"
        )
        tk.Label(
            self.root, text=stats_line,
            font=("Courier New", 8),
            fg="#aaaaff", bg="#050510"
        ).pack(pady=(2, 6))

        # ── graph selector tabs ──────────────────────────────────
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        graph_defs = [
            ("Knowledge",      self._plot_knowledge),
            ("Mission Score",  self._plot_scores),
            ("Outcomes",       self._plot_outcomes),
            ("Sun Brightness", self._plot_sun),
            ("Beetles",        self._plot_beetles),
            ("All-in-One",     self._plot_combined),
        ]

        for tab_name, plot_fn in graph_defs:
            frame = tk.Frame(notebook, bg="#050510")
            notebook.add(frame, text=f"  {tab_name}  ")

            fig = plt.Figure(figsize=(11, 5.5), facecolor="#050510")
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            plot_fn(fig, results)
            canvas.draw()

    # ─────────────────────────────────────────
    #  INDIVIDUAL PLOTS
    # ─────────────────────────────────────────
    def _style(self, ax, title, xl="", yl=""):
        ax.set_facecolor("#0d0d2b")
        ax.set_title(title, color="#aaaaff", fontsize=9, pad=4)
        ax.set_xlabel(xl, color="gray", fontsize=7)
        ax.set_ylabel(yl, color="gray", fontsize=7)
        ax.tick_params(colors="gray", labelsize=6)
        for sp in ax.spines.values():
            sp.set_edgecolor("#222255")

    def _plot_knowledge(self, fig, results):
        ax = fig.add_subplot(111)
        self._style(ax, "Knowledge Score per Run", "Run #", "Knowledge Score")
        runs   = list(range(1, len(results) + 1))
        scores = [r["knowledge"] for r in results]
        colours = ["#69ff47" if r["taumoeba_viable_earth"] else "#ff6600"
                   for r in results]
        bars = ax.bar(runs, scores, color=colours, alpha=0.85, width=0.7)
        ax.axhline(
            statistics.mean(scores), color="white",
            linestyle="--", linewidth=0.9, label="Mean"
        )
        ax.legend(fontsize=7, labelcolor="white",
                  facecolor="#0d0d2b", edgecolor="#333366")
        # colour legend
        from matplotlib.patches import Patch
        ax.legend(
            handles=[Patch(color="#69ff47", label="Taumoeba viable"),
                     Patch(color="#ff6600", label="Not viable")],
            fontsize=7, labelcolor="white",
            facecolor="#0d0d2b", edgecolor="#333366"
        )

    def _plot_scores(self, fig, results):
        ax = fig.add_subplot(111)
        self._style(ax, "Mission Score Distribution", "Mission Score", "Frequency")
        scores = [r["mission_score"] for r in results]
        ax.hist(scores, bins=10, color="#00e5ff", alpha=0.8,
                edgecolor="white", linewidth=0.5)
        ax.axvline(
            statistics.mean(scores), color="#ff6600",
            linestyle="--", linewidth=1, label=f"Mean: {statistics.mean(scores):.0f}"
        )
        ax.legend(fontsize=7, labelcolor="white",
                  facecolor="#0d0d2b", edgecolor="#333366")

    def _plot_outcomes(self, fig, results):
        ax = fig.add_subplot(111)
        outcome_types  = ["success", "partial", "failure", "incomplete"]
        outcome_counts = [
            [r["outcome"] for r in results].count(o) for o in outcome_types
        ]
        colours_pie = ["#69ff47", "#ffe57f", "#ff4444", "#777777"]
        wedges, texts, autos = ax.pie(
            outcome_counts, labels=outcome_types,
            colors=colours_pie, autopct="%1.0f%%",
            startangle=90,
            textprops={"color": "white", "fontsize": 9},
            wedgeprops={"linewidth": 0.5, "edgecolor": "#050510"}
        )
        for a in autos:
            a.set_fontsize(8)
            a.set_color("#050510")
        ax.set_title("Outcome Distribution (20 runs)",
                     color="#aaaaff", fontsize=9)

    def _plot_sun(self, fig, results):
        ax = fig.add_subplot(111)
        self._style(ax, "Sun Brightness at End of Each Run",
                    "Run #", "Brightness (1.0 = normal)")
        runs = list(range(1, len(results) + 1))
        sun  = [r["sun_brightness"] for r in results]
        ax.bar(runs, sun, color="#fff176", alpha=0.85, width=0.7)
        ax.axhline(0.7, color="#ff4444", linestyle="--",
                   linewidth=0.9, label="Critical threshold (0.7)")
        ax.axhline(statistics.mean(sun), color="white",
                   linestyle=":", linewidth=0.8, label="Mean")
        ax.set_ylim(0, 1.05)
        ax.legend(fontsize=7, labelcolor="white",
                  facecolor="#0d0d2b", edgecolor="#333366")

    def _plot_beetles(self, fig, results):
        ax = fig.add_subplot(111)
        self._style(ax, "Beetles Deployed vs Knowledge Score",
                    "Knowledge Score", "Beetles Deployed")
        knowledge  = [r["knowledge"] for r in results]
        beetles    = [r["beetles_deployed"] for r in results]
        m_scores   = [r["mission_score"] for r in results]
        sc = ax.scatter(
            knowledge, beetles,
            c=m_scores, cmap="plasma",
            alpha=0.85, s=80, edgecolors="white", linewidths=0.4
        )
        fig.colorbar(sc, ax=ax, label="Mission Score",
                     shrink=0.8).ax.yaxis.label.set_color("gray")
        ax.set_yticks([0, 1, 2, 3, 4])

    def _plot_combined(self, fig, results):
        """2x3 combined overview."""
        fig.suptitle(
            "Full Run Analysis — 20 Simulations",
            color="white", fontsize=10
        )
        runs  = list(range(1, len(results) + 1))
        turns = [r["turns"]          for r in results]
        know  = [r["knowledge"]       for r in results]
        score = [r["mission_score"]   for r in results]
        sun   = [r["sun_brightness"]  for r in results]
        beet  = [r["beetles_deployed"] for r in results]
        exps  = [r["experiments_run"] for r in results]

        specs = [
            (231, "Knowledge",        know,  "#ffe57f", "bar"),
            (232, "Mission Score",    score, "#00e5ff", "line"),
            (233, "Turns Survived",   turns, "#ff6600", "line"),
            (234, "Sun Brightness",   sun,   "#fff176", "bar"),
            (235, "Beetles Deployed", beet,  "#80deea", "bar"),
            (236, "Experiments Run",  exps,  "#ce93d8", "bar"),
        ]
        for pos, title, data, colour, kind in specs:
            ax = fig.add_subplot(pos)
            self._style(ax, title, "Run #")
            if kind == "bar":
                ax.bar(runs, data, color=colour, alpha=0.8, width=0.7)
                ax.axhline(statistics.mean(data), color="white",
                           linestyle="--", linewidth=0.7)
            else:
                ax.plot(runs, data, color=colour,
                        marker="o", markersize=3, linewidth=1.2)
                ax.fill_between(runs, data, alpha=0.2, color=colour)

        fig.tight_layout(rect=[0, 0, 1, 0.95])


# ══════════════════════════════════════════════════════════════════
#  ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════
class HailMaryOrchestrator:
    """
    Controls the full flow:
    1. Run simulations one by one (up to 20)
    2. After each, ask user to continue
    3. After 20 (or when user stops), show graphs
    """

    def __init__(self):
        self.all_results: list[dict] = []
        self.current_run = 1
        self.base_seed   = random.randint(0, 999)

    def start(self):
        self._show_welcome()

    def _show_welcome(self):
        """Welcome splash screen."""
        root = tk.Tk()
        root.title("Project Hail Mary")
        root.configure(bg="#050510")
        root.resizable(False, False)

        tk.Label(
            root,
            text="\n  🚀  PROJECT HAIL MARY\n  Multi-Agent Simulation\n",
            font=("Courier New", 18, "bold"),
            fg="#00e5ff", bg="#050510"
        ).pack(padx=40)

        tk.Label(
            root,
            text=(
                "  Each simulation runs for 300 turns.\n"
                "  After each run you can continue to the next,\n"
                "  or stop and view analysis graphs.\n"
                "  Graphs appear automatically after 20 runs.\n"
            ),
            font=("Courier New", 9),
            fg="#7777aa", bg="#050510",
            justify="left"
        ).pack()

        tk.Button(
            root,
            text="  ▶  Start Simulation 1  ",
            font=("Courier New", 11, "bold"),
            fg="#050510", bg="#00e5ff",
            activebackground="#80deea",
            relief="flat", bd=0, padx=20, pady=10,
            cursor="hand2",
            command=lambda: [root.destroy(), self._run_next()]
        ).pack(pady=20)

        root.mainloop()

    def _run_next(self):
        seed = self.base_seed + self.current_run
        SimWindow(
            run_number=self.current_run,
            seed=seed,
            on_close_callback=self._on_sim_done
        )

    def _on_sim_done(self, result, proceed):
        if result:
            self.all_results.append(result)

        # If user chose to run remaining simulations in batch
        if proceed == "batch":
            # Run remaining runs headless
            for i in range(self.current_run + 1, MAX_RUNS + 1):
                seed = self.base_seed + i
                print(f"Running headless simulation {i}/{MAX_RUNS} (seed={seed})")
                sim = Simulation(seed=seed, verbose=True)
                res = sim.run()
                self.all_results.append(res.to_dict())
            self.current_run = MAX_RUNS
            if self.all_results:
                self._ask_graphs()
            return

        if not proceed or self.current_run >= MAX_RUNS:
            # Show graphs if we have at least 1 result
            if self.all_results:
                self._ask_graphs()
            return

        self.current_run += 1
        self._run_next()

    def _ask_graphs(self):
        """Ask user which graphs to show, then open GraphWindow."""
        n = len(self.all_results)
        self._print_terminal_summary()

        root = tk.Tk()
        root.title("View Results")
        root.configure(bg="#050510")
        root.resizable(False, False)

        tk.Label(
            root,
            text=f"\n  ✓  {n} simulation{'s' if n > 1 else ''} completed!\n",
            font=("Courier New", 13, "bold"),
            fg="#69ff47", bg="#050510"
        ).pack(padx=40)

        # Quick stats
        outcomes = [r["outcome"] for r in self.all_results]
        avg_score = statistics.mean([r["mission_score"] for r in self.all_results])
        avg_know  = statistics.mean([r["knowledge"]     for r in self.all_results])

        tk.Label(
            root,
            text=(
                f"  Success: {outcomes.count('success')}   "
                f"Partial: {outcomes.count('partial')}   "
                f"Failure: {outcomes.count('failure')}\n"
                f"  Avg Mission Score: {avg_score:.0f}   "
                f"Avg Knowledge: {avg_know:.0f}\n"
            ),
            font=("Courier New", 9),
            fg="#aaaaff", bg="#050510",
            justify="left"
        ).pack()

        tk.Label(
            root,
            text="  What would you like to do?\n",
            font=("Courier New", 9),
            fg="#555588", bg="#050510"
        ).pack()

        btn_frame = tk.Frame(root, bg="#050510")
        btn_frame.pack(pady=(0, 20))

        tk.Button(
            btn_frame,
            text="📊  Open Analysis Graphs",
            font=("Courier New", 10, "bold"),
            fg="#050510", bg="#69ff47",
            activebackground="#a5d6a7",
            relief="flat", bd=0, padx=16, pady=8,
            cursor="hand2",
            command=lambda: [root.destroy(), self._open_graphs()]
        ).pack(pady=4, fill="x")

        tk.Button(
            btn_frame,
            text="💾  Save Results (JSON)",
            font=("Courier New", 10),
            fg="#050510", bg="#ffe57f",
            activebackground="#fff9c4",
            relief="flat", bd=0, padx=16, pady=8,
            cursor="hand2",
            command=lambda: self._save_results(root)
        ).pack(pady=4, fill="x")

        tk.Button(
            btn_frame,
            text="✕  Exit",
            font=("Courier New", 9),
            fg="#ff4444", bg="#1a0a0a",
            activebackground="#330000",
            relief="flat", bd=0, padx=16, pady=6,
            cursor="hand2",
            command=root.destroy
        ).pack(pady=4, fill="x")

        root.mainloop()

    def _open_graphs(self):
        GraphWindow(self.all_results)

    def _print_terminal_summary(self):
        results = self.all_results
        n = len(results)
        outcomes = [r["outcome"] for r in results]
        turns   = [r["turns"] for r in results]
        know    = [r["knowledge"] for r in results]
        score   = [r["mission_score"] for r in results]
        beetles = [r["beetles_deployed"] for r in results]
        transmitted = sum(1 for r in results if r["data_transmitted"] > 0 or r.get("taumoeba_viable_earth"))

        print("\n=== PROJECT HAIL MARY SUMMARY (20 SIMULATIONS) ===")
        print(f"Total simulations : {n}")
        print(f"Successes         : {outcomes.count('success')}" )
        print(f"Partial outcomes  : {outcomes.count('partial')}" )
        print(f"Failures          : {outcomes.count('failure')}" )
        print(f"Incomplete        : {outcomes.count('incomplete')}" )
        print("---")
        print(f"Avg turns         : {statistics.mean(turns):.1f}")
        print(f"Avg knowledge     : {statistics.mean(know):.1f}")
        print(f"Avg mission score : {statistics.mean(score):.1f}")
        print(f"Avg beetles used  : {statistics.mean(beetles):.2f}")
        print(f"Transmitted runs  : {transmitted}/{n}")
        print("===========================================\n")

    def _save_results(self, parent_root):
        import tkinter.filedialog as fd
        path = fd.asksaveasfilename(
            parent=parent_root,
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="hail_mary_results.json",
            title="Save Results"
        )
        if path:
            with open(path, "w") as f:
                json.dump(self.all_results, f, indent=2)
            messagebox.showinfo(
                "Saved", f"Results saved to:\n{path}", parent=parent_root
            )


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    orch = HailMaryOrchestrator()
    orch.start()
