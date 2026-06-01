"""
agents/base_agent.py
--------------------
Abstract base class for all agents in the simulation.
"""

from abc import ABC, abstractmethod


class Agent(ABC):
    """
    Base class for Grace, Rocky, and Beetle probes.
    Provides shared attributes: health, energy, position, and action log.
    """

    def __init__(self, name: str, x: int, y: int,
                 health: float = 100.0, energy: float = 100.0):
        self.name = name
        self.x = x
        self.y = y
        self.health = health
        self.energy = energy
        self.alive = True
        self.action_log: list[str] = []

    # ------------------------------------------------------------------ #
    #  Movement                                                             #
    # ------------------------------------------------------------------ #

    def move(self, dx: int, dy: int, grid) -> bool:
        """
        Attempt to move by (dx, dy) on the given grid.
        Returns True if move succeeded.
        Costs energy; agents cannot move if energy < move_cost.
        """
        cost = self.move_cost()
        if self.energy < cost:
            self._log("Cannot move - insufficient energy")
            return False

        nx = (self.x + dx) % grid.width
        ny = (self.y + dy) % grid.height
        self.x, self.y = nx, ny
        self.energy -= cost

        # Apply environmental hazard drain
        cell = grid.get(self.x, self.y)
        drain = cell.energy_drain()
        self.energy = max(0.0, self.energy - drain)
        cell.visited = True

        self._log(f"Moved to ({self.x},{self.y}) [energy={self.energy:.1f}]")
        self._check_alive()
        return True

    def move_cost(self) -> float:
        return 1.0   # override in subclasses if needed

    # ------------------------------------------------------------------ #
    #  Health / Energy management                                           #
    # ------------------------------------------------------------------ #

    def rest(self):
        """Recover a small amount of energy."""
        recovered = 5.0
        self.energy = min(100.0, self.energy + recovered)
        self._log(f"Rested. Energy={self.energy:.1f}")

    def take_damage(self, amount: float, source: str = "unknown"):
        self.health = max(0.0, self.health - amount)
        self._log(f"Took {amount:.1f} damage from {source}. Health={self.health:.1f}")
        self._check_alive()

    def _check_alive(self):
        if self.health <= 0 or self.energy <= 0:
            self.alive = False
            self._log("*** AGENT DOWN ***")

    # ------------------------------------------------------------------ #
    #  Logging                                                              #
    # ------------------------------------------------------------------ #

    def _log(self, message: str):
        entry = f"[{self.name}] {message}"
        self.action_log.append(entry)

    def status(self) -> str:
        return (
            f"{self.name} | pos=({self.x},{self.y}) | "
            f"HP={self.health:.1f} | E={self.energy:.1f} | alive={self.alive}"
        )

    # ------------------------------------------------------------------ #
    #  Abstract interface                                                   #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def choose_action(self, grid, simulation) -> str:
        """Decide and perform one action this turn. Returns action name."""
        pass

    def __repr__(self):
        return self.status()
