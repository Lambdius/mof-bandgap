import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from mof_bandgap.constants import METAL_DESCRIPTOR_NAMES
from mof_bandgap.infrastructure.database.models import Features, MofFeatures
from mof_bandgap.train.dataset import Sample
from mof_bandgap.train.descriptors import linker_descriptors, linker_fingerprint, metal_descriptors
from mof_bandgap.train.linker import extract_linker_molecule, molecule_to_smiles

logger = logging.getLogger(__name__)


async def iter_features(session: AsyncSession, samples: AsyncIterator[Sample]) -> AsyncIterator[Features]:
    built = 0
    cached = 0
    skipped = 0

    async for sample in samples:
        structure = sample.structure

        if structure.metal is None or structure.band_gap is None:
            logger.warning("[Train] skipping %s: missing metal or band gap", structure.name)
            skipped += 1
            continue

        cached_row = await session.get(MofFeatures, structure.id)
        if cached_row is not None:
            cached += 1
            yield cached_row.to_features(structure.name, structure.band_gap)
            continue

        metal_symbols = {symbol for symbol in (structure.metal, structure.metal2) if symbol}

        molecule = extract_linker_molecule(sample.cif.decode(), metal_symbols)
        if molecule is None:
            logger.warning("[Train] skipping %s: no linker found", structure.name)
            skipped += 1
            continue

        smiles = molecule_to_smiles(molecule)
        if smiles is None:
            logger.warning("[Train] skipping %s: could not derive smiles", structure.name)
            skipped += 1
            continue

        lig_desc = linker_descriptors(smiles)
        fingerprint = linker_fingerprint(smiles)
        if lig_desc is None or fingerprint is None:
            logger.warning("[Train] skipping %s: descriptor computation failed", structure.name)
            skipped += 1
            continue

        metal2_desc = (
            metal_descriptors(structure.metal2) if structure.metal2 else [0.0] * len(METAL_DESCRIPTOR_NAMES)
        )

        features = Features(
            name=structure.name,
            metal_descriptors=metal_descriptors(structure.metal),
            metal2_descriptors=metal2_desc,
            has_interior_metal=float(bool(structure.metal2)),
            linker_descriptors=lig_desc,
            linker_fingerprint=fingerprint,
            band_gap=structure.band_gap,
        )

        session.add(MofFeatures.from_features(structure.id, smiles, features))
        await session.commit()

        built += 1
        yield features

    logger.info("[Train] features: %d built, %d cached, %d skipped", built, cached, skipped)
