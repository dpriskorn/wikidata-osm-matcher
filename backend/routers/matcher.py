from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from clients.wikidata import WikidataClient, WikidataItem
from clients.overpass import OverpassClient
from matcher import NameMatcher, BBoxMatcher
from config import get_config, get_all_configs, get_wikidata_settings


router = APIRouter(prefix="/api", tags=["matcher"])


class ObjectTypeInfo(BaseModel):
    object_type: str
    label: str


class CandidateInfo(BaseModel):
    qid: str
    label: str
    country_label: str | None = None


class MatchInfo(BaseModel):
    osm_id: str
    osm_type: str
    osm_name: str
    similarity: float
    osm_url: str


class MatchResponse(BaseModel):
    qid: str
    label: str
    matches: list[MatchInfo]


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
        ObjectTypeInfo(object_type=k, label=v.label)
        for k, v in configs.items()
    ]


@router.get("/types/{object_type}/candidates", response_model=list[CandidateInfo])
async def get_candidates(object_type: str):
    config = get_config(object_type)
    settings = get_wikidata_settings()
    async with WikidataClient(access_token=settings.access_token) as wikidata:
        results = await wikidata.sparql_query(config.wikidata.sparql_query)
        items = wikidata.parse_sparql_result(results, config.wikidata.label_property)
        return [
            CandidateInfo(
                qid=item.qid,
                label=item.label,
                country_label=item.country_label,
            )
            for item in items
        ]


@router.get("/types/{object_type}/candidates/{qid}/matches", response_model=MatchResponse)
async def get_matches(object_type: str, qid: str):
    config = get_config(object_type)
    settings = get_wikidata_settings()
    async with WikidataClient(access_token=settings.access_token) as wikidata, OverpassClient() as overpass:
        item = await wikidata.get_item(qid)
        matcher = get_matcher_type(config, wikidata, overpass)
        matches = await matcher.find_matches(item)
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
                )
                for m in matches
            ],
        )


@router.post("/types/{object_type}/candidates/{qid}/confirm")
async def confirm_match(object_type: str, qid: str, request: ConfirmRequest):
    config = get_config(object_type)
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


@router.post("/types/{object_type}/candidates/{qid}/reject")
async def reject_match(object_type: str, qid: str, request: RejectRequest):
    config = get_config(object_type)
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
