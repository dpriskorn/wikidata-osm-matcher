from typing import Any
from clients.wikidata import WikidataItem, WikidataClient
from clients.overpass import OverpassClient
from matcher.base import Matcher, MatchCandidate
from config import ObjectTypeConfig


class NameMatcher(Matcher[WikidataItem]):
    def __init__(
        self,
        config: ObjectTypeConfig,
        wikidata_client: WikidataClient,
        overpass_client: OverpassClient,
    ):
        super().__init__(
            exclude_words=config.matching.exclude_words,
            threshold=config.matching.similarity_threshold,
        )
        self.config = config
        self.wikidata = wikidata_client
        self.overpass = overpass_client

    async def find_matches(self, wikidata_item: WikidataItem) -> list[MatchCandidate[WikidataItem]]:
        bbox = self._get_bbox(wikidata_item)
        query = self.config.overpass.query.replace("{{bbox}}", bbox)

        raw_results = await self.overpass.query(query)
        osm_items = self.overpass.parse_results(raw_results)

        candidates = []
        for osm in osm_items:
            sim = self.similarity(wikidata_item.label, osm.name)
            if sim >= self.threshold:
                candidates.append(MatchCandidate(
                    item=wikidata_item,
                    similarity=sim,
                    osm_id=osm.osm_id,
                    osm_type=osm.osm_type,
                    osm_name=osm.name,
                ))

        candidates.sort(key=lambda c: c.similarity, reverse=True)
        return candidates

    def _get_bbox(self, item: WikidataItem) -> str:
        if self.config.overpass.country_bbox_map and item.country:
            return self.config.overpass.country_bbox_map.get(
                item.country,
                self.config.overpass.fallback_bbox or "55.5,10.5,69.5,24.5"
            )
        return self.config.overpass.fallback_bbox or "55.5,10.5,69.5,24.5"
