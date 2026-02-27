"""Jewelry domain lookup tables: carat-to-mm, ring sizes, material properties."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .ring_spec import CutType, Material


# ---------------------------------------------------------------------------
# Carat-to-millimeter conversion
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StoneDimensions:
    """Physical dimensions of a gemstone in mm."""
    length: float
    width: float
    depth: float

    @property
    def diameter(self) -> float:
        return self.length


# Reference data: maps (cut, carat) -> approximate (length_mm, width_mm, depth_mm).
# For cuts where length == width (round, princess, cushion, asscher) only one
# value is needed; for elongated cuts the L/W ratio is baked in.

_ROUND_BRILLIANT_MM: dict[float, tuple[float, float]] = {
    0.10: (3.0, 1.8),
    0.25: (4.1, 2.5),
    0.33: (4.4, 2.7),
    0.50: (5.2, 3.1),
    0.75: (5.9, 3.5),
    1.00: (6.5, 3.9),
    1.25: (6.9, 4.2),
    1.50: (7.4, 4.5),
    1.75: (7.8, 4.7),
    2.00: (8.2, 4.9),
    2.50: (8.8, 5.3),
    3.00: (9.4, 5.6),
    4.00: (10.4, 6.2),
    5.00: (11.0, 6.6),
}

_MARQUISE_MM: dict[float, tuple[float, float, float]] = {
    0.10: (4.0, 2.0, 1.5),
    0.25: (6.0, 3.0, 2.0),
    0.33: (6.5, 3.3, 2.2),
    0.50: (8.0, 4.0, 2.6),
    0.75: (9.0, 4.5, 3.0),
    1.00: (10.0, 5.0, 3.3),
    1.50: (11.5, 5.8, 3.8),
    2.00: (13.0, 6.5, 4.0),
}

_OVAL_MM: dict[float, tuple[float, float, float]] = {
    0.25: (5.0, 3.5, 2.2),
    0.50: (6.0, 4.0, 2.7),
    0.75: (7.0, 5.0, 3.1),
    1.00: (7.7, 5.7, 3.5),
    1.50: (8.5, 6.5, 3.9),
    2.00: (9.0, 7.0, 4.2),
}

_PEAR_MM: dict[float, tuple[float, float, float]] = {
    0.25: (5.5, 3.5, 2.2),
    0.50: (7.0, 4.5, 2.8),
    0.75: (7.5, 5.0, 3.1),
    1.00: (8.0, 5.5, 3.4),
    1.50: (9.5, 6.0, 3.8),
    2.00: (10.5, 7.0, 4.2),
}

_EMERALD_CUT_MM: dict[float, tuple[float, float, float]] = {
    0.25: (4.5, 3.0, 2.0),
    0.50: (5.5, 4.0, 2.8),
    0.75: (6.0, 4.5, 3.1),
    1.00: (7.0, 5.0, 3.5),
    1.50: (7.5, 5.5, 3.8),
    2.00: (8.5, 6.5, 4.2),
}

_PRINCESS_MM: dict[float, tuple[float, float]] = {
    0.25: (3.5, 2.6),
    0.50: (4.5, 3.3),
    0.75: (5.0, 3.6),
    1.00: (5.5, 4.0),
    1.50: (6.2, 4.5),
    2.00: (7.0, 5.0),
}

_CUSHION_MM: dict[float, tuple[float, float]] = {
    0.25: (3.5, 2.5),
    0.50: (4.5, 3.2),
    0.75: (5.2, 3.6),
    1.00: (5.5, 3.9),
    1.50: (6.5, 4.5),
    2.00: (7.0, 5.0),
}

_HEART_MM: dict[float, tuple[float, float, float]] = {
    0.25: (4.0, 4.0, 2.4),
    0.50: (5.0, 5.0, 3.0),
    0.75: (5.8, 5.8, 3.4),
    1.00: (6.5, 6.5, 3.9),
    1.50: (7.5, 7.5, 4.3),
    2.00: (8.2, 8.2, 4.8),
}

_BAGUETTE_MM: dict[float, tuple[float, float, float]] = {
    0.10: (3.5, 2.0, 1.4),
    0.25: (5.0, 2.5, 1.8),
    0.50: (6.0, 3.5, 2.4),
    0.75: (7.0, 4.0, 2.8),
    1.00: (7.5, 4.5, 3.2),
}


def _interpolate(table_2d: dict[float, tuple[float, float]], carat: float) -> StoneDimensions:
    """Interpolate a round/square table (diameter, depth) -> StoneDimensions."""
    keys = sorted(table_2d.keys())
    if carat <= keys[0]:
        d, dp = table_2d[keys[0]]
        scale = (carat / keys[0]) ** (1 / 3)
        return StoneDimensions(d * scale, d * scale, dp * scale)
    if carat >= keys[-1]:
        d, dp = table_2d[keys[-1]]
        scale = (carat / keys[-1]) ** (1 / 3)
        return StoneDimensions(d * scale, d * scale, dp * scale)
    for i in range(len(keys) - 1):
        if keys[i] <= carat <= keys[i + 1]:
            t = (carat - keys[i]) / (keys[i + 1] - keys[i])
            d0, dp0 = table_2d[keys[i]]
            d1, dp1 = table_2d[keys[i + 1]]
            d = d0 + t * (d1 - d0)
            dp = dp0 + t * (dp1 - dp0)
            return StoneDimensions(d, d, dp)
    d, dp = table_2d[keys[-1]]
    return StoneDimensions(d, d, dp)


def _interpolate_3d(table_3d: dict[float, tuple[float, float, float]], carat: float) -> StoneDimensions:
    """Interpolate an elongated-cut table (length, width, depth) -> StoneDimensions."""
    keys = sorted(table_3d.keys())
    if carat <= keys[0]:
        l, w, dp = table_3d[keys[0]]
        scale = (carat / keys[0]) ** (1 / 3)
        return StoneDimensions(l * scale, w * scale, dp * scale)
    if carat >= keys[-1]:
        l, w, dp = table_3d[keys[-1]]
        scale = (carat / keys[-1]) ** (1 / 3)
        return StoneDimensions(l * scale, w * scale, dp * scale)
    for i in range(len(keys) - 1):
        if keys[i] <= carat <= keys[i + 1]:
            t = (carat - keys[i]) / (keys[i + 1] - keys[i])
            l0, w0, dp0 = table_3d[keys[i]]
            l1, w1, dp1 = table_3d[keys[i + 1]]
            return StoneDimensions(
                l0 + t * (l1 - l0),
                w0 + t * (w1 - w0),
                dp0 + t * (dp1 - dp0),
            )
    l, w, dp = table_3d[keys[-1]]
    return StoneDimensions(l, w, dp)


def get_stone_dimensions(cut: CutType, carat: float) -> StoneDimensions:
    """Return approximate physical dimensions for a stone given its cut and carat weight."""
    match cut:
        case CutType.ROUND_BRILLIANT:
            return _interpolate(_ROUND_BRILLIANT_MM, carat)
        case CutType.PRINCESS:
            return _interpolate(_PRINCESS_MM, carat)
        case CutType.CUSHION:
            return _interpolate(_CUSHION_MM, carat)
        case CutType.ASSCHER:
            return _interpolate(_PRINCESS_MM, carat)
        case CutType.RADIANT:
            return _interpolate(_PRINCESS_MM, carat)
        case CutType.MARQUISE:
            return _interpolate_3d(_MARQUISE_MM, carat)
        case CutType.OVAL:
            return _interpolate_3d(_OVAL_MM, carat)
        case CutType.PEAR:
            return _interpolate_3d(_PEAR_MM, carat)
        case CutType.EMERALD_CUT:
            return _interpolate_3d(_EMERALD_CUT_MM, carat)
        case CutType.HEART:
            return _interpolate_3d(_HEART_MM, carat)
        case CutType.BAGUETTE:
            return _interpolate_3d(_BAGUETTE_MM, carat)
        case _:
            return _interpolate(_ROUND_BRILLIANT_MM, carat)


# ---------------------------------------------------------------------------
# US Ring sizes -> inner diameter in mm
# ---------------------------------------------------------------------------

US_RING_SIZES: dict[float, float] = {
    3.0: 14.0,
    3.5: 14.4,
    4.0: 14.8,
    4.5: 15.2,
    5.0: 15.7,
    5.5: 16.1,
    6.0: 16.5,
    6.5: 16.9,
    7.0: 17.3,
    7.5: 17.7,
    8.0: 18.1,
    8.5: 18.5,
    9.0: 19.0,
    9.5: 19.4,
    10.0: 19.8,
    10.5: 20.2,
    11.0: 20.6,
    11.5: 21.0,
    12.0: 21.4,
    12.5: 21.8,
    13.0: 22.2,
    13.5: 22.6,
    14.0: 23.0,
    14.5: 23.4,
    15.0: 23.8,
    15.5: 24.2,
    16.0: 24.6,
}


def get_inner_diameter(us_size: float) -> float:
    """Return inner diameter in mm for a US ring size, interpolating if needed."""
    if us_size in US_RING_SIZES:
        return US_RING_SIZES[us_size]
    keys = sorted(US_RING_SIZES.keys())
    if us_size < keys[0]:
        return US_RING_SIZES[keys[0]]
    if us_size > keys[-1]:
        return US_RING_SIZES[keys[-1]]
    for i in range(len(keys) - 1):
        if keys[i] <= us_size <= keys[i + 1]:
            t = (us_size - keys[i]) / (keys[i + 1] - keys[i])
            return US_RING_SIZES[keys[i]] + t * (US_RING_SIZES[keys[i + 1]] - US_RING_SIZES[keys[i]])
    return US_RING_SIZES[keys[-1]]


# ---------------------------------------------------------------------------
# Material properties
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MaterialProperties:
    density_g_cm3: float
    min_wall_mm: float
    display_name: str


MATERIAL_PROPERTIES: dict[str, MaterialProperties] = {
    "18k_yellow_gold": MaterialProperties(15.58, 0.8, "18K Yellow Gold"),
    "18k_white_gold": MaterialProperties(16.0, 0.8, "18K White Gold"),
    "18k_rose_gold": MaterialProperties(15.2, 0.8, "18K Rose Gold"),
    "14k_yellow_gold": MaterialProperties(13.07, 0.7, "14K Yellow Gold"),
    "14k_white_gold": MaterialProperties(12.76, 0.7, "14K White Gold"),
    "14k_rose_gold": MaterialProperties(13.03, 0.7, "14K Rose Gold"),
    "platinum": MaterialProperties(21.45, 0.5, "Platinum 950"),
    "sterling_silver": MaterialProperties(10.36, 0.9, "Sterling Silver 925"),
}


def get_material_props(material_value: str) -> MaterialProperties:
    """Retrieve material properties by enum value string."""
    if material_value in MATERIAL_PROPERTIES:
        return MATERIAL_PROPERTIES[material_value]
    raise ValueError(f"Unknown material: {material_value}")
