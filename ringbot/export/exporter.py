"""Multi-format exporter: STEP, STL, OBJ with output directory management."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cadquery as cq

from ringbot.config import OUTPUT_DIR
from ringbot.generator.ring_builder import RingAssembly
from ringbot.validation.manufacturability import ValidationReport


def _make_output_dir(description: str) -> Path:
    """Create a timestamped + hash output directory."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    desc_hash = hashlib.md5(description.encode()).hexdigest()[:8]
    dirname = f"{ts}_{desc_hash}"
    out = OUTPUT_DIR / dirname
    out.mkdir(parents=True, exist_ok=True)
    return out


def export_step(solid: cq.Workplane, path: Path) -> Path:
    """Export to STEP format."""
    filepath = path / "ring_metal.step"
    cq.exporters.export(solid, str(filepath), exportType="STEP")
    return filepath


def export_stl(solid: cq.Workplane, path: Path, name: str = "ring_metal") -> Path:
    """Export to STL format."""
    filepath = path / f"{name}.stl"
    cq.exporters.export(solid, str(filepath), exportType="STL")
    return filepath


def export_obj(solid: cq.Workplane, path: Path, name: str = "ring_metal") -> Path:
    """Export to OBJ via STL -> trimesh conversion."""
    stl_path = path / f"_{name}_tmp.stl"
    obj_path = path / f"{name}.obj"

    cq.exporters.export(solid, str(stl_path), exportType="STL")

    try:
        import trimesh
        mesh = trimesh.load(str(stl_path))
        mesh.export(str(obj_path), file_type="obj")
    finally:
        if stl_path.exists():
            stl_path.unlink()

    return obj_path


def export_assembly(
    assembly: RingAssembly,
    validation_report: Optional[ValidationReport] = None,
    formats: Optional[list[str]] = None,
    output_dir: Optional[Path] = None,
) -> dict:
    """Export the full ring assembly to requested formats.

    Returns a dict with paths to all generated files and metadata.
    """
    if formats is None:
        formats = ["step", "stl", "obj"]

    out_dir = output_dir or _make_output_dir(assembly.spec.description)

    result = {"output_dir": str(out_dir), "files": {}}

    if "step" in formats:
        p = export_step(assembly.metal, out_dir)
        result["files"]["step"] = str(p)

    if "stl" in formats:
        p = export_stl(assembly.metal, out_dir)
        result["files"]["stl"] = str(p)

        for i, stone in enumerate(assembly.stones):
            sp = export_stl(stone, out_dir, name=f"stone_{i}")
            result["files"][f"stone_{i}_stl"] = str(sp)

        for i, deco in enumerate(getattr(assembly, "decorations", [])):
            try:
                dp = export_stl(deco, out_dir, name=f"deco_{i}")
                result["files"][f"deco_{i}_stl"] = str(dp)
            except Exception:
                pass

    if "obj" in formats:
        p = export_obj(assembly.metal, out_dir)
        result["files"]["obj"] = str(p)

    metadata = {
        "description": assembly.spec.description,
        "spec": assembly.spec.model_dump(mode="json"),
        "design_seed": assembly.spec.design_seed,
        "files": result["files"],
    }
    if validation_report:
        metadata["validation"] = {
            "passed": validation_report.passed,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "value": c.value,
                    "suggestion": c.suggestion,
                }
                for c in validation_report.checks
            ],
        }

    meta_path = out_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    result["files"]["metadata"] = str(meta_path)

    return result
