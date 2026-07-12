# Wikidata-OSM Matcher

Web application for matching Wikidata objects to OpenStreetMap with manual validation.

## Overview

The system fetches objects from Wikidata that are missing an OSM link (P402), presents candidates from the Overpass API for matching, and lets the user confirm or reject each match.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Vue/Vite  │────▶│   FastAPI   │────▶│  Wikidata   │
│  Frontend   │◀────│   Backend   │────▶│  (SPARQL)   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Overpass   │
                    │    API      │
                    └─────────────┘
```

## Object Types

Matching methods are configured per object type in YAML:

| Type | Method | Description |
|------|--------|-------------|
| `hiking_trail` | name | Name-based fuzzy match within country bbox (experimental) |
| `bathing_place` | bbox | Geographic search within 500m radius from coordinates |

## Configuration

YAML files in `configs/`:

```yaml
object_type: hiking_trail
label: "Hiking Trails"

wikidata:
  sparql_query: |     # SPARQL to fetch objects without P402
  overpass:
    query: |          # Overpass QL with {{bbox}} placeholder
  matching:
    method: name      # "name" or "bbox"
    similarity_threshold: 0.3
    exclude_words: [...]
```

## Installation

### Backend

```bash
cd backend
poetry install
poetry run uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/types` | List object types |
| GET | `/api/types/{type}/candidates` | Objects needing matching |
| GET | `/api/types/{type}/candidates/{qid}/matches` | OSM candidates for an object |
| POST | `/api/types/{type}/candidates/{qid}/confirm` | Confirm match |
| POST | `/api/types/{type}/candidates/{qid}/reject` | Mark as "no match" |

## Adding a New Object Type

1. Create `configs/{new_type}.yaml` with SPARQL query and Overpass query
2. Restart backend
3. New type appears in the web interface

## Matching

Matching combines fuzzy name matching, geographic proximity, and Wikidata tag detection.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Pydantic, httpx |
| Frontend | Vue 3, Vite, TypeScript, Pinia |
| Wikidata | SPARQL (Qlever) + EntityData API |
| OSM | Overpass API |
