import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.clients.wikidata import WikidataItem, WikidataCoordinates


client = TestClient(app)


class TestHealthEndpoint:
    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestListObjectTypes:
    def test_list_types(self):
        response = client.get("/api/types")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        types = [t["object_type"] for t in data]
        assert "hiking_trail" in types
        assert "bathing_place" in types

    def test_list_types_labels(self):
        response = client.get("/api/types")
        data = response.json()
        labels = [t["label"] for t in data]
        assert "Vandringsleder" in labels
        assert "Badplatser" in labels


class TestGetCandidates:
    @patch("backend.routers.matcher.WikidataClient")
    def test_get_candidates_success(self, mock_client_class):
        mock_client = AsyncMock()
        mock_client.sparql_query = AsyncMock(return_value=[])
        mock_client.parse_sparql_result = MagicMock(return_value=[])

        with patch("backend.routers.matcher.WikidataClient", return_value=mock_client):
            response = client.get("/api/types/hiking_trail/candidates")
            assert response.status_code == 200

    @patch("backend.routers.matcher.WikidataClient")
    def test_get_candidates_unknown_type(self, mock_client_class):
        response = client.get("/api/types/nonexistent/candidates")
        assert response.status_code == 500


class TestGetMatches:
    @patch("backend.routers.matcher.OverpassClient")
    @patch("backend.routers.matcher.WikidataClient")
    def test_get_matches_success(self, mock_wd_class, mock_op_class):
        mock_wd = AsyncMock()
        mock_wd.get_item = AsyncMock(return_value=WikidataItem(
            qid="Q123",
            label="Test",
            country="Q34",
            country_label="Sweden",
        ))
        mock_op = AsyncMock()
        mock_op.query = AsyncMock(return_value={"elements": []})
        mock_op.parse_results = MagicMock(return_value=[])

        with patch("backend.routers.matcher.WikidataClient", return_value=mock_wd):
            with patch("backend.routers.matcher.OverpassClient", return_value=mock_op):
                response = client.get("/api/types/hiking_trail/candidates/Q123/matches")
                assert response.status_code == 200
                data = response.json()
                assert data["qid"] == "Q123"
                assert data["label"] == "Test"

    @patch("backend.routers.matcher.WikidataClient")
    def test_get_matches_unknown_type(self, mock_client_class):
        response = client.get("/api/types/nonexistent/candidates/Q123/matches")
        assert response.status_code == 500


class TestConfirmMatch:
    @patch("backend.routers.matcher.WikidataClient")
    def test_confirm_success(self, mock_client_class):
        mock_client = AsyncMock()
        mock_client.update_property = AsyncMock(return_value=True)

        with patch("backend.routers.matcher.WikidataClient", return_value=mock_client):
            response = client.post(
                "/api/types/hiking_trail/candidates/Q123/confirm",
                json={"osm_id": "456", "osm_type": "relation", "osm_name": "Test"},
            )
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    @patch("backend.routers.matcher.WikidataClient")
    def test_confirm_wikidata_failure(self, mock_client_class):
        mock_client = AsyncMock()
        mock_client.update_property = AsyncMock(return_value=False)

        with patch("backend.routers.matcher.WikidataClient", return_value=mock_client):
            response = client.post(
                "/api/types/hiking_trail/candidates/Q123/confirm",
                json={"osm_id": "456", "osm_type": "relation", "osm_name": "Test"},
            )
            assert response.status_code == 500


class TestRejectMatch:
    @patch("backend.routers.matcher.WikidataClient")
    def test_reject_success(self, mock_client_class):
        mock_client = AsyncMock()
        mock_client.add_not_found_marker = AsyncMock(return_value=True)

        with patch("backend.routers.matcher.WikidataClient", return_value=mock_client):
            response = client.post(
                "/api/types/hiking_trail/candidates/Q123/reject",
                json={"reason": None},
            )
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    @patch("backend.routers.matcher.WikidataClient")
    def test_reject_wikidata_failure(self, mock_client_class):
        mock_client = AsyncMock()
        mock_client.add_not_found_marker = AsyncMock(return_value=False)

        with patch("backend.routers.matcher.WikidataClient", return_value=mock_client):
            response = client.post(
                "/api/types/hiking_trail/candidates/Q123/reject",
                json={"reason": None},
            )
            assert response.status_code == 500
