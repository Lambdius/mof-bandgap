from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass
class ScrapeResult:
    name:       str
    properties: dict[str, str]
    selections: dict[str, str | None]


@dataclass
class ResumePoint:
    metal:  str
    linker: str
    model:  str
    group:  str | None
    metal2: str | None


class Algorithm(Protocol):
    async def check_ready(self) -> bool: ...

    def run(self, resume: ResumePoint | None = None) -> AsyncIterator[ScrapeResult]: ...
