import pytest
from backend.clients.wikidata import WikidataClient, WikidataCoordinates


class TestWikidataClientHelpers:
    def test_extract_qid_valid_uri(self):
        client = WikidataClient()
        assert client._extract_qid("http://www.wikidata.org/entity/Q12345") == "Q12345"
        assert client._extract_qid("https://www.wikidata.org/entity/Q999") == "Q999"

    def test_extract_qid_no_qid(self):
        client = WikidataClient()
        assert client._extract_qid("http://example.com/item") is None

    def test_extract_qid_empty(self):
        client = WikidataClient()
        assert client._extract_qid("") is None
        assert client._extract_qid(None) is None

    def test_extract_qid_first_match(self):
        client = WikidataClient()
        assert client._extract_qid("http://example.com/Q123/entity/Q456") == "Q123"

    def test_parse_coord_valid(self):
        client = WikidataClient()
        result = client._parse_coord("Point(18.5 59.5)")
        assert result is not None
        assert result.lon == 18.5
        assert result.lat == 59.5

    def test_parse_coord_negative_coordinates(self):
        client = WikidataClient()
        result = client._parse_coord("Point(-122.5 37.5)")
        assert result is not None
        assert result.lon == -122.5
        assert result.lat == 37.5

    def test_parse_coord_invalid_format(self):
        client = WikidataClient()
        assert client._parse_coord("Invalid") is None
        assert client._parse_coord("Point()") is None
        assert client._parse_coord("") is None

    def test_parse_coord_wrong_prefix(self):
        client = WikidataClient()
        assert client._parse_coord("Point(18.5)") is None


class TestWikidataClientParseSparqlResult:
    def test_parse_basic_results(self):
        client = WikidataClient()
        results = [
            {
                "item": {"value": "http://www.wikidata.org/entity/Q123"},
                "itemLabel": {"value": "Test Item"},
            }
        ]
        items = client.parse_sparql_result(results, "itemLabel")
        assert len(items) == 1
        assert items[0].qid == "Q123"
        assert items[0].label == "Test Item"

    def test_parse_with_country(self):
        client = WikidataClient()
        results = [
            {
                "item": {"value": "http://www.wikidata.org/entity/Q123"},
                "itemLabel": {"value": "Test"},
                "country": {"value": "http://www.wikidata.org/entity/Q34"},
                "countryLabel": {"value": "Sweden"},
            }
        ]
        items = client.parse_sparql_result(results, "itemLabel")
        assert items[0].country == "Q34"
        assert items[0].country_label == "Sweden"

    def test_parse_with_coordinates(self):
        client = WikidataClient()
        results = [
            {
                "item": {"value": "http://www.wikidata.org/entity/Q123"},
                "itemLabel": {"value": "Test"},
                "coord": {"value": "Point(18.5 59.5)"},
            }
        ]
        items = client.parse_sparql_result(results, "itemLabel")
        assert items[0].coord is not None
        assert items[0].coord.lon == 18.5
        assert items[0].coord.lat == 59.5

    def test_parse_empty_results(self):
        client = WikidataClient()
        items = client.parse_sparql_result([], "itemLabel")
        assert len(items) == 0

    def test_parse_missing_qid(self):
        client = WikidataClient()
        results = [{"itemLabel": {"value": "Test"}}]
        items = client.parse_sparql_result(results, "itemLabel")
        assert len(items) == 0

    def test_parse_missing_label(self):
        client = WikidataClient()
        results = [{"item": {"value": "http://www.wikidata.org/entity/Q123"}}]
        items = client.parse_sparql_result(results, "itemLabel")
        assert items[0].label == ""
