import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.clients.wikidata import WikidataItem, WikidataCoordinates
from backend.clients.overpass import OverpassResult


@pytest.fixture
def wikidata_item_stockholm():
    return WikidataItem(
        qid="Q12345",
        label="Stockholm",
        country="Q34",
        country_label="Sweden",
        coord=WikidataCoordinates(lat=59.5, lon=18.5),
    )


@pytest.fixture
def wikidata_item_no_coord():
    return WikidataItem(
        qid="Q67890",
        label="Some Trail",
        country="Q34",
        country_label="Sweden",
        coord=None,
    )


@pytest.fixture
def wikidata_item_norway():
    return WikidataItem(
        qid="Q111",
        label="North Cape Trail",
        country="Q35",
        country_label="Norway",
        coord=None,
    )


@pytest.fixture
def sample_sparql_results():
    return [
        {
            "item": {"type": "uri", "value": "http://www.wikidata.org/entity/Q12345"},
            "itemLabel": {"type": "literal", "value": "Stockholm"},
            "country": {"type": "uri", "value": "http://www.wikidata.org/entity/Q34"},
            "countryLabel": {"type": "literal", "value": "Sweden"},
        },
        {
            "item": {"type": "uri", "value": "http://www.wikidata.org/entity/Q67890"},
            "itemLabel": {"type": "literal", "value": "Oslo"},
            "country": {"type": "uri", "value": "http://www.wikidata.org/entity/Q35"},
            "countryLabel": {"type": "literal", "value": "Norway"},
        },
    ]


@pytest.fixture
def sample_sparql_with_coord():
    return [
        {
            "item": {"type": "uri", "value": "http://www.wikidata.org/entity/Q12345"},
            "itemLabel": {"type": "literal", "value": "Badplatsen"},
            "coord": {"type": "literal", "value": "Point(18.5 59.5)"},
            "country": {"type": "uri", "value": "http://www.wikidata.org/entity/Q34"},
            "countryLabel": {"type": "literal", "value": "Sweden"},
        },
    ]


@pytest.fixture
def sample_overpass_response():
    return {
        "elements": [
            {
                "type": "node",
                "id": 123,
                "lat": 59.5,
                "lon": 18.5,
                "tags": {"name": "Stockholm City", "name:sv": "Stockholm"},
            },
            {
                "type": "way",
                "id": 456,
                "center": {"lat": 59.6, "lon": 18.4},
                "tags": {"name": "Central Stockholm"},
            },
            {
                "type": "relation",
                "id": 789,
                "tags": {"name": "Kungsleden"},
            },
            {
                "type": "node",
                "id": 999,
                "lat": 59.4,
                "lon": 18.3,
                "tags": {"name:sv": "Only Swedish Name"},
            },
        ]
    }


@pytest.fixture
def sample_overpass_empty():
    return {"elements": []}


@pytest.fixture
def mock_wikidata_client():
    client = AsyncMock()
    client.sparql_query = AsyncMock(return_value=[])
    client.get_item = AsyncMock()
    client.update_property = AsyncMock(return_value=True)
    client.add_not_found_marker = AsyncMock(return_value=True)
    client.parse_sparql_result = MagicMock()
    return client


@pytest.fixture
def mock_overpass_client():
    client = AsyncMock()
    client.query = AsyncMock(return_value={"elements": []})
    client.parse_results = MagicMock(return_value=[])
    return client
