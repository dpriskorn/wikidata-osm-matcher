install:
    cd backend && poetry install
    cd frontend && npm install --legacy-peer-deps

api:
    cd backend && LOG_LEVEL=DEBUG poetry run uvicorn main:app --reload --port 8000

vite:
    cd frontend && npm run dev

be-lint:
    cd backend && poetry run ruff check . && poetry run mypy .

fe-lint:
    cd frontend && npx vue-tsc --noEmit

be-test:
    cd backend && poetry run pytest --cov=. --cov-report=term-missing -v -x

be-test-coverage:
    cd backend && poetry run pytest --cov=backend --cov-report=term-missing --cov-report=html

fe-test:
    cd frontend && npm test -- --run

fe-test-watch:
    cd frontend && npm test

test: be-test fe-test

test-all: be-test-coverage fe-test
