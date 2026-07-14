import asyncio
import logging
import os
from collections.abc import AsyncIterator
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mof_bandgap.constants import FEATURES_COMMIT_BATCH_SIZE, METAL_DESCRIPTOR_NAMES
from mof_bandgap.infrastructure.database.models import Features, MofFeatures, MofStructure
from mof_bandgap.train.dataset import Sample
from mof_bandgap.train.descriptors import linker_descriptors, linker_fingerprint, metal_descriptors
from mof_bandgap.train.linker import extract_linker_molecule, molecule_to_smiles

logger = logging.getLogger(__name__)


def available_cpu_count() -> int:
    try:
        with open("/sys/fs/cgroup/cpu.max") as f:
            quota, period = f.read().split()
        if quota != "max":
            n = max(1, int(quota) // int(period))
            logger.info("[Train] cgroup v2 cpu.max reports %d usable core(s)", n)
            return n
    except (FileNotFoundError, ValueError):
        pass

    try:
        with open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us") as f:
            quota_us = int(f.read())
        with open("/sys/fs/cgroup/cpu/cpu.cfs_period_us") as f:
            period_us = int(f.read())
        if quota_us > 0:
            n = max(1, quota_us // period_us)
            logger.info("[Train] cgroup v1 cfs_quota reports %d usable core(s)", n)
            return n
    except (FileNotFoundError, ValueError):
        pass

    try:
        n = len(os.sched_getaffinity(0))  # type: ignore[attr-defined]
        logger.info("[Train] os.sched_getaffinity reports %d usable core(s)", n)
        return n
    except AttributeError:
        pass

    n = os.cpu_count() or 1
    logger.info("[Train] no cgroup limit found, falling back to os.cpu_count(): %d core(s)", n)
    return n


STRUCTURAL_COLUMNS = (
    MofStructure.volume,
    MofStructure.density,
    MofStructure.av_void_fraction,
    MofStructure.gsa,
    MofStructure.vsa,
    MofStructure.lcd,
    MofStructure.poav_void_fraction,
)


async def _structural_defaults(session: AsyncSession) -> list[float]:
    row = (await session.execute(select(*(func.avg(column) for column in STRUCTURAL_COLUMNS)))).one()
    defaults = [float(value) if value is not None else 0.0 for value in row]
    logger.info("[Train] structural descriptor fallbacks (dataset mean, 0.0 if unavailable): %s", defaults)
    return defaults


def _structural_descriptors(structure: MofStructure, defaults: list[float]) -> list[float]:
    values = (
        structure.volume,
        structure.density,
        structure.av_void_fraction,
        structure.gsa,
        structure.vsa,
        structure.lcd,
        structure.poav_void_fraction,
    )
    return [value if value is not None else default for value, default in zip(values, defaults, strict=True)]


@dataclass
class BuildOutcome:
    name: str
    features: Features | None
    smiles: str | None
    reason: str | None


def _build_features(
    name: str,
    cif_text: str,
    metal: str,
    metal2: str | None,
    band_gap: float,
    structural_descriptors: list[float],
) -> BuildOutcome:
    metal_symbols = {symbol for symbol in (metal, metal2) if symbol}

    molecule = extract_linker_molecule(cif_text, metal_symbols)
    if molecule is None:
        return BuildOutcome(name=name, features=None, smiles=None, reason="no linker found")

    smiles = molecule_to_smiles(molecule)
    if smiles is None:
        return BuildOutcome(name=name, features=None, smiles=None, reason="could not derive smiles")

    lig_desc = linker_descriptors(smiles)
    fingerprint = linker_fingerprint(smiles)
    if lig_desc is None or fingerprint is None:
        return BuildOutcome(name=name, features=None, smiles=None, reason="descriptor computation failed")

    metal2_desc = metal_descriptors(metal2) if metal2 else [0.0] * len(METAL_DESCRIPTOR_NAMES)
    features = Features(
        name=name,
        metal_descriptors=metal_descriptors(metal),
        metal2_descriptors=metal2_desc,
        has_interior_metal=float(bool(metal2)),
        linker_descriptors=lig_desc,
        linker_fingerprint=fingerprint,
        structural_descriptors=structural_descriptors,
        band_gap=band_gap,
    )
    return BuildOutcome(name=name, features=features, smiles=smiles, reason=None)


async def iter_features(session: AsyncSession, samples: AsyncIterator[Sample]) -> AsyncIterator[Features]:
    built = 0
    cached = 0
    skipped = 0
    uncommitted = 0

    cached_rows = {row.mof_structure_id: row for row in (await session.execute(select(MofFeatures))).scalars().all()}
    logger.info("[Train] %d structure(s) already present in mof_features", len(cached_rows))

    structural_defaults = await _structural_defaults(session)

    to_build: list[MofStructure] = []
    cif_by_name: dict[str, str] = {}

    async for sample in samples:
        structure = sample.structure
        logger.info(
            "[Train] %s: received from dataset (metal=%s, metal2=%s, band_gap=%s)",
            structure.name,
            structure.metal,
            structure.metal2,
            structure.band_gap,
        )

        if structure.metal is None or structure.band_gap is None:
            logger.warning("[Train] skipping %s: missing metal or band gap", structure.name)
            skipped += 1
            continue

        cached_row = cached_rows.get(structure.id)
        if cached_row is not None:
            cached += 1
            logger.info("[Train] %s: using cached features", structure.name)
            yield cached_row.to_features(
                structure.name, structure.band_gap, _structural_descriptors(structure, structural_defaults)
            )
            continue

        to_build.append(structure)
        cif_by_name[structure.name] = sample.cif.decode()

    logger.info("[Train] %d structure(s) queued for feature extraction", len(to_build))

    if not to_build:
        logger.info("[Train] features: %d built, %d cached, %d skipped", built, cached, skipped)
        return

    worker_count = available_cpu_count()
    logger.info("[Train] launching process pool with %d worker(s) for %d structure(s)", worker_count, len(to_build))

    id_by_name = {structure.name: structure.id for structure in to_build}
    loop = asyncio.get_running_loop()

    executor = ProcessPoolExecutor(max_workers=worker_count)
    try:
        futures = []
        for structure in to_build:
            assert structure.metal is not None
            assert structure.band_gap is not None
            futures.append(
                loop.run_in_executor(
                    executor,
                    _build_features,
                    structure.name,
                    cif_by_name[structure.name],
                    structure.metal,
                    structure.metal2,
                    structure.band_gap,
                    _structural_descriptors(structure, structural_defaults),
                )
            )
            logger.info("[Train] %s: dispatched to worker pool", structure.name)

        for future in asyncio.as_completed(futures):
            outcome: BuildOutcome = await future
            logger.info("[Train] %s: worker finished (ok=%s)", outcome.name, outcome.features is not None)

            if outcome.features is None or outcome.smiles is None:
                logger.warning("[Train] skipping %s: %s", outcome.name, outcome.reason)
                skipped += 1
                continue

            structure_id = id_by_name[outcome.name]
            session.add(MofFeatures.from_features(structure_id, outcome.smiles, outcome.features))
            built += 1
            uncommitted += 1
            logger.info("[Train] %s: added to session (uncommitted=%d)", outcome.name, uncommitted)

            if uncommitted >= FEATURES_COMMIT_BATCH_SIZE:
                logger.info("[Train] committing batch of %d row(s)", uncommitted)
                await session.commit()
                uncommitted = 0

            yield outcome.features
    finally:
        logger.info("[Train] shutting down worker pool")
        for process in executor._processes.values():
            if process.is_alive():
                logger.warning("[Train] force-killing stuck worker pid=%s", process.pid)
                process.kill()
        executor.shutdown(wait=False, cancel_futures=True)

    if uncommitted:
        logger.info("[Train] committing final batch of %d row(s)", uncommitted)
        await session.commit()

    logger.info("[Train] features: %d built, %d cached, %d skipped", built, cached, skipped)
