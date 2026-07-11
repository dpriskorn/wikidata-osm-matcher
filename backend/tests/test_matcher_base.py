import pytest
from backend.matcher.base import Matcher, MatchCandidate
from backend.clients.wikidata import WikidataItem


class ConcreteMatcher(Matcher[WikidataItem]):
    async def find_matches(self, wikidata_item: WikidataItem):
        return []


class TestMatcherCleanName:
    def setup_method(self):
        self.matcher = ConcreteMatcher(exclude_words=["trail", "led", "the"], threshold=0.3)

    def test_clean_name_lowercase(self):
        result = self.matcher.clean_name("HELLO WORLD")
        assert result == "hello world"

    def test_clean_name_replaces_separators(self):
        result = self.matcher.clean_name("test-name,here:another-one")
        assert result == "test name here another one"

    def test_clean_name_removes_exclude_words(self):
        result = self.matcher.clean_name("hiking trail is the led")
        assert result == "hiking is"

    def test_clean_name_removes_multiple_exclude_words(self):
        result = self.matcher.clean_name("trail led the")
        assert result == ""

    def test_clean_name_empty_after_exclusions(self):
        result = self.matcher.clean_name("trail")
        assert result == ""

    def test_clean_name_collapse_spaces(self):
        result = self.matcher.clean_name("hello    world")
        assert result == "hello world"

    def test_clean_name_strip_whitespace(self):
        result = self.matcher.clean_name("  hello world  ")
        assert result == "hello world"

    def test_clean_name_empty_input(self):
        result = self.matcher.clean_name("")
        assert result == ""

    def test_clean_name_unicode(self):
        result = self.matcher.clean_name("kungsleden är fin")
        assert "kungsleden" not in result
        assert "är" in result
        assert "fin" in result


class TestMatcherSimilarity:
    def setup_method(self):
        self.matcher = ConcreteMatcher(exclude_words=["trail"], threshold=0.3)

    def test_similarity_identical(self):
        sim = self.matcher.similarity("stockholm", "stockholm")
        assert sim == 1.0

    def test_similarity_case_insensitive(self):
        sim = self.matcher.similarity("STOCKHOLM", "stockholm")
        assert sim == 1.0

    def test_similarity_similar_words(self):
        sim = self.matcher.similarity("stockholm", "stockholme")
        assert sim > 0.8

    def test_similarity_different_words(self):
        sim = self.matcher.similarity("stockholm", "oslo")
        assert sim < 1.0

    def test_similarity_empty_strings(self):
        sim = self.matcher.similarity("", "")
        assert sim == 1.0

    def test_similarity_one_empty(self):
        sim = self.matcher.similarity("stockholm", "")
        assert sim < 1.0

    def test_similarity_with_exclude_words(self):
        sim = self.matcher.similarity("hiking trail", "hiking path")
        assert "trail" not in self.matcher.clean_name("hiking trail")
        assert "trail" not in self.matcher.clean_name("hiking path")


class TestMatchCandidate:
    def test_osm_url_node(self):
        candidate = MatchCandidate(
            item=WikidataItem(qid="Q1", label="Test"),
            similarity=0.8,
            osm_id="123",
            osm_type="node",
            osm_name="Test",
        )
        assert candidate.osm_url == "https://www.openstreetmap.org/N/123"

    def test_osm_url_way(self):
        candidate = MatchCandidate(
            item=WikidataItem(qid="Q1", label="Test"),
            similarity=0.8,
            osm_id="456",
            osm_type="way",
            osm_name="Test",
        )
        assert candidate.osm_url == "https://www.openstreetmap.org/W/456"

    def test_osm_url_relation(self):
        candidate = MatchCandidate(
            item=WikidataItem(qid="Q1", label="Test"),
            similarity=0.8,
            osm_id="789",
            osm_type="relation",
            osm_name="Test",
        )
        assert candidate.osm_url == "https://www.openstreetmap.org/R/789"
