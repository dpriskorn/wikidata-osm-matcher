import logging
import math
from typing import Any
from clients.wikidata import WikidataItem, WikidataClient
from clients.overpass import OverpassClient
from matcher.base import Matcher, MatchCandidate
from config import ObjectTypeConfig


log = logging.getLogger(__name__)


class BBoxMatcher(Matcher[WikidataItem]):
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
        self.radius_km = config.overpass.bbox_radius_km

    async def find_matches(self, wikidata_item: WikidataItem) -> tuple[list[MatchCandidate[WikidataItem]], str | None]:
        if not wikidata_item.coord:
            log.warning(f"BBoxMatcher: no coordinates for {wikidata_item.label}")
            return [], None

        bbox = self._coord_to_bbox(wikidata_item.coord.lat, wikidata_item.coord.lon)
        log.debug(f"BBoxMatcher: bbox={bbox} for {wikidata_item.label} at {wikidata_item.coord.lat},{wikidata_item.coord.lon}")
        query = self.config.overpass.query.replace("{{bbox}}", bbox)

        raw_results = await self.overpass.query(query)
        osm_items = self.overpass.parse_results(raw_results)
        osm_timestamp = raw_results.get("osm3s", {}).get("timestamp_osm_base")

        candidates = []
        has_wikidata_match = False

        for osm in osm_items:
            wikidata_names = [wikidata_item.label] + wikidata_item.aliases
            sim = self.best_similarity(wikidata_names, osm.name)
            wikidata_match = osm.wikidata_tag == wikidata_item.qid
            is_leisure_bathing_place = osm.osm_type == "node" and osm.tags.get("leisure") == "bathing_place"

            distance_m = None
            if wikidata_item.coord and osm.lat and osm.lon:
                distance_m = self._haversine_distance(
                    wikidata_item.coord.lat, wikidata_item.coord.lon,
                    osm.lat, osm.lon
                )

            if wikidata_match:
                sim = 1.0
                has_wikidata_match = True

            needs_investigation = True
            if wikidata_match:
                needs_investigation = False
            elif is_leisure_bathing_place and distance_m is not None and distance_m < 25:
                sim = 0.9
                needs_investigation = False

            candidates.append(MatchCandidate(
                item=wikidata_item,
                similarity=sim,
                osm_id=osm.osm_id,
                osm_type=osm.osm_type,
                osm_name=osm.name,
                wikidata_match=wikidata_match,
                lat=osm.lat,
                lon=osm.lon,
                tags=osm.tags,
                needs_investigation=needs_investigation,
                distance_m=distance_m,
            ))

        if not has_wikidata_match:
            for c in candidates:
                if c.wikidata_match:
                    continue
                if c.osm_type == "node" and c.tags.get("leisure") == "bathing_place" and c.distance_m is not None and c.distance_m < 25:
                    continue
                c.needs_investigation = True

        candidates.sort(key=lambda c: (
            not c.wikidata_match,
            c.needs_investigation,
            c.distance_m if c.distance_m is not None else float('inf'),
        ))
        log.info(f"BBoxMatcher: found {len(candidates)} matches for {wikidata_item.label}, wikidata_match={has_wikidata_match}")
        for c in candidates:
            log.debug(f"  - {c.osm_type}/{c.osm_id} '{c.osm_name}' sim={c.similarity:.2f} dist={c.distance_m}m investigation={c.needs_investigation}")
        return candidates, osm_timestamp

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    def _coord_to_bbox(self, lat: float, lon: float) -> str:
        km_per_deg_lat = 111.32
        km_per_deg_lon = 111.32 * math.cos(math.radians(lat))
        delta_lat = self.radius_km / km_per_deg_lat
        delta_lon = self.radius_km / km_per_deg_lon
        south = lat - delta_lat
        north = lat + delta_lat
        west = lon - delta_lon
        east = lon + delta_lon
        return f"{south},{west},{north},{east}"
