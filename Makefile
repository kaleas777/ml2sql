.PHONY: install seed api ui test lint

install:
	python -m pip install -r requirements-dev.txt

seed:
	python -m scripts.seed_db

api:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

ui:
	streamlit run ui/streamlit_app.py

test:
	pytest -q

lint:
	ruff check .

