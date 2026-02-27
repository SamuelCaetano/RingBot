"""Stone geometry generation for display purposes.

These are simplified representations of gemstones for visualisation.
They are NOT part of the metal model and are exported separately or
combined into a display assembly.
"""

from __future__ import annotations

import math

import cadquery as cq

from ringbot.models.jewelry_data import get_stone_dimensions
from ringbot.models.ring_spec import CutType, StoneSpec


def _round_brilliant(dims) -> cq.Workplane:
    """Simplified brilliant-cut: cone (pavilion) + low dome (crown)."""
    r = dims.width / 2
    crown_h = dims.depth * 0.35
    pavilion_h = dims.depth * 0.65

    crown = (
        cq.Workplane("XY")
        .workplane(offset=0)
        .circle(r)
        .workplane(offset=crown_h)
        .circle(r * 0.55)
        .loft()
    )

    pavilion = (
        cq.Workplane("XY")
        .workplane(offset=0)
        .circle(r)
        .workplane(offset=-pavilion_h)
        .circle(0.1)
        .loft()
    )

    return crown.union(pavilion)


def _marquise_stone(dims) -> cq.Workplane:
    """Marquise: elongated pointed oval, modelled as an elliptical cone shape."""
    hl = dims.length / 2
    hw = dims.width / 2
    crown_h = dims.depth * 0.35
    pavilion_h = dims.depth * 0.65

    crown = (
        cq.Workplane("XY")
        .ellipse(hl, hw)
        .workplane(offset=crown_h)
        .ellipse(hl * 0.5, hw * 0.5)
        .loft()
    )
    pavilion = (
        cq.Workplane("XY")
        .ellipse(hl, hw)
        .workplane(offset=-pavilion_h)
        .ellipse(0.1, 0.05)
        .loft()
    )
    return crown.union(pavilion)


def _rectangular_stone(dims) -> cq.Workplane:
    """For princess, emerald-cut, asscher, radiant, baguette."""
    l = dims.length
    w = dims.width
    crown_h = dims.depth * 0.35
    pavilion_h = dims.depth * 0.65

    crown = (
        cq.Workplane("XY")
        .rect(l, w)
        .workplane(offset=crown_h)
        .rect(l * 0.6, w * 0.6)
        .loft()
    )
    pavilion = (
        cq.Workplane("XY")
        .rect(l, w)
        .workplane(offset=-pavilion_h)
        .rect(l * 0.1, w * 0.1)
        .loft()
    )
    return crown.union(pavilion)


def _oval_stone(dims) -> cq.Workplane:
    """Oval cut stone."""
    hl = dims.length / 2
    hw = dims.width / 2
    crown_h = dims.depth * 0.35
    pavilion_h = dims.depth * 0.65

    crown = (
        cq.Workplane("XY")
        .ellipse(hl, hw)
        .workplane(offset=crown_h)
        .ellipse(hl * 0.5, hw * 0.5)
        .loft()
    )
    pavilion = (
        cq.Workplane("XY")
        .ellipse(hl, hw)
        .workplane(offset=-pavilion_h)
        .ellipse(0.1, 0.05)
        .loft()
    )
    return crown.union(pavilion)


def _pear_stone(dims) -> cq.Workplane:
    """Pear/teardrop — approximate with an oval (simplified)."""
    return _oval_stone(dims)


def _heart_stone(dims) -> cq.Workplane:
    """Heart shape — approximate as oval (simplified)."""
    return _oval_stone(dims)


_CUT_BUILDERS = {
    CutType.ROUND_BRILLIANT: _round_brilliant,
    CutType.MARQUISE: _marquise_stone,
    CutType.OVAL: _oval_stone,
    CutType.PEAR: _pear_stone,
    CutType.HEART: _heart_stone,
    CutType.PRINCESS: _rectangular_stone,
    CutType.EMERALD_CUT: _rectangular_stone,
    CutType.ASSCHER: _rectangular_stone,
    CutType.RADIANT: _rectangular_stone,
    CutType.BAGUETTE: _rectangular_stone,
    CutType.CUSHION: _round_brilliant,
}


def build_stone_geometry(spec: StoneSpec) -> cq.Workplane:
    """Build a simplified display stone, centred at origin with table facing +Z."""
    dims = get_stone_dimensions(spec.cut, spec.carat)
    builder = _CUT_BUILDERS.get(spec.cut, _round_brilliant)
    return builder(dims)
