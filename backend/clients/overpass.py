import json
import logging
import httpx
import hashlib
from pathlib import Path
from typing import Any, Self
from pydantic import BaseModel


log = logging.getLogger(__name__)

USER_AGENT = "osm-wikidata-matcher-neo 1.0 (https://github.com/anomalyco/opencode)"

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
]

HEADERS = {"User-Agent": USER_AGENT}

DEBUG_DIR = Path(__file__).parent.parent / "debug"
DEBUG_DIR.mkdir(exist_ok=True)


def _get_debug_filename(query: str) -> str:
    query_hash = hashlib.md5(query.encode()).hexdigest()[:12]
    return f"overpass_{query_hash}.json"


class OverpassError(Exception):
    def __init__(self, message: str, last_url: str):
        super().__init__(message)
        self.message = message
        self.last_url = last_url


class OverpassResult(BaseModel):
    osm_id: str
    osm_type: str
    name: str
    lat: float | None = None
    lon: float | None = None


class OverpassClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=120.0)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.aclose()

    async def query(self, overpass_query: str) -> dict[str, Any]:
        log.debug(f"Overpass QL query:\n{overpass_query}")

        debug_file = DEBUG_DIR / _get_debug_filename(overpass_query)
        if debug_file.exists():
            log.info(f"Loading cached response from {debug_file}")
            with open(debug_file) as f:
                return json.load(f)

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
                with open(debug_file, "w") as f:
                    json.dump(result, f, indent=2)
                log.info(f"Saved Overpass response to {debug_file}")
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

            if osm_type in ("node", "way", "relation"):
                results.append(OverpassResult(
                    osm_id=osm_id,
                    osm_type=osm_type,
                    name=name,
                    lat=lat,
                    lon=lon,
                ))
        log.info(f"Parsed {len(results)} OSM objects from {len(elements)} elements")
        return results
