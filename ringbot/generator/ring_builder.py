"""Ring assembly orchestrator: RingSpec -> complete CadQuery solids.

Produces three groups of geometry:
  1. The *metal model* (band + gallery + settings) — boolean-unioned structural parts.
  2. *Decoration solids* — small elements kept separate to avoid corrupting
     the main metal geometry through cascading boolean operations.
  3. *Display stones* — gem geometry for visualisation only.

Internal convention (during construction):
  - Ring centred at origin, finger-hole along Z, top of ring at +X.
  - Settings/stones are built along +Z, then rotated to point radially
    outward (+X) for placement at the 12-o'clock position.

Output convention (after final rotation, +90° around Z):
  - Ring band lies in the XY plane, finger-hole along Z.
  - The setting/stone (12-o'clock) points along +Y (upward).
  - Y-up convention for Three.js and standard 3D viewers.
"""

from __future__ import annotations

import math
import random as _random
from dataclasses import dataclass, field
from typing import Optional

import cadquery as cq

from ringbot.generator.band import build_band
from ringbot.generator.decorations import build_decoration
from ringbot.generator.settings import build_setting
from ringbot.generator.stones import build_stone_geometry
from ringbot.models.jewelry_data import (
    get_inner_diameter,
    get_stone_dimensions,
)
from ringbot.models.ring_spec import (
    DecorativeElement,
    ElementPosition,
    ElementType,
    RingSpec,
    StoneSpec,
)


@dataclass
class RingAssembly:
    """Container for the generated ring components."""
    metal: cq.Workplane
    stones: list[cq.Workplane] = field(default_factory=list)
    decorations: list[cq.Workplane] = field(default_factory=list)
    spec: RingSpec = None


def _band_outer_radius(spec: RingSpec) -> float:
    inner_r = get_inner_diameter(spec.band.us_size) / 2
    return inner_r + spec.band.thickness_mm


def _orient_for_ring_top(solid: cq.Workplane) -> cq.Workplane:
    """Rotate a solid built along +Z so it points radially outward (+X).

    +90° around Y maps (0,0,H) -> (H,0,0), so the top of the solid
    (which was at +Z) now faces +X (radially outward from the ring).
    """
    return solid.rotate((0, 0, 0), (0, 1, 0), 90)


def _place_at_top(
    solid: cq.Workplane,
    outer_r: float,
    penetration: float = 0.3,
) -> cq.Workplane:
    """Place a pre-oriented solid at the top of the ring."""
    oriented = _orient_for_ring_top(solid)
    return oriented.translate((outer_r - penetration, 0, 0))


def _place_at_angle(
    solid: cq.Workplane,
    outer_r: float,
    angle_deg: float,
    penetration: float = 0.3,
) -> cq.Workplane:
    """Place an oriented solid at an angular position around the ring."""
    placed = _place_at_top(solid, outer_r, penetration)
    return placed.rotate((0, 0, 0), (0, 0, 1), angle_deg)


_FINAL_ROTATION = ((0, 0, 0), (0, 0, 1), 90)


def _final_rotate(solid: cq.Workplane) -> cq.Workplane:
    """Apply the construction-to-display rotation."""
    origin, axis, angle = _FINAL_ROTATION
    return solid.rotate(origin, axis, angle)


def _get_volume(wp: cq.Workplane) -> float:
    """Get absolute volume, handling compounds and errors."""
    try:
        v = wp.val().Volume()
        if v != 0:
            return abs(v)
        return abs(sum(s.Volume() for s in wp.solids().vals()))
    except Exception:
        return 0.0


def _safe_union(base: cq.Workplane, addition: cq.Workplane) -> cq.Workplane:
    """Boolean union with integrity check.

    If the resulting volume is much smaller than the base volume, the
    union produced corrupt geometry and we reject it.
    """
    base_vol = _get_volume(base)
    try:
        result = base.union(addition)
        result_vol = _get_volume(result)
        if base_vol > 0 and result_vol < base_vol * 0.5:
            return base
        return result
    except Exception:
        return base


def _build_gallery(
    dims,
    band_width: float,
    band_thickness: float,
) -> cq.Workplane:
    """Build a gallery/pedestal connecting the ring band to the stone setting.

    Uses a simple box shape for robust boolean operations with the torus band.
    Built along +Z at the origin, oriented/placed by the caller.
    """
    base_hw = band_width / 2
    gallery_height = max(band_thickness * 0.8, 1.2)
    gallery_width = min(dims.width + 2.0, dims.width * 1.4)

    return (
        cq.Workplane("XY")
        .box(gallery_width, base_hw * 2, gallery_height,
             centered=(True, True, False))
    )


def build_ring(spec: RingSpec) -> RingAssembly:
    """Build the complete ring from a RingSpec.

    Structural parts (band + galleries + settings) are boolean-unioned into
    the ``metal`` solid.  Decorative elements are kept as separate solids in
    ``decorations`` to avoid cascading boolean corruption.
    """
    rng = _random.Random(spec.design_seed)
    outer_r = _band_outer_radius(spec)

    # --- Band ---
    metal = build_band(spec.band)
    display_stones: list[cq.Workplane] = []
    decoration_solids: list[cq.Workplane] = []

    # --- Centre stone setting ---
    if spec.center_stone:
        center_dims = get_stone_dimensions(spec.center_stone.cut, spec.center_stone.carat)
        center_setting = build_setting(spec.center_stone)

        gallery = _build_gallery(
            center_dims, spec.band.width_mm, spec.band.thickness_mm,
        )
        placed_gallery = _place_at_top(gallery, outer_r, penetration=1.2)
        metal = _safe_union(metal, placed_gallery)

        placed_setting = _place_at_top(center_setting, outer_r, penetration=0.5)
        metal = _safe_union(metal, placed_setting)

        stone_geo = build_stone_geometry(spec.center_stone)
        seat_depth = center_dims.depth * 0.6
        stone_rise = seat_depth * 0.4
        display_stones.append(
            _orient_for_ring_top(stone_geo)
            .translate((outer_r + stone_rise, 0, 0))
        )

    # --- Accent stone settings ---
    if spec.accent_stones:
        center_dims = None
        if spec.center_stone:
            center_dims = get_stone_dimensions(spec.center_stone.cut, spec.center_stone.carat)

        for stone_spec in spec.accent_stones:
            accent_dims = get_stone_dimensions(stone_spec.cut, stone_spec.carat)
            accent_setting = build_setting(stone_spec)

            gap = accent_dims.width / 2 + 1.5
            if center_dims:
                gap += center_dims.width / 2
            angle_offset_rad = gap / outer_r

            for copy_i in range(stone_spec.count):
                side = 1 if copy_i % 2 == 0 else -1
                multiplier = 1 + (copy_i // 2)
                angle_deg = math.degrees(side * angle_offset_rad * multiplier)

                accent_gallery = _build_gallery(
                    accent_dims, spec.band.width_mm, spec.band.thickness_mm,
                )
                placed_gallery = _place_at_angle(
                    accent_gallery, outer_r, angle_deg, penetration=1.2,
                )
                metal = _safe_union(metal, placed_gallery)

                placed = _place_at_angle(
                    accent_setting, outer_r, angle_deg, penetration=0.5,
                )
                metal = _safe_union(metal, placed)

                stone_geo = build_stone_geometry(stone_spec)
                stone_z_offset = accent_dims.depth * 0.6 * 0.4
                display_stones.append(
                    _orient_for_ring_top(stone_geo)
                    .translate((outer_r + stone_z_offset, 0, 0))
                    .rotate((0, 0, 0), (0, 0, 1), angle_deg)
                )

    # --- Decorative elements (kept separate to protect metal geometry) ---
    for i, elem in enumerate(spec.decorative_elements):
        deco_solid = build_decoration(elem, spec.band.thickness_mm)

        if elem.position == ElementPosition.SHANK_SIDES:
            base_angle = 35 + i * 20 + rng.uniform(-5, 5)
            for side in [1, -1]:
                placed = _place_at_angle(
                    deco_solid, outer_r, side * base_angle, penetration=0.5,
                )
                decoration_solids.append(placed)

        elif elem.position == ElementPosition.GALLERY:
            placed = _place_at_top(deco_solid, outer_r * 0.9, penetration=0.4)
            decoration_solids.append(placed)

        elif elem.position == ElementPosition.UNDER_SETTING:
            placed = (
                _orient_for_ring_top(deco_solid)
                .translate((outer_r - 0.5, 0, -spec.band.width_mm * 0.15))
            )
            decoration_solids.append(placed)

        elif elem.position == ElementPosition.FULL_SHANK:
            for j in range(4):
                angle = 90 * j + rng.uniform(-10, 10)
                placed = _place_at_angle(deco_solid, outer_r, angle, penetration=0.5)
                decoration_solids.append(placed)
        else:
            placed = _place_at_angle(deco_solid, outer_r, i * 30)
            decoration_solids.append(placed)

    # --- Final orientation for display ---
    metal = _final_rotate(metal)
    display_stones = [_final_rotate(s) for s in display_stones]
    decoration_solids = [_final_rotate(d) for d in decoration_solids]

    return RingAssembly(
        metal=metal,
        stones=display_stones,
        decorations=decoration_solids,
        spec=spec,
    )
