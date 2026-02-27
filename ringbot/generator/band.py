"""Band profile generation: create the ring band solid using CadQuery.

The band is built by drawing a 2D cross-section on the XZ plane (X = radial,
Y = world-Z height), offset from the Z axis by the ring radius, and then
revolving it around the Z axis.

Convention: ring centred at origin, finger-hole along Z axis.

Important CadQuery note: we use .moveTo() NOT .center() to offset the
profile, because .center() shifts the workplane origin and breaks the
default revolve axis (which needs to pass through the world origin).
"""

from __future__ import annotations

import math

import cadquery as cq

from ringbot.models.jewelry_data import get_inner_diameter
from ringbot.models.ring_spec import BandProfile, BandSpec


def _d_shape(wp: cq.Workplane, mid_r: float, inner_r: float, outer_r: float, hw: float) -> cq.Workplane:
    """D-shape: flat inside, domed outside."""
    return (
        wp
        .moveTo(inner_r, -hw)
        .lineTo(inner_r, hw)
        .threePointArc((outer_r, 0), (inner_r, -hw))
        .close()
    )


def _flat(wp: cq.Workplane, mid_r: float, inner_r: float, outer_r: float, hw: float) -> cq.Workplane:
    """Flat band: rectangular cross-section."""
    return (
        wp
        .moveTo(inner_r, -hw)
        .lineTo(outer_r, -hw)
        .lineTo(outer_r, hw)
        .lineTo(inner_r, hw)
        .close()
    )


def _knife_edge(wp: cq.Workplane, mid_r: float, inner_r: float, outer_r: float, hw: float) -> cq.Workplane:
    """Knife-edge: flat inside, pointed ridge outside."""
    return (
        wp
        .moveTo(inner_r, -hw)
        .lineTo(inner_r, hw)
        .lineTo(outer_r, 0)
        .close()
    )


def _comfort_fit(wp: cq.Workplane, mid_r: float, inner_r: float, outer_r: float, hw: float) -> cq.Workplane:
    """Comfort-fit: elliptical cross-section (rounded inside and outside)."""
    t = outer_r - inner_r
    return wp.moveTo(mid_r, 0).ellipse(t / 2, hw)


def _rounded(wp: cq.Workplane, mid_r: float, inner_r: float, outer_r: float, hw: float) -> cq.Workplane:
    """Circular cross-section."""
    r = min(outer_r - inner_r, hw * 2) / 2
    return wp.moveTo(mid_r, 0).circle(r)


_PROFILE_BUILDERS = {
    BandProfile.D_SHAPE: _d_shape,
    BandProfile.FLAT: _flat,
    BandProfile.KNIFE_EDGE: _knife_edge,
    BandProfile.COMFORT_FIT: _comfort_fit,
    BandProfile.ROUNDED: _rounded,
}


def build_band(spec: BandSpec) -> cq.Workplane:
    """Generate a ring band solid from a BandSpec.

    Returns a CadQuery Workplane with the band solid centred at the origin,
    finger-hole along Z.
    """
    inner_diam = get_inner_diameter(spec.us_size)
    inner_r = inner_diam / 2
    outer_r = inner_r + spec.thickness_mm
    mid_r = (inner_r + outer_r) / 2
    hw = spec.width_mm / 2  # half-width (in Z direction)

    wp = cq.Workplane("XZ")
    profile_fn = _PROFILE_BUILDERS.get(spec.profile, _comfort_fit)
    wp = profile_fn(wp, mid_r, inner_r, outer_r, hw)

    band = wp.revolve()
    return band
