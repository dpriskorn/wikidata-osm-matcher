from pathlib import Path
from functools import lru_cache
import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class WikidataSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        extra="ignore",
        env_prefix="WIKIMEDIA_",
    )

    client_key: str = ""
    client_secret: str = ""
    access_token: str = ""


class OsmSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        extra="ignore",
        env_nested_delimiter="__",
    )

    zoom: int = 18


class WikidataConfig(BaseModel):
    sparql_query: str
    label_property: str
    update_property: str
    not_found_property: str
    not_found_qualifier: Optional[str] = None
    coord_property: Optional[str] = None


class OverpassQuery(BaseModel):
    query: str
    bbox_from_country: bool = False
    bbox_from_coord: bool = False
    bbox_radius_km: float = 1.0
    country_bbox_map: Optional[dict[str, str]] = None
    fallback_bbox: Optional[str] = None


class MatchingConfig(BaseModel):
    method: str
    similarity_threshold: float
    exclude_words: list[str]


class ObjectTypeConfig(BaseModel):
    object_type: str
    label: str
    qid: str
    wikidata: WikidataConfig
    overpass: OverpassQuery
    matching: MatchingConfig


@lru_cache
def get_configs_dir() -> Path:
    return Path(__file__).parent.parent / "configs"


_cached_configs: tuple[tuple[str, ObjectTypeConfig], ...] | None = None
_config_mtime: float = 0.0


def get_all_configs() -> dict[str, ObjectTypeConfig]:
    global _cached_configs, _config_mtime
    configs_dir = get_configs_dir()

    latest_mtime = max((f.stat().st_mtime for f in configs_dir.glob("*.yaml")), default=0)

    if _cached_configs is None or latest_mtime > _config_mtime:
        configs: dict[str, ObjectTypeConfig] = {}
        for yaml_file in configs_dir.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                obj_type = data["object_type"]
                configs[obj_type] = ObjectTypeConfig(**data)
        _cached_configs = tuple(configs.items())
        _config_mtime = latest_mtime

    return dict(_cached_configs)


def get_config(object_type: str) -> ObjectTypeConfig:
    configs = get_all_configs()
    if object_type not in configs:
        raise ValueError(f"Unknown object type: {object_type}")
    return configs[object_type]


def get_config_by_qid(type_qid: str) -> tuple[str, ObjectTypeConfig]:
    configs = get_all_configs()
    for obj_type, config in configs.items():
        if config.qid == type_qid:
            return obj_type, config
    raise ValueError(f"Unknown object type QID: {type_qid}")


@lru_cache
def get_wikidata_settings() -> WikidataSettings:
    return WikidataSettings()


@lru_cache
def get_osm_settings() -> OsmSettings:
    return OsmSettings()
