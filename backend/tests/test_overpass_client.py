import pytest
from backend.clients.overpass import OverpassClient, OverpassResult


class TestOverpassClientParseResults:
    def test_parse_node_with_direct_coords(self):
        client = OverpassClient()
        data = {
            "elements": [
                {"type": "node", "id": 123, "lat": 59.5, "lon": 18.5, "tags": {"name": "Test"}}
            ]
        }
        results = client.parse_results(data)
        assert len(results) == 1
        assert results[0].osm_id == "123"
        assert results[0].osm_type == "node"
        assert results[0].name == "Test"
        assert results[0].lat == 59.5
        assert results[0].lon == 18.5

    def test_parse_way_with_center(self):
        client = OverpassClient()
        data = {
            "elements": [
                {
                    "type": "way",
                    "id": 456,
                    "center": {"lat": 59.6, "lon": 18.4},
                    "tags": {"name": "Way Test"},
                }
            ]
        }
        results = client.parse_results(data)
        assert len(results) == 1
        assert results[0].osm_id == "456"
        assert results[0].osm_type == "way"
        assert results[0].lat == 59.6
        assert results[0].lon == 18.4

    def test_parse_relation(self):
        client = OverpassClient()
        data = {
            "elements": [
                {"type": "relation", "id": 789, "tags": {"name": "Relation Test"}}
            ]
        }
        results = client.parse_results(data)
        assert len(results) == 1
        assert results[0].osm_id == "789"
        assert results[0].osm_type == "relation"

    def test_parse_with_swedish_name_fallback(self):
        client = OverpassClient()
        data = {
            "elements": [
                {
                    "type": "node",
                    "id": 999,
                    "lat": 59.5,
                    "lon": 18.5,
                    "tags": {"name:sv": "Swedish Name"},
                }
            ]
        }
        results = client.parse_results(data)
        assert results[0].name == "Swedish Name"

    def test_parse_empty_elements(self):
        client = OverpassClient()
        data = {"elements": []}
        results = client.parse_results(data)
        assert len(results) == 0

    def test_parse_missing_tags(self):
        client = OverpassClient()
        data = {"elements": [{"type": "node", "id": 123, "lat": 59.5, "lon": 18.5}]}
        results = client.parse_results(data)
        assert len(results) == 1
        assert results[0].name == ""

    def test_parse_invalid_type_skipped(self):
        client = OverpassClient()
        data = {
            "elements": [
                {"type": "invalid", "id": 123},
                {"type": "node", "id": 456, "lat": 59.5, "lon": 18.5, "tags": {"name": "Valid"}},
            ]
        }
        results = client.parse_results(data)
        assert len(results) == 1
        assert results[0].osm_id == "456"

    def test_parse_missing_coordinates(self):
        client = OverpassClient()
        data = {
            "elements": [
                {"type": "node", "id": 123, "tags": {"name": "No Coords"}}
            ]
        }
        results = client.parse_results(data)
        assert len(results) == 1
        assert results[0].lat is None
        assert results[0].lon is None

    def test_parse_multiple_elements(self):
        client = OverpassClient()
        data = {
            "elements": [
                {"type": "node", "id": 1, "lat": 59.5, "lon": 18.5, "tags": {"name": "A"}},
                {"type": "way", "id": 2, "lat": 59.6, "lon": 18.6, "tags": {"name": "B"}},
                {"type": "relation", "id": 3, "lat": 59.7, "lon": 18.7, "tags": {"name": "C"}},
            ]
        }
        results = client.parse_results(data)
        assert len(results) == 3
        assert all(r.name for r in results)
