import logging
import re
import os
from datetime import datetime, timezone
from pydantic import BaseModel
from wikibaseintegrator import wbi_helpers
from wikibaseintegrator.wbi_config import config as wbi_config


log = logging.getLogger(__name__)

USER_AGENT = "osm-wikidata-matcher-neo 1.0 (https://github.com/anomalyco/opencode)"
wbi_config["USER_AGENT"] = USER_AGENT
wbi_config["MEDIAWIKI_API_URL"] = "https://www.wikidata.org/w/api.php"


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


class WikidataClient:
    def __init__(self) -> None:
        self._wbi = None

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
        log.debug("Executing SPARQL query via wikibaseintegrator")
        data = wbi_helpers.execute_sparql_query(query)
        results = data.get("results", {}).get("bindings", [])
        log.debug(f"SPARQL returned {len(results)} raw results")
        return results

    def get_item(self, qid: str) -> WikidataItem:
        query = f"""
        SELECT ?itemLabel ?country ?countryLabel ?coord ?alias ?badkartan WHERE {{
          BIND(wd:{qid} AS ?item)
          OPTIONAL {{ ?item wdt:P17 ?country }}
          OPTIONAL {{ ?item wdt:P625 ?coord }}
          OPTIONAL {{ ?item wdt:P9615 ?badkartan }}
          OPTIONAL {{ ?item skos:altLabel ?alias FILTER(LANG(?alias) = "sv") }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "sv,en". }}
        }}
        """
        results = self.sparql_query(query)
        if not results:
            raise ValueError(f"Item {qid} not found")

        r = results[0]
        coord = None
        if coord_str := r.get("coord", {}).get("value"):
            coord = self._parse_coord(coord_str)

        aliases = []
        for result in results:
            if alias := result.get("alias", {}).get("value"):
                aliases.append(alias)

        return WikidataItem(
            qid=qid,
            label=r.get("itemLabel", {}).get("value", ""),
            aliases=aliases,
            country=self._extract_qid(r.get("country", {}).get("value")),
            country_label=r.get("countryLabel", {}).get("value"),
            coord=coord,
            badkartan=r.get("badkartan", {}).get("value"),
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

    def parse_sparql_result(self, results: list[dict[str, any]], label_property: str) -> list[WikidataItem]:
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
                division=self._extract_qid(r.get("division", {}).get("value")),
                division_label=r.get("divisionLabel", {}).get("value"),
                coord=coord,
                badkartan=r.get("badkartan", {}).get("value"),
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
