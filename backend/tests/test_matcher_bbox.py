import pytest
import math
from backend.matcher.bbox import BBoxMatcher
from backend.config import get_config
from backend.clients.wikidata import WikidataCoordinates


class TestBBoxMatcherCoordToBbox:
    def setup_method(self):
        config = get_config("bathing_place")
        self.matcher = BBoxMatcher(config, None, None)

    def test_stockholm_coordinates(self):
        bbox = self.matcher._coord_to_bbox(59.5, 18.5)
        parts = bbox.split(",")
        assert len(parts) == 4
        south, west, north, east = map(float, parts)
        assert south < 59.5 < north
        assert west < 18.5 < east

    def test_equator_coordinates(self):
        bbox = self.matcher._coord_to_bbox(0.0, 0.0)
        parts = bbox.split(",")
        south, west, north, east = map(float, parts)
        assert south < 0 < north
        assert west < 0 < east
        delta_lat = north - south
        delta_lon = east - west
        assert abs(delta_lat - delta_lon) < 0.1

    def test_pole_coordinates(self):
        bbox = self.matcher._coord_to_bbox(89.0, 0.0)
        parts = bbox.split(",")
        south, west, north, east = map(float, parts)
        assert south < 89.0 < north

    def test_southern_hemisphere(self):
        bbox = self.matcher._coord_to_bbox(-33.0, 151.0)
        parts = bbox.split(",")
        south, west, north, east = map(float, parts)
        assert south < -33.0 < north
        assert west < 151.0 < east

    def test_bbox_string_format(self):
        bbox = self.matcher._coord_to_bbox(59.5, 18.5)
        assert "," in bbox
        parts = bbox.split(",")
        assert len(parts) == 4
        for p in parts:
            assert p.replace(".", "").replace("-", "").isdigit()


class TestBBoxMatcherFindMatches:
    def test_find_matches_no_coord_returns_empty(self):
        config = get_config("bathing_place")
        from backend.clients.wikidata import WikidataItem
        matcher = BBoxMatcher(config, None, None)
        item = WikidataItem(qid="Q1", label="No Coord", coord=None)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(matcher.find_matches(item))
        assert result == []
