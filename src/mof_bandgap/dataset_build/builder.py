import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from sqlalchemy import select  # pyright: ignore[reportMissingImports]
from sqlalchemy.ext.asyncio import AsyncSession  # pyright: ignore[reportMissingImports]

from mof_bandgap.constants import DATASET_COMMIT_BATCH_SIZE, METAL_DESCRIPTOR_NAMES
from mof_bandgap.dataset_build.cpu import available_cpu_count
from mof_bandgap.dataset_build.descriptors import linker_descriptors, linker_fingerprint, metal_descriptors
from mof_bandgap.dataset_build.graph import build_crystal_graph
from mof_bandgap.dataset_build.linker import extract_linker_molecule, molecule_to_smiles
from mof_bandgap.dataset_build.samples import Sample
from mof_bandgap.infrastructure.database.models import Features, MofDataset, MofStructure, StructuralDescriptors

logger = logging.getLogger(__name__)


@dataclass
class BuildOutcome:
    name:     str
    features: Features | None
    smiles:   str | None
    reason:   str | None


def _build_dataset_row(
    name:                   str,
    cif_text:               str,
    metal:                  str,
    metal2:                 str | None,
    band_gap:               float,
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

    graph = build_crystal_graph(cif_text)
    if graph is None:
        return BuildOutcome(name=name, features=None, smiles=None, reason="graph construction failed")

    metal2_desc = metal_descriptors(metal2) if metal2 else [0.0] * len(METAL_DESCRIPTOR_NAMES)
    features = Features(
        name                   = name,
        metal_descriptors      = metal_descriptors(metal),
        metal2_descriptors     = metal2_desc,
        has_interior_metal     = float(bool(metal2)),
        linker_descriptors     = lig_desc,
        linker_fingerprint     = fingerprint,
        structural_descriptors = structural_descriptors,
        atomic_numbers         = graph.atomic_numbers,
        edge_index             = graph.edge_index,
        edge_distances         = graph.edge_distances,
        band_gap               = band_gap,
    )
    return BuildOutcome(name=name, features=features, smiles=smiles, reason=None)


class DatasetBuilder:
    def __init__(self, session: AsyncSession) -> None:
        self._session     = session
        self._built       = 0
        self._cached      = 0
        self._skipped     = 0
        self._uncommitted = 0

    async def build(self, samples: AsyncIterator[Sample]) -> AsyncIterator[Features]:
        cached_rows = await self._load_cache()
        structural_defaults = await StructuralDescriptors.defaults(self._session)
        model_categories = await StructuralDescriptors.model_categories(self._session)

        to_build: list[MofStructure] = []
        cif_by_name: dict[str, str] = {}

        async for sample in samples:
            structure = sample.structure

            if structure.metal is None or structure.band_gap is None:
                logger.warning("[Dataset] skipping %s: missing metal or band gap", structure.name)
                self._skipped += 1
                self._report_progress()
                continue

            cached_row = cached_rows.get(structure.id)
            if cached_row is not None:
                self._cached += 1
                self._report_progress()
                yield cached_row.to_features(
                    structure.name,
                    structure.band_gap,
                    StructuralDescriptors.for_structure(structure, structural_defaults, model_categories),
                )
                continue

            to_build.append(structure)
            cif_by_name[structure.name] = sample.cif.decode()

        if to_build:
            async for features in self._build_remaining(to_build, cif_by_name, structural_defaults, model_categories):
                yield features

        print()
        logger.info("[Dataset] datasets: %d built, %d cached, %d skipped", self._built, self._cached, self._skipped)

    async def _load_cache(self) -> dict[uuid.UUID, MofDataset]:
        rows = (await self._session.execute(select(MofDataset))).scalars().all()
        logger.info("[Dataset] %d structure(s) already present in datasets", len(rows))
        return {row.mof_structure_id: row for row in rows}

    async def _build_remaining(
        self,
        to_build: list[MofStructure],
        cif_by_name: dict[str, str],
        structural_defaults: dict[str | None, list[float]],
        model_categories: list[str],
    ) -> AsyncIterator[Features]:
        worker_count = available_cpu_count()
        logger.info(
            "[Dataset] launching process pool with %d worker(s) for %d structure(s)", worker_count, len(to_build)
        )

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
                        _build_dataset_row,
                        structure.name,
                        cif_by_name[structure.name],
                        structure.metal,
                        structure.metal2,
                        structure.band_gap,
                        StructuralDescriptors.for_structure(structure, structural_defaults, model_categories),
                    )
                )

            for future in asyncio.as_completed(futures):
                outcome: BuildOutcome = await future

                if outcome.features is None or outcome.smiles is None:
                    logger.warning("[Dataset] skipping %s: %s", outcome.name, outcome.reason)
                    self._skipped += 1
                    self._report_progress()
                    continue

                structure_id = id_by_name[outcome.name]
                await self._persist(structure_id, outcome.smiles, outcome.features)
                self._report_progress()
                yield outcome.features
        finally:
            self._shutdown(executor)

        if self._uncommitted:
            await self._session.commit()
            self._uncommitted = 0

    async def _persist(self, structure_id: uuid.UUID, smiles: str, features: Features) -> None:
        self._session.add(MofDataset.from_features(structure_id, smiles, features))
        self._built += 1
        self._uncommitted += 1

        if self._uncommitted >= DATASET_COMMIT_BATCH_SIZE:
            await self._session.commit()
            self._uncommitted = 0

    def _report_progress(self) -> None:
        print(
            f"\r[Dataset] datasets: {self._built} built, {self._cached} cached, {self._skipped} skipped",
            end="",
            flush=True,
        )

    @staticmethod
    def _shutdown(executor: ProcessPoolExecutor) -> None:
        for process in executor._processes.values():
            if process.is_alive():
                logger.warning("[Dataset] force-killing stuck worker pid=%s", process.pid)
                process.kill()
        executor.shutdown(wait=False, cancel_futures=True)
