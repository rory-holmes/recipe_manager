from decimal import Decimal
from typing import Dict, Tuple

class UnitConversionService:
    # Standard conversion factors to base units (grams for mass, milliliters for volume)
    MASS_TO_GRAMS: Dict[str, Decimal] = {
        "g": Decimal("1"),
        "kg": Decimal("1000"),
        "mg": Decimal("0.001"),
        "oz": Decimal("28.3495"),
        "lb": Decimal("453.592"),
    }

    VOLUME_TO_ML: Dict[str, Decimal] = {
        "ml": Decimal("1"),
        "l": Decimal("1000"),
        "tsp": Decimal("4.92892"),
        "tbsp": Decimal("14.7868"),
        "cup": Decimal("240.0"),  # US legal cup standard approximation
        "floz": Decimal("29.5735"),
    }

    def __init__(self, density_registry: Dict[str, Decimal] = None):
        # Density registry mapping canonical_id -> grams per ml (e.g., flour ~ 0.5 g/ml -> 120g per 240ml cup)
        self.density_registry = density_registry or {
            "flour_all_purpose": Decimal("0.5"),
            "sugar_granulated": Decimal("0.85"),
            "water": Decimal("1.0"),
        }

    def convert(
        self, quantity: Decimal, from_unit: str, to_unit: str, canonical_id: str = None
    ) -> Tuple[Decimal, bool]:
        """
        Converts quantity between units. Returns (converted_quantity, is_estimated).
        Raises ValueError if dimensions are incompatible and no density factor exists.
        """
        from_unit = from_unit.lower()
        to_unit = to_unit.lower()

        if from_unit == to_unit:
            return quantity, False

        # 1. Mass to Mass
        if from_unit in self.MASS_TO_GRAMS and to_unit in self.MASS_TO_GRAMS:
            grams = quantity * self.MASS_TO_GRAMS[from_unit]
            converted = grams / self.MASS_TO_GRAMS[to_unit]
            return converted, False

        # 2. Volume to Volume
        if from_unit in self.VOLUME_TO_ML and to_unit in self.VOLUME_TO_ML:
            ml = quantity * self.VOLUME_TO_ML[from_unit]
            converted = ml / self.VOLUME_TO_ML[to_unit]
            return converted, False

        # 3. Cross-Dimensional (Volume -> Mass)
        if from_unit in self.VOLUME_TO_ML and to_unit in self.MASS_TO_GRAMS:
            if not canonical_id or canonical_id not in self.density_registry:
                raise ValueError(f"Incompatible units [{from_unit} -> {to_unit}] and missing density factor for '{canonical_id}'.")
            ml = quantity * self.VOLUME_TO_ML[from_unit]
            grams = ml * self.density_registry[canonical_id]
            converted = grams / self.MASS_TO_GRAMS[to_unit]
            return converted, True  # Cross-dimensional conversion is estimated

        # 4. Cross-Dimensional (Mass -> Volume)
        if from_unit in self.MASS_TO_GRAMS and to_unit in self.VOLUME_TO_ML:
            if not canonical_id or canonical_id not in self.density_registry:
                raise ValueError(f"Incompatible units [{from_unit} -> {to_unit}] and missing density factor for '{canonical_id}'.")
            grams = quantity * self.MASS_TO_GRAMS[from_unit]
            ml = grams / self.density_registry[canonical_id]
            converted = ml / self.VOLUME_TO_ML[to_unit]
            return converted, True  # Cross-dimensional conversion is estimated

        raise ValueError(f"Unsupported or incompatible unit conversion: {from_unit} to {to_unit}")