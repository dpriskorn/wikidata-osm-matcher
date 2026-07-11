import json
import logging
import httpx
from pathlib import Path
from typing import Any, Self
from pydantic import BaseModel


log = logging.getLogger(__name__)

USER_AGENT = "osm-wikidata-matcher-neo 1.0 (https://github.com/anomalyco/opencode)"

OVERPASS_MIRRORS = [
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

HEADERS = {"User-Agent": USER_AGENT}

DEBUG_FILE = Path(__file__).parent.parent / "debug.json"


class OverpassError(Exception):
    def __init__(self, message: str, last_url: str):
        super().__init__(message)
        self.message = message
        self.last_url = last_url


class OverpassResult(BaseModel):
    osm_id: str
    osm_type: str
    name: str
    wikidata_tag: str | None = None
    lat: float | None = None
    lon: float | None = None
    tags: dict[str, str] = {}


class OverpassClient:
    def __init__(self, timeout: float = 10.0) -> None:
        self._client = httpx.AsyncClient(timeout=timeout)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.aclose()

    async def query(self, overpass_query: str) -> dict[str, Any]:
        log.debug(f"Overpass QL query:\n{overpass_query}")
        last_error = None
        for url in OVERPASS_MIRRORS:
            try:
                log.info(f"Trying Overpass mirror: {url}")
                response = await self._client.post(
                    url,
                    data={"data": overpass_query},
                    headers=HEADERS,
                )
                if response.status_code == 504:
                    log.warning(f"Overpass mirror {url} returned 504 Gateway Timeout")
                    continue
                response.raise_for_status()
                result = response.json()
                debug_data = {"query": overpass_query, "response": result}
                with open(DEBUG_FILE, "w") as f:
                    json.dump(debug_data, f, indent=2)
                log.info(f"Saved debug to {DEBUG_FILE}")
                return result
            except httpx.HTTPStatusError as e:
                last_error = e
                log.warning(f"Overpass mirror {url} failed: {e.response.status_code}")
                continue
            except httpx.TimeoutException:
                log.warning(f"Overpass mirror {url} timed out")
                continue

        error_msg = f"All Overpass mirrors failed. Last error: {last_error}"
        if last_error:
            try:
                error_data = last_error.response.json()
                if "error" in error_data:
                    error_msg = f"Overpass API error: {error_data['error']}"
            except Exception:
                pass
        log.error(error_msg)
        raise OverpassError(error_msg, OVERPASS_MIRRORS[-1])

    def parse_results(self, data: dict[str, Any]) -> list[OverpassResult]:
        elements = data.get("elements", [])
        log.debug(f"Overpass returned {len(elements)} elements")
        results = []
        for el in elements:
            osm_type = el.get("type")
            osm_id = str(el.get("id"))
            tags = el.get("tags", {})

            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")

            name = tags.get("name", "") or tags.get("name:sv", "") or ""
            wikidata_tag = tags.get("wikidata")

            if osm_type in ("node", "way", "relation"):
                results.append(OverpassResult(
                    osm_id=osm_id,
                    osm_type=osm_type,
                    name=name,
                    wikidata_tag=wikidata_tag,
                    lat=lat,
                    lon=lon,
                    tags=tags,
                ))
        log.info(f"Parsed {len(results)} OSM objects from {len(elements)} elements")
        return results
