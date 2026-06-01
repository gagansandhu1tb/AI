"""
entities/astrophage.py
----------------------
Astrophage - microscopic organism consuming stellar energy.
Manages spread dynamics, resistance tracking, and Petrova line simulation.
"""

import random


class AstrophageManager:
    """
    Manages global Astrophage dynamics across the simulation.
    Tracks spread rate, Sun dimming, and adaptive resistance.
    """

    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)
        self.sun_brightness: float = 1.0       # 1.0 = normal, 0.0 = dead
        self.spread_rate: float = 0.15          # base spread chance per turn
        self.taumoeba_deployed: bool = False
        self.taumoeba_resistance: float = 0.0   # Astrophage adapts over time
        self.total_spread_events: int = 0
        self.turns_of_taumoeba_exposure: int = 0

        # Petrova line intensity
        self.petrova_intensity: float = 0.9

        # History tracking
        self.coverage_history: list[float] = []
        self.brightness_history: list[float] = []

    def tick(self, grid, taumoeba_deployed: bool = False):
        """
        Called each simulation turn.
        Dims the Sun, spreads Astrophage, adapts resistance.
        """
        self.taumoeba_deployed = taumoeba_deployed

        # Adapt resistance when Taumoeba is deployed
        if taumoeba_deployed:
            self.turns_of_taumoeba_exposure += 1
            self.taumoeba_resistance = min(
                0.8,
                self.taumoeba_resistance + 0.01 * self.rng.uniform(0.5, 1.5)
            )

        # Dim Sun slightly each turn
        self.sun_brightness = max(
            0.0,
            self.sun_brightness - 0.002 * (1.0 - self.taumoeba_resistance * 0.5)
        )

        # Spread on grid
        effective_spread = max(
            0.0, self.spread_rate - self.taumoeba_resistance * 0.1
        )
        grid.spread_astrophage(taumoeba_resistance=self.taumoeba_resistance)

        # Track history
        coverage = grid.astrophage_coverage()
        self.coverage_history.append(round(coverage, 4))
        self.brightness_history.append(round(self.sun_brightness, 4))

    def apply_taumoeba_cleanup(self, grid, cleanup_rate: float = 0.05):
        """
        When viable Taumoeba is deployed, gradually reduce Astrophage clouds.
        cleanup_rate: fraction of Astrophage cells reduced per turn.
        """
        from grid import CellType
        cleaned = 0
        for y in range(grid.height):
            for x in range(grid.width):
                cell = grid.cells[y][x]
                if cell.cell_type == CellType.ASTROPHAGE:
                    if self.rng.random() < cleanup_rate * (
                        1.0 - self.taumoeba_resistance
                    ):
                        cell.astrophage_intensity = max(
                            0.0, cell.astrophage_intensity - 0.1
                        )
                        if cell.astrophage_intensity <= 0.0:
                            cell.cell_type = CellType.EMPTY
                            cleaned += 1
        return cleaned

    def earth_status(self) -> str:
        """Report on Earth's situation based on Sun brightness."""
        if self.sun_brightness > 0.95:
            return "Earth: Normal - Astrophage threat early stage"
        elif self.sun_brightness > 0.85:
            return "Earth: Warning - crop failures beginning"
        elif self.sun_brightness > 0.70:
            return "Earth: Critical - global temperature dropping"
        elif self.sun_brightness > 0.50:
            return "Earth: Catastrophic - civilisation collapsing"
        else:
            return "Earth: EXTINCTION LEVEL - mission critical"

    def summary(self) -> str:
        return (
            f"Astrophage Status:\n"
            f"  Sun brightness   : {self.sun_brightness:.3f}\n"
            f"  Spread rate      : {self.spread_rate:.3f}\n"
            f"  Taumoeba resistance: {self.taumoeba_resistance:.3f}\n"
            f"  {self.earth_status()}"
        )
