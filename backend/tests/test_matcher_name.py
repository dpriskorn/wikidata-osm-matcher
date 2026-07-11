import pytest
from backend.matcher.name import NameMatcher
from backend.config import get_config


class TestNameMatcherGetBbox:
    def setup_method(self):
        config = get_config("hiking_trail")
        self.matcher = NameMatcher(config, None, None)

    def test_country_in_map_returns_mapped_bbox(self):
        from backend.clients.wikidata import WikidataItem
        item = WikidataItem(qid="Q1", label="Test", country="Q34", country_label="Sweden")
        bbox = self.matcher._get_bbox(item)
        assert bbox == "55.5,10.5,69.5,24.5"

    def test_norway_bbox(self):
        from backend.clients.wikidata import WikidataItem
        item = WikidataItem(qid="Q1", label="Test", country="Q35", country_label="Norway")
        bbox = self.matcher._get_bbox(item)
        assert bbox == "58.5,4.5,70.5,31.5"

    def test_country_not_in_map_returns_fallback(self):
        from backend.clients.wikidata import WikidataItem
        item = WikidataItem(qid="Q1", label="Test", country="Q999", country_label="Unknown")
        bbox = self.matcher._get_bbox(item)
        assert bbox == "55.5,10.5,69.5,24.5"

    def test_no_country_returns_fallback(self):
        from backend.clients.wikidata import WikidataItem
        item = WikidataItem(qid="Q1", label="Test", country=None)
        bbox = self.matcher._get_bbox(item)
        assert bbox == "55.5,10.5,69.5,24.5"
