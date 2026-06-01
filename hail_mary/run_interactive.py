"""
run_interactive.py  —  Project Hail Mary Interactive Runner
============================================================
- Ek simulation window khulti hai (70 turns animated)
- Grace ship se nikti hai, step by step Adrian ki taraf aati hai
- Rocky Blip-A ke aas paas wander karta hai
- Dono legends dikhte hain (agents + cell types)
- Knowledge AND Health dono live charts
- 20 ke baad seedha graphs — beech mein nahi poochta
- Har run ke baad sirf: "Next" ya "Stop" dialog

Run:  python run_interactive.py
"""

import sys, os, json, random, statistics
import tkinter as tk

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simulation import Simulation
from grid import CellType

# ─────────────────────────────────────────────────────────────────────────────
#  COLOURS
# ─────────────────────────────────────────────────────────────────────────────
CELL_IDX = {
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
CELL_HEX = [
    "#050510",  # EMPTY      – deep space
    "#1b5e20",  # ADRIAN     – green planet
    "#e65100",  # ASTROPHAGE – orange threat
    "#b71c1c",  # PETROVA    – deep red dense
    "#0d47a1",  # HAIL_MARY  – blue ship
    "#6a1b9a",  # BLIP_A     – purple alien
    "#00838f",  # TUNNEL     – cyan connector
    "#f57f17",  # RADIATION  – amber hazard
    "#4e342e",  # DEBRIS     – brown field
]
CELL_NAMES = [
    "Empty Space", "Planet Adrian", "Astrophage Cloud",
    "Petrova Line", "Hail Mary", "Blip-A",
    "Xenonite Tunnel", "Radiation Zone", "Debris Field"
]

BG     = "#05050f"
PANEL  = "#0c0c20"
BORDER = "#1a1a38"
ACCENT = "#00e5ff"
GREEN  = "#69ff47"
ORANGE = "#ff6600"
YELLOW = "#ffd600"
WHITE  = "#dde8ff"
RED    = "#ff1744"
PURPLE = "#ce93d8"
PINK   = "#ff80ab"

MAX_TURNS  = 70
TOTAL_RUNS = 20
TICK_MS    = 180   # ms between frames


# ─────────────────────────────────────────────────────────────────────────────
#  GRID → numpy
# ─────────────────────────────────────────────────────────────────────────────
def grid_arr(sim):
    g = sim.grid
    return np.array([
        [CELL_IDX.get(g.cells[y][x].cell_type, 0) for x in range(g.width)]
        for y in range(g.height)
    ], dtype=np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
#  SIMULATION WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class SimWindow:

    def __init__(self, sim: Simulation, run_num: int):
        self.sim     = sim
        self.run_num = run_num
        self.done    = False
        self.result  = None
        self.cmap    = mcolors.ListedColormap(CELL_HEX)
        self.bnorm   = mcolors.BoundaryNorm(range(len(CELL_HEX)+1), self.cmap.N)
        self._build()

    # ── build window ─────────────────────────────────────────────────────────
    def _build(self):
        self.root = tk.Tk()
        self.root.title(
            f"Project Hail Mary  —  Simulation {self.run_num}/{TOTAL_RUNS}")
        self.root.configure(bg=BG)
        self.root.geometry("1340x760")
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        # ── figure: 2 rows × 4 cols ──
        self.fig = Figure(figsize=(17, 8.8), facecolor=BG)
        self.fig.suptitle(
            f"PROJECT HAIL MARY  ·  Run {self.run_num}/{TOTAL_RUNS}"
            f"  ·  {MAX_TURNS} Turns",
            color=WHITE, fontsize=12, fontweight="bold",
            fontfamily="monospace"
        )

        gs = gridspec.GridSpec(
            2, 4, figure=self.fig,
            left=0.03, right=0.98,
            top=0.92, bottom=0.06,
            hspace=0.42, wspace=0.30
        )

        # large grid spans both rows, first 2 cols
        self.ax_grid  = self.fig.add_subplot(gs[:, :2])
        self.ax_know  = self.fig.add_subplot(gs[0, 2])   # knowledge
        self.ax_hp    = self.fig.add_subplot(gs[0, 3])   # health
        self.ax_astr  = self.fig.add_subplot(gs[1, 2])   # astrophage/sun
        self.ax_stat  = self.fig.add_subplot(gs[1, 3])   # status text

        for ax in (self.ax_grid, self.ax_know, self.ax_hp,
                   self.ax_astr, self.ax_stat):
            ax.set_facecolor(PANEL)
            for sp in ax.spines.values():
                sp.set_edgecolor(BORDER)

        # ── embed in tk ──
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Grace & Rocky health history (we track ourselves)
        self._grace_hp_hist  = []
        self._rocky_hp_hist  = []

        self._draw()
        self.root.after(TICK_MS, self._tick)

    # ── animation tick ───────────────────────────────────────────────────────
    def _tick(self):
        if self.done:
            return
        ended = self.sim.step_once()

        # Record HP
        self._grace_hp_hist.append(self.sim.grace.health)
        self._rocky_hp_hist.append(self.sim.rocky.health)

        self._draw()

        if ended or self.sim.turn >= MAX_TURNS:
            self.done   = True
            self.result = self.sim._compile_result()
            self._finish_label()
            return

        self.root.after(TICK_MS, self._tick)

    # ── draw one frame ───────────────────────────────────────────────────────
    def _draw(self):
        sim = self.sim
        g   = sim.grace
        r   = sim.rocky
        am  = sim.astrophage_mgr

        # ══ GRID ══════════════════════════════════════════════════════════════
        self.ax_grid.cla()
        self.ax_grid.set_facecolor(PANEL)
        for sp in self.ax_grid.spines.values():
            sp.set_edgecolor(BORDER)

        self.ax_grid.imshow(
            grid_arr(sim), cmap=self.cmap, norm=self.bnorm,
            origin="upper", interpolation="nearest"
        )

        # Agent markers
        if g.alive:
            self.ax_grid.plot(g.x, g.y, "w*",  ms=15, zorder=7)
        if r.alive:
            self.ax_grid.plot(r.x, r.y, color=PURPLE,
                              marker="^", ms=11, zorder=7)
        for b in sim.beetle_probes:
            if b.alive and not b.transmitted:
                self.ax_grid.plot(b.x, b.y, color=GREEN,
                                  marker=">", ms=7, zorder=6)

        # ── LEGEND 1: agents ──
        agent_patches = [
            mpatches.Patch(color="white",  label="★ Grace (Dr. Ryland)"),
            mpatches.Patch(color=PURPLE,   label="▲ Rocky (Eridian)"),
            mpatches.Patch(color=GREEN,    label="► Beetle Probe"),
        ]
        leg1 = self.ax_grid.legend(
            handles=agent_patches, loc="upper left",
            fontsize=6.5, facecolor="#0a0a1c", edgecolor="#333",
            labelcolor=WHITE, title="Agents",
            title_fontsize=6.5,
        )
        leg1.get_title().set_color(ACCENT)
        self.ax_grid.add_artist(leg1)

        # ── LEGEND 2: cell types ──
        cell_patches = [
            mpatches.Patch(color=CELL_HEX[i], label=CELL_NAMES[i])
            for i in range(len(CELL_HEX))
        ]
        leg2 = self.ax_grid.legend(
            handles=cell_patches, loc="lower right",
            fontsize=5.8, facecolor="#0a0a1c", edgecolor="#333",
            labelcolor=WHITE, title="Cell Types",
            title_fontsize=6,
        )
        leg2.get_title().set_color(YELLOW)

        self.ax_grid.set_title(
            f"Turn {sim.turn}/{MAX_TURNS}   "
            f"Phase: {g.phase.upper()}",
            color=ACCENT, fontsize=9, pad=4, fontfamily="monospace"
        )
        self.ax_grid.set_xticks([]); self.ax_grid.set_yticks([])

        # ══ KNOWLEDGE CHART ═══════════════════════════════════════════════════
        self.ax_know.cla()
        self.ax_know.set_facecolor(PANEL)
        for sp in self.ax_know.spines.values():
            sp.set_edgecolor(BORDER)
        if sim.knowledge_history:
            xs = range(len(sim.knowledge_history))
            self.ax_know.plot(sim.knowledge_history, color=YELLOW, lw=1.8)
            self.ax_know.fill_between(xs, sim.knowledge_history,
                                       alpha=0.18, color=YELLOW)
            self.ax_know.set_ylabel("Score", color="#666", fontsize=7)
        self.ax_know.set_title(
            f"Knowledge  [{g.knowledge_score:.0f}]",
            color=YELLOW, fontsize=8, pad=3, fontfamily="monospace"
        )
        self.ax_know.tick_params(colors="#555", labelsize=6)

        # ══ HEALTH CHART ══════════════════════════════════════════════════════
        self.ax_hp.cla()
        self.ax_hp.set_facecolor(PANEL)
        for sp in self.ax_hp.spines.values():
            sp.set_edgecolor(BORDER)
        if self._grace_hp_hist:
            xs = range(len(self._grace_hp_hist))
            gcol = GREEN if g.health > 60 else (YELLOW if g.health > 30 else RED)
            self.ax_hp.plot(self._grace_hp_hist,
                            color=gcol, lw=1.6, label=f"Grace {g.health:.0f}")
            self.ax_hp.fill_between(xs, self._grace_hp_hist,
                                     alpha=0.14, color=gcol)
        if self._rocky_hp_hist:
            self.ax_hp.plot(self._rocky_hp_hist,
                            color=PURPLE, lw=1.4, ls="--",
                            label=f"Rocky {r.health:.0f}")
        self.ax_hp.set_ylim(0, 130)
        self.ax_hp.axhline(100, color="#333", lw=0.6, ls=":")
        if self._grace_hp_hist:
            self.ax_hp.legend(fontsize=6, facecolor=PANEL,
                               edgecolor=BORDER, labelcolor=WHITE)
        self.ax_hp.set_title("Health (Grace / Rocky)",
                              color=GREEN, fontsize=8, pad=3,
                              fontfamily="monospace")
        self.ax_hp.tick_params(colors="#555", labelsize=6)

        # ══ ASTROPHAGE / SUN ══════════════════════════════════════════════════
        self.ax_astr.cla()
        self.ax_astr.set_facecolor(PANEL)
        for sp in self.ax_astr.spines.values():
            sp.set_edgecolor(BORDER)
        if am.coverage_history:
            self.ax_astr.plot(am.coverage_history,
                               color=ORANGE, lw=1.5, label="Astrophage %")
            self.ax_astr.plot(am.brightness_history,
                               color=YELLOW, lw=1.5, ls="--", label="☀ Sun")
            self.ax_astr.legend(fontsize=6, facecolor=PANEL,
                                  edgecolor=BORDER, labelcolor=WHITE)
        self.ax_astr.set_title("Astrophage / Sun Brightness",
                                color=ORANGE, fontsize=8, pad=3,
                                fontfamily="monospace")
        self.ax_astr.tick_params(colors="#555", labelsize=6)

        # ══ STATUS TEXT ═══════════════════════════════════════════════════════
        self.ax_stat.cla()
        self.ax_stat.set_facecolor(PANEL)
        for sp in self.ax_stat.spines.values():
            sp.set_edgecolor(BORDER)
        self.ax_stat.set_xticks([]); self.ax_stat.set_yticks([])
        self.ax_stat.set_title("Mission Status",
                                color=WHITE, fontsize=8, pad=3)

        tv  = sim.taumoeba_lab.has_viable_earth_strain()
        ev  = sim.taumoeba_lab.has_viable_erid_strain()
        tx  = sum(1 for b in sim.beetle_probes if b.transmitted)
        sun = am.sun_brightness * 100

        rows = [
            ("GRACE",       "",                              WHITE),
            (" Phase",      g.phase,                         ACCENT),
            (" HP",         f"{g.health:.0f}/{g.max_health:.0f}",
                            GREEN if g.health>60 else RED),
            (" Energy",     f"{g.energy:.0f}",               ACCENT),
            (" Knowledge",  f"{g.knowledge_score:.0f}",      YELLOW),
            (" Samples",    f"A:{g.astrophage_samples} T:{g.taumoeba_samples}", WHITE),
            (" Flashbacks", f"{len(g.flashbacks_triggered)}/5", PINK),
            ("",            "",                              WHITE),
            ("ROCKY",       "",                              WHITE),
            (" HP",         f"{r.health:.0f}",               PURPLE),
            (" Energy",     f"{r.energy:.0f}",               PURPLE),
            (" Translate",  f"{r.translation_level}/10",     PURPLE),
            (" Cooperate",  f"{r.cooperation_score:.2f}",    PURPLE),
            ("",            "",                              WHITE),
            ("MISSION",     "",                              WHITE),
            (" Earth Strain", "YES ✓" if tv else "—",       GREEN if tv else "#555"),
            (" Erid Strain",  "YES ✓" if ev else "—",       GREEN if ev else "#555"),
            (" Beetles",    f"{len(g.beetles_deployed)}/4",  YELLOW),
            (" Transmitted",f"{tx} probe(s)",                GREEN if tx else "#555"),
            (" Sun",        f"{sun:.1f}%",                   YELLOW if sun>70 else RED),
            (" Score",      f"{sim.mission_score:.0f}",      GREEN),
        ]

        y0 = 0.97; step = 0.044
        for i, (lbl, val, col) in enumerate(rows):
            yp = y0 - i * step
            if yp < 0.01:
                break
            if not lbl.strip():
                continue
            # section headers (no leading space)
            if not lbl.startswith(" "):
                self.ax_stat.text(
                    0.03, yp, lbl,
                    transform=self.ax_stat.transAxes,
                    color=ACCENT, fontsize=7, fontfamily="monospace",
                    va="top", fontweight="bold"
                )
            else:
                self.ax_stat.text(
                    0.04, yp, lbl.strip() + ":",
                    transform=self.ax_stat.transAxes,
                    color="#888", fontsize=6.5,
                    fontfamily="monospace", va="top"
                )
                self.ax_stat.text(
                    0.52, yp, val,
                    transform=self.ax_stat.transAxes,
                    color=col, fontsize=6.5,
                    fontfamily="monospace", va="top", fontweight="bold"
                )

        self.canvas.draw_idle()

    # ── finish label ─────────────────────────────────────────────────────────
    def _finish_label(self):
        tv  = self.sim.taumoeba_lab.has_viable_earth_strain()
        txt = "MISSION SUCCESS ✓" if tv else "INCOMPLETE"
        col = GREEN if tv else ORANGE
        self.ax_grid.set_title(
            f"RUN {self.run_num} COMPLETE  —  {txt}",
            color=col, fontsize=10, fontfamily="monospace", pad=5
        )
        self.canvas.draw_idle()

        lbl = tk.Label(
            self.root,
            text=f"  Simulation {self.run_num} done — close this window to continue  ",
            bg="#110022", fg=WHITE,
            font=("Courier New", 11, "bold")
        )
        lbl.place(relx=0.5, rely=0.974, anchor="center")

    # ── close ────────────────────────────────────────────────────────────────
    def _close(self):
        if not self.done:
            self.done   = True
            self.result = self.sim._compile_result()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        return self.result


# ─────────────────────────────────────────────────────────────────────────────
#  BETWEEN-RUN DIALOG  (no graph prompt — graphs always at end)
# ─────────────────────────────────────────────────────────────────────────────
def ask_next(run_num: int, result, total_runs: int) -> bool:
    outcome   = (result.outcome if result else "unknown").upper()
    score     = result.mission_score if result else 0
    turns     = result.turns_survived if result else 0
    tviable   = result.taumoeba_viable if result else False
    remaining = total_runs - run_num

    root = tk.Tk()
    root.title("Hail Mary — Next?")
    root.configure(bg=BG)
    root.resizable(False, False)
    root.update_idletasks()
    w, h = 420, 260
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    tk.Label(root,
             text=f"✦  Run {run_num}/{total_runs} Complete  ✦",
             font=("Courier New", 13, "bold"),
             fg=ACCENT, bg=BG).pack(pady=(18, 5))

    col = GREEN if outcome == "SUCCESS" else ORANGE
    tk.Label(root, text=f"Outcome :  {outcome}",
             font=("Courier New", 11, "bold"), fg=col, bg=BG).pack()
    tk.Label(root,
             text=f"Turns : {turns}     Score : {score:.0f}",
             font=("Courier New", 10), fg=WHITE, bg=BG).pack(pady=2)
    tk.Label(root,
             text=f"Earth Strain : {'YES ✓' if tviable else 'No'}",
             font=("Courier New", 10),
             fg=GREEN if tviable else "#666", bg=BG).pack(pady=(0, 8))

    if remaining > 0:
        tk.Label(root,
                 text=f"{remaining} simulation(s) remaining until analysis graphs",
                 font=("Courier New", 8), fg="#445566", bg=BG).pack()

    choice = {"go": False}
    bf = tk.Frame(root, bg=BG)
    bf.pack(pady=14)

    def on_next():
        choice["go"] = True; root.destroy()
    def on_stop():
        choice["go"] = False; root.destroy()

    if remaining > 0:
        tk.Button(bf,
                  text=f"▶  Run Simulation {run_num+1}",
                  command=on_next,
                  font=("Courier New", 10, "bold"),
                  bg="#0d2a6e", fg="white",
                  activebackground="#1565c0",
                  relief="flat", padx=16, pady=7,
                  cursor="hand2").grid(row=0, column=0, padx=8)
        tk.Button(bf,
                  text="✕  Stop Early",
                  command=on_stop,
                  font=("Courier New", 10),
                  bg="#1a0000", fg="#ff6666",
                  activebackground="#300000",
                  relief="flat", padx=16, pady=7,
                  cursor="hand2").grid(row=0, column=1, padx=8)
    else:
        # Last run — auto-open graphs (button just closes dialog)
        tk.Label(root,
                 text="All 20 runs complete! Opening analysis graphs...",
                 font=("Courier New", 9, "bold"),
                 fg=YELLOW, bg=BG).pack()
        tk.Button(bf,
                  text="📊  Open Analysis Graphs",
                  command=on_next,
                  font=("Courier New", 11, "bold"),
                  bg="#1b5e20", fg="white",
                  activebackground="#2e7d32",
                  relief="flat", padx=22, pady=9,
                  cursor="hand2").grid(row=0, column=0)

    root.mainloop()
    return choice["go"]


# ─────────────────────────────────────────────────────────────────────────────
#  ANALYSIS GRAPHS  (opens after all 20 done)
# ─────────────────────────────────────────────────────────────────────────────
def show_graphs(results: list[dict]):
    n   = len(results)
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.patch.set_facecolor(BG)
    fig.suptitle(
        f"Project Hail Mary — Full Analysis  ({n} Simulations)",
        color=WHITE, fontsize=13, fontweight="bold",
        fontfamily="monospace"
    )

    def style(ax, title, xl="", yl=""):
        ax.set_facecolor(PANEL)
        ax.set_title(title, color=ACCENT, fontsize=9, pad=4,
                     fontfamily="monospace")
        ax.set_xlabel(xl, color="#666", fontsize=7)
        ax.set_ylabel(yl, color="#666", fontsize=7)
        ax.tick_params(colors="#555", labelsize=7)
        for sp in ax.spines.values():
            sp.set_edgecolor(BORDER)

    turns     = [r["turns"]         for r in results]
    knowledge = [r["knowledge"]     for r in results]
    scores    = [r["mission_score"] for r in results]
    beetles   = [r["beetles_deployed"] for r in results]
    sun_b     = [r["sun_brightness"]*100 for r in results]
    outcomes  = [r["outcome"]       for r in results]
    run_ids   = list(range(1, n+1))

    # 1 — knowledge per run (green=taumoeba viable, orange=not)
    ax = axes[0][0]
    cols = [GREEN if r["taumoeba_viable_earth"] else ORANGE for r in results]
    ax.bar(run_ids, knowledge, color=cols, alpha=0.85,
           edgecolor="#222", linewidth=0.4)
    mk = statistics.mean(knowledge)
    ax.axhline(mk, color=WHITE, lw=1, ls="--", label=f"Mean {mk:.0f}")
    ax.legend(fontsize=7, facecolor=PANEL, edgecolor=BORDER, labelcolor=WHITE)
    style(ax, "Knowledge Score per Run", "Run #", "Knowledge")

    # 2 — mission score distribution
    ax = axes[0][1]
    ax.hist(scores, bins=max(4, n//3), color=ACCENT, alpha=0.8,
            edgecolor="#111", linewidth=0.5)
    ms = statistics.mean(scores)
    ax.axvline(ms, color=YELLOW, lw=1.3, ls="--", label=f"Mean {ms:.0f}")
    ax.legend(fontsize=7, facecolor=PANEL, edgecolor=BORDER, labelcolor=WHITE)
    style(ax, "Mission Score Distribution", "Score", "Runs")

    # 3 — turns survived
    ax = axes[0][2]
    ax.plot(run_ids, turns, color=ORANGE, marker="o", ms=5, lw=1.6)
    ax.fill_between(run_ids, turns, alpha=0.15, color=ORANGE)
    mt = statistics.mean(turns)
    ax.axhline(mt, color=WHITE, lw=0.9, ls="--", label=f"Mean {mt:.1f}")
    ax.legend(fontsize=7, facecolor=PANEL, edgecolor=BORDER, labelcolor=WHITE)
    style(ax, "Turns Survived", "Run #", "Turns")

    # 4 — outcome pie
    ax = axes[1][0]
    otypes  = ["success","partial","failure","incomplete"]
    ocounts = [outcomes.count(o) for o in otypes]
    ocols   = [GREEN, YELLOW, RED, "#555"]
    data    = [(c,cl,lb) for c,cl,lb in zip(ocounts,ocols,otypes) if c>0]
    if data:
        cs,cls,lbs = zip(*data)
        _,_,autos = ax.pie(cs, labels=lbs, colors=cls,
                           autopct="%1.0f%%", startangle=90,
                           textprops={"color":WHITE,"fontsize":8})
        for at in autos: at.set_color("#111"); at.set_fontsize(7)
    ax.set_title("Outcome Distribution", color=ACCENT,
                 fontsize=9, fontfamily="monospace")
    ax.set_facecolor(PANEL)

    # 5 — knowledge vs beetles scatter
    ax = axes[1][1]
    sc = ax.scatter(knowledge, beetles, c=scores, cmap="plasma",
                    alpha=0.85, s=75, edgecolors="#111", linewidths=0.5)
    cb = fig.colorbar(sc, ax=ax)
    cb.ax.tick_params(colors="#777", labelsize=6)
    cb.set_label("Mission Score", color="#777", fontsize=7)
    style(ax, "Knowledge vs Beetles Deployed", "Knowledge", "Beetles")

    # 6 — sun brightness at end
    ax = axes[1][2]
    bcols = [GREEN if s>70 else (YELLOW if s>50 else RED) for s in sun_b]
    ax.bar(run_ids, sun_b, color=bcols, alpha=0.85,
           edgecolor="#222", linewidth=0.4)
    ax.axhline(70, color=RED, lw=1, ls="--", label="Critical 70%")
    ax.set_ylim(0, 108)
    ax.legend(fontsize=7, facecolor=PANEL, edgecolor=BORDER, labelcolor=WHITE)
    style(ax, "Sun Brightness at End (%)", "Run #", "%")

    # footer
    s_rate = sum(1 for r in results if r["outcome"]=="success") / n
    t_rate = sum(1 for r in results if r["taumoeba_viable_earth"]) / n
    fig.text(
        0.5, 0.003,
        f"Success rate: {s_rate:.0%}  |  Taumoeba viable: {t_rate:.0%}  |  "
        f"Avg score: {statistics.mean(scores):.0f}  |  "
        f"Avg turns: {statistics.mean(turns):.1f}  |  "
        f"Avg knowledge: {statistics.mean(knowledge):.0f}",
        ha="center", va="bottom", color="#888",
        fontsize=8, fontfamily="monospace"
    )

    plt.tight_layout()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "analysis_graphs.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    print(f"Graphs saved → {out}")
    plt.show()
    plt.close("all")


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    all_results = []
    base_seed   = random.randint(100, 9999)

    print("="*55)
    print("  PROJECT HAIL MARY — INTERACTIVE RUNNER")
    print(f"  Turns/run : {MAX_TURNS}   Total : {TOTAL_RUNS}")
    print(f"  Seed base : {base_seed}")
    print("="*55)

    for run_num in range(1, TOTAL_RUNS + 1):
        seed = base_seed + run_num
        print(f"\n[Run {run_num}/{TOTAL_RUNS}] seed={seed} — opening window...")

        sim           = Simulation(seed=seed, verbose=False)
        sim.MAX_TURNS = MAX_TURNS

        win    = SimWindow(sim, run_num)
        result = win.run()
        if result is None:
            print("  Window closed early — skipping")
            continue

        d = result.to_dict()
        all_results.append(d)
        print(f"  → {d['outcome'].upper():12s}  "
              f"turns={d['turns']}  "
              f"knowledge={d['knowledge']:.0f}  "
              f"score={d['mission_score']:.0f}")

        # save progress after every run
        jp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "results.json")
        with open(jp, "w") as f:
            json.dump(all_results, f, indent=2)

        # after all 20: show graphs directly (no extra prompt)
        if run_num == TOTAL_RUNS:
            _print_summary(all_results)
            ask_next(run_num, result, TOTAL_RUNS)  # shows "open graphs" btn
            show_graphs(all_results)
            break

        # between runs: just next/stop
        if not ask_next(run_num, result, TOTAL_RUNS):
            print(f"Stopped after {run_num} run(s).")
            if len(all_results) >= 2:
                show_graphs(all_results)
            break

    print("\nDone. results.json saved.")


def _print_summary(results):
    turns     = [r["turns"]         for r in results]
    knowledge = [r["knowledge"]     for r in results]
    scores    = [r["mission_score"] for r in results]
    outcomes  = [r["outcome"]       for r in results]
    print("\n" + "="*45)
    print("  FINAL SUMMARY")
    print("="*45)
    print(f"  Runs         : {len(results)}")
    print(f"  Success      : {outcomes.count('success')}/{len(results)}")
    print(f"  Avg turns    : {statistics.mean(turns):.1f}")
    print(f"  Avg knowledge: {statistics.mean(knowledge):.1f}")
    print(f"  Avg score    : {statistics.mean(scores):.1f}")
    print("="*45)


if __name__ == "__main__":
    main()
