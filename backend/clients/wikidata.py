import logging
import re
import os
import requests
from datetime import datetime, timezone
from pydantic import BaseModel


log = logging.getLogger(__name__)

USER_AGENT = "osm-wikidata-matcher-neo 1.0 (https://github.com/anomalyco/opencode; User:So9q)"


class QleverIntegrator:
    endpoint: str = "https://qlever.cs.uni-freiburg.de/api/wikidata"
    session: requests.Session = requests.Session()

    SPARQL_PREFIXES = """
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX bd: <http://www.bigdata.com/rdf#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
"""

    def execute_query(self, query: str) -> dict:
        full_query = self.SPARQL_PREFIXES + query
        log.debug(f"SPARQL query:\n{full_query}\n---")
        params = {'query': full_query, 'action': 'json_export'}
        response = self.session.get(self.endpoint, params=params)
        response.raise_for_status()
        return response.json()


class WikidataCoordinates(BaseModel):
    lat: float
    lon: float


class WikidataItem(BaseModel):
    qid: str
    label: str
    aliases: list[str] = []
    country: str | None = None
    country_label: str | None = None
    division: str | None = None
    division_label: str | None = None
    coord: WikidataCoordinates | None = None
    badkartan: str | None = None
    naturkartan: str | None = None
    commons_p373: str | None = None
    commons_sitelink: str | None = None


class WikidataClient:
    def __init__(self) -> None:
        self._wbi = None
        self._qlever = QleverIntegrator()

    def __enter__(self) -> "WikidataClient":
        return self

    def __exit__(self, *args) -> None:
        pass

    def _get_wbi(self):
        if self._wbi is None:
            from wikibaseintegrator import WikibaseIntegrator
            from wikibaseintegrator.wbi_login import Login

            bot_user = os.getenv("WIKIMEDIA_BOT_USER", "")
            bot_pass = os.getenv("WIKIMEDIA_BOT_PASS", "")
            login = Login(user=bot_user, password=bot_pass)
            self._wbi = WikibaseIntegrator(login=login)
        return self._wbi

    def sparql_query(self, query: str) -> list[dict[str, any]]:
        log.debug("Executing SPARQL query via Qlever")
        data = self._qlever.execute_query(query)
        results = data.get("results", {}).get("bindings", [])
        log.debug(f"SPARQL returned {len(results)} raw results")
        return results

    def fetch_item_from_entity_api(self, qid: str) -> dict | None:
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        log.warning(f"EntityData API failed for {qid}: {response.status_code}")
        return None

    def get_item(self, qid: str) -> WikidataItem:
        # Use EntityData API for coordinates (more reliable than Qlever sync)
        entity_data = self.fetch_item_from_entity_api(qid)
        if not entity_data:
            raise ValueError(f"Item {qid} not found")

        item_data = entity_data.get('entities', {}).get(qid, {})
        claims = item_data.get('claims', {})

        coord = None
        if 'P625' in claims:
            coord_data = claims['P625'][0]['mainsnak']['datavalue']['value']
            coord = WikidataCoordinates(lat=coord_data['latitude'], lon=coord_data['longitude'])

        badkartan = None
        if 'P9615' in claims:
            badkartan = claims['P9615'][0]['mainsnak']['datavalue']['value']

        naturkartan = None
        if 'P10467' in claims:
            naturkartan = claims['P10467'][0]['mainsnak']['datavalue']['value']

        commons_p373 = None
        if 'P373' in claims:
            commons_p373 = claims['P373'][0]['mainsnak']['datavalue']['value']

        commons_sitelink = item_data.get('sitelinks', {}).get('commonswiki', {}).get('title')

        country = None
        if 'P17' in claims:
            country = claims['P17'][0]['mainsnak']['datavalue']['value']
            if isinstance(country, dict) and 'id' in country:
                country = country['id']
            else:
                country = None

        return WikidataItem(
            qid=qid,
            label="",
            aliases=[],
            country=country,
            coord=coord,
            badkartan=badkartan,
            naturkartan=naturkartan,
            commons_p373=commons_p373,
            commons_sitelink=commons_sitelink,
        )

    def update_property(self, qid: str, property_id: str, value: str) -> bool:
        from wikibaseintegrator import datatypes

        try:
            item = self._get_wbi().item.get(qid)
            claim = datatypes.ExternalID(prop_nr=property_id, value=value)
            item.claims.add(claim)
            item.write()
            return True
        except Exception as e:
            log.warning(f"Wikidata update failed: {e}")
            return False

    def add_not_found_marker(
        self,
        qid: str,
        property_id: str,
        qualifier_property: str,
        value: str = "not found",
    ) -> bool:
        from wikibaseintegrator import datatypes

        try:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            item = self._get_wbi().item.get(qid)
            qualifiers = datatypes.Time(
                prop_nr=qualifier_property,
                time=f"+{now}/11",
            )
            claim = datatypes.Item(
                prop_nr=property_id,
                value=value,
                qualifiers=[qualifiers],
            )
            item.claims.add(claim)
            item.write()
            return True
        except Exception as e:
            log.warning(f"Wikidata add_not_found_marker failed: {e}")
            return False

    def parse_sparql_result(self, results: list[dict[str, any]], label_variable: str) -> list[WikidataItem]:
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
                label=r.get(label_variable, {}).get("value", ""),
                country=self._extract_qid(r.get("country", {}).get("value")),
                country_label=r.get("countryLabel", {}).get("value"),
                division=self._extract_qid(r.get("division", {}).get("value")),
                division_label=r.get("divisionLabel", {}).get("value"),
                coord=coord,
                badkartan=r.get("badkartan", {}).get("value"),
                naturkartan=r.get("naturkartan", {}).get("value"),
                commons_p373=r.get("commons", {}).get("value"),
                commons_sitelink=r.get("commonsSitelink", {}).get("value"),
            ))
        log.info(f"Parsed {len(items)} Wikidata items from {len(results)} bindings")
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
