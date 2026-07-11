from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel
from rapidfuzz import fuzz


T = TypeVar("T")


class MatchCandidate(BaseModel, Generic[T]):
    item: T
    similarity: float
    osm_id: str
    osm_type: str
    osm_name: str

    @property
    def osm_url(self) -> str:
        prefix = "N" if self.osm_type == "node" else ("W" if self.osm_type == "way" else "R")
        return f"https://www.openstreetmap.org/{prefix}/{self.osm_id}"


class Matcher(ABC, Generic[T]):
    def __init__(self, exclude_words: list[str], threshold: float):
        self.exclude_words = [w.lower() for w in exclude_words]
        self.threshold = threshold

    def clean_name(self, name: str) -> str:
        import re
        name = name.lower()
        for sep in ["-", ",", ":", "–"]:
            name = name.replace(sep, " ")
        name = re.sub(r"\s+", " ", name).strip()
        words = [w for w in name.split() if w not in self.exclude_words]
        return " ".join(words)

    def similarity(self, name1: str, name2: str) -> float:
        cleaned1 = self.clean_name(name1)
        cleaned2 = self.clean_name(name2)
        return fuzz.token_sort_ratio(cleaned1, cleaned2) / 100.0

    @abstractmethod
    async def find_matches(self, wikidata_item: T) -> list[MatchCandidate[T]]:
        pass
