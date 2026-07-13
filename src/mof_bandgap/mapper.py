import uuid

from mof_bandgap.infrastructure.database.models import MofStructure
from mof_bandgap.scraper.algorithms.base import ScrapeResult


class Mapper:
    @staticmethod
    def to_float(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def to_structure(result: ScrapeResult) -> MofStructure:
        properties = result.properties
        selections = result.selections
        return MofStructure(
            id=uuid.uuid4(),
            name=result.name,
            metal=selections.get("METAL"),
            linker_code=selections.get("LINKER"),
            group=selections.get("GROUP"),
            metal2=selections.get("METAL2"),
            model=selections.get("MODEL"),
            volume=Mapper.to_float(properties.get("Volume")),
            density=Mapper.to_float(properties.get("Density")),
            av_void_fraction=Mapper.to_float(properties.get("AV_Void_Fraction")),
            gsa=Mapper.to_float(properties.get("GSA")),
            vsa=Mapper.to_float(properties.get("VSA")),
            lcd=Mapper.to_float(properties.get("LCD")),
            poav_void_fraction=Mapper.to_float(properties.get("POAV_Void_Fraction")),
            e_f=Mapper.to_float(properties.get("E_f")),
            e_b=Mapper.to_float(properties.get("E_b")),
            band_gap=Mapper.to_float(properties.get("Band_Gap")),
            dbc_up=Mapper.to_float(properties.get("DBC_Up")),
            dbc_down=Mapper.to_float(properties.get("DBC_Down")),
            metal_center=properties.get("Metal_Center") or None,
            linker=properties.get("Linker") or None,
        )
