.PHONY: install install-dev test app smoke lint embeddings train eval

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v --cov=model --cov-report=term-missing

app:
	streamlit run app/main.py

smoke:
	python scripts/verify_stage1.py
	PYTHONPATH=. python scripts/sync_cities.py

lint:
	ruff check model/ app/ scripts/

embeddings:
	PYTHONPATH=. python scripts/build_region_embeddings.py
	PYTHONPATH=. python scripts/build_photo_embeddings.py

train:
	PYTHONPATH=. python scripts/build_training_pairs.py
	python -m model.train_ranker

eval:
	python notebooks/01_synthetic_eval.py
