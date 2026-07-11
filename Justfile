api:
    cd backend && uvicorn main:app --reload --port 8000

vite:
    cd frontend && npm run dev

be-lint:
    cd backend && ruff check . && mypy .

fe-lint:
    cd frontend && npx vue-tsc --noEmit

be-test:
    cd backend && poetry run pytest -v

be-test-coverage:
    cd backend && poetry run pytest --cov=backend --cov-report=term-missing

fe-test:
    cd frontend && npm test -- --run

fe-test-watch:
    cd frontend && npm test

test: be-test fe-test

test-all: be-test-coverage fe-test
