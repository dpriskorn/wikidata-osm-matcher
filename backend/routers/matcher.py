import logging
import math
import re
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from clients.wikidata import WikidataClient, WikidataItem, WikidataCoordinates
from clients.overpass import OverpassClient, OverpassError
from matcher import NameMatcher, BBoxMatcher
from config import ObjectTypeConfig, get_all_configs, get_config_by_qid, get_osm_settings, get_wikidata_settings


log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["matcher"])


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def get_property_for_osm_type(config: ObjectTypeConfig, osm_type: str) -> str | None:
    if osm_type == "node":
        return config.wikidata.node_property
    elif osm_type == "way":
        return config.wikidata.way_property
    elif osm_type == "relation":
        return config.wikidata.relation_property
    return config.wikidata.update_property


def build_values_clause(qids: list[str]) -> str:
    """Build SPARQL VALUES clause like 'wd:Q123 wd:Q456 wd:Q789'"""
    return " ".join(f"wd:{qid}" for qid in qids)


class ObjectTypeInfo(BaseModel):
    object_type: str
    label: str
    qid: str
    experimental: bool = False


class CandidateInfo(BaseModel):
    qid: str
    label: str
    country: str | None = None
    country_label: str | None = None
    division: str | None = None
    division_label: str | None = None
    coord: WikidataCoordinates | None = None
    badkartan: str | None = None
    naturkartan: str | None = None
    commons_p373: str | None = None
    commons_sitelink: str | None = None


class CountryInfo(BaseModel):
    qid: str
    label: str
    count: int


class DivisionInfo(BaseModel):
    qid: str
    label: str
    count: int
    lat: float | None = None
    lon: float | None = None


class MatchInfo(BaseModel):
    osm_id: str
    osm_type: str
    osm_name: str
    similarity: float
    osm_url: str
    zoom: int
    wikidata_match: bool = False
    lat: float | None = None
    lon: float | None = None
    distance_m: float | None = None
    property_id: str | None = None
    tags: dict[str, str] = {}
    needs_investigation: bool = False


class MatchResponse(BaseModel):
    qid: str
    label: str
    matches: list[MatchInfo]
    coord: WikidataCoordinates | None = None
    error: str | None = None
    osm_timestamp: str | None = None
    badkartan: str | None = None
    naturkartan: str | None = None
    commons_p373: str | None = None
    commons_sitelink: str | None = None


class ConfirmRequest(BaseModel):
    osm_id: str
    osm_type: str
    osm_name: str


class RejectRequest(BaseModel):
    reason: str | None = None


def get_matcher_type(config, wikidata: WikidataClient, overpass: OverpassClient, radius_km: float | None = None):
    method = config.matching.method.lower()
    if method == "name":
        return NameMatcher(config, wikidata, overpass)
    elif method == "bbox":
        return BBoxMatcher(config, wikidata, overpass, radius_km=radius_km)
    else:
        raise ValueError(f"Unknown matching method: {method}")


@router.get("/types", response_model=list[ObjectTypeInfo])
async def list_object_types():
    configs = get_all_configs()
    return [
        ObjectTypeInfo(object_type=k, label=v.label, qid=v.qid, experimental=v.experimental)
        for k, v in configs.items()
    ]


@router.get("/types/{type_qid}/countries", response_model=list[CountryInfo])
async def get_countries(type_qid: str):
    log.info(f"Getting countries for type_qid={type_qid}")
    object_type, config = get_config_by_qid(type_qid)
    settings = get_wikidata_settings()
    with WikidataClient() as wikidata:
        results = wikidata.sparql_query(config.wikidata.candidates.sparql_query)
        items = wikidata.parse_sparql_result(results, config.wikidata.candidates.label_variable)

        country_counts: dict[str, tuple[str, int]] = {}
        for item in items:
            if item.country:
                if item.country not in country_counts:
                    country_counts[item.country] = (item.country_label or item.country, 0)
                country_counts[item.country] = (country_counts[item.country][0], country_counts[item.country][1] + 1)

        return [
            CountryInfo(qid=qid, label=label, count=count)
            for qid, (label, count) in sorted(country_counts.items(), key=lambda x: -x[1][1])
        ]


@router.get("/types/{type_qid}/countries/{country_qid}/divisions", response_model=list[DivisionInfo])
async def get_divisions(type_qid: str, country_qid: str):
    log.info(f"Getting divisions for type_qid={type_qid}, country={country_qid}")
    object_type, config = get_config_by_qid(type_qid)
    settings = get_wikidata_settings()

    with WikidataClient() as wikidata:
        candidates_query = config.wikidata.candidates.sparql_query
        candidates_query = candidates_query.rstrip().rstrip('}')
        candidates_query = candidates_query.replace('?item wdt:P17 ?country .', f'?item wdt:P17 wd:{country_qid} .')
        candidates_query += '}'

        results = wikidata.sparql_query(candidates_query)

        division_data: dict[str, dict] = {}
        for r in results:
            div_uri = r.get("division", {}).get("value", "")
            if not div_uri:
                continue
            div_qid = wikidata._extract_qid(div_uri)
            if not div_qid:
                continue

            div_label = r.get("divisionLabel", {}).get("value") or div_qid

            if div_qid not in division_data:
                division_data[div_qid] = {"label": div_label, "count": 0}
            division_data[div_qid]["count"] += 1

        division_qids = list(division_data.keys())
        if not division_qids:
            return []

        values_clause = build_values_clause(division_qids)
        div_coords_query = config.wikidata.division_coordinates.sparql_query
        div_coords_query = div_coords_query.replace('{?divisions_values}', f'{{{values_clause}}}')
        div_coords_query = div_coords_query.replace('?item wdt:P17 ?country .', f'?item wdt:P17 wd:{country_qid} .')

        coord_results = wikidata.sparql_query(div_coords_query)
        coord_map: dict[str, tuple[float, float]] = {}
        for r in coord_results:
            div_uri = r.get("division", {}).get("value", "")
            if not div_uri:
                continue
            div_qid = wikidata._extract_qid(div_uri)
            if not div_qid:
                continue
            coord_str = r.get("coord", {}).get("value", "")
            if coord_str:
                coord_match = re.match(r"Point\(([^ ]+) ([^ ]+)\)", coord_str)
                if coord_match:
                    lon, lat = float(coord_match.group(1)), float(coord_match.group(2))
                    coord_map[div_qid] = (lat, lon)

        for div_qid, data in division_data.items():
            if div_qid in coord_map:
                data["lat"], data["lon"] = coord_map[div_qid]
            else:
                data["lat"] = None
                data["lon"] = None

        return [
            DivisionInfo(qid=qid, label=data["label"], count=data["count"], lat=data.get("lat"), lon=data.get("lon"))
            for qid, data in sorted(division_data.items(), key=lambda x: -x[1]["count"])
        ]


@router.get("/types/{type_qid}/countries/{country_qid}/divisions/{division_qid}/candidates", response_model=list[CandidateInfo])
async def get_candidates_by_division(type_qid: str, country_qid: str, division_qid: str):
    log.info(f"Getting candidates for type_qid={type_qid}, country={country_qid}, division={division_qid}")
    object_type, config = get_config_by_qid(type_qid)
    settings = get_wikidata_settings()

    query = config.wikidata.candidates.sparql_query
    query = query.rstrip().rstrip('}')
    query = query.replace('?item wdt:P17 ?country .', f'?item wdt:P17 wd:{country_qid} .')
    query = query.replace('?item wdt:P131 ?division .', f'?item wdt:P131 wd:{division_qid} .')
    query += '}'

    with WikidataClient() as wikidata:
        results = wikidata.sparql_query(query)
        items = wikidata.parse_sparql_result(results, config.wikidata.candidates.label_variable)
        log.info(f"Returning {len(items)} candidates for {object_type} in {country_qid}/{division_qid}")
        return [
            CandidateInfo(
                qid=item.qid,
                label=item.label,
                country_label=item.country_label,
                division=item.division,
                division_label=item.division_label,
                coord=item.coord,
                badkartan=item.badkartan,
                naturkartan=item.naturkartan,
                commons_p373=item.commons_p373,
                commons_sitelink=item.commons_sitelink,
            )
            for item in items
        ]


@router.get("/types/{type_qid}/countries/{country_qid}/divisions/{division_qid}/candidates/{qid}/matches", response_model=MatchResponse)
async def get_matches(type_qid: str, country_qid: str, division_qid: str, qid: str, radius_km: float = 0.5):
    log.info(f"Finding matches for type_qid={type_qid}, country={country_qid}, division={division_qid}, qid={qid}, radius_km={radius_km}")
    object_type, config = get_config_by_qid(type_qid)
    settings = get_wikidata_settings()
    osm_settings = get_osm_settings()
    with WikidataClient() as wikidata, OverpassClient(timeout=config.overpass.timeout) as overpass:
        item = wikidata.get_item(qid)
        try:
            matcher = get_matcher_type(config, wikidata, overpass, radius_km=radius_km)
            matches, osm_timestamp = await matcher.find_matches(item)
            log.info(f"Returning {len(matches)} matches for {qid}")
            return MatchResponse(
                qid=qid,
                label=item.label,
                matches=[
                    MatchInfo(
                        osm_id=m.osm_id,
                        osm_type=m.osm_type,
                        osm_name=m.osm_name,
                        similarity=m.similarity,
                        osm_url=m.osm_url,
                        zoom=osm_settings.zoom,
                        wikidata_match=m.wikidata_match,
                        lat=m.lat,
                        lon=m.lon,
                        distance_m=round(haversine_distance(item.coord.lat, item.coord.lon, m.lat, m.lon)) if item.coord and m.lat and m.lon else None,
                        property_id=get_property_for_osm_type(config, m.osm_type),
                        tags=m.tags,
                        needs_investigation=m.needs_investigation,
                    )
                    for m in matches
                ],
                coord=item.coord,
                osm_timestamp=osm_timestamp,
                badkartan=item.badkartan,
                naturkartan=item.naturkartan,
                commons_p373=item.commons_p373,
                commons_sitelink=item.commons_sitelink,
            )
        except OverpassError as e:
            log.error(f"Overpass error for {qid}: {e.message}")
            return MatchResponse(
                qid=qid,
                label=item.label,
                matches=[],
                coord=item.coord,
                error=e.message,
                badkartan=item.badkartan,
                naturkartan=item.naturkartan,
                commons_p373=item.commons_p373,
                commons_sitelink=item.commons_sitelink,
            )


@router.post("/types/{type_qid}/countries/{country_qid}/divisions/{division_qid}/candidates/{qid}/confirm")
async def confirm_match(type_qid: str, country_qid: str, division_qid: str, qid: str, request: ConfirmRequest):
    object_type, config = get_config_by_qid(type_qid)
    prop = config.wikidata.node_property if request.osm_type == "node" else \
           config.wikidata.way_property if request.osm_type == "way" else \
           config.wikidata.relation_property if request.osm_type == "relation" else \
           config.wikidata.update_property
    if not prop:
        raise HTTPException(status_code=500, detail=f"No property configured for OSM type: {request.osm_type}")
    wikidata = WikidataClient()
    success = wikidata.update_property(
        qid=qid,
        property_id=prop,
        value=request.osm_id,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update Wikidata")
    return {"status": "ok"}


@router.post("/types/{type_qid}/countries/{country_qid}/divisions/{division_qid}/candidates/{qid}/reject")
async def reject_match(type_qid: str, country_qid: str, division_qid: str, qid: str, request: RejectRequest):
    object_type, config = get_config_by_qid(type_qid)
    wikidata = WikidataClient()
    if config.wikidata.not_found_qualifier:
        success = wikidata.add_not_found_marker(
            qid=qid,
            property_id=config.wikidata.not_found_property,
            qualifier_property=config.wikidata.not_found_qualifier,
            value="Q12013",
        )
    else:
        success = wikidata.update_property(
            qid=qid,
            property_id=config.wikidata.not_found_property,
            value="Q12013",
        )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update Wikidata")
    return {"status": "ok"}
