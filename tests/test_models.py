"""Unit tests for data models and jewelry domain data.

These tests do not require CadQuery and can run with just pydantic + pytest.
"""

import pytest

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
from ringbot.models.jewelry_data import (
    get_inner_diameter,
    get_material_props,
    get_stone_dimensions,
)


class TestStoneSpec:
    def test_valid_center_stone(self):
        s = StoneSpec(
            gem_type=GemType.DIAMOND,
            cut=CutType.ROUND_BRILLIANT,
            carat=2.0,
            role="center",
            setting_type=SettingType.COLLET,
            count=1,
        )
        assert s.carat == 2.0
        assert s.role == "center"

    def test_center_stone_must_have_count_1(self):
        with pytest.raises(Exception):
            StoneSpec(
                gem_type=GemType.DIAMOND,
                cut=CutType.ROUND_BRILLIANT,
                carat=1.0,
                role="center",
                setting_type=SettingType.PRONG,
                count=2,
            )

    def test_accent_stone_multiple(self):
        s = StoneSpec(
            gem_type=GemType.EMERALD,
            cut=CutType.MARQUISE,
            carat=0.3,
            role="accent",
            setting_type=SettingType.PRONG,
            count=2,
        )
        assert s.count == 2

    def test_invalid_carat(self):
        with pytest.raises(Exception):
            StoneSpec(
                gem_type=GemType.DIAMOND,
                cut=CutType.ROUND_BRILLIANT,
                carat=-1.0,
                role="center",
                setting_type=SettingType.PRONG,
            )


class TestBandSpec:
    def test_defaults(self):
        b = BandSpec()
        assert b.profile == BandProfile.COMFORT_FIT
        assert b.width_mm == 2.5
        assert b.us_size == 7.0

    def test_custom_values(self):
        b = BandSpec(
            profile=BandProfile.FLAT,
            width_mm=4.0,
            thickness_mm=2.0,
            material=Material.PLATINUM,
            us_size=9.0,
        )
        assert b.material == Material.PLATINUM

    def test_width_out_of_range(self):
        with pytest.raises(Exception):
            BandSpec(width_mm=0.5)

    def test_thickness_out_of_range(self):
        with pytest.raises(Exception):
            BandSpec(thickness_mm=5.0)


class TestRingSpec:
    def test_full_spec(self):
        spec = RingSpec(
            band=BandSpec(material=Material.GOLD_18K_YELLOW),
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
                )
            ],
            decorative_elements=[
                DecorativeElement(
                    element_type=ElementType.LEAF,
                    position=ElementPosition.SHANK_SIDES,
                    style=ElementStyle.ORGANIC,
                )
            ],
            description="Test ring",
        )
        assert spec.center_stone is not None
        assert len(spec.accent_stones) == 1
        assert spec.accent_stones[0].count == 2

    def test_minimal_spec(self):
        spec = RingSpec(description="Simple band")
        assert spec.center_stone is None
        assert spec.accent_stones == []


class TestJewelryData:
    def test_round_brilliant_2ct(self):
        dims = get_stone_dimensions(CutType.ROUND_BRILLIANT, 2.0)
        assert 7.5 < dims.diameter < 9.0
        assert dims.depth > 0

    def test_marquise_interpolation(self):
        dims = get_stone_dimensions(CutType.MARQUISE, 0.3)
        assert dims.length > dims.width
        assert dims.depth > 0

    def test_ring_size_7(self):
        d = get_inner_diameter(7.0)
        assert d == pytest.approx(17.3, abs=0.1)

    def test_ring_size_interpolation(self):
        d = get_inner_diameter(7.25)
        assert 17.3 < d < 17.7

    def test_material_props(self):
        gold = get_material_props("18k_yellow_gold")
        assert gold.density_g_cm3 > 10
        assert gold.min_wall_mm > 0

    def test_unknown_material(self):
        with pytest.raises(ValueError):
            get_material_props("unobtanium")


class TestAIPrompts:
    def test_system_prompt_not_empty(self):
        from ringbot.ai.prompts import SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 100
        assert "collet" in SYSTEM_PROMPT.lower()
        assert "prong" in SYSTEM_PROMPT.lower()
