"""
simulation.py
-------------
Core simulation engine for Project Hail Mary.
Manages the turn loop, agent coordination, mission protocol,
scoring, and end conditions.
"""

import random
from grid import Grid, CellType
from agents.grace import Grace
from agents.rocky import Rocky
from agents.beetle import BeetleProbe
from entities.astrophage import AstrophageManager
from entities.taumoeba import TaupoebaExperimentSystem, AtmosphereType


class MissionResult:
    """Stores the outcome of a completed simulation run."""

    def __init__(self):
        self.outcome = "incomplete"         # success / partial / failure / abort
        self.turns_survived = 0
        self.final_knowledge = 0.0
        self.beetles_deployed = 0
        self.data_transmitted = 0.0
        self.taumoeba_viable = False
        self.taumoeba_viable_erid = False
        self.sun_brightness = 1.0
        self.grace_alive = True
        self.rocky_alive = True
        self.flashbacks = 0
        self.experiments = 0
        self.mission_score = 0.0
        self.event_log: list[str] = []

    def to_dict(self) -> dict:
        return {
            "outcome": self.outcome,
            "turns": self.turns_survived,
            "knowledge": round(self.final_knowledge, 1),
            "beetles_deployed": self.beetles_deployed,
            "data_transmitted": round(self.data_transmitted, 1),
            "taumoeba_viable_earth": self.taumoeba_viable,
            "taumoeba_viable_erid": self.taumoeba_viable_erid,
            "sun_brightness": round(self.sun_brightness, 3),
            "grace_alive": self.grace_alive,
            "rocky_alive": self.rocky_alive,
            "flashbacks_triggered": self.flashbacks,
            "experiments_run": self.experiments,
            "mission_score": round(self.mission_score, 1),
        }


class Simulation:
    """
    Project Hail Mary multi-agent simulation.
    Orchestrates all agents, the grid, Astrophage dynamics,
    and mission protocol enforcement.
    """

    MAX_TURNS = 300   # simulation ends after this many turns

    def __init__(self, seed: int = None, verbose: bool = True):
        self.seed = seed
        self.rng = random.Random(seed)
        self.verbose = verbose
        self.turn = 0

        # Core components
        self.grid = Grid(width=25, height=25, seed=seed)
        self.grace = Grace(x=3, y=3, seed=seed)
        self.rocky = Rocky(x=5, y=3, seed=seed)
        self.astrophage_mgr = AstrophageManager(seed=seed)
        self.taumoeba_lab = TaupoebaExperimentSystem(seed=seed)

        # Beetle probes (created when Grace deploys them)
        self.beetle_probes: list[BeetleProbe] = []

        # Shared state
        self.rocky_cooperation: float = 0.5
        self.mission_score: float = 0.0
        self.data_transmitted: float = 0.0

        # Mission protocol tracking
        self.protocol_violations: int = 0

        # Event log
        self.event_log: list[str] = []
        self.knowledge_history: list[float] = []
        self.mission_score_history: list[float] = []

        self.log_event("=== PROJECT HAIL MARY SIMULATION STARTED ===")
        self.log_event(
            "Grace wakes from coma aboard the Hail Mary. No memory. "
            "Two dead crewmates. The mission begins."
        )

    # ------------------------------------------------------------------ #
    #  Main simulation loop                                                 #
    # ------------------------------------------------------------------ #

    def run(self) -> MissionResult:
        """Run the full simulation until end condition. Returns MissionResult."""
        while self.turn < self.MAX_TURNS:
            self.turn += 1
            self._step()

            if self._check_end_conditions():
                break

        return self._compile_result()

    def step_once(self):
        """Advance simulation by exactly one turn (for visualiser)."""
        if self.turn < self.MAX_TURNS:
            self.turn += 1
            self._step()
        return self._check_end_conditions()

    def _step(self):
        """Execute one full simulation turn."""
        if self.verbose and self.turn % 10 == 0:
            print(f"\n--- Turn {self.turn} ---")

        # 1. Astrophage spreads
        taumoeba_deployed = self.taumoeba_lab.has_viable_earth_strain()
        self.astrophage_mgr.tick(self.grid, taumoeba_deployed)

        if taumoeba_deployed:
            cleaned = self.astrophage_mgr.apply_taumoeba_cleanup(self.grid)
            if cleaned > 0:
                self.log_event(f"Taumoeba cleaned {cleaned} Astrophage cells!")

        # 2. Grace takes action
        if self.grace.alive:
            action = self._grace_turn()
            self._apply_cell_effects(self.grace)

        # 3. Rocky takes action
        if self.rocky.alive:
            self.rocky.choose_action(self.grid, self)

        # 4. Beetle probes move
        for beetle in self.beetle_probes:
            if beetle.alive and not beetle.transmitted:
                beetle.choose_action(self.grid, self)

        # 5. Deploy beetles from Grace if conditions met
        self._check_beetle_deployment()

        # 5b. Force beetle deploy if Grace has enough knowledge
        if (self.grace.alive
                and self.grace.knowledge_score >= 40
                and self.grace.beetles_available
                and self.grace.energy >= 10):
            self.grace.deploy_beetle(self)

        # 6. Mission protocol checks
        self._enforce_mission_protocol()

        # 7. Track history
        self.knowledge_history.append(round(self.grace.knowledge_score, 1))
        self.mission_score_history.append(round(self.mission_score, 1))

        # 8. Periodic status if verbose
        if self.verbose and self.turn % 10 == 0:
            print(self.grace.full_status())
            print(self.rocky.full_status())
            print(self.astrophage_mgr.summary())

    def _grace_turn(self) -> str:
        """Handle Grace's turn - integrates Taumoeba lab into her decisions."""
        grace = self.grace
        cell = self.grid.get(grace.x, grace.y)

        # Override: use Taumoeba lab for experiments
        if (grace.taumoeba_samples >= 3 and grace.astrophage_samples >= 1
                and grace.energy >= 8):
            parent_strain = self.taumoeba_lab.best_strain()
            result = self.taumoeba_lab.breed_strain(
                parent_strain,
                rocky_assistance=self.rocky_cooperation,
                grace_knowledge=grace.knowledge_score,
            )
            outcome = result["outcome"]
            grace.knowledge_score += result["knowledge_gained"]
            grace.taumoeba_samples -= 2
            grace.astrophage_samples = max(0, grace.astrophage_samples - 1)
            grace.energy -= 8.0

            record = {
                "turn": self.turn,
                "outcome": outcome,
                "knowledge_gained": result["knowledge_gained"],
                "total_knowledge": round(grace.knowledge_score, 1),
                "notes": result["notes"],
            }
            grace.experiment_results.append(record)
            grace._check_flashbacks()

            if outcome == "success" and self.taumoeba_lab.has_viable_earth_strain():
                grace.taumoeba_bred = True
                self.mission_score += 30
                self.log_event(
                    "*** VIABLE TAUMOEBA STRAIN FOR EARTH ACHIEVED! "
                    "Mission critical milestone reached! ***"
                )

            if self.taumoeba_lab.has_viable_erid_strain():
                self.mission_score += 20
                self.log_event("Viable Taumoeba strain for ERID also achieved!")

            grace._log(
                f"Taumoeba experiment {outcome}: +{result['knowledge_gained']:.0f} knowledge"
            )
            return f"experiment_{outcome}"

        # Fall back to Grace's own choose_action
        return grace.choose_action(self.grid, self)

    def _check_beetle_deployment(self):
        """Create beetle probe agents when Grace deploys them."""
        grace = self.grace
        for name in list(grace.beetles_deployed):
            already_created = any(b.probe_name == name for b in self.beetle_probes)
            if not already_created:
                probe = BeetleProbe(
                    name=name,
                    x=grace.x, y=grace.y,
                    data_payload=grace.knowledge_score,
                    seed=self.rng.randint(0, 9999)
                )
                self.beetle_probes.append(probe)
                self.log_event(
                    f"Beetle probe '{name}' created at ({grace.x},{grace.y}) "
                    f"with {grace.knowledge_score:.0f} knowledge payload"
                )

    def _apply_cell_effects(self, agent):
        """Apply ongoing cell hazard effects to an agent."""
        cell = self.grid.get(agent.x, agent.y)
        drain = cell.energy_drain()
        if drain > 0:
            agent.energy = max(0.0, agent.energy - drain)
            if drain > 2:
                agent.take_damage(drain * 0.5, source=cell.cell_type.name)

    # ------------------------------------------------------------------ #
    #  Mission protocol enforcement                                         #
    # ------------------------------------------------------------------ #

    def _enforce_mission_protocol(self):
        """
        Checks mission protocol rules and applies penalties for violations.
        Rules from the Hail Mary Mission Protocol.
        """
        grace = self.grace

        # Rule 1: Don't waste resources (energy too low without resting)
        if grace.energy < 5 and grace.action_log:
            last_action = grace.action_log[-1] if grace.action_log else ""
            if "Moved" in last_action:
                grace.energy -= 2.0   # penalty
                self.protocol_violations += 1
                self.log_event("PROTOCOL VIOLATION: Moving with critically low energy")

        # Rule 2: Beetles should be deployed when knowledge is high
        if (grace.knowledge_score > 80 and grace.beetles_available
                and len(grace.beetles_deployed) == 0):
            # Give gentle reminder but no hard penalty yet
            if self.turn % 20 == 0:
                self.log_event(
                    "MISSION REMINDER: Beetle probes should be deployed "
                    "to protect data"
                )

        # Rule 3: Mission abort if Grace has no energy and no way to recover
        if grace.energy <= 0 and grace.health <= 0:
            grace.alive = False
            self.mission_score -= 20
            self.log_event("MISSION ABORT: Grace has no energy or health")

    # ------------------------------------------------------------------ #
    #  End condition checks                                                 #
    # ------------------------------------------------------------------ #

    def _check_end_conditions(self) -> bool:
        """Check if simulation should end. Returns True if game over."""
        grace = self.grace

        # Grace died
        if not grace.alive:
            self.log_event("SIMULATION END: Grace is no longer alive")
            return True

        # Mission success: Earth viable strain + at least one beetle transmitted
        transmitted = sum(1 for b in self.beetle_probes if b.transmitted)
        if (self.taumoeba_lab.has_viable_earth_strain() and transmitted >= 1):
            self.mission_score += 50
            self.log_event(
                "*** MISSION SUCCESS: Taumoeba solution transmitted to Earth! ***"
            )
            return True

        # Sun went dark (too late)
        if self.astrophage_mgr.sun_brightness < 0.3:
            self.log_event("SIMULATION END: Sun too dim - Earth doomed")
            return True

        # Max turns
        if self.turn >= self.MAX_TURNS:
            self.log_event("SIMULATION END: Maximum turns reached")
            return True

        return False

    # ------------------------------------------------------------------ #
    #  Result compilation                                                   #
    # ------------------------------------------------------------------ #

    def _compile_result(self) -> MissionResult:
        """Compile all metrics into a MissionResult."""
        result = MissionResult()
        result.turns_survived = self.turn
        result.final_knowledge = self.grace.knowledge_score
        result.beetles_deployed = len(self.grace.beetles_deployed)
        result.data_transmitted = self.data_transmitted
        result.taumoeba_viable = self.taumoeba_lab.has_viable_earth_strain()
        result.taumoeba_viable_erid = self.taumoeba_lab.has_viable_erid_strain()
        result.sun_brightness = self.astrophage_mgr.sun_brightness
        result.grace_alive = self.grace.alive
        result.rocky_alive = self.rocky.alive
        result.flashbacks = len(self.grace.flashbacks_triggered)
        result.experiments = len(self.grace.experiment_results)
        result.mission_score = self.mission_score
        result.event_log = self.event_log.copy()

        # Determine outcome
        transmitted = sum(1 for b in self.beetle_probes if b.transmitted)
        if result.taumoeba_viable and transmitted >= 1:
            result.outcome = "success"
        elif not result.taumoeba_viable:
            result.outcome = "failure"
        elif not result.grace_alive:
            result.outcome = "failure"
        else:
            result.outcome = "partial"

        return result

    # ------------------------------------------------------------------ #
    #  Logging                                                              #
    # ------------------------------------------------------------------ #

    def log_event(self, message: str):
        entry = f"[T{self.turn:03d}] {message}"
        self.event_log.append(entry)
        if self.verbose:
            print(entry)

    # ------------------------------------------------------------------ #
    #  Utility                                                              #
    # ------------------------------------------------------------------ #

    def get_all_agents(self):
        agents = [self.grace, self.rocky] + self.beetle_probes
        return agents

    def summary(self) -> str:
        transmitted = sum(1 for b in self.beetle_probes if b.transmitted)
        return (
            f"\n{'='*50}\n"
            f"SIMULATION SUMMARY - Turn {self.turn}\n"
            f"{'='*50}\n"
            f"Mission Score   : {self.mission_score:.1f}\n"
            f"Knowledge       : {self.grace.knowledge_score:.1f}\n"
            f"Taumoeba viable : {self.taumoeba_lab.has_viable_earth_strain()}\n"
            f"Beetles deployed: {len(self.grace.beetles_deployed)}\n"
            f"Data transmitted: {transmitted} probes\n"
            f"Experiments run : {len(self.grace.experiment_results)}\n"
            f"Flashbacks      : {len(self.grace.flashbacks_triggered)}/{5}\n"
            f"Sun brightness  : {self.astrophage_mgr.sun_brightness:.3f}\n"
            f"Astrophage cover: {self.grid.astrophage_coverage():.2%}\n"
            f"Rocky cooperat. : {self.rocky_cooperation:.2f}\n"
            f"{'='*50}"
        )
