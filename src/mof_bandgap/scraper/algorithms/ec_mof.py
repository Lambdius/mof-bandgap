import logging
from collections.abc import AsyncIterator

from mof_bandgap.constants import (
    EXPECTED_SELECT_COUNT,
    HIDDEN_CLASS,
    LOAD_BUTTON_NAME,
    MOFSDB_URL_PATTERN,
    Field,
)
from mof_bandgap.scraper.algorithms.base import Algorithm, ResumePoint, ScrapeResult
from mof_bandgap.scraper.browser import Browser
from mof_bandgap.scraper.parser import parse_properties

logger = logging.getLogger(__name__)


class EcMofAlgorithm(Algorithm):
    def __init__(self, browser: Browser) -> None:
        self._browser = browser

    async def check_ready(self) -> bool:
        if await self._browser.select_count() != EXPECTED_SELECT_COUNT:
            return False
        return await self._browser.button_visible(LOAD_BUTTON_NAME)

    async def field_options(self, field: Field, *, by_label: bool = False) -> list[str]:
        all_options = await self._browser.select(field.value).locator("option").all()
        options = [option for option in all_options if not await option.is_disabled()]

        if by_label:
            labels = [await option.text_content() for option in options]
            return [label.strip() for label in labels if label and label.strip()]

        values = [await option.get_attribute("value") for option in options]
        return [value for value in values if value]

    async def is_field_visible(self, field: Field) -> bool:
        select = self._browser.select(field.value)
        return not await self._browser.has_ancestor_with_class(select, HIDDEN_CLASS)

    async def select(self, field: Field, value: str, *, by_label: bool = False) -> None:
        select = self._browser.select(field.value)
        if by_label:
            await select.select_option(label=value)
        else:
            await select.select_option(value)
        logger.info("[Scrap] select %s = %s", field.name, value)

    async def _try_submit(
        self, *, metal: str, linker: str, model: str, group: str | None, metal2: str | None
    ) -> ScrapeResult | None:
        logger.info(
            "[Scrap] submit metal=%s linker=%s model=%s group=%s metal2=%s",
            metal,
            linker,
            model,
            group,
            metal2,
        )
        response = await self._browser.submit(LOAD_BUTTON_NAME, MOFSDB_URL_PATTERN)

        text = await response.text()
        properties = parse_properties(text)
        if properties is None:
            logger.warning(
                "[Scrap] unparsable response status=%s url=%s body=%r",
                response.status,
                response.url,
                text[:500],
            )
            return None

        name = response.url.split("q=", 1)[1]
        logger.info("[Scrap] loaded %s: %s", name, properties)
        return ScrapeResult(
            name       = name,
            properties = properties,
            selections = {
                "METAL":  metal,
                "LINKER": linker,
                "GROUP":  group,
                "METAL2": metal2,
                "MODEL":  model
            },
        )

    async def run(self, resume: ResumePoint | None = None) -> AsyncIterator[ScrapeResult]:
        metals  = await self.field_options(Field.METAL)
        linkers = await self.field_options(Field.LINKER, by_label=True)
        models  = await self.field_options(Field.MODEL)
        groups  = await self.field_options(Field.GROUP)
        metal2s = await self.field_options(Field.METAL2)

        skipping = resume is not None

        for metal in metals:
            await self.select(Field.METAL, metal)

            for linker in linkers:
                await self.select(Field.LINKER, linker, by_label=True)

                for model in models:
                    await self.select(Field.MODEL, model)

                    if not await self.is_field_visible(Field.GROUP):
                        if skipping:
                            if resume is not None and (metal, linker, model, None, None) == (
                                resume.metal,
                                resume.linker,
                                resume.model,
                                resume.group,
                                resume.metal2,
                            ):
                                skipping = False
                            continue
                        result = await self._try_submit(
                            metal=metal, linker=linker, model=model, group=None, metal2=None
                        )
                        if result is not None:
                            yield result
                        continue

                    for group in groups:
                        await self.select(Field.GROUP, group)

                        if not await self.is_field_visible(Field.METAL2):
                            if skipping:
                                if resume is not None and (metal, linker, model, group, None) == (
                                    resume.metal,
                                    resume.linker,
                                    resume.model,
                                    resume.group,
                                    resume.metal2,
                                ):
                                    skipping = False
                                continue
                            result = await self._try_submit(
                                metal=metal, linker=linker, model=model, group=group, metal2=None
                            )
                            if result is not None:
                                yield result
                            continue

                        for metal2 in metal2s:
                            await self.select(Field.METAL2, metal2)

                            if skipping:
                                if resume is not None and (metal, linker, model, group, metal2) == (
                                    resume.metal,
                                    resume.linker,
                                    resume.model,
                                    resume.group,
                                    resume.metal2,
                                ):
                                    skipping = False
                                continue

                            result = await self._try_submit(
                                metal=metal, linker=linker, model=model, group=group, metal2=metal2
                            )
                            if result is not None:
                                yield result

        if skipping:
            logger.warning("[Scrap] resume point %s was never reached — nothing was submitted", resume)
