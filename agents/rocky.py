"""
agents/rocky.py
---------------
Rocky - Eridian alien.
Stays aboard Blip-A but moves randomly within a small area around it.
Communicates via sonar chords, shares knowledge, repairs, shares energy.
"""

import random
from agents.base_agent import Agent
from grid import CellType

CHORD_VOCAB = {
    "greeting":     "♪♩♫",  "danger":       "♩♩♩♩",
    "astrophage":   "♪♫♩♫", "taumoeba":     "♫♩♪♪",
    "help":         "♩♫♫♩", "understand":   "♪♪♩♫",
    "experiment":   "♫♫♩♩", "success":      "♪♫♪♫",
    "failure":      "♩♩♫♫", "energy_share": "♫♩♩♪",
    "repair":       "♩♪♫♩", "erid_threat":  "♩♫♩♩",
    "friendship":   "♪♪♪♫", "star_map":     "♫♪♩♩",
    "xenonite":     "♩♪♪♫",
}


class Rocky(Agent):

    def __init__(self, x: int = 5, y: int = 3, seed: int = None):
        super().__init__("Rocky", x, y, health=100.0, energy=120.0)
        self.rng = random.Random(seed)

        self.home_x = x   # Blip-A centre
        self.home_y = y
        self.roam_radius = 3   # Rocky wanders within 3 cells of Blip-A

        self.ammonia_environment  = True
        self.aboard_blip_a        = True
        self.xenonite_fabricated  = False

        self.scientific_knowledge = {
            "astrophage_properties": 0.8,
            "star_maps":             0.9,
            "xenonite_engineering":  0.95,
            "taumoeba_biology":      0.2,
            "earth_atmosphere":      0.1,
        }
        self.knowledge_score: float = 40.0

        self.translation_level:  int   = 0
        self.shared_vocabulary:  list  = []
        self.communication_log:  list  = []
        self.cooperation_score:  float = 0.5
        self.repairs_done:       int   = 0
        self.energy_shared:      float = 0.0
        self.erid_threat_level:  float = 0.7
        self.fuel_reserves:      float = 80.0

        # Wander counter
        self._wander_cd: int = 0

    # ── choose_action ────────────────────────────────────────────────────────
    def choose_action(self, grid, simulation) -> str:
        if simulation is None:
            self.rest(); return "rest"
        grace = simulation.grace

        # 1. Build translation
        if self.translation_level < 10:
            self.communicate(simulation)
            # Also wander a little
            self._maybe_wander(grid)
            return "communicate"

        # 2. Share energy if Grace is low
        if grace.energy < 30 and self.fuel_reserves > 20:
            self.share_energy(grace, simulation)
            self._maybe_wander(grid)
            return "share_energy"

        # 3. Repair Grace if health low
        if grace.health < 60 and self.cooperation_score > 0.6:
            self.repair_hail_mary(grace, simulation)
            self._maybe_wander(grid)
            return "repair"

        # 4. Share knowledge periodically
        if self.cooperation_score > 0.4 and simulation.turn % 5 == 0:
            self.share_knowledge(grace, simulation)
            self._maybe_wander(grid)
            return "share_knowledge"

        # 5. Recon + wander
        self.conduct_recon(grid, simulation)
        self._maybe_wander(grid)
        return "recon"

    # ── random wander near Blip-A ────────────────────────────────────────────
    def _maybe_wander(self, grid):
        """Rocky wanders randomly within roam_radius of his home position."""
        self._wander_cd -= 1
        if self._wander_cd > 0:
            return
        self._wander_cd = self.rng.randint(2, 5)

        directions = [(1,0),(-1,0),(0,1),(0,-1)]
        self.rng.shuffle(directions)
        for mdx, mdy in directions:
            nx = (self.x + mdx) % grid.width
            ny = (self.y + mdy) % grid.height
            # Stay within roam_radius of home
            dist_x = abs(nx - self.home_x)
            dist_y = abs(ny - self.home_y)
            if dist_x <= self.roam_radius and dist_y <= self.roam_radius:
                # Don't walk into hazards
                if grid.get(nx, ny).cell_type not in (
                    CellType.PETROVA, CellType.RADIATION
                ):
                    self.move(mdx, mdy, grid)
                    return

    # ── communication ────────────────────────────────────────────────────────
    def communicate(self, simulation) -> str:
        # Fuzzy-influenced communication: distance + tunnel presence
        grace = simulation.grace if simulation else None
        grid = simulation.grid if simulation else None
        # compute wrapped distance
        if grid and grace:
            dx = abs(self.x - grace.x)
            dy = abs(self.y - grace.y)
            # wrap distances
            if dx > grid.width // 2: dx = grid.width - dx
            if dy > grid.height // 2: dy = grid.height - dy
            import math
            dist = math.hypot(dx, dy)
            maxd = max(grid.width, grid.height) / 2
            dist_norm = min(1.0, dist / maxd)
        else:
            dist_norm = 1.0

        # fuzzy membership for closeness (1.0 = very close)
        fuzzy_close = max(0.0, 1.0 - dist_norm)

        tunnel_present = False
        if grid:
            tunnel_present = grid.count_cell_type(CellType.TUNNEL) > 0

        unlocked = list(CHORD_VOCAB.keys())
        for word in unlocked:
            if word not in self.shared_vocabulary:
                self.shared_vocabulary.append(word)
                self.translation_level = min(10, len(self.shared_vocabulary))
                chord = CHORD_VOCAB[word]
                msg = f"Rocky: {chord} [{word}]"
                self.communication_log.append(msg)

                # fuzzy cooperation increment: closer + tunnel -> much better
                base = 0.02
                tunnel_factor = 2.0 if tunnel_present else 0.6
                increment = base * (1.0 + 2.0 * fuzzy_close) * tunnel_factor
                self.cooperation_score = min(1.0, self.cooperation_score + increment)

                if simulation:
                    simulation.rocky_cooperation = self.cooperation_score
                    if tunnel_present:
                        simulation.log_event(
                            f"Translation: '{word}' [level {self.translation_level}/10] (tunnel present, comms improved)")
                    else:
                        simulation.log_event(
                            f"Translation: '{word}' [level {self.translation_level}/10] (no tunnel, limited) ")
                self._log(msg)
                return msg
        return "Rocky: ♪♪♪♫ [friendship - fluent]"

    def send_chord(self, word: str) -> str:
        chord = CHORD_VOCAB.get(word, "?")
        msg = f"Rocky: {chord} [{word}]"
        self.communication_log.append(msg)
        return msg

    # ── knowledge sharing ────────────────────────────────────────────────────
    def share_knowledge(self, grace, simulation) -> float:
        if self.translation_level < 3: return 0.0
        eff   = self.translation_level / 10.0
        total = 0.0
        topics = []
        for topic, level in self.scientific_knowledge.items():
            if level > 0.5:
                gained = level * eff * 8.0
                grace.knowledge_score += gained
                total += gained
                topics.append(topic)
        self.cooperation_score = min(1.0, self.cooperation_score + 0.05)
        if simulation:
            simulation.rocky_cooperation = self.cooperation_score
        self._log(f"Shared knowledge: {topics} +{total:.1f}")
        grace._check_flashbacks()
        return total

    # ── repair ───────────────────────────────────────────────────────────────
    def repair_hail_mary(self, grace, simulation) -> bool:
        cost = 10.0
        if self.energy < cost: return False
        self.energy -= cost
        amt = 15.0 * self.cooperation_score
        grace.health = min(grace.max_health, grace.health + amt)
        self.repairs_done += 1
        if simulation:
            simulation.log_event(f"Rocky repaired! Grace HP +{amt:.0f}")
        return True

    # ── energy sharing ───────────────────────────────────────────────────────
    def share_energy(self, grace, simulation) -> float:
        if self.fuel_reserves < 10 or self.cooperation_score < 0.4: return 0.0
        amount = min(20.0, self.fuel_reserves * 0.25)
        self.fuel_reserves -= amount
        grace.energy = min(100.0, grace.energy + amount)
        self.energy_shared += amount
        if simulation:
            simulation.log_event(f"Rocky shared {amount:.0f} energy!")
        return amount

    # ── recon ─────────────────────────────────────────────────────────────────
    def conduct_recon(self, grid, simulation):
        cost = 2.0
        if self.energy < cost:
            self.rest(); return
        self.energy -= cost
        self.knowledge_score += 0.5

    # ── status ───────────────────────────────────────────────────────────────
    def full_status(self) -> str:
        return (
            f"=== Rocky ===\n"
            f"pos:({self.x},{self.y}) HP:{self.health:.0f} "
            f"NRG:{self.energy:.0f} Fuel:{self.fuel_reserves:.0f}\n"
            f"Translation:{self.translation_level}/10 "
            f"Coop:{self.cooperation_score:.2f}\n"
            f"Vocab:{self.shared_vocabulary}"
        )
