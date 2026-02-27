"""Decorative element generators: leaves, vines, milgrain, twists, filigree.

Each builder returns a CadQuery solid positioned at the origin.  The caller
translates / rotates it into place on the ring.  A random seed controls
parametric variation so each design is unique but reproducible.
"""

from __future__ import annotations

import math
import random as _random

import cadquery as cq

from ringbot.models.ring_spec import DecorativeElement, ElementType


def _seeded_rng(seed: int) -> _random.Random:
    return _random.Random(seed)


def build_leaf(element: DecorativeElement, band_thickness: float) -> cq.Workplane:
    """A single organic leaf shape built from spline curves.

    The leaf lies in the XZ plane, base at origin, tip along +X.
    Approx 3-5 mm long depending on randomised parameters.
    """
    rng = _seeded_rng(element.seed)
    length = 2.5 + rng.uniform(0, 1.5)  # 2.5-4.0 mm
    max_width = 1.0 + rng.uniform(0, 0.6)  # half-width
    thickness = 0.4 + rng.uniform(0, 0.2)

    bulge = 0.3 + rng.uniform(0, 0.3)

    pts_upper = [
        (0, 0),
        (length * 0.25, max_width * (0.7 + rng.uniform(-0.1, 0.1))),
        (length * (0.5 + rng.uniform(-0.05, 0.05)), max_width),
        (length * 0.75, max_width * (0.5 + rng.uniform(-0.1, 0.1))),
        (length, 0),
    ]
    pts_lower = [
        (0, 0),
        (length * 0.25, -max_width * (0.6 + rng.uniform(-0.1, 0.1))),
        (length * 0.5, -max_width * (0.9 + rng.uniform(-0.1, 0.1))),
        (length * 0.75, -max_width * (0.4 + rng.uniform(-0.1, 0.1))),
        (length, 0),
    ]

    leaf_2d = (
        cq.Workplane("XY")
        .spline(pts_upper)
        .spline(list(reversed(pts_lower)))
        .close()
    )

    leaf = leaf_2d.extrude(thickness)

    return leaf


def build_vine(element: DecorativeElement, band_thickness: float) -> cq.Workplane:
    """A thin vine/tendril: a swept circle along a wavy spline path."""
    rng = _seeded_rng(element.seed)
    vine_r = 0.25 + rng.uniform(0, 0.1)
    length = 4.0 + rng.uniform(0, 2.0)
    amplitude = 0.5 + rng.uniform(0, 0.5)

    n_pts = 6
    path_pts = []
    for i in range(n_pts):
        x = length * i / (n_pts - 1)
        y = amplitude * math.sin(2 * math.pi * i / (n_pts - 1) + rng.uniform(-0.3, 0.3))
        path_pts.append((x, y, 0))

    path = cq.Workplane("XY").spline(path_pts)
    vine = (
        cq.Workplane("YZ")
        .circle(vine_r)
        .sweep(path)
    )
    return vine


def build_milgrain(element: DecorativeElement, band_thickness: float) -> cq.Workplane:
    """A row of tiny beads (milgrain) along a straight line.

    Returns a series of small spheres fused together.
    """
    rng = _seeded_rng(element.seed)
    bead_r = 0.15 + rng.uniform(0, 0.05)
    count = 8 + rng.randint(0, 6)
    spacing = bead_r * 2.2
    total_length = spacing * (count - 1)

    result = None
    for i in range(count):
        x = -total_length / 2 + i * spacing
        bead = cq.Workplane("XY").transformed(offset=(x, 0, 0)).sphere(bead_r)
        if result is None:
            result = bead
        else:
            result = result.union(bead)

    return result


def build_twist(element: DecorativeElement, band_thickness: float) -> cq.Workplane:
    """A helical twist element — a small rod swept along a helix."""
    rng = _seeded_rng(element.seed)
    wire_r = 0.2 + rng.uniform(0, 0.1)
    length = 4.0 + rng.uniform(0, 2.0)
    pitch = 1.5 + rng.uniform(0, 0.5)
    helix_r = 0.4 + rng.uniform(0, 0.2)

    n_pts = 20
    path_pts = []
    for i in range(n_pts):
        t = i / (n_pts - 1)
        x = length * t
        y = helix_r * math.cos(2 * math.pi * t * length / pitch)
        z = helix_r * math.sin(2 * math.pi * t * length / pitch)
        path_pts.append((x, y, z))

    path = cq.Workplane("XY").spline(path_pts)
    twist = cq.Workplane("YZ").circle(wire_r).sweep(path)
    return twist


def build_filigree(element: DecorativeElement, band_thickness: float) -> cq.Workplane:
    """Simplified filigree: a set of curved wire loops."""
    rng = _seeded_rng(element.seed)
    wire_r = 0.18 + rng.uniform(0, 0.07)
    n_loops = 3 + rng.randint(0, 2)

    result = None
    for i in range(n_loops):
        angle_offset = rng.uniform(0, math.pi / 4)
        loop_r = 0.8 + rng.uniform(0, 0.4)
        cx = (i - n_loops / 2) * loop_r * 1.5
        cy = rng.uniform(-0.3, 0.3)

        loop_path = cq.Workplane("XY").transformed(offset=(cx, cy, 0)).circle(loop_r)
        loop = (
            cq.Workplane("XZ")
            .transformed(offset=(cx + loop_r, cy, 0))
            .circle(wire_r)
            .sweep(loop_path)
        )
        if result is None:
            result = loop
        else:
            result = result.union(loop)

    return result


_ELEMENT_BUILDERS = {
    ElementType.LEAF: build_leaf,
    ElementType.VINE: build_vine,
    ElementType.MILGRAIN: build_milgrain,
    ElementType.TWIST: build_twist,
    ElementType.FILIGREE: build_filigree,
}


def build_decoration(element: DecorativeElement, band_thickness: float) -> cq.Workplane:
    """Build a single decorative element solid."""
    builder = _ELEMENT_BUILDERS.get(element.element_type, build_leaf)
    return builder(element, band_thickness)
