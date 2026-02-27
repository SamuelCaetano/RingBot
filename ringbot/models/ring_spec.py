"""Pydantic data models for the structured ring specification."""

from __future__ import annotations

import random
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class GemType(str, Enum):
    DIAMOND = "diamond"
    EMERALD = "emerald"
    RUBY = "ruby"
    SAPPHIRE = "sapphire"
    AMETHYST = "amethyst"
    TOPAZ = "topaz"
    OPAL = "opal"
    PEARL = "pearl"
    GARNET = "garnet"
    AQUAMARINE = "aquamarine"
    MORGANITE = "morganite"
    TANZANITE = "tanzanite"
    MOISSANITE = "moissanite"


class CutType(str, Enum):
    ROUND_BRILLIANT = "round_brilliant"
    PRINCESS = "princess"
    OVAL = "oval"
    MARQUISE = "marquise"
    PEAR = "pear"
    CUSHION = "cushion"
    EMERALD_CUT = "emerald_cut"
    ASSCHER = "asscher"
    RADIANT = "radiant"
    HEART = "heart"
    BAGUETTE = "baguette"


class SettingType(str, Enum):
    PRONG = "prong"
    BEZEL = "bezel"
    COLLET = "collet"
    CHANNEL = "channel"
    PAVE = "pave"


class BandProfile(str, Enum):
    D_SHAPE = "d_shape"
    FLAT = "flat"
    KNIFE_EDGE = "knife_edge"
    COMFORT_FIT = "comfort_fit"
    ROUNDED = "rounded"


class Material(str, Enum):
    GOLD_18K_YELLOW = "18k_yellow_gold"
    GOLD_18K_WHITE = "18k_white_gold"
    GOLD_18K_ROSE = "18k_rose_gold"
    GOLD_14K_YELLOW = "14k_yellow_gold"
    GOLD_14K_WHITE = "14k_white_gold"
    GOLD_14K_ROSE = "14k_rose_gold"
    PLATINUM = "platinum"
    SILVER_925 = "sterling_silver"


class ElementType(str, Enum):
    LEAF = "leaf"
    VINE = "vine"
    MILGRAIN = "milgrain"
    TWIST = "twist"
    FILIGREE = "filigree"
    SPLIT_SHANK = "split_shank"


class ElementPosition(str, Enum):
    SHANK_SIDES = "shank_sides"
    GALLERY = "gallery"
    UNDER_SETTING = "under_setting"
    FULL_SHANK = "full_shank"


class ElementStyle(str, Enum):
    ORGANIC = "organic"
    GEOMETRIC = "geometric"
    ART_DECO = "art_deco"
    VINTAGE = "vintage"
    MODERN = "modern"


class StoneSpec(BaseModel):
    gem_type: GemType
    cut: CutType
    carat: float = Field(gt=0, le=20.0)
    role: str = Field(pattern=r"^(center|accent)$")
    setting_type: SettingType
    count: int = Field(default=1, ge=1, le=50)

    @model_validator(mode="after")
    def validate_stone(self) -> "StoneSpec":
        if self.role == "center" and self.count != 1:
            raise ValueError("Center stone count must be 1")
        return self


class BandSpec(BaseModel):
    profile: BandProfile = BandProfile.COMFORT_FIT
    width_mm: float = Field(default=2.5, ge=1.5, le=15.0)
    thickness_mm: float = Field(default=1.8, ge=1.0, le=3.5)
    material: Material = Material.GOLD_18K_YELLOW
    us_size: float = Field(default=7.0, ge=3.0, le=16.0)


class DecorativeElement(BaseModel):
    element_type: ElementType
    position: ElementPosition = ElementPosition.SHANK_SIDES
    style: ElementStyle = ElementStyle.ORGANIC
    seed: int = Field(default_factory=lambda: random.randint(0, 2**31))


class RingSpec(BaseModel):
    band: BandSpec = Field(default_factory=BandSpec)
    center_stone: Optional[StoneSpec] = None
    accent_stones: list[StoneSpec] = Field(default_factory=list)
    decorative_elements: list[DecorativeElement] = Field(default_factory=list)
    aesthetic: str = "feminine"
    design_seed: int = Field(default_factory=lambda: random.randint(0, 2**31))
    description: str = ""
