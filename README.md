# Wikidata-OSM Matcher

A FastAPI + Vue/Vite application for matching Wikidata items to OpenStreetMap objects.

## Tech Stack

- **Backend**: FastAPI, Python 3.10+, rapidfuzz, PyYAML
- **Frontend**: Vue 3, Vite, TypeScript, Pinia, Axios

## Setup

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

## Features

- Match Wikidata items to OSM objects based on configurable rules
- Support for different entity types (hiking trails, bathing places, etc.)
- Fuzzy string matching using rapidfuzz
- REST API with CORS support

## Configuration

YAML configuration files in `configs/` define matching rules for different entity types.
