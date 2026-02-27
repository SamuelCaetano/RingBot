"""Stone setting generators: bezel/collet, prong, and channel settings.

Each builder returns a CadQuery solid representing the metal setting,
positioned so its base sits at the origin on the XY plane.  The caller
(ring_builder) is responsible for translating it to the correct location
on the ring.
"""

from __future__ import annotations

import math

import cadquery as cq

from ringbot.models.jewelry_data import StoneDimensions, get_stone_dimensions
from ringbot.models.ring_spec import CutType, SettingType, StoneSpec

# Wall thickness around the stone in settings
_BEZEL_WALL = 0.8  # mm
_COLLET_WALL = 0.9
_PRONG_DIAMETER = 0.8  # mm
_PRONG_COUNT_DEFAULT = 4
_SEAT_DEPTH_FRACTION = 0.6  # stone sits 60% into the setting


def _is_round(cut: CutType) -> bool:
    return cut in (CutType.ROUND_BRILLIANT, CutType.CUSHION, CutType.ASSCHER, CutType.RADIANT)


def build_bezel_setting(stone: StoneSpec) -> cq.Workplane:
    """Full bezel: a metal rim encircling the stone completely."""
    dims = get_stone_dimensions(stone.cut, stone.carat)
    seat_depth = dims.depth * _SEAT_DEPTH_FRACTION
    total_height = seat_depth + 0.5  # 0.5mm lip above seat

    if _is_round(stone.cut):
        outer_r = dims.width / 2 + _BEZEL_WALL
        inner_r = dims.width / 2 + 0.05  # tiny clearance
        setting = (
            cq.Workplane("XY")
            .circle(outer_r)
            .circle(inner_r)
            .extrude(total_height)
        )
        base = cq.Workplane("XY").circle(outer_r).extrude(0.5)
        setting = setting.union(base)
    else:
        outer_l = dims.length / 2 + _BEZEL_WALL
        outer_w = dims.width / 2 + _BEZEL_WALL
        inner_l = dims.length / 2 + 0.05
        inner_w = dims.width / 2 + 0.05
        setting = (
            cq.Workplane("XY")
            .ellipse(outer_l, outer_w)
            .ellipse(inner_l, inner_w)
            .extrude(total_height)
        )
        base = cq.Workplane("XY").ellipse(outer_l, outer_w).extrude(0.5)
        setting = setting.union(base)

    return setting


def build_collet_setting(stone: StoneSpec) -> cq.Workplane:
    """Collet: a tapered cup/tube that holds the stone.  Similar to bezel
    but with a conical taper — wider at top, narrower at bottom."""
    dims = get_stone_dimensions(stone.cut, stone.carat)
    seat_depth = dims.depth * _SEAT_DEPTH_FRACTION
    total_height = seat_depth + 0.5
    taper_factor = 0.8  # bottom is 80% the diameter of the top

    if _is_round(stone.cut):
        top_outer_r = dims.width / 2 + _COLLET_WALL
        top_inner_r = dims.width / 2 + 0.05
        bot_outer_r = top_outer_r * taper_factor
        bot_inner_r = top_inner_r * taper_factor

        outer = (
            cq.Workplane("XY")
            .circle(bot_outer_r)
            .workplane(offset=total_height)
            .circle(top_outer_r)
            .loft()
        )
        inner = (
            cq.Workplane("XY")
            .circle(bot_inner_r)
            .workplane(offset=total_height)
            .circle(top_inner_r)
            .loft()
        )
        setting = outer.cut(inner)
    else:
        top_ol = dims.length / 2 + _COLLET_WALL
        top_ow = dims.width / 2 + _COLLET_WALL
        top_il = dims.length / 2 + 0.05
        top_iw = dims.width / 2 + 0.05

        outer = (
            cq.Workplane("XY")
            .ellipse(top_ol * taper_factor, top_ow * taper_factor)
            .workplane(offset=total_height)
            .ellipse(top_ol, top_ow)
            .loft()
        )
        inner = (
            cq.Workplane("XY")
            .ellipse(top_il * taper_factor, top_iw * taper_factor)
            .workplane(offset=total_height)
            .ellipse(top_il, top_iw)
            .loft()
        )
        setting = outer.cut(inner)

    return setting


def build_prong_setting(stone: StoneSpec, num_prongs: int | None = None) -> cq.Workplane:
    """Prong/claw setting: individual prongs gripping the stone."""
    dims = get_stone_dimensions(stone.cut, stone.carat)
    seat_depth = dims.depth * _SEAT_DEPTH_FRACTION
    prong_height = seat_depth + 1.0  # prongs extend above the seat
    prong_r = _PRONG_DIAMETER / 2

    if num_prongs is None:
        if stone.carat >= 1.5:
            num_prongs = 6
        else:
            num_prongs = _PRONG_COUNT_DEFAULT

    if _is_round(stone.cut):
        stone_r = dims.width / 2
        prong_orbit_r = stone_r + prong_r * 0.3  # prongs slightly overlap stone edge
    else:
        prong_orbit_r = max(dims.length, dims.width) / 2 + prong_r * 0.3

    base_ring_outer = prong_orbit_r + prong_r + 0.3
    base_ring_inner = prong_orbit_r - prong_r - 0.3
    if base_ring_inner < 0.5:
        base_ring_inner = 0.5

    base = (
        cq.Workplane("XY")
        .circle(base_ring_outer)
        .circle(base_ring_inner)
        .extrude(0.6)
    )

    result = base
    for i in range(num_prongs):
        angle = 2 * math.pi * i / num_prongs
        px = prong_orbit_r * math.cos(angle)
        py = prong_orbit_r * math.sin(angle)

        prong_bottom_r = prong_r * 1.2
        prong = (
            cq.Workplane("XY")
            .transformed(offset=(px, py, 0))
            .circle(prong_bottom_r)
            .workplane(offset=prong_height)
            .circle(prong_r * 0.7)
            .loft()
        )
        result = result.union(prong)

    return result


def build_channel_setting(stone: StoneSpec) -> cq.Workplane:
    """Channel setting: two parallel walls holding the stone between them."""
    dims = get_stone_dimensions(stone.cut, stone.carat)
    seat_depth = dims.depth * _SEAT_DEPTH_FRACTION
    wall_height = seat_depth + 0.3
    wall_thickness = 0.8
    gap = dims.width + 0.1  # tiny clearance

    total_width = gap + 2 * wall_thickness
    length = dims.length + 1.0  # extend beyond stone

    setting = (
        cq.Workplane("XY")
        .box(length, total_width, wall_height, centered=(True, True, False))
    )
    slot = (
        cq.Workplane("XY")
        .box(length + 0.1, gap, wall_height + 0.1, centered=(True, True, False))
    )
    setting = setting.cut(slot)

    base = (
        cq.Workplane("XY")
        .box(length, total_width, 0.5, centered=(True, True, False))
    )
    setting = setting.union(base)

    return setting


_SETTING_BUILDERS = {
    SettingType.BEZEL: build_bezel_setting,
    SettingType.COLLET: build_collet_setting,
    SettingType.PRONG: build_prong_setting,
    SettingType.CHANNEL: build_channel_setting,
    SettingType.PAVE: build_bezel_setting,  # simplified: treat pave as mini bezels
}


def build_setting(stone: StoneSpec) -> cq.Workplane:
    """Build the appropriate setting for a given stone spec."""
    builder = _SETTING_BUILDERS.get(stone.setting_type, build_prong_setting)
    return builder(stone)
