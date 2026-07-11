import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from clients.wikidata import WikidataClient, WikidataItem, WikidataCoordinates
from clients.overpass import OverpassClient
from matcher import NameMatcher, BBoxMatcher
from config import get_config, get_all_configs, get_config_by_qid, get_wikidata_settings, get_osm_settings


log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["matcher"])


class ObjectTypeInfo(BaseModel):
    object_type: str
    label: str
    qid: str


class CandidateInfo(BaseModel):
    qid: str
    label: str
    country: str | None = None
    country_label: str | None = None
    division: str | None = None
    division_label: str | None = None
    coord: WikidataCoordinates | None = None


class CountryInfo(BaseModel):
    qid: str
    label: str
    count: int


class DivisionInfo(BaseModel):
    qid: str
    label: str
    count: int


class MatchInfo(BaseModel):
    osm_id: str
    osm_type: str
    osm_name: str
    similarity: float
    osm_url: str
    zoom: int


class MatchResponse(BaseModel):
    qid: str
    label: str
    matches: list[MatchInfo]
    coord: WikidataCoordinates | None = None


class ConfirmRequest(BaseModel):
    osm_id: str
    osm_type: str
    osm_name: str


class RejectRequest(BaseModel):
    reason: str | None = None


def get_matcher_type(config, wikidata: WikidataClient, overpass: OverpassClient):
    method = config.matching.method.lower()
    if method == "name":
        return NameMatcher(config, wikidata, overpass)
    elif method == "bbox":
        return BBoxMatcher(config, wikidata, overpass)
    else:
        raise ValueError(f"Unknown matching method: {method}")


@router.get("/types", response_model=list[ObjectTypeInfo])
async def list_object_types():
    configs = get_all_configs()
    return [
        ObjectTypeInfo(object_type=k, label=v.label, qid=v.qid)
        for k, v in configs.items()
    ]


@router.get("/types/{type_qid}/countries", response_model=list[CountryInfo])
async def get_countries(type_qid: str):
    log.info(f"Getting countries for type_qid={type_qid}")
    object_type, config = get_config_by_qid(type_qid)
    settings = get_wikidata_settings()
    async with WikidataClient(access_token=settings.access_token) as wikidata:
        results = await wikidata.sparql_query(config.wikidata.sparql_query)
        items = wikidata.parse_sparql_result(results, config.wikidata.label_property)

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

    query = config.wikidata.sparql_query
    query = query.rstrip().rstrip('}')
    query = query.replace('?item wdt:P17 ?country .', f'?item wdt:P17 wd:{country_qid} .')
    query += '}'

    async with WikidataClient(access_token=settings.access_token) as wikidata:
        results = await wikidata.sparql_query(query)
        items = wikidata.parse_sparql_result(results, config.wikidata.label_property)

        division_counts: dict[str, tuple[str, int]] = {}
        for item in items:
            div = item.division or "unknown"
            if div not in division_counts:
                division_counts[div] = (item.division_label or div, 0)
            division_counts[div] = (division_counts[div][0], division_counts[div][1] + 1)

        return [
            DivisionInfo(qid=qid, label=label, count=count)
            for qid, (label, count) in sorted(division_counts.items(), key=lambda x: -x[1][1])
        ]


@router.get("/types/{type_qid}/countries/{country_qid}/divisions/{division_qid}/candidates", response_model=list[CandidateInfo])
async def get_candidates_by_division(type_qid: str, country_qid: str, division_qid: str):
    log.info(f"Getting candidates for type_qid={type_qid}, country={country_qid}, division={division_qid}")
    object_type, config = get_config_by_qid(type_qid)
    settings = get_wikidata_settings()

    query = config.wikidata.sparql_query
    query = query.rstrip().rstrip('}')
    query = query.replace('?item wdt:P17 ?country .', f'?item wdt:P17 wd:{country_qid} .')
    query = query.replace('?item wdt:P131 ?division .', f'?item wdt:P131 wd:{division_qid} .')
    query += '}'

    async with WikidataClient(access_token=settings.access_token) as wikidata:
        results = await wikidata.sparql_query(query)
        items = wikidata.parse_sparql_result(results, config.wikidata.label_property)
        log.info(f"Returning {len(items)} candidates for {object_type} in {country_qid}/{division_qid}")
        return [
            CandidateInfo(
                qid=item.qid,
                label=item.label,
                country_label=item.country_label,
                division=item.division,
                division_label=item.division_label,
                coord=item.coord,
            )
            for item in items
        ]


@router.get("/types/{type_qid}/countries/{country_qid}/divisions/{division_qid}/candidates/{qid}/matches", response_model=MatchResponse)
async def get_matches(type_qid: str, country_qid: str, division_qid: str, qid: str):
    log.info(f"Finding matches for type_qid={type_qid}, country={country_qid}, division={division_qid}, qid={qid}")
    object_type, config = get_config_by_qid(type_qid)
    settings = get_wikidata_settings()
    osm_settings = get_osm_settings()
    async with WikidataClient(access_token=settings.access_token) as wikidata, OverpassClient() as overpass:
        item = await wikidata.get_item(qid)
        matcher = get_matcher_type(config, wikidata, overpass)
        matches = await matcher.find_matches(item)
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
                )
                for m in matches
            ],
            coord=item.coord,
        )


@router.post("/types/{type_qid}/countries/{country_qid}/divisions/{division_qid}/candidates/{qid}/confirm")
async def confirm_match(type_qid: str, country_qid: str, division_qid: str, qid: str, request: ConfirmRequest):
    object_type, config = get_config_by_qid(type_qid)
    settings = get_wikidata_settings()
    async with WikidataClient(access_token=settings.access_token) as wikidata:
        success = await wikidata.update_property(
            qid=qid,
            property_id=config.wikidata.update_property,
            value=request.osm_id,
        )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update Wikidata")
    return {"status": "ok"}


@router.post("/types/{type_qid}/countries/{country_qid}/divisions/{division_qid}/candidates/{qid}/reject")
async def reject_match(type_qid: str, country_qid: str, division_qid: str, qid: str, request: RejectRequest):
    object_type, config = get_config_by_qid(type_qid)
    settings = get_wikidata_settings()
    async with WikidataClient(access_token=settings.access_token) as wikidata:
        if config.wikidata.not_found_qualifier:
            success = await wikidata.add_not_found_marker(
                qid=qid,
                property_id=config.wikidata.not_found_property,
                qualifier_property=config.wikidata.not_found_qualifier,
            )
        else:
            success = await wikidata.update_property(
                qid=qid,
                property_id=config.wikidata.not_found_property,
                value="not found",
            )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update Wikidata")
    return {"status": "ok"}
