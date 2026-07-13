import uuid

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mof_bandgap.infrastructure.database.base import Base


class MofStructure(Base):
    __tablename__ = "mof_structures"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(unique=True, index=True)

    metal: Mapped[str | None]
    linker_code: Mapped[str | None]
    group: Mapped[str | None]
    metal2: Mapped[str | None]
    model: Mapped[str | None]

    volume: Mapped[float | None]
    density: Mapped[float | None]
    av_void_fraction: Mapped[float | None]
    gsa: Mapped[float | None]
    vsa: Mapped[float | None]
    lcd: Mapped[float | None]
    poav_void_fraction: Mapped[float | None]
    e_f: Mapped[float | None]
    e_b: Mapped[float | None]
    band_gap: Mapped[float | None]
    dbc_up: Mapped[float | None]
    dbc_down: Mapped[float | None]
    metal_center: Mapped[str | None]
    linker: Mapped[str | None]
