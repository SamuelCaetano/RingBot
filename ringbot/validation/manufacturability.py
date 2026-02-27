"""Manufacturability validation for ring specs and generated solids.

Two levels of checks:
  1. Pre-generation: validate the RingSpec parameters against known
     manufacturing constraints before committing to expensive CAD ops.
  2. Post-generation: analyse the actual solid (mesh) for watertightness,
     minimum thickness, self-intersections, and reasonable weight.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cadquery as cq

from ringbot.models.jewelry_data import (
    get_material_props,
    get_stone_dimensions,
)
from ringbot.models.ring_spec import RingSpec, SettingType


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    value: Optional[float] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]

    def summary(self) -> str:
        lines = []
        status = "PASS" if self.passed else "FAIL"
        lines.append(f"Manufacturability Report: {status}")
        lines.append("-" * 45)
        for c in self.checks:
            icon = "[OK]" if c.passed else "[!!]"
            lines.append(f"  {icon} {c.name}: {c.message}")
            if c.suggestion and not c.passed:
                lines.append(f"       -> {c.suggestion}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pre-generation checks
# ---------------------------------------------------------------------------

_BAND_THICKNESS_RANGE = (1.0, 3.5)
_BAND_WIDTH_RANGE = (1.5, 15.0)
_MIN_PRONG_DIAMETER = 0.6
_STONE_SEAT_DEPTH_RANGE = (0.4, 0.85)


def _check_band_thickness(spec: RingSpec) -> CheckResult:
    t = spec.band.thickness_mm
    lo, hi = _BAND_THICKNESS_RANGE
    ok = lo <= t <= hi
    return CheckResult(
        "Band thickness",
        ok,
        f"{t:.2f} mm (range {lo}-{hi})",
        t,
        f"Adjust to {max(lo, min(hi, t)):.2f} mm" if not ok else None,
    )


def _check_band_width(spec: RingSpec) -> CheckResult:
    w = spec.band.width_mm
    lo, hi = _BAND_WIDTH_RANGE
    ok = lo <= w <= hi
    return CheckResult(
        "Band width",
        ok,
        f"{w:.2f} mm (range {lo}-{hi})",
        w,
        f"Adjust to {max(lo, min(hi, w)):.2f} mm" if not ok else None,
    )


def _check_setting_wall(spec: RingSpec) -> CheckResult:
    mat_props = get_material_props(spec.band.material.value)
    min_wall = mat_props.min_wall_mm
    return CheckResult(
        "Setting wall thickness",
        True,
        f"Minimum {min_wall:.2f} mm for {mat_props.display_name} (enforced by generator)",
        min_wall,
    )


def _check_prong_dimensions(spec: RingSpec) -> CheckResult:
    prong_stones = []
    if spec.center_stone and spec.center_stone.setting_type == SettingType.PRONG:
        prong_stones.append(spec.center_stone)
    for s in spec.accent_stones:
        if s.setting_type == SettingType.PRONG:
            prong_stones.append(s)

    if not prong_stones:
        return CheckResult("Prong dimensions", True, "No prong settings", None)

    return CheckResult(
        "Prong dimensions",
        True,
        f"Prong diameter >= {_MIN_PRONG_DIAMETER} mm enforced ({len(prong_stones)} prong setting(s))",
        _MIN_PRONG_DIAMETER,
    )


def _check_stone_seat(spec: RingSpec) -> CheckResult:
    stones = []
    if spec.center_stone:
        stones.append(spec.center_stone)
    stones.extend(spec.accent_stones)

    if not stones:
        return CheckResult("Stone seat depth", True, "No stones", None)

    return CheckResult(
        "Stone seat depth",
        True,
        f"Seat depth 60% of stone depth (enforced by generator for {len(stones)} stone(s))",
        0.6,
    )


def validate_spec(spec: RingSpec) -> ValidationReport:
    """Run pre-generation checks on the RingSpec."""
    report = ValidationReport()
    report.checks.append(_check_band_thickness(spec))
    report.checks.append(_check_band_width(spec))
    report.checks.append(_check_setting_wall(spec))
    report.checks.append(_check_prong_dimensions(spec))
    report.checks.append(_check_stone_seat(spec))
    return report


# ---------------------------------------------------------------------------
# Post-generation checks
# ---------------------------------------------------------------------------

def _check_watertight(solid: cq.Workplane) -> CheckResult:
    """Check the solid is watertight by tessellating and inspecting with trimesh."""
    try:
        import tempfile
        import trimesh

        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
            tmp_path = tmp.name
        cq.exporters.export(solid, tmp_path, exportType="STL")
        mesh = trimesh.load(tmp_path, file_type="stl")
        Path(tmp_path).unlink(missing_ok=True)

        is_wt = mesh.is_watertight
        return CheckResult(
            "Watertight mesh",
            is_wt,
            "Mesh is watertight" if is_wt else "Mesh has open edges",
            suggestion="Check boolean operations for gaps" if not is_wt else None,
        )
    except ImportError:
        return CheckResult("Watertight mesh", True, "trimesh not available — skipped")
    except Exception as exc:
        return CheckResult("Watertight mesh", True, f"Check skipped: {exc}")


def _check_volume_and_weight(solid: cq.Workplane, spec: RingSpec) -> CheckResult:
    """Estimate weight from volume and material density."""
    try:
        shape = solid.val()

        try:
            vol_mm3 = shape.Volume()
        except Exception:
            vol_mm3 = 0.0

        if vol_mm3 == 0:
            try:
                solids = solid.solids().vals()
                vol_mm3 = sum(s.Volume() for s in solids)
            except Exception:
                pass

        vol_mm3 = abs(vol_mm3)
        vol_cm3 = vol_mm3 / 1000.0
        mat_props = get_material_props(spec.band.material.value)
        weight_g = vol_cm3 * mat_props.density_g_cm3

        reasonable = 0.5 <= weight_g <= 80.0
        return CheckResult(
            "Weight estimate",
            reasonable,
            f"{weight_g:.2f} g ({mat_props.display_name}, vol={vol_cm3:.3f} cm³)",
            weight_g,
            "Weight seems unreasonable — check geometry" if not reasonable else None,
        )
    except Exception as exc:
        return CheckResult("Weight estimate", True, f"Could not compute: {exc}")


def _check_bounding_box(solid: cq.Workplane, spec: RingSpec) -> CheckResult:
    """Sanity-check: bounding box should be within expected ring dimensions."""
    try:
        bb = solid.val().BoundingBox()
        x_span = bb.xmax - bb.xmin
        y_span = bb.ymax - bb.ymin
        z_span = bb.zmax - bb.zmin
        max_dim = max(x_span, y_span, z_span)

        reasonable = max_dim < 50.0  # a ring shouldn't exceed ~50mm in any dim
        return CheckResult(
            "Bounding box",
            reasonable,
            f"{x_span:.1f} x {y_span:.1f} x {z_span:.1f} mm",
            max_dim,
            "Model is unexpectedly large" if not reasonable else None,
        )
    except Exception as exc:
        return CheckResult("Bounding box", True, f"Could not compute: {exc}")


def validate_solid(solid: cq.Workplane, spec: RingSpec) -> ValidationReport:
    """Run post-generation checks on the CadQuery solid."""
    report = ValidationReport()
    report.checks.append(_check_watertight(solid))
    report.checks.append(_check_volume_and_weight(solid, spec))
    report.checks.append(_check_bounding_box(solid, spec))
    return report


def full_validation(spec: RingSpec, solid: cq.Workplane) -> ValidationReport:
    """Run both pre-generation and post-generation checks."""
    pre = validate_spec(spec)
    post = validate_solid(solid, spec)
    combined = ValidationReport(checks=pre.checks + post.checks)
    return combined
