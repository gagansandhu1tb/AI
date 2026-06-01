"""
agents/beetle.py
----------------
Beetle probes - autonomous data-relay drones (John, Paul, George, Ringo).
Navigate using stellar positioning toward Earth, carrying Grace's findings.
"""

import random
import math
from agents.base_agent import Agent
from grid import CellType


class BeetleProbe(Agent):
    """
    Autonomous beetle probe carrying scientific data toward Earth.
    Navigates the grid using stellar positioning.
    Transmits data payload on reaching the grid boundary.
    """

    def __init__(self, name: str, x: int, y: int,
                 data_payload: float, seed: int = None):
        super().__init__(f"Beetle-{name}", x, y, health=100.0, energy=80.0)
        self.probe_name = name
        self.data_payload = data_payload      # knowledge units carried
        self.deployed = True
        self.transmitted = False
        self.distance_travelled = 0
        self.trajectory: list[tuple[int, int]] = [(x, y)]
        self.rng = random.Random(seed)

        # Target: opposite corner of grid (approximating Earth direction)
        # Probe heads "away" from Tau Ceti toward the edge
        self.target_x = 0
        self.target_y = 0

    def choose_action(self, grid, simulation) -> str:
        """
        Beetles use stellar positioning to navigate toward Earth.
        They move one step per turn toward their target.
        """
        if self.transmitted or not self.alive:
            return "idle"

        if self.energy < 2:
            self._log("Beetle out of fuel!")
            self.alive = False
            return "dead"

        # Check if at grid boundary (transmission zone)
        if self._at_boundary(grid):
            self._transmit(simulation)
            return "transmitted"

        # Move toward target (corner)
        self._navigate(grid)
        return "navigate"

    def _navigate(self, grid):
        """Move one step toward target using stellar positioning."""
        cost = 1.5
        if self.energy < cost:
            return

        dx = self.target_x - self.x
        dy = self.target_y - self.y

        # Wrap
        if abs(dx) > grid.width // 2:
            dx = -dx // abs(dx) * (grid.width - abs(dx))
        if abs(dy) > grid.height // 2:
            dy = -dy // abs(dy) * (grid.height - abs(dy))

        # Step
        if abs(dx) >= abs(dy):
            move_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
            move_y = 0
        else:
            move_x = 0
            move_y = 1 if dy > 0 else (-1 if dy < 0 else 0)

        # Avoid dense Astrophage if possible
        nx = (self.x + move_x) % grid.width
        ny = (self.y + move_y) % grid.height
        if grid.get(nx, ny).cell_type == CellType.PETROVA:
            # Try perpendicular
            move_x, move_y = move_y, move_x

        old_x, old_y = self.x, self.y
        self.move(move_x, move_y, grid)
        if (self.x, self.y) != (old_x, old_y):
            self.distance_travelled += 1
            self.trajectory.append((self.x, self.y))

    def _at_boundary(self, grid) -> bool:
        """Check if probe has reached the grid boundary."""
        return (
            self.x == 0 or self.x == grid.width - 1 or
            self.y == 0 or self.y == grid.height - 1
        )

    def _transmit(self, simulation):
        """Transmit data payload - mission success contribution."""
        self.transmitted = True
        if simulation:
            simulation.mission_score += self.data_payload * 0.5
            simulation.data_transmitted += self.data_payload
            simulation.log_event(
                f"Beetle '{self.probe_name}' TRANSMITTED! "
                f"Data payload: {self.data_payload:.0f} units | "
                f"Distance: {self.distance_travelled} cells"
            )
        self._log(
            f"Data transmitted! Payload={self.data_payload:.0f}, "
            f"dist={self.distance_travelled}"
        )

    def status_line(self) -> str:
        state = "TRANSMITTED" if self.transmitted else (
            "ACTIVE" if self.alive else "DEAD"
        )
        return (
            f"Beetle {self.probe_name}: {state} | "
            f"pos=({self.x},{self.y}) | "
            f"data={self.data_payload:.0f} | "
            f"dist={self.distance_travelled}"
        )

    def move_cost(self) -> float:
        return 1.5
