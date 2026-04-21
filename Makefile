.PHONY: venv install dev docker-build docker-run

PYTHON         ?= python3.12
UPSTREAM_URL   ?= http://localhost:8081/image.jpg
MODEL_PATH     ?= yolov8s-worldv2.pt
WORLD_PROMPTS  ?= wheelie bin,car,person
CONF_THRESHOLD ?= 0.4

venv:
	$(PYTHON) -m venv .venv

install: venv
	./.venv/bin/pip install --upgrade pip
	./.venv/bin/pip install -r app/requirements.txt

dev:
	UPSTREAM_URL="$(UPSTREAM_URL)" \
	MODEL_PATH="$(MODEL_PATH)" \
	WORLD_PROMPTS="$(WORLD_PROMPTS)" \
	CONF_THRESHOLD=$(CONF_THRESHOLD) \
	./.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -t poormanyolocam:dev .

docker-run:
	docker run --rm -p 8000:8000 \
		-e UPSTREAM_URL="$(UPSTREAM_URL)" \
		-e WORLD_PROMPTS="$(WORLD_PROMPTS)" \
		-e CONF_THRESHOLD=$(CONF_THRESHOLD) \
		poormanyolocam:dev
