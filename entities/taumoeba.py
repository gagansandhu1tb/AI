"""
entities/taumoeba.py
--------------------
Taumoeba - single-celled organism from Adrian's atmosphere
that naturally consumes Astrophage. Key to saving Earth and Erid.

Handles: biology simulation, strain breeding, mutation tracking,
and atmospheric compatibility testing.
"""

import random
from dataclasses import dataclass, field
from enum import Enum


class AtmosphereType(Enum):
    ADRIAN = "adrian"          # native environment (ammonia-rich)
    EARTH = "earth"            # nitrogen-rich - target
    ERID = "erid"              # 40 Eridani - ammonia at high pressure
    VACUUM = "vacuum"          # space - lethal to Taumoeba


@dataclass
class TaumoebaStrain:
    """Represents a bred strain of Taumoeba with specific characteristics."""
    strain_id: int
    generation: int
    astrophage_consumption_rate: float    # how fast it eats Astrophage
    atmosphere_tolerance: dict            # {AtmosphereType: survival_chance}
    mutation_rate: float
    viable_for_earth: bool = False
    viable_for_erid: bool = False
    notes: str = ""

    def check_viability(self):
        """Check if this strain can survive in target atmospheres."""
        self.viable_for_earth = (
            self.atmosphere_tolerance.get(AtmosphereType.EARTH, 0.0) > 0.7
        )
        self.viable_for_erid = (
            self.atmosphere_tolerance.get(AtmosphereType.ERID, 0.0) > 0.7
        )


class TaupoebaExperimentSystem:
    """
    Manages all Taumoeba experimentation aboard the Hail Mary.
    Tracks strain evolution, breeding outcomes, and scientific progress.
    """

    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)
        self.strains: list[TaumoebaStrain] = []
        self.experiment_count: int = 0
        self.strain_counter: int = 0

        # Base wild strain from Adrian
        self._create_wild_strain()

    def _create_wild_strain(self):
        """Create the initial wild Taumoeba strain from Adrian."""
        wild = TaumoebaStrain(
            strain_id=0,
            generation=0,
            astrophage_consumption_rate=0.8,
            atmosphere_tolerance={
                AtmosphereType.ADRIAN:  0.95,
                AtmosphereType.EARTH:   0.05,   # dies in Earth atmosphere
                AtmosphereType.ERID:    0.60,
                AtmosphereType.VACUUM:  0.0,
            },
            mutation_rate=0.1,
            notes="Wild strain - native to Adrian"
        )
        wild.check_viability()
        self.strains.append(wild)

    def breed_strain(self, parent_strain: TaumoebaStrain,
                     rocky_assistance: float = 0.0,
                     grace_knowledge: float = 0.0) -> dict:
        """
        Attempt to breed a new strain with improved atmospheric tolerance.
        Returns a result dict with outcome and new strain (if successful).
        """
        self.experiment_count += 1
        self.strain_counter += 1

        # Calculate success probability
        base_prob = 0.30
        knowledge_bonus = min(0.30, grace_knowledge / 200.0)
        rocky_bonus = rocky_assistance * 0.20
        total_prob = base_prob + knowledge_bonus + rocky_bonus

        roll = self.rng.random()
        success = roll < total_prob
        partial = not success and roll < total_prob + 0.35

        if success:
            new_strain = self._mutate_strain(parent_strain, strength=0.3)
            new_strain.notes = (
                f"Bred from strain {parent_strain.strain_id}, gen {parent_strain.generation + 1}"
            )
            self.strains.append(new_strain)
            return {
                "outcome": "success",
                "strain": new_strain,
                "knowledge_gained": 15.0,
                "notes": new_strain.notes,
            }
        elif partial:
            new_strain = self._mutate_strain(parent_strain, strength=0.1)
            new_strain.notes = f"Partial breed - limited improvement"
            self.strains.append(new_strain)
            return {
                "outcome": "partial",
                "strain": new_strain,
                "knowledge_gained": 6.0,
                "notes": new_strain.notes,
            }
        else:
            return {
                "outcome": "failure",
                "strain": None,
                "knowledge_gained": 2.0,
                "notes": "Strain died during atmospheric exposure test",
            }

    def _mutate_strain(self, parent: TaumoebaStrain,
                       strength: float) -> TaumoebaStrain:
        """Create a mutated child strain with improved tolerances."""
        new_tolerance = {}
        for atm, tol in parent.atmosphere_tolerance.items():
            if atm == AtmosphereType.EARTH:
                # Target: improve Earth tolerance
                delta = self.rng.uniform(0, strength * 0.5)
                new_tolerance[atm] = min(1.0, tol + delta)
            elif atm == AtmosphereType.ERID:
                delta = self.rng.uniform(0, strength * 0.3)
                new_tolerance[atm] = min(1.0, tol + delta)
            else:
                # Other tolerances may slightly decrease
                delta = self.rng.uniform(-0.05, 0.05)
                new_tolerance[atm] = max(0.0, min(1.0, tol + delta))

        new_strain = TaumoebaStrain(
            strain_id=self.strain_counter,
            generation=parent.generation + 1,
            astrophage_consumption_rate=parent.astrophage_consumption_rate
                * self.rng.uniform(0.9, 1.1),
            atmosphere_tolerance=new_tolerance,
            mutation_rate=parent.mutation_rate * self.rng.uniform(0.8, 1.2),
        )
        new_strain.check_viability()
        return new_strain

    def best_strain(self) -> TaumoebaStrain:
        """Return strain with highest Earth viability."""
        return max(
            self.strains,
            key=lambda s: s.atmosphere_tolerance.get(AtmosphereType.EARTH, 0.0)
        )

    def has_viable_earth_strain(self) -> bool:
        return any(s.viable_for_earth for s in self.strains)

    def has_viable_erid_strain(self) -> bool:
        return any(s.viable_for_erid for s in self.strains)

    def summary(self) -> str:
        best = self.best_strain()
        earth_tol = best.atmosphere_tolerance.get(AtmosphereType.EARTH, 0.0)
        return (
            f"Taumoeba Lab Summary:\n"
            f"  Total strains bred : {len(self.strains)}\n"
            f"  Experiments run    : {self.experiment_count}\n"
            f"  Best Earth tolerance: {earth_tol:.2%}\n"
            f"  Earth viable strain: {self.has_viable_earth_strain()}\n"
            f"  Erid viable strain : {self.has_viable_erid_strain()}\n"
            f"  Best strain gen    : {best.generation}"
        )
