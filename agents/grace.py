"""
agents/grace.py
---------------
Dr. Ryland Grace - central human agent.
Movement is realistic:
  Phase 1 (ABOARD)     : stays on Hail Mary, rests, waits for Rocky comms
  Phase 2 (TRAVELING)  : moves cell by cell toward Adrian, avoiding hazards
  Phase 3 (AT_ADRIAN)  : collects samples, runs experiments
  Phase 4 (RETURNING)  : moves back toward Hail Mary
  Phase 5 (DEPLOYING)  : deploys beetles when knowledge is high enough
"""

import random
from agents.base_agent import Agent
from grid import CellType

# ── Flashbacks ───────────────────────────────────────────────────────────────
FLASHBACKS = [
    {
        "trigger_knowledge": 10,
        "title": "Memory: Eva Stratt",
        "text": "Eva Stratt: 'Dr. Grace, humanity has one last chance. You are that chance.'",
        "effect": "energy_boost", "effect_value": 10.0,
    },
    {
        "trigger_knowledge": 25,
        "title": "Memory: The Hail Mary Launch",
        "text": "The roar of engines. A one-way trip. No fuel for return. You volunteered.",
        "effect": "max_health_boost", "effect_value": 10.0,
    },
    {
        "trigger_knowledge": 45,
        "title": "Memory: Astrophage Threat on Earth",
        "text": "Crops failing. Temperatures dropping. Thirty years until extinction.",
        "effect": "knowledge_boost", "effect_value": 5.0,
    },
    {
        "trigger_knowledge": 65,
        "title": "Memory: You Were a Teacher",
        "text": "Middle-school science. You loved it. Stratt needed your extremophile paper.",
        "effect": "experiment_boost", "effect_value": 0.15,
    },
    {
        "trigger_knowledge": 85,
        "title": "Memory: The Full Mission Brief",
        "text": "Everything floods back. Tau Ceti. Taumoeba. Transmit. Save Earth.",
        "effect": "full_recall", "effect_value": 0.0,
    },
]

# Movement phases
PHASE_ABOARD    = "aboard"
PHASE_TRAVELING = "traveling"
PHASE_AT_ADRIAN = "at_adrian"
PHASE_RETURNING = "returning"
PHASE_IDLE      = "idle"


class Grace(Agent):

    def __init__(self, x: int = 3, y: int = 3, seed: int = None):
        super().__init__("Grace", x, y, health=100.0, energy=100.0)
        self.rng = random.Random(seed)

        # Science
        self.knowledge_score: float = 0.0
        self.astrophage_samples: int = 0
        self.taumoeba_samples: int = 0
        self.experiment_results: list[dict] = []
        self.taumoeba_bred: bool = False
        self.experiment_success_bonus: float = 0.0

        # Flashbacks
        self.flashbacks_triggered: list[str] = []
        self.memory_restored: bool = False

        # Beetles
        self.beetle_names     = ["John", "Paul", "George", "Ringo"]
        self.beetles_deployed: list[str] = []
        self.beetles_available: list[str] = list(self.beetle_names)

        # Location flags
        self.aboard_hail_mary: bool = True
        self.aboard_blip_a:    bool = False

        # Max health
        self.max_health: float = 100.0

        # Movement phase state machine
        self.phase: str = PHASE_ABOARD
        self.turns_aboard: int = 0          # how many turns spent on ship
        self.turns_at_adrian: int = 0
        self.sample_trips: int = 0          # how many round trips done

        # Random wander counter (small random detour before heading to Adrian)
        self._wander_steps: int = 0

    # ── choose_action ────────────────────────────────────────────────────────
    def choose_action(self, grid, simulation) -> str:
        """
        State-machine movement:
          ABOARD      → wait a few turns, rest, receive Rocky knowledge
                        then transition to TRAVELING
          TRAVELING   → move step by step toward Adrian (with small random
                        detours), avoid PETROVA if low energy
          AT_ADRIAN   → collect samples, experiment, then go RETURNING
          RETURNING   → move back toward Hail Mary
          IDLE        → deploy beetles, rest
        """

        cell = grid.get(self.x, self.y)

        # ── always rest if critically low ──
        if self.energy < 12:
            self.rest()
            return "rest"

        # ── phase: ABOARD ────────────────────────────────────────────────
        if self.phase == PHASE_ABOARD:
            self.turns_aboard += 1
            # Stay aboard for a few turns (Rocky comms, prepare)
            wait = 8 if simulation and simulation.rocky_cooperation < 0.6 else 5
            if self.turns_aboard >= wait:
                self.phase = PHASE_TRAVELING
                self._wander_steps = self.rng.randint(2, 5)
                self._log("Leaving Hail Mary — heading to Adrian")
                return "depart"
            self.rest()
            return "rest_aboard"

        # ── phase: TRAVELING ─────────────────────────────────────────────
        if self.phase == PHASE_TRAVELING:
            # Check if we arrived at Adrian
            if cell.cell_type == CellType.ADRIAN:
                self.aboard_hail_mary = False
                self.phase = PHASE_AT_ADRIAN
                self.turns_at_adrian = 0
                self._log("Arrived at Adrian!")
                return "arrived_adrian"

            # Random wander detour at the start of each trip
            if self._wander_steps > 0:
                self._wander_steps -= 1
                self._random_step(grid)
                return "wander"

            # Move toward Adrian
            self._move_toward(grid, *grid.adrian_pos)
            return "travel"

        # ── phase: AT_ADRIAN ─────────────────────────────────────────────
        if self.phase == PHASE_AT_ADRIAN:
            self.turns_at_adrian += 1

            # Collect taumoeba
            if self.taumoeba_samples < 8:
                self.collect_taumoeba(grid)
                return "collect_taumoeba"

            # Collect astrophage
            if self.astrophage_samples < 3:
                self.collect_astrophage(grid)
                return "collect_astrophage"

            # Done collecting — head back
            self.phase = PHASE_RETURNING
            self.sample_trips += 1
            self._log("Samples collected — returning to Hail Mary")
            return "depart_adrian"

        # ── phase: RETURNING ─────────────────────────────────────────────
        if self.phase == PHASE_RETURNING:
            hx, hy = grid.hail_mary_pos
            if abs(self.x - hx) <= 1 and abs(self.y - hy) <= 1:
                # Back at ship
                self.aboard_hail_mary = True
                # Deploy beetle if knowledge high enough
                if self.knowledge_score >= 40 and self.beetles_available:
                    self.deploy_beetle(simulation)
                self.phase = PHASE_IDLE
                self._log("Back at Hail Mary")
                return "returned"
            self._move_toward(grid, hx, hy)
            return "return_travel"

        # ── phase: IDLE ───────────────────────────────────────────────────
        if self.phase == PHASE_IDLE:
            # Deploy remaining beetles
            if self.beetles_available and self.knowledge_score >= 40:
                self.deploy_beetle(simulation)
                return "deploy_beetle"
            # Go again if more samples needed and taumoeba not yet bred
            if not self.taumoeba_bred and self.sample_trips < 6:
                self.phase = PHASE_TRAVELING
                self._wander_steps = self.rng.randint(1, 3)
                return "new_trip"
            self.rest()
            return "idle_rest"

        self.rest()
        return "rest"

    # ── movement helpers ─────────────────────────────────────────────────────
    def _move_toward(self, grid, tx: int, ty: int):
        """Move one step toward (tx, ty), wrapping, avoiding Petrova if tired."""
        dx = tx - self.x
        dy = ty - self.y

        # Wrap shortest path
        if dx >  grid.width  // 2: dx -= grid.width
        if dx < -grid.width  // 2: dx += grid.width
        if dy >  grid.height // 2: dy -= grid.height
        if dy < -grid.height // 2: dy += grid.height

        # Add small random jitter so path is not perfectly straight
        if self.rng.random() < 0.25:
            if abs(dx) >= abs(dy):
                # try moving diagonally via y first
                mdx, mdy = 0, (1 if dy > 0 else -1) if dy != 0 else 0
            else:
                mdx, mdy = (1 if dx > 0 else -1) if dx != 0 else 0, 0
        else:
            if abs(dx) >= abs(dy):
                mdx = 1 if dx > 0 else (-1 if dx < 0 else 0)
                mdy = 0
            else:
                mdx = 0
                mdy = 1 if dy > 0 else (-1 if dy < 0 else 0)

        # Avoid Petrova when energy < 40
        nx = (self.x + mdx) % grid.width
        ny = (self.y + mdy) % grid.height
        if grid.get(nx, ny).cell_type == CellType.PETROVA and self.energy < 40:
            # try perpendicular
            mdx, mdy = mdy, mdx

        self.move(mdx, mdy, grid)

    def _random_step(self, grid):
        """Take a random adjacent step (wander behaviour)."""
        choices = [(1,0),(-1,0),(0,1),(0,-1)]
        mdx, mdy = self.rng.choice(choices)
        # Don't wander into Petrova
        nx = (self.x + mdx) % grid.width
        ny = (self.y + mdy) % grid.height
        if grid.get(nx, ny).cell_type in (CellType.PETROVA, CellType.RADIATION):
            mdx, mdy = self.rng.choice(choices)
        self.move(mdx, mdy, grid)

    # ── sample collection ────────────────────────────────────────────────────
    def collect_astrophage(self, grid) -> bool:
        cost = 3.0
        if self.energy < cost: return False
        self.energy -= cost
        self.astrophage_samples += 1
        self.knowledge_score += 2.0
        self._log(f"Collected Astrophage. Total={self.astrophage_samples}")
        self._check_flashbacks()
        return True

    def collect_taumoeba(self, grid) -> bool:
        if grid.get(self.x, self.y).cell_type != CellType.ADRIAN:
            return False
        cost = 4.0
        if self.energy < cost: return False
        self.energy -= cost
        self.taumoeba_samples += 1
        self.knowledge_score += 3.0
        self._log(f"Collected Taumoeba. Total={self.taumoeba_samples}")
        self._check_flashbacks()
        return True

    # ── experiments ──────────────────────────────────────────────────────────
    def run_experiment(self, simulation) -> str:
        if self.taumoeba_samples < 3 or self.astrophage_samples < 1:
            return "skipped"
        cost = 8.0
        if self.energy < cost: return "skipped"

        self.energy -= cost
        self.taumoeba_samples  -= 2
        self.astrophage_samples -= 1

        rocky_bonus = 0.15 if (simulation and simulation.rocky_cooperation > 0.5) else 0.0
        base_chance = 0.40 + self.experiment_success_bonus + rocky_bonus
        roll = self.rng.random()

        if roll < base_chance:
            outcome = "success"
            kg = 15.0
            if not self.taumoeba_bred:
                self.taumoeba_bred = True
                kg += 20.0
        elif roll < base_chance + 0.35:
            outcome = "partial"
            kg = 6.0
        else:
            outcome = "failure"
            kg = 2.0

        self.knowledge_score += kg
        self.experiment_results.append({
            "turn":              simulation.turn if simulation else 0,
            "outcome":           outcome,
            "knowledge_gained":  kg,
            "total_knowledge":   round(self.knowledge_score, 1),
        })
        self._log(f"Experiment {outcome.upper()} +{kg:.0f} knowledge")
        self._check_flashbacks()
        return outcome

    # ── beetle deployment ────────────────────────────────────────────────────
    def deploy_beetle(self, simulation) -> bool:
        if not self.beetles_available: return False
        cost = 10.0
        if self.energy < cost: return False
        name = self.beetles_available.pop(0)
        self.beetles_deployed.append(name)
        self.energy -= cost
        self.knowledge_score += 5.0
        if simulation:
            simulation.mission_score += 20
            simulation.log_event(
                f"Beetle '{name}' deployed! Payload: {self.knowledge_score:.0f}")
        self._log(f"Deployed beetle '{name}'")
        return True

    # ── repairs ──────────────────────────────────────────────────────────────
    def repair_health(self, amount: float):
        if not self.aboard_hail_mary: return
        self.health = min(self.max_health, self.health + amount)
        self.energy -= 3.0
        self._log(f"Repaired health → {self.health:.1f}")

    # ── flashbacks ───────────────────────────────────────────────────────────
    def _check_flashbacks(self):
        for fb in FLASHBACKS:
            title = fb["title"]
            if title in self.flashbacks_triggered: continue
            if self.knowledge_score >= fb["trigger_knowledge"]:
                self.flashbacks_triggered.append(title)
                self._apply_flashback(fb)
                self._log(f"FLASHBACK: {title}")

    def _apply_flashback(self, fb):
        e, v = fb["effect"], fb["effect_value"]
        if e == "energy_boost":        self.energy  = min(100.0, self.energy + v)
        elif e == "max_health_boost":  self.max_health += v; self.health = min(self.max_health, self.health+v)
        elif e == "knowledge_boost":   self.knowledge_score += v
        elif e == "experiment_boost":  self.experiment_success_bonus += v
        elif e == "full_recall":       self.memory_restored = True

    # ── status ───────────────────────────────────────────────────────────────
    def full_status(self) -> str:
        return (
            f"=== Grace ===\n"
            f"Phase:{self.phase} pos:({self.x},{self.y})\n"
            f"HP:{self.health:.0f}/{self.max_health:.0f} "
            f"NRG:{self.energy:.0f} KNW:{self.knowledge_score:.0f}\n"
            f"Samples A:{self.astrophage_samples} T:{self.taumoeba_samples}\n"
            f"Beetles dep:{self.beetles_deployed}\n"
            f"Flashbacks:{len(self.flashbacks_triggered)}/5"
        )
