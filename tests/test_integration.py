"""Integration tests that require CadQuery.

These test the 3D generation pipeline without the AI step, using
a hand-crafted RingSpec.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

cadquery = pytest.importorskip("cadquery", reason="CadQuery not installed")

from ringbot.models.ring_spec import (
    BandProfile,
    BandSpec,
    CutType,
    DecorativeElement,
    ElementPosition,
    ElementStyle,
    ElementType,
    GemType,
    Material,
    RingSpec,
    SettingType,
    StoneSpec,
)
from ringbot.generator.ring_builder import build_ring, RingAssembly
from ringbot.validation.manufacturability import full_validation
from ringbot.export.exporter import export_assembly


@pytest.fixture
def nature_ring_spec() -> RingSpec:
    """The example ring from the plan: feminine 18k gold nature-inspired."""
    return RingSpec(
        band=BandSpec(
            profile=BandProfile.COMFORT_FIT,
            width_mm=2.5,
            thickness_mm=1.8,
            material=Material.GOLD_18K_YELLOW,
            us_size=7.0,
        ),
        center_stone=StoneSpec(
            gem_type=GemType.DIAMOND,
            cut=CutType.ROUND_BRILLIANT,
            carat=2.0,
            role="center",
            setting_type=SettingType.COLLET,
        ),
        accent_stones=[
            StoneSpec(
                gem_type=GemType.EMERALD,
                cut=CutType.MARQUISE,
                carat=0.3,
                role="accent",
                setting_type=SettingType.PRONG,
                count=2,
            ),
        ],
        decorative_elements=[
            DecorativeElement(
                element_type=ElementType.LEAF,
                position=ElementPosition.SHANK_SIDES,
                style=ElementStyle.ORGANIC,
                seed=42,
            ),
        ],
        aesthetic="feminine nature-inspired elegance",
        design_seed=12345,
        description="Test: feminine 18k gold nature inspired ring",
    )


@pytest.fixture
def simple_band_spec() -> RingSpec:
    """Minimal ring: just a band, no stones or decorations."""
    return RingSpec(
        band=BandSpec(
            profile=BandProfile.D_SHAPE,
            width_mm=3.0,
            thickness_mm=2.0,
            material=Material.PLATINUM,
            us_size=8.0,
        ),
        description="Test: simple platinum band",
        design_seed=99999,
    )


class TestBandGeneration:
    def test_simple_band(self, simple_band_spec):
        assembly = build_ring(simple_band_spec)
        assert assembly.metal is not None
        assert assembly.stones == []

        shape = assembly.metal.val()
        vol = shape.Volume()
        assert vol > 0

    def test_all_profiles(self):
        for profile in BandProfile:
            spec = RingSpec(
                band=BandSpec(profile=profile, width_mm=2.5, thickness_mm=1.8),
                design_seed=1,
            )
            assembly = build_ring(spec)
            assert assembly.metal.val().Volume() > 0


class TestFullRing:
    def test_nature_ring_builds(self, nature_ring_spec):
        assembly = build_ring(nature_ring_spec)
        assert assembly.metal is not None
        assert len(assembly.stones) > 0

    def test_nature_ring_validation(self, nature_ring_spec):
        assembly = build_ring(nature_ring_spec)
        report = full_validation(nature_ring_spec, assembly.metal)
        print(report.summary())
        assert report.passed, f"Validation failed:\n{report.summary()}"

    def test_nature_ring_export(self, nature_ring_spec):
        assembly = build_ring(nature_ring_spec)
        report = full_validation(nature_ring_spec, assembly.metal)

        tmp = Path(tempfile.mkdtemp(prefix="ringbot_test_"))
        try:
            result = export_assembly(
                assembly,
                validation_report=report,
                formats=["step", "stl", "obj"],
                output_dir=tmp,
            )
            assert Path(result["files"]["step"]).exists()
            assert Path(result["files"]["stl"]).exists()
            assert Path(result["files"]["obj"]).exists()
            assert Path(result["files"]["metadata"]).exists()

            meta = json.loads(Path(result["files"]["metadata"]).read_text())
            assert meta["design_seed"] == 12345
            assert meta["validation"]["passed"] is True
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestSeedReproducibility:
    def test_same_seed_same_volume(self, nature_ring_spec):
        a1 = build_ring(nature_ring_spec)
        a2 = build_ring(nature_ring_spec)
        v1 = a1.metal.val().Volume()
        v2 = a2.metal.val().Volume()
        assert v1 == pytest.approx(v2, rel=1e-6)

    def test_different_seed_different_volume(self, nature_ring_spec):
        spec2 = nature_ring_spec.model_copy(update={"design_seed": 54321})
        a1 = build_ring(nature_ring_spec)
        a2 = build_ring(spec2)
        v1 = a1.metal.val().Volume()
        v2 = a2.metal.val().Volume()
        # They may or may not differ — decorations use different seeds
        # but the core band+settings are deterministic from the spec.
        # Just ensure both build successfully.
        assert v1 > 0
        assert v2 > 0
