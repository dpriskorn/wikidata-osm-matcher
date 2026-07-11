import pytest
from backend.config import (
    ObjectTypeConfig,
    WikidataConfig,
    OverpassQuery,
    MatchingConfig,
    get_all_configs,
    get_config,
)


class TestObjectTypeConfig:
    def test_valid_hiking_trail_config(self):
        config = get_config("hiking_trail")
        assert config.object_type == "hiking_trail"
        assert config.label == "Vandringsleder"
        assert config.wikidata.update_property == "P402"
        assert config.matching.method == "name"
        assert config.matching.similarity_threshold == 0.3

    def test_valid_bathing_place_config(self):
        config = get_config("bathing_place")
        assert config.object_type == "bathing_place"
        assert config.label == "Badplatser"
        assert config.wikidata.update_property == "P402"
        assert config.matching.method == "bbox"
        assert config.matching.similarity_threshold == 0.25

    def test_hiking_trail_exclude_words(self):
        config = get_config("hiking_trail")
        assert "trail" in config.matching.exclude_words
        assert "led" in config.matching.exclude_words
        assert "kungsleden" in config.matching.exclude_words

    def test_bathing_place_exclude_words(self):
        config = get_config("bathing_place")
        assert "badplats" in config.matching.exclude_words
        assert "strand" in config.matching.exclude_words

    def test_hiking_trail_bbox_mapping(self):
        config = get_config("hiking_trail")
        assert config.overpass.country_bbox_map is not None
        assert "Q34" in config.overpass.country_bbox_map
        assert config.overpass.fallback_bbox is not None

    def test_bathing_place_bbox_from_coord(self):
        config = get_config("bathing_place")
        assert config.overpass.bbox_from_coord is True
        assert config.overpass.bbox_radius_km == 1.0

    def test_get_all_configs_returns_dict(self):
        configs = get_all_configs()
        assert isinstance(configs, dict)
        assert "hiking_trail" in configs
        assert "bathing_place" in configs

    def test_get_config_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown object type"):
            get_config("nonexistent_type")


class TestWikidataConfig:
    def test_sparql_query_not_empty(self):
        config = get_config("hiking_trail")
        assert len(config.wikidata.sparql_query) > 0
        assert "SELECT" in config.wikidata.sparql_query
        assert "wdt:P31" in config.wikidata.sparql_query

    def test_update_properties(self):
        config = get_config("hiking_trail")
        assert config.wikidata.update_property == "P402"
        assert config.wikidata.not_found_property == "P9660"
        assert config.wikidata.not_found_qualifier == "P5017"


class TestMatchingConfig:
    def test_method_values(self):
        hiking = get_config("hiking_trail")
        bathing = get_config("bathing_place")
        assert hiking.matching.method == "name"
        assert bathing.matching.method == "bbox"

    def test_threshold_range(self):
        hiking = get_config("hiking_trail")
        bathing = get_config("bathing_place")
        assert 0.0 < hiking.matching.similarity_threshold <= 1.0
        assert 0.0 < bathing.matching.similarity_threshold <= 1.0
