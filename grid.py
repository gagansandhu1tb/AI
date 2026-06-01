"""
grid.py
-------
2D wrapping grid environment for the Project Hail Mary simulation.
Cells can contain empty space, Adrian planet, Astrophage clouds,
spacecraft, beetle probes, radiation zones, and debris fields.
"""

import random
from enum import Enum


class CellType(Enum):
    EMPTY = "."
    ADRIAN = "A"          # Planet Adrian - rich in Taumoeba
    ASTROPHAGE = "*"      # Astrophage cloud - energy drain hazard
    PETROVA = "P"         # Dense Astrophage (Petrova line)
    HAIL_MARY = "H"       # Grace's spacecraft
    BLIP_A = "B"          # Rocky's spacecraft
    RADIATION = "R"       # Radiation zone hazard
    DEBRIS = "D"          # Debris field hazard
    TUNNEL = "T"          # Xenonite tunnel between ships


class Cell:
    """Represents a single cell in the grid."""

    def __init__(self, cell_type: CellType = CellType.EMPTY):
        self.cell_type = cell_type
        self.astrophage_intensity = 0.0   # 0.0 - 1.0 how dense astrophage is
        self.taumoeba_present = False
        self.agents = []                  # agents currently in this cell
        self.visited = False              # has Grace visited this cell

    def is_hazardous(self) -> bool:
        return self.cell_type in (
            CellType.ASTROPHAGE,
            CellType.PETROVA,
            CellType.RADIATION,
            CellType.DEBRIS,
        )

    def energy_drain(self) -> float:
        """Returns energy drained per turn from environmental hazards."""
        drains = {
            CellType.ASTROPHAGE: 2.0 * self.astrophage_intensity,
            CellType.PETROVA:    5.0 * self.astrophage_intensity,
            CellType.RADIATION:  3.0,
            CellType.DEBRIS:     1.5,
            CellType.EMPTY:      0.0,
            CellType.HAIL_MARY:  0.0,
            CellType.BLIP_A:     0.0,
            CellType.TUNNEL:     0.0,
            CellType.ADRIAN:     0.5,
        }
        return drains.get(self.cell_type, 0.0)

    def __repr__(self):
        return self.cell_type.value


class Grid:
    """
    20x20 toroidal (wrapping) grid representing space near Tau Ceti.
    Supports cell placement, Astrophage spreading, and agent tracking.
    """

    def __init__(self, width: int = 25, height: int = 25, seed: int = None):
        self.width = width
        self.height = height
        self.rng = random.Random(seed)
        self.cells: list[list[Cell]] = [
            [Cell() for _ in range(width)] for _ in range(height)
        ]
        self.turn = 0
        self._place_fixed_objects()
        self._scatter_hazards()

    # ------------------------------------------------------------------ #
    #  Setup helpers                                                        #
    # ------------------------------------------------------------------ #

    def _place_fixed_objects(self):
        """Place the key locations on the grid."""
        # Hail Mary in the upper-left quadrant
        self.hail_mary_pos = (3, 3)
        self._set(3, 3, CellType.HAIL_MARY)

        # Blip-A nearby
        self.blip_a_pos = (5, 3)
        self._set(5, 3, CellType.BLIP_A)

        # Xenonite tunnel connecting the two ships
        self._set(4, 3, CellType.TUNNEL)

        # Planet Adrian - smaller planet at the opposite end of the ship
        ax, ay = self.width - 4, self.height - 10
        self.adrian_pos = (ax, ay)
        for dx in range(0, 3):
            for dy in range(0, 3):
                self._set(ax + dx, ay + dy, CellType.ADRIAN)

        # Petrova column - a straight vertical line down the centre
        px = self.width // 2
        for y in range(self.height):
            cell = self.get(px, y)
            if cell.cell_type in (CellType.HAIL_MARY, CellType.BLIP_A, CellType.TUNNEL, CellType.ADRIAN):
                continue
            cell.cell_type = CellType.PETROVA
            cell.astrophage_intensity = 0.9

    def _scatter_hazards(self):
        """Randomly scatter Astrophage clouds, radiation, and debris."""
        for _ in range(30):
            x = self.rng.randint(0, self.width - 1)
            y = self.rng.randint(0, self.height - 1)
            c = self.get(x, y)
            if c.cell_type == CellType.EMPTY:
                c.cell_type = CellType.ASTROPHAGE
                c.astrophage_intensity = self.rng.uniform(0.2, 0.7)

        for _ in range(10):
            x = self.rng.randint(0, self.width - 1)
            y = self.rng.randint(0, self.height - 1)
            c = self.get(x, y)
            if c.cell_type == CellType.EMPTY:
                c.cell_type = CellType.RADIATION

        for _ in range(8):
            x = self.rng.randint(0, self.width - 1)
            y = self.rng.randint(0, self.height - 1)
            c = self.get(x, y)
            if c.cell_type == CellType.EMPTY:
                c.cell_type = CellType.DEBRIS

    # ------------------------------------------------------------------ #
    #  Core grid access (wrapping)                                         #
    # ------------------------------------------------------------------ #

    def _wrap(self, x: int, y: int) -> tuple[int, int]:
        return x % self.width, y % self.height

    def get(self, x: int, y: int) -> Cell:
        x, y = self._wrap(x, y)
        return self.cells[y][x]

    def _set(self, x: int, y: int, cell_type: CellType):
        x, y = self._wrap(x, y)
        self.cells[y][x].cell_type = cell_type

    def neighbours(self, x: int, y: int) -> list[tuple[int, int]]:
        """Return the 4 orthogonal neighbours (wrapped)."""
        return [
            self._wrap(x + 1, y),
            self._wrap(x - 1, y),
            self._wrap(x, y + 1),
            self._wrap(x, y - 1),
        ]

    # ------------------------------------------------------------------ #
    #  Astrophage dynamics                                                  #
    # ------------------------------------------------------------------ #

    def spread_astrophage(self, taumoeba_resistance: float = 0.0):
        """
        Each turn, Astrophage clouds have a chance to spread to adjacent
        empty cells. Taumoeba resistance slows the spread.
        taumoeba_resistance: 0.0 = no resistance, 1.0 = full resistance
        """
        spread_chance = max(0.0, 0.15 - taumoeba_resistance * 0.12)
        intensify_chance = 0.10

        new_astrophage: list[tuple[int, int, float]] = []

        for y in range(self.height):
            for x in range(self.width):
                cell = self.cells[y][x]
                if cell.cell_type in (CellType.ASTROPHAGE, CellType.PETROVA):
                    # Intensify existing clouds
                    if self.rng.random() < intensify_chance:
                        cell.astrophage_intensity = min(
                            1.0, cell.astrophage_intensity + 0.05
                        )
                    # Spread to neighbours
                    for nx, ny in self.neighbours(x, y):
                        ncell = self.cells[ny][nx]
                        if ncell.cell_type == CellType.EMPTY:
                            if self.rng.random() < spread_chance:
                                new_astrophage.append(
                                    (nx, ny, self.rng.uniform(0.1, 0.3))
                                )

        for nx, ny, intensity in new_astrophage:
            c = self.cells[ny][nx]
            if c.cell_type == CellType.EMPTY:
                c.cell_type = CellType.ASTROPHAGE
                c.astrophage_intensity = intensity

        self.turn += 1

    def astrophage_coverage(self) -> float:
        """Fraction of grid cells affected by Astrophage."""
        affected = sum(
            1
            for row in self.cells
            for cell in row
            if cell.cell_type in (CellType.ASTROPHAGE, CellType.PETROVA)
        )
        return affected / (self.width * self.height)

    # ------------------------------------------------------------------ #
    #  Utility                                                              #
    # ------------------------------------------------------------------ #

    def count_cell_type(self, ct: CellType) -> int:
        return sum(
            1 for row in self.cells for cell in row if cell.cell_type == ct
        )

    def display(self) -> str:
        """Return a text representation of the grid."""
        lines = []
        for row in self.cells:
            lines.append("".join(cell.cell_type.value for cell in row))
        return "\n".join(lines)

    def __repr__(self):
        return f"Grid({self.width}x{self.height}, turn={self.turn})"
