from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import Uuid, func, select  # pyright: ignore[reportMissingImports]
from sqlalchemy.ext.asyncio import AsyncSession  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import Mapped, mapped_column  # pyright: ignore[reportMissingImports]

from mof_bandgap.infrastructure.database.base import Base
from mof_bandgap.scraper.algorithms.base import ScrapeResult

logger = logging.getLogger(__name__)


class MofStructure(Base):
    __tablename__ = "mof_structures"

    id:         Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name:       Mapped[str]       = mapped_column(unique=True, index=True)
    has_file:   Mapped[bool]      = mapped_column(default=False)
    created_at: Mapped[datetime]  = mapped_column(server_default=func.now())

    metal:       Mapped[str | None]
    linker_code: Mapped[str | None]
    group:       Mapped[str | None]
    metal2:      Mapped[str | None]
    model:       Mapped[str | None]

    volume:             Mapped[float | None]
    density:            Mapped[float | None]
    av_void_fraction:   Mapped[float | None]
    gsa:                Mapped[float | None]
    vsa:                Mapped[float | None]
    lcd:                Mapped[float | None]
    poav_void_fraction: Mapped[float | None]
    e_f:                Mapped[float | None]
    e_b:                Mapped[float | None]
    band_gap:           Mapped[float | None]
    dbc_up:             Mapped[float | None]
    dbc_down:           Mapped[float | None]
    metal_center:       Mapped[str | None]
    linker:             Mapped[str | None]

    @staticmethod
    def _to_float(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @classmethod
    def from_scrape_result(cls, result: ScrapeResult) -> MofStructure:
        properties = result.properties
        selections = result.selections
        return cls(
            id                 = uuid.uuid4(),
            name               = result.name,
            metal              = selections.get("METAL"),
            linker_code        = selections.get("LINKER"),
            group              = selections.get("GROUP"),
            metal2             = selections.get("METAL2"),
            model              = selections.get("MODEL"),
            volume             = cls._to_float(properties.get("Volume")),
            density            = cls._to_float(properties.get("Density")),
            av_void_fraction   = cls._to_float(properties.get("AV_Void_Fraction")),
            gsa                = cls._to_float(properties.get("GSA")),
            vsa                = cls._to_float(properties.get("VSA")),
            lcd                = cls._to_float(properties.get("LCD")),
            poav_void_fraction = cls._to_float(properties.get("POAV_Void_Fraction")),
            e_f                = cls._to_float(properties.get("E_f")),
            e_b                = cls._to_float(properties.get("E_b")),
            band_gap           = cls._to_float(properties.get("Band_Gap")),
            dbc_up             = cls._to_float(properties.get("DBC_Up")),
            dbc_down           = cls._to_float(properties.get("DBC_Down")),
            metal_center       = properties.get("Metal_Center") or None,
            linker             = properties.get("Linker") or None,
        )


class StructuralDescriptors:
    COLUMNS = (
        MofStructure.volume,
        MofStructure.density,
        MofStructure.av_void_fraction,
        MofStructure.gsa,
        MofStructure.vsa,
        MofStructure.lcd,
        MofStructure.poav_void_fraction,
        MofStructure.e_f,
        MofStructure.e_b,
        MofStructure.dbc_up,
        MofStructure.dbc_down,
    )

    @classmethod
    async def defaults(cls, session: AsyncSession) -> dict[str | None, list[float]]:
        stmt = select(MofStructure.model, *(func.avg(column) for column in cls.COLUMNS)).group_by(MofStructure.model)
        rows = (await session.execute(stmt)).all()
        defaults = {row[0]: [float(value) if value is not None else 0.0 for value in row[1:]] for row in rows}
        logger.info("[Dataset] structural descriptor fallbacks by model (dataset mean per group): %s", defaults)
        return defaults

    @classmethod
    async def model_categories(cls, session: AsyncSession) -> list[str]:
        rows = (await session.execute(select(MofStructure.model).distinct())).scalars().all()
        categories = sorted({value for value in rows if value is not None})
        logger.info("[Dataset] model categories: %s", categories)
        return categories

    @staticmethod
    def for_structure(
        structure: MofStructure, defaults: dict[str | None, list[float]], model_categories: list[str]
    ) -> list[float]:
        values = (
            structure.volume,
            structure.density,
            structure.av_void_fraction,
            structure.gsa,
            structure.vsa,
            structure.lcd,
            structure.poav_void_fraction,
            structure.e_f,
            structure.e_b,
            structure.dbc_up,
            structure.dbc_down,
        )
        group_defaults = defaults.get(structure.model) or [0.0] * len(values)
        numeric = [
            value if value is not None else default for value, default in zip(values, group_defaults, strict=True)
        ]
        one_hot = [1.0 if structure.model == category else 0.0 for category in model_categories]
        return numeric + one_hot
