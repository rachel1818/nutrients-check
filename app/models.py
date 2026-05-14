import re
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _make_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)


class Nutrient(Base):
    __tablename__ = "nutrients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    solubility: Mapped[str | None] = mapped_column(String(50), nullable=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    synonyms: Mapped[list["NutrientSynonym"]] = relationship(
        "NutrientSynonym", back_populates="nutrient", cascade="all, delete-orphan"
    )
    rda_values: Mapped[list["NutrientRdaValue"]] = relationship(
        "NutrientRdaValue", back_populates="nutrient", cascade="all, delete-orphan"
    )
    food_sources: Mapped[list["NutrientFoodSource"]] = relationship(
        "NutrientFoodSource", back_populates="nutrient", cascade="all, delete-orphan"
    )
    absorption_helpers: Mapped[list["NutrientAbsorptionHelper"]] = relationship(
        "NutrientAbsorptionHelper", back_populates="nutrient", cascade="all, delete-orphan"
    )
    absorption_blockers: Mapped[list["NutrientAbsorptionBlocker"]] = relationship(
        "NutrientAbsorptionBlocker", back_populates="nutrient", cascade="all, delete-orphan"
    )
    body_roles: Mapped[list["NutrientBodyRole"]] = relationship(
        "NutrientBodyRole", back_populates="nutrient", cascade="all, delete-orphan"
    )


@event.listens_for(Nutrient, "before_insert")
def set_slug(mapper, connection, target):
    if not target.slug:
        target.slug = _make_slug(target.name)


class NutrientSynonym(Base):
    __tablename__ = "nutrient_synonyms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nutrient_id: Mapped[int] = mapped_column(Integer, ForeignKey("nutrients.id"), nullable=False)
    synonym: Mapped[str] = mapped_column(String(255), nullable=False)

    nutrient: Mapped["Nutrient"] = relationship("Nutrient", back_populates="synonyms")


class NutrientRdaValue(Base):
    __tablename__ = "nutrient_rda_values"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nutrient_id: Mapped[int] = mapped_column(Integer, ForeignKey("nutrients.id"), nullable=False)
    age_group: Mapped[str] = mapped_column(String(50), nullable=False)
    sex: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    intake_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "RDA" or "AI"
    upper_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    nutrient: Mapped["Nutrient"] = relationship("Nutrient", back_populates="rda_values")
    source: Mapped["Source"] = relationship("Source")


class NutrientFoodSource(Base):
    __tablename__ = "nutrient_food_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nutrient_id: Mapped[int] = mapped_column(Integer, ForeignKey("nutrients.id"), nullable=False)
    food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    serving_size: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    bioavailability_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    preparation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    nutrient: Mapped["Nutrient"] = relationship("Nutrient", back_populates="food_sources")
    source: Mapped["Source"] = relationship("Source")


class NutrientAbsorptionHelper(Base):
    __tablename__ = "nutrient_absorption_helpers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nutrient_id: Mapped[int] = mapped_column(Integer, ForeignKey("nutrients.id"), nullable=False)
    helper_name: Mapped[str] = mapped_column(String(255), nullable=False)
    helper_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "nutrient" or "food"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    nutrient: Mapped["Nutrient"] = relationship("Nutrient", back_populates="absorption_helpers")
    source: Mapped["Source"] = relationship("Source")


class NutrientAbsorptionBlocker(Base):
    __tablename__ = "nutrient_absorption_blockers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nutrient_id: Mapped[int] = mapped_column(Integer, ForeignKey("nutrients.id"), nullable=False)
    blocker_name: Mapped[str] = mapped_column(String(255), nullable=False)
    blocker_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "nutrient" or "food"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    nutrient: Mapped["Nutrient"] = relationship("Nutrient", back_populates="absorption_blockers")
    source: Mapped["Source"] = relationship("Source")


class NutrientBodyRole(Base):
    __tablename__ = "nutrient_body_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nutrient_id: Mapped[int] = mapped_column(Integer, ForeignKey("nutrients.id"), nullable=False)
    body_system: Mapped[str] = mapped_column(String(100), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    deficiency_signs: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    nutrient: Mapped["Nutrient"] = relationship("Nutrient", back_populates="body_roles")
    source: Mapped["Source"] = relationship("Source")


# Database indexes
Index("ix_nutrients_name", Nutrient.name)
Index("ix_nutrients_slug", Nutrient.slug, unique=True)
Index("ix_synonyms_synonym", NutrientSynonym.synonym)
Index("ix_food_sources_nutrient_id", NutrientFoodSource.nutrient_id)
