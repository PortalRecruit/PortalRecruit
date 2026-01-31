SHELL := /bin/bash

VENV ?= $(HOME)/.venvs/PortalRecruit
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

.PHONY: help venv install install-gpu doctor run dashboard test clean

help:
	@echo "Targets:"
	@echo "  venv        - create venv at $(VENV) using python3.13 (skips if exists)"
	@echo "  install     - install deps using CPU torch wheels (default)"
	@echo "  install-gpu - install deps assuming you already installed CUDA-enabled torch"
	@echo "  doctor      - run sanity checks"
	@echo "  run         - run run_portalrecruit.py"
	@echo "  dashboard   - run streamlit dashboard"
	@echo "  test        - run pytest (if present)"
	@echo "  clean       - remove local python caches"

venv:
	@if [[ -d "$(VENV)" ]]; then \
		echo "Venv exists at $(VENV) (set FORCE_RECREATE=1 to recreate)"; \
		if [[ "${FORCE_RECREATE:-0}" == "1" ]]; then rm -rf "$(VENV)"; else exit 0; fi; \
	fi
	python3.13 -m venv "$(VENV)"
	"$(PIP)" install -U pip

install: venv
	# CPU wheels prevent pulling multi-GB CUDA packages by default.
	"$(PIP)" install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
	"$(PIP)" install -r requirements.txt

install-gpu: venv
	@echo "NOTE: install-gpu does not pick a CUDA build. Install torch per PyTorch docs first."
	"$(PIP)" install -r requirements.txt

doctor:
	"$(PY)" scripts/doctor.py

run:
	"$(PY)" run_portalrecruit.py

dashboard:
	"$(VENV)/bin/streamlit" run src/dashboard/Home.py

test:
	"$(VENV)/bin/pytest" -q || true

clean:
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	find . -name '*.pyc' -delete
