import httpx
import re
from typing import Any, Self
from datetime import datetime, timezone
from pydantic import BaseModel


WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"


class WikidataCoordinates(BaseModel):
    lat: float
    lon: float


class WikidataItem(BaseModel):
    qid: str
    label: str
    country: str | None = None
    country_label: str | None = None
    coord: WikidataCoordinates | None = None


class WikidataClient:
    def __init__(self, access_token: str = "") -> None:
        self._client = httpx.AsyncClient(timeout=30.0)
        self._access_token = access_token

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.aclose()

    async def sparql_query(self, query: str) -> list[dict[str, Any]]:
        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": "wikidata-osm-matcher/0.1.0",
        }
        response = await self._client.get(
            WIKIDATA_SPARQL_URL,
            params={"query": query, "format": "json"},
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("results", {}).get("bindings", [])

    async def get_item(self, qid: str) -> WikidataItem:
        query = f"""
        SELECT ?itemLabel ?country ?countryLabel WHERE {{
          BIND(wd:{qid} AS ?item)
          OPTIONAL {{ ?item wdt:P17 ?country }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "sv,en". }}
        }}
        """
        results = await self.sparql_query(query)
        if not results:
            raise ValueError(f"Item {qid} not found")
        r = results[0]
        return WikidataItem(
            qid=qid,
            label=r.get("itemLabel", {}).get("value", ""),
            country=self._extract_qid(r.get("country", {}).get("value")),
            country_label=r.get("countryLabel", {}).get("value"),
        )

    async def update_property(self, qid: str, property_id: str, value: str) -> bool:
        token = await self._get_edit_token()
        data = {
            "action": "wbcreateclaim",
            "entity": qid,
            "property": property_id,
            "value": f'"{value}"',
            "token": token,
            "format": "json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(WIKIDATA_API_URL, data=data)
            return response.status_code == 200

    async def add_not_found_marker(
        self,
        qid: str,
        property_id: str,
        qualifier_property: str,
    ) -> bool:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        token = await self._get_edit_token()
        data = {
            "action": "wbcreateclaim",
            "entity": qid,
            "property": property_id,
            "value": '"not found"',
            "qualifiers": qualifier_property,
            "qualifier-value": f'"{now}"',
            "token": token,
            "format": "json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(WIKIDATA_API_URL, data=data)
            return response.status_code == 200

    async def _get_edit_token(self) -> str:
        headers = {"Authorization": f"Bearer {self._access_token}"} if self._access_token else {}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                WIKIDATA_API_URL,
                params={"action": "query", "meta": "token", "format": "json"},
                headers=headers,
            )
            data = response.json()
            return data.get("query", {}).get("tokens", {}).get("csrfToken", "")

    def parse_sparql_result(self, results: list[dict[str, Any]], label_property: str) -> list[WikidataItem]:
        items: list[WikidataItem] = []
        for r in results:
            qid = self._extract_qid(r.get("item", {}).get("value", ""))
            if not qid:
                continue

            coord = None
            if "coord" in r and r["coord"]:
                coord_str = r["coord"].get("value", "")
                coord = self._parse_coord(coord_str)

            items.append(WikidataItem(
                qid=qid,
                label=r.get(label_property, {}).get("value", ""),
                country=self._extract_qid(r.get("country", {}).get("value")),
                country_label=r.get("countryLabel", {}).get("value"),
                coord=coord,
            ))
        return items

    def _extract_qid(self, uri: str) -> str | None:
        if not uri:
            return None
        match = re.search(r"(Q\d+)", uri)
        return match.group(1) if match else None

    def _parse_coord(self, coord_str: str) -> WikidataCoordinates | None:
        match = re.match(r"Point\(([^ ]+) ([^ ]+)\)", coord_str)
        if match:
            return WikidataCoordinates(lon=float(match.group(1)), lat=float(match.group(2)))
        return None
